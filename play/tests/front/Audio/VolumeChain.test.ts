import { describe, it, expect } from "vitest";
import {
    canKeepElementVolumePath,
    gainPathMutesElement,
    isMegaphoneSpace,
} from "../../../src/front/Audio/VolumeModel";


/**
 * Only the decision logic is covered here. Building a real GainNode needs an
 * AudioContext, which is exactly the thing that behaves differently per
 * platform -- so that half is verified on hardware with the bench page rather
 * than against a mock that would agree with whatever we assumed.
 */

function elementWithSinkId(hasSinkId: boolean): Pick<HTMLAudioElement, "setSinkId"> {
    return (hasSinkId ? { setSinkId: () => Promise.resolve() } : {}) as unknown as HTMLAudioElement;
}

describe("canKeepElementVolumePath", () => {
    it("keeps the element path where an output device can be chosen", () => {
        // Desktop Firefox and Chrome: setSinkId exists and .volume works, so
        // routing through the graph would only cost the device picker.
        expect(canKeepElementVolumePath(elementWithSinkId(true), false)).toBe(true);
    });

    it("takes the gain path where there is no device selection to protect", () => {
        // Android Chrome lacks setSinkId. It does not need gain, but loses nothing.
        expect(canKeepElementVolumePath(elementWithSinkId(false), false)).toBe(false);
    });

    it("takes the gain path on iOS even though setSinkId exists there", () => {
        // The regression this guards: the in-room diagnostic on 2026-10-05
        // read "setSinkId: function" on an iPhone, so the setSinkId test alone
        // kept iPhones on the element path, where .volume writes do nothing.
        expect(canKeepElementVolumePath(elementWithSinkId(true), true)).toBe(false);
        expect(canKeepElementVolumePath(elementWithSinkId(false), true)).toBe(false);
    });
});

describe("gainPathMutesElement", () => {
    it("hands the sound to the gain once the context is running", () => {
        expect(gainPathMutesElement("running", 0.5)).toBe(true);
    });

    it("keeps the element audible whenever the graph cannot be heard", () => {
        // Muting the element here would make peers silent rather than merely
        // uncontrollable -- worse than the bug being fixed.
        expect(gainPathMutesElement("suspended", 0.5)).toBe(false);
        // iOS-only state after a phone call or Siri.
        expect(gainPathMutesElement("interrupted", 0.5)).toBe(false);
        expect(gainPathMutesElement("closed", 0.5)).toBe(false);
    });

    it("mutes the element at level zero even while it carries the sound", () => {
        // .muted works on iOS where .volume does not, so a muted peer stays
        // muted before the context is running.
        expect(gainPathMutesElement("suspended", 0)).toBe(true);
        expect(gainPathMutesElement("interrupted", 0)).toBe(true);
        expect(gainPathMutesElement("running", 0)).toBe(true);
    });
});

describe("isMegaphoneSpace", () => {
    const megaphone = { id: "megaphone" } as object;
    const proximity = { id: "proximity" } as object;

    it("matches the megaphone space by identity", () => {
        expect(isMegaphoneSpace(megaphone, megaphone)).toBe(true);
    });

    it("does not match a different space", () => {
        expect(isMegaphoneSpace(proximity, megaphone)).toBe(false);
    });

    it("is false when there is no megaphone space at all", () => {
        expect(isMegaphoneSpace(proximity, undefined)).toBe(false);
        expect(isMegaphoneSpace(megaphone, undefined)).toBe(false);
    });

    it("is false for a peer with no space rather than matching an absent one", () => {
        // Two undefineds must not compare equal and send proximity audio to the
        // megaphone slider.
        expect(isMegaphoneSpace(undefined, undefined)).toBe(false);
        expect(isMegaphoneSpace(undefined, megaphone)).toBe(false);
    });
});
