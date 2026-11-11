import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import {
    LiveStreamKeeper,
    RETRY_DELAYS_MS,
    STALL_TIMEOUT_MS,
    StreamBackoff,
    WARN_AFTER_ATTEMPTS,
    isLiveStream,
} from "../../../src/front/Audio/LiveStreamKeeper";

/**
 * The decision logic only. What the browsers actually fire when Icecast drops
 * was measured in real Firefox and Chrome, and the keeper was driven through
 * those same outages there (see the header of LiveStreamKeeper.ts).
 */

const SRC = "https://icecast.example/live.mp3";

function fakeElement(duration = Infinity) {
    const listeners: Record<string, Array<() => void>> = {};
    const el = {
        duration,
        currentTime: 0,
        ended: false,
        addEventListener: (type: string, fn: () => void) => {
            (listeners[type] ??= []).push(fn);
        },
        removeEventListener: (type: string, fn: () => void) => {
            listeners[type] = (listeners[type] ?? []).filter((f) => f !== fn);
        },
        /** The browser reporting a (new) duration. */
        reportDuration(d: number) {
            el.duration = d;
            (listeners["durationchange"] ?? []).forEach((f) => f());
        },
    };
    return el as unknown as HTMLMediaElement & {
        duration: number;
        currentTime: number;
        ended: boolean;
        reportDuration(d: number): void;
    };
}

describe("isLiveStream", () => {
    it("treats an infinite duration as live and anything else as a file", () => {
        expect(isLiveStream(Infinity)).toBe(true);
        expect(isLiveStream(20)).toBe(false);
        expect(isLiveStream(NaN)).toBe(false);
    });
});

describe("StreamBackoff", () => {
    it("walks the delay table and then holds at the last step", () => {
        const b = new StreamBackoff(() => 0.5); // no jitter
        const seen = Array.from({ length: RETRY_DELAYS_MS.length + 3 }, () => b.next());
        const last = RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - 1];
        expect(last).toBe(15000);
        expect(seen).toEqual([...RETRY_DELAYS_MS, last, last, last]);
    });

    it("jitters by at most 20 percent", () => {
        expect(new StreamBackoff(() => 0).next()).toBe(800);
        expect(new StreamBackoff(() => 1).next()).toBe(1200);
    });

    it("starts over after a reset", () => {
        const b = new StreamBackoff(() => 0.5);
        b.next();
        b.next();
        b.reset();
        expect(b.next()).toBe(1000);
        expect(b.attemptCount).toBe(1);
    });
});

