/**
 * Keeps a zone's live audio stream playing through source dropouts.
 *
 * The venue's audio bed is an Icecast stream. When Icecast's source drops, even
 * for a second, every listener's connection is closed, and the mount answers 404
 * until the source returns. Measured in Firefox 158 and Chrome against a stand-in
 * Icecast (2026-11-10):
 *
 *   - already listening: the element plays out its buffer, then fires `ended`.
 *     The player used to treat that as "the sound is over" and hid itself.
 *     Note that the moment the connection closes, BOTH browsers change
 *     `duration` from Infinity to the length they happened to download (~10 s),
 *     so whether the source is live must be decided while it plays, not at
 *     `ended`.
 *   - (re)dialling during the outage: `error` (code 4) and play() rejects with
 *     NotSupportedError. That raised "Could not load sound" plus an "audio not
 *     allowed" bubble.
 *   - connection open but no data: Chrome waits forever; Firefox gives up after
 *     ~10 s with `error` (code 2) and `ended`.
 *
 * Nothing retried, so every one of these left the bed dead until a page reload.
 * This class turns all of them into a reconnect with backoff, for as long as the
 * visitor is still in the zone.
 */

/** Waits between attempts. The last value repeats for as long as the outage lasts. */
// Capped at 15 s: a retry against a 404 mount costs Icecast nothing, and the cap
// is the longest anyone waits for the bed once the source is back.
export const RETRY_DELAYS_MS = [1000, 2000, 4000, 8000, 15000];
/** No playback progress for this long, while we expect audio, counts as a dropout. */
export const STALL_TIMEOUT_MS = 15000;
/** Tell the visitor once the outage has outlasted this many attempts (1+2+4+8+15 = 30 s). */
export const WARN_AFTER_ATTEMPTS = 5;

/**
 * While it plays, a live stream reports an infinite duration (checked against
 * the real Icecast mount in both browsers); a file reports its length. `ended`
 * on a file is a real ending, `ended` on a live stream is a dropped connection.
 * Only meaningful during playback: see the header on what happens at `ended`.
 */
export function isLiveStream(duration: number): boolean {
    return duration === Infinity;
}

export class StreamBackoff {
    private attempts = 0;

    constructor(private readonly random: () => number = Math.random) {}

    /** The wait before the next attempt. Advances the attempt count. */
    next(): number {
        const base = RETRY_DELAYS_MS[Math.min(this.attempts, RETRY_DELAYS_MS.length - 1)];
        this.attempts++;
        // +-20 % so a whole room doesn't re-dial Icecast in the same instant.
        return Math.round(base * (0.8 + 0.4 * this.random()));
    }

    get attemptCount(): number {
        return this.attempts;
    }

    reset(): void {
        this.attempts = 0;
    }
}

export class StallWatch {
    private lastTime = -1;
    private lastProgressAt = 0;

    constructor(private readonly timeoutMs: number = STALL_TIMEOUT_MS) {}

    reset(now: number): void {
        this.lastTime = -1;
        this.lastProgressAt = now;
    }

    /** Feed it the element's currentTime; true once that has not moved for the timeout. */
    stalled(currentTime: number, now: number): boolean {
        if (currentTime !== this.lastTime) {
            this.lastTime = currentTime;
            this.lastProgressAt = now;
            return false;
        }
        return now - this.lastProgressAt >= this.timeoutMs;
    }
}

export interface LiveStreamKeeperHooks {
    /** Dial the stream again: set src, load(), play(). */
    redial: (src: string) => void;
    /** False while the visitor has paused or stopped the sound. Never reconnect then. */
    mayPlay: () => boolean;
    /** True while the player believes it is playing (not loading, not blocked by autoplay). */
    expectingAudio: () => boolean;
    /** A reconnect has been scheduled. */
    onReconnecting?: () => void;
    /** Called once per outage, after WARN_AFTER_ATTEMPTS attempts. */
    onLongOutage?: () => void;
    random?: () => number;
    now?: () => number;
    /** How often the stall check runs. */
    watchIntervalMs?: number;
}

