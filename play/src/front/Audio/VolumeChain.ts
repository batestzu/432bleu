import { audioContextManager } from "../WebRtc/AudioContextManager";
import { isIOS } from "../WebRtc/DeviceUtils";
import { canKeepElementVolumePath, gainPathMutesElement } from "./VolumeModel";

/**
 * Applying a level to a peer's audio.
 *
 * There are two ways to do it and neither works everywhere:
 *
 *   - write HTMLMediaElement.volume. Simple, and it keeps setSinkId working so
 *     the listener can choose an output device. But iOS ignores the write
 *     entirely -- measured on iOS 18.7 / Safari 26.6, the property stores the
 *     value and playback is unchanged -- so every slider is inert there.
 *   - route the MediaStream through a GainNode. Works on iOS, measured on the
 *     same device. But once audio goes through the graph it leaves the
 *     element's own output path, so setSinkId silently stops having any effect,
 *     and AudioContext.setSinkId() does not exist in Firefox, which is what the
 *     venue machine runs.
 *
 * So iOS always takes gain, because nothing else works there -- and it cannot be
 * told apart by setSinkId, which the iPhone turned out to have (measured in the
 * room, 2026-10-05). Everywhere else the choice is made by asking the one
 * question that distinguishes the paths: is there an output-device selection to
 * preserve? Where setSinkId exists, keep the element path and the device picker
 * keeps working. Where it does not -- Android Chrome -- use gain, which is
 * harmless there.
 *
 * Note what is NOT used as the test. Reading HTMLMediaElement.volume back after
 * writing it returns the value you wrote even on iOS, where it does nothing, so
 * a read-back probe reports success on exactly the platform that is broken.
 */

export interface VolumeTarget {
    /** The element carrying the stream. Always present; it is what pulls the media. */
    element: HTMLAudioElement;
    /** The stream being played, needed to build a source node for the gain path. */
    stream: MediaStream | undefined;
}

export interface VolumeHandle {
    /** Apply a new level, 0..1. */
    setLevel(level: number): void;
    /** Point the chain at a new stream, rebuilding the graph if one is in use. */
    setStream(stream: MediaStream | undefined): void;
    /** Release nodes. Safe to call twice. */
    detach(): void;
    /** Which path was taken. Exposed for logging and tests, not for branching. */
    readonly usesGain: boolean;
}

/** Seconds for the gain ramp. Long enough not to click, short enough to feel instant. */
const RAMP_SECONDS = 0.05;

/**
 * Events that count as a user gesture for starting audio. iOS accepts a tap's
 * touchend or click, but not touchstart.
 */
const GESTURE_EVENTS = ["touchend", "click", "keydown"] as const;

/** The context currently waiting for a gesture, so listeners are added once. */
let contextAwaitingGesture: AudioContext | undefined;

/**
 * Get the shared context running: try now, and failing that on every gesture
 * until it is.
 *
 * Nothing else in the app resumes the shared context, and a resume() outside a
 * gesture is ignored where the page has not been tapped yet, so a single try is
 * not enough. Until it works the elements carry the sound (see
 * gainPathMutesElement), so waiting costs volume control, not audio.
 */
function resumeUntilRunning(context: AudioContext): void {
    if (context.state === "running" || context.state === "closed" || contextAwaitingGesture === context) {
        return;
    }
    contextAwaitingGesture = context;

    function stopListening() {
        for (const type of GESTURE_EVENTS) {
            document.removeEventListener(type, tryResume, true);
        }
        if (contextAwaitingGesture === context) {
            contextAwaitingGesture = undefined;
        }
    }
    function tryResume() {
        if (context.state === "closed") {
            stopListening();
            return;
        }
        context
            .resume()
            .then(() => {
                if (context.state === "running") {
                    stopListening();
                }
            })
            .catch(() => {
                // Refused without a gesture; the next one tries again.
            });
    }

    for (const type of GESTURE_EVENTS) {
        document.addEventListener(type, tryResume, { capture: true, passive: true });
    }
    tryResume();
}

/**
 * Attach volume control to an audio element, picking the path that works.
 *
 * On the gain path the element keeps playing: it stays the thing that pulls the
 * stream, while the audible copy comes out of the graph. Without the element
 * still running, Safari will not deliver samples to createMediaStreamSource at
 * all. It is muted only while the graph can actually be heard.
 */
export function attachVolume(target: VolumeTarget, initialLevel: number): VolumeHandle {
    const { element } = target;

    if (canKeepElementVolumePath(element, isIOS())) {
        let detached = false;
        element.muted = false;
        element.volume = initialLevel;
        return {
            usesGain: false,
            setLevel(level: number) {
                if (!detached) {
                    element.volume = level;
                }
            },
            setStream() {
                // Nothing to rebuild: the element plays the stream directly.
            },
            detach() {
                detached = true;
            },
        };
    }

    const context = audioContextManager.getContext();
    const gain = context.createGain();
    gain.gain.value = initialLevel;
    gain.connect(context.destination);

    let source: MediaStreamAudioSourceNode | undefined;
    let detached = false;

    const connectStream = (stream: MediaStream | undefined) => {
        if (source) {
            source.disconnect();
            source = undefined;
        }
        // A stream with no audio track would throw on createMediaStreamSource.
        if (!stream || stream.getAudioTracks().length === 0) {
            return;
        }
        source = context.createMediaStreamSource(stream);
        source.connect(gain);
    };

    // The element is the pump. While the graph is audible it is muted, so the
    // stream is not heard twice; while the graph is suspended it carries the
    // sound itself, at a level that is honoured everywhere except iOS.
    let level = initialLevel;
    const followContextState = () => {
        if (detached) {
            return;
        }
        element.muted = gainPathMutesElement(context.state, level);
        resumeUntilRunning(context);
    };
    element.volume = level;
    context.addEventListener("statechange", followContextState);
    followContextState();
    connectStream(target.stream);

    return {
        usesGain: true,
        setLevel(newLevel: number) {
            if (detached) {
                return;
            }
            level = newLevel;
            element.volume = level;
            element.muted = gainPathMutesElement(context.state, level);
            // setTargetAtTime rather than assigning .value: an abrupt change in
            // gain is an audible click.
            gain.gain.setTargetAtTime(level, context.currentTime, RAMP_SECONDS);
        },
        setStream(stream: MediaStream | undefined) {
            if (!detached) {
                connectStream(stream);
            }
        },
        detach() {
            if (detached) {
                return;
            }
            detached = true;
            context.removeEventListener("statechange", followContextState);
            if (source) {
                source.disconnect();
                source = undefined;
            }
            gain.disconnect();
            // The context is shared and deliberately not closed here.
        },
    };
}
