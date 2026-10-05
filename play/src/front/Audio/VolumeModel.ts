/**
 * The volume model.
 *
 * One rule: a playback level is COMPUTED from independent inputs and never written
 * back over any of them. Everything here is pure so it can be reasoned about and
 * tested without a browser.
 *
 * This replaces a design where a single `volume` number was mutated in place by
 * whoever touched it last, which produced two bugs that were invisible on iOS
 * (where the write is discarded by the platform anyway) but broke Android and
 * desktop outright:
 *
 *   - the one-way ratchet: `setVolume(Math.min(saved, current))` at mount and on
 *     every zone entry meant the level could only ever descend. Sliding down once
 *     stuck forever, and a zone could never be louder than the one before it.
 *   - the talking duck: `volume *= 0.5` on entry and `*= 2.0` on exit. Moving the
 *     slider while ducked desynced the restore permanently, and two separate
 *     components ran the same mutation on the same shared object.
 *
 * Neither can occur here: the inputs are independent, and the output is derived.
 */

/**
 * How a map area's `volume` property combines with the user's slider.
 *
 * "ceiling" (current behaviour): the area caps the level. A user at 0.2 in a 0.35
 * area hears 0.2; a user at 1.0 hears 0.35. Every existing map was authored
 * against this.
 *
 * "multiplier": the area scales the level, so that same user at 0.2 hears 0.07.
 * More musical, and the only mode in which stepped-volume rings behave sensibly,
 * but it makes every existing area quieter and needs the maps re-tuned.
 *
 * Kept as a named switch because it changes how the room sounds and is therefore
 * a decision to be made by ear, not silently in a refactor.
 */
export type ZoneVolumeMode = "ceiling" | "multiplier";

export const ZONE_VOLUME_MODE: ZoneVolumeMode = "ceiling";

/** Level applied to zone audio while a nearby peer is talking. */
export const DUCK_FACTOR = 0.5;

/** Used when an area sets no volume, and outside any audio zone. */
export const NO_ZONE_ATTENUATION = 1;

export interface VolumeInputs {
    /** The slider, 0..1. Persisted. Written ONLY in response to the user. */
    userVolume: number;
    /** The current area's `volume` property, 0..1, or 1 outside any audio zone. */
    zoneFactor: number;
    /** True while zone audio should step out of the way of a talking peer. */
    ducked: boolean;
    /** The mute toggle. Independent of level, so un-muting restores it exactly. */
    muted: boolean;
}

/**
 * Clamps to the range a media element and a GainNode both accept.
 *
 * NaN becomes silence rather than propagating: assigning NaN to
 * HTMLMediaElement.volume throws, and a NaN gain silences the whole graph with
 * no clue where it came from. Infinities clamp normally, like any other
 * out-of-range number.
 */
export function clamp01(value: number): number {
    if (Number.isNaN(value)) {
        return 0;
    }
    return Math.min(1, Math.max(0, value));
}

/**
 * Combine the user's slider with the area's setting, per ZONE_VOLUME_MODE.
 */
export function combineZone(userVolume: number, zoneFactor: number, mode: ZoneVolumeMode = ZONE_VOLUME_MODE): number {
    const user = clamp01(userVolume);
    const zone = clamp01(zoneFactor);
    return mode === "multiplier" ? user * zone : Math.min(user, zone);
}

/**
 * The level to actually apply, from inputs that are never modified.
 *
 * Muting returns 0 rather than clearing the level, so the value to restore on
 * un-mute is still there to be read.
 */
export function effectiveVolume(inputs: VolumeInputs, mode: ZoneVolumeMode = ZONE_VOLUME_MODE): number {
    if (inputs.muted) {
        return 0;
    }
    const base = combineZone(inputs.userVolume, inputs.zoneFactor, mode);
    return clamp01(inputs.ducked ? base * DUCK_FACTOR : base);
}

/**
 * Whether volume can keep going through the media element, or has to be routed
 * through a GainNode.
 *
 * A platform that ignores writes to .volume always takes gain, whatever else it
 * offers. That is iOS, and it is passed in rather than inferred: iOS was assumed
 * to lack setSinkId, but the in-room diagnostic on 2026-10-05 (iPhone, iOS 26.6)
 * found setSinkId present, so the test below sent iPhones down the inert element
 * path and left every slider dead.
 *
 * Elsewhere the test is whether an output device can be chosen, because that is
 * the only thing the element path buys that the gain path cannot do: routing
 * through the graph silently disables setSinkId, and AudioContext.setSinkId()
 * does not exist in Firefox. Where setSinkId is absent -- Android Chrome --
 * there is nothing to protect.
 *
 * NOT tested by writing .volume and reading it back: iOS returns the value it
 * was given while changing nothing, so that probe reports success on exactly
 * the platform that is broken.
 */
export function canKeepElementVolumePath(
    element: Pick<HTMLAudioElement, "setSinkId">,
    ignoresElementVolume: boolean
): boolean {
    if (ignoresElementVolume) {
        return false;
    }
    return typeof element.setSinkId === "function";
}

/**
 * Whether, on the gain path, the element itself is muted.
 *
 * The graph only makes sound while its AudioContext is running. iOS creates the
 * context suspended until a tap, can drop it to "interrupted" (a phone call,
 * Siri), and Chrome does the same before the page has had a click. Muting the
 * element then would turn "the slider does nothing" into "nobody can be heard",
 * so the element carries the sound until the context runs and hands over to the
 * gain then. Never both at once: a suspended graph outputs nothing, so there is
 * no doubled audio.
 *
 * A level of zero mutes the element regardless. .muted is the one control iOS
 * honours on an element, so muting someone works there even before the context
 * runs.
 */
export function gainPathMutesElement(contextState: string, level: number): boolean {
    return contextState === "running" || level <= 0;
}

/**
 * Whether a stream's space is the megaphone space.
 *
 * Compared by identity: the megaphone space store holds the very object the
 * peer was constructed with. Names are not reliable -- the megaphone space name
 * is derived from the WAM's megaphone title, which the map editor can change.
 *
 * Two undefineds must NOT compare equal, or a peer with no space would be
 * treated as the megaphone whenever there is no megaphone space.
 */
export function isMegaphoneSpace<T>(space: T | undefined, megaphoneSpace: T | undefined): boolean {
    return space !== undefined && megaphoneSpace !== undefined && space === megaphoneSpace;
}

/**
 * Whether zone audio should currently duck. Derived, so it cannot drift out of
 * step with the talking state the way a stored `volumeReduced` flag did.
 */
export function shouldDuck(talking: boolean, decreaseWhileTalking: boolean): boolean {
    return talking && decreaseWhileTalking;
}
