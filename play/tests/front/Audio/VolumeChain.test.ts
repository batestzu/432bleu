import { describe, it, expect } from "vitest";
import { canKeepElementVolumePath, isMegaphoneSpace } from "../../../src/front/Audio/VolumeModel";


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
        expect(canKeepElementVolumePath(elementWithSinkId(true))).toBe(true);
    });

    it("takes the gain path where there is no device selection to protect", () => {
        // iOS Safari and Android Chrome both lack setSinkId. iOS needs gain
        // because .volume is inert there; Android does not, but loses nothing.
        expect(canKeepElementVolumePath(elementWithSinkId(false))).toBe(false);
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