export class LiveStreamKeeper {
    private src = "";
    private retryTimer: ReturnType<typeof setTimeout> | undefined;
    private readonly watchTimer: ReturnType<typeof setInterval>;
    private redialing = false;
    private warned = false;
    /** Seen with an infinite duration since the zone gave us this source. Survives re-dials. */
    private live = false;
    private readonly onDuration = (): void => {
        if (isLiveStream(this.el.duration)) this.live = true;
    };
    private readonly backoff: StreamBackoff;
    private readonly stall = new StallWatch();
    private readonly now: () => number;

    constructor(private readonly el: HTMLMediaElement, private readonly hooks: LiveStreamKeeperHooks) {
        this.backoff = new StreamBackoff(hooks.random);
        this.now = hooks.now ?? (() => Date.now());
        this.watchTimer = setInterval(() => this.checkStall(), hooks.watchIntervalMs ?? 2000);
        this.el.addEventListener("durationchange", this.onDuration);
    }

    /** The zone's source changed ("" when leaving). Any pending reconnect is for the old one. */
    setSource(src: string): void {
        this.cancel();
        this.src = src;
        this.live = false;
        this.redialing = false;
        this.backoff.reset();
        this.warned = false;
        this.stall.reset(this.now());
    }

    /** play() resolved. Returns true when this start was one of our reconnects. */
    playing(): boolean {
        const wasRedial = this.redialing;
        this.redialing = false;
        this.backoff.reset();
        this.warned = false;
        this.stall.reset(this.now());
        return wasRedial;
    }

    /** The element fired `ended`. True when it was a dropout and a reconnect is under way. */
    ended(): boolean {
        // Not this.el.duration: by now it has turned finite (see the header).
        if (!this.src || !this.live) return false;
        this.dropped("stream ended");
        return true;
    }

    /** The element errored, or play() failed for a reason other than autoplay or a superseding load. */
    failed(reason: string): void {
        this.dropped(reason);
    }

    /** The visitor stopped the sound. */
    stop(): void {
        this.cancel();
    }

    destroy(): void {
        this.cancel();
        clearInterval(this.watchTimer);
        this.el.removeEventListener("durationchange", this.onDuration);
    }

    get reconnectPending(): boolean {
        return this.retryTimer !== undefined;
    }

    private cancel(): void {
        if (this.retryTimer !== undefined) {
            clearTimeout(this.retryTimer);
            this.retryTimer = undefined;
        }
    }

    private dropped(reason: string): void {
        if (!this.src || !this.hooks.mayPlay()) return;
        // The error event and the rejected play() promise report the same failure: one attempt.
        if (this.retryTimer !== undefined) return;
        const delay = this.backoff.next();
        console.warn(
            `Zone audio: ${reason}; reconnecting in ${delay} ms (attempt ${this.backoff.attemptCount})`
        );
        this.hooks.onReconnecting?.();
        if (this.backoff.attemptCount >= WARN_AFTER_ATTEMPTS && !this.warned) {
            this.warned = true;
            this.hooks.onLongOutage?.();
        }
        const src = this.src;
        this.retryTimer = setTimeout(() => {
            this.retryTimer = undefined;
            if (src !== this.src || !this.hooks.mayPlay()) return;
            this.redialing = true;
            this.stall.reset(this.now());
            this.hooks.redial(src);
        }, delay);
    }

    private checkStall(): void {
        const now = this.now();
        // An element that has ended is not stalled: a file that finished stays
        // finished, and a live stream that ended is already handled by ended().
        if (
            !this.src ||
            this.el.ended ||
            this.retryTimer !== undefined ||
            !this.hooks.mayPlay() ||
            !this.hooks.expectingAudio()
        ) {
            this.stall.reset(now);
            return;
        }
        if (this.stall.stalled(this.el.currentTime, now)) {
            this.stall.reset(now);
            this.dropped(`no audio for ${STALL_TIMEOUT_MS / 1000} s`);
        }
    }
}