describe("LiveStreamKeeper", () => {
    let paused: boolean;
    let state: string;
    let redial: Mock<(src: string) => void>;
    let onLongOutage: Mock<() => void>;
    let el: ReturnType<typeof fakeElement>;
    let keeper: LiveStreamKeeper;

    beforeEach(() => {
        vi.useFakeTimers();
        vi.spyOn(console, "warn").mockImplementation(() => undefined);
        paused = false;
        state = "playing";
        redial = vi.fn<(src: string) => void>();
        onLongOutage = vi.fn<() => void>();
        el = fakeElement();
        keeper = new LiveStreamKeeper(el, {
            redial,
            mayPlay: () => !paused,
            expectingAudio: () => state === "playing",
            // As in the player: a scheduled reconnect shows the spinner, which is not "playing".
            onReconnecting: () => {
                state = "loading";
            },
            onLongOutage,
            random: () => 0.5,
            now: () => Date.now(),
        });
        keeper.setSource(SRC);
        el.reportDuration(Infinity); // the stream starts playing
    });

    afterEach(() => {
        keeper.destroy();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it("reconnects a live stream that ends, instead of treating it as finished", () => {
        // What Firefox and Chrome do when Icecast closes the connection: the
        // duration turns finite (the bytes they got), then `ended` fires.
        el.reportDuration(10);
        el.ended = true;
        expect(keeper.ended()).toBe(true);
        vi.advanceTimersByTime(999);
        expect(redial).not.toHaveBeenCalled();
        vi.advanceTimersByTime(1);
        expect(redial).toHaveBeenCalledWith(SRC);
    });

    it("lets a file that ends stay ended", () => {
        keeper.setSource("https://example/chime.mp3");
        el.reportDuration(20);
        el.ended = true;
        expect(keeper.ended()).toBe(false);
        // Its clock has stopped for good; that must not read as a stall either.
        vi.advanceTimersByTime(60000);
        expect(redial).not.toHaveBeenCalled();
    });

    it("counts the error event and the rejected play() of one failure as one attempt", () => {
        keeper.failed("media error 4");
        keeper.failed("play() failed: NotSupportedError");
        vi.advanceTimersByTime(1000);
        expect(redial).toHaveBeenCalledTimes(1);
        // The next failure waits the second step, not the third.
        keeper.failed("media error 4");
        vi.advanceTimersByTime(1999);
        expect(redial).toHaveBeenCalledTimes(1);
        vi.advanceTimersByTime(1);
        expect(redial).toHaveBeenCalledTimes(2);
    });

    it("keeps trying through a long outage and warns exactly once", () => {
        for (let i = 0; i < 12; i++) {
            keeper.failed("media error 4");
            // The warning comes with the WARN_AFTER_ATTEMPTS-th attempt, not before.
            expect(onLongOutage).toHaveBeenCalledTimes(i + 1 < WARN_AFTER_ATTEMPTS ? 0 : 1);
            vi.advanceTimersByTime(30000);
        }
        expect(redial).toHaveBeenCalledTimes(12);
        expect(onLongOutage).toHaveBeenCalledTimes(1);
    });

    it("waits from the first step again once the stream plays", () => {
        keeper.failed("media error 4");
        vi.advanceTimersByTime(1000);
        keeper.failed("media error 4");
        vi.advanceTimersByTime(2000);
        expect(keeper.playing()).toBe(true); // that start was ours
        keeper.ended();
        vi.advanceTimersByTime(1000);
        expect(redial).toHaveBeenCalledTimes(3);
    });

    it("reports a zone entry's first start as not a reconnect", () => {
        expect(keeper.playing()).toBe(false);
    });

    it("forgets that a source was live when the zone hands over a different one", () => {
        keeper.setSource("https://example/chime.mp3");
        expect(keeper.ended()).toBe(false);
    });

    it("drops a pending reconnect when the visitor leaves the zone", () => {
        keeper.ended();
        keeper.setSource("");
        vi.advanceTimersByTime(60000);
        expect(redial).not.toHaveBeenCalled();
        expect(keeper.ended()).toBe(false);
    });

    it("drops a pending reconnect for the old source when the zone changes", () => {
        keeper.ended();
        keeper.setSource("https://icecast.example/other.mp3");
        vi.advanceTimersByTime(60000);
        expect(redial).not.toHaveBeenCalled();
    });

    it("never reconnects while the visitor has paused or stopped", () => {
        paused = true;
        keeper.failed("media error 2");
        vi.advanceTimersByTime(60000);
        expect(redial).not.toHaveBeenCalled();

        paused = false;
        keeper.ended();
        paused = true; // paused during the wait
        vi.advanceTimersByTime(1000);
        expect(redial).not.toHaveBeenCalled();

        paused = false;
        keeper.ended();
        keeper.stop();
        vi.advanceTimersByTime(60000);
        expect(redial).not.toHaveBeenCalled();
    });

    it("reconnects a stream that stops moving while it should be playing", () => {
        el.currentTime = 5;
        // Checks run every 2 s; the first one records t=2 s as the last progress.
        vi.advanceTimersByTime(STALL_TIMEOUT_MS + 1000);
        expect(keeper.reconnectPending).toBe(false);
        vi.advanceTimersByTime(2000);
        expect(keeper.reconnectPending).toBe(true);
        vi.advanceTimersByTime(1000);
        expect(redial).toHaveBeenCalledTimes(1);
    });

    it("leaves a stream alone while it is moving", () => {
        for (let t = 0; t < 60; t++) {
            el.currentTime = t;
            vi.advanceTimersByTime(1000);
        }
        expect(keeper.reconnectPending).toBe(false);
        expect(redial).not.toHaveBeenCalled();
    });

    it("does not count time spent loading or blocked by autoplay as a stall", () => {
        state = "not_allowed";
        vi.advanceTimersByTime(60000);
        state = "loading";
        vi.advanceTimersByTime(60000);
        expect(redial).not.toHaveBeenCalled();
    });
});
