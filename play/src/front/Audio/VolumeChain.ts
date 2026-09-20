import { audioContextManager } from "../WebRtc/AudioContextManager";
import { canKeepElementVolumePath } from "./VolumeModel";

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
 * So the choice is made by asking the one question that actually distinguishes
 * them: is there an output-device selection to preserve? Where setSinkId
 * exists, keep the element path and the device picker keeps working. Where it
 * does not -- iOS and Android Chrome both -- use gain, which is the only thing
 * that works on one of them and is harmless on the other.
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
 * Attach volume control to an audio element, picking the path that works.
 *
 * On the gain path the element is muted and kept playing: it stays the thing
 * that pulls the stream, while the audible copy comes out of the graph. Without
 * the element still running, Safari will not deliver samples to
 * createMediaStreamSource at all.
 */
export function attachVolume(target: VolumeTarget, initialLevel: number): VolumeHandle {
    const { element } = target;

    if (canKeepElementVolumePath(element)) {
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

    // The element is the pump. Muting it prevents hearing the stream twice,
    // once ungoverned through the element and once through the gain.
    element.muted = true;
    connectStream(target.stream);

    return {
        usesGain: true,
        setLevel(level: number) {
            if (detached) {
                return;
            }
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
            if (source) {
                source.disconnect();
                source = undefined;
            }
            gain.disconnect();
            // The context is shared and deliberately not closed here.
        },
    };
}
