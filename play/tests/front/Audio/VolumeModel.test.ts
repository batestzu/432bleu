import { describe, it, expect } from "vitest";
import {
    clamp01,
    combineZone,
    DUCK_FACTOR,
    effectiveVolume,
    NO_ZONE_ATTENUATION,
    shouldDuck,
    type VolumeInputs,
} from "../../../src/front/Audio/VolumeModel";

function inputs(overrides: Partial<VolumeInputs> = {}): VolumeInputs {
    return {
        userVolume: 1,
        zoneFactor: NO_ZONE_ATTENUATION,
        ducked: false,
        muted: false,
        ...overrides,
    };
}

describe("clamp01", () => {
    it("keeps values in range", () => {
        expect(clamp01(0.5)).toBe(0.5);
        expect(clamp01(-1)).toBe(0);
        expect(clamp01(2)).toBe(1);
    });

    it("treats a non-finite level as silence rather than passing NaN to the player", () => {
        expect(clamp01(NaN)).toBe(0);
        expect(clamp01(Infinity)).toBe(1);
    });
});

describe("combineZone", () => {
    it("caps the user level at the area's setting in ceiling mode", () => {
        expect(combineZone(1, 0.35, "ceiling")).toBe(0.35);
        expect(combineZone(0.2, 0.35, "ceiling")).toBe(0.2);
    });

    it("scales the user level in multiplier mode", () => {
        expect(combineZone(1, 0.35, "multiplier")).toBeCloseTo(0.35);
        expect(combineZone(0.2, 0.35, "multiplier")).toBeCloseTo(0.07);
    });

    it("leaves the user level alone outside an audio zone", () => {
        expect(combineZone(0.6, NO_ZONE_ATTENUATION, "ceiling")).toBe(0.6);
        expect(combineZone(0.6, NO_ZONE_ATTENUATION, "multiplier")).toBe(0.6);
    });
});

describe("shouldDuck", () => {
    it("ducks only while talking and only when the preference is on", () => {
        expect(shouldDuck(true, true)).toBe(true);
        expect(shouldDuck(true, false)).toBe(false);
        expect(shouldDuck(false, true)).toBe(false);
    });
});

describe("effectiveVolume", () => {
    it("returns the user level when nothing is attenuating it", () => {
        expect(effectiveVolume(inputs({ userVolume: 0.8 }))).toBe(0.8);
    });

    it("applies the duck without touching the user level", () => {
        const state = inputs({ userVolume: 0.8, ducked: true });
        expect(effectiveVolume(state)).toBeCloseTo(0.8 * DUCK_FACTOR);
        expect(state.userVolume).toBe(0.8);
    });

    it("reports silence when muted but keeps the level to restore", () => {
        const state = inputs({ userVolume: 0.8, muted: true });
        expect(effectiveVolume(state)).toBe(0);
        expect(state.userVolume).toBe(0.8);
    });

    it("combines the zone and the duck together", () => {
        expect(effectiveVolume(inputs({ userVolume: 1, zoneFactor: 0.35, ducked: true }))).toBeCloseTo(
            0.35 * DUCK_FACTOR
        );
    });
});

/**
 * The two defects this model exists to make impossible. Both reached a live
 * show; both are cheap to assert against forever.
 */
describe("regressions", () => {
    it("does not ratchet: leaving a quiet area restores the user's level", () => {
        const user = 0.9;

        const inQuietArea = effectiveVolume(inputs({ userVolume: user, zoneFactor: 0.2 }));
        expect(inQuietArea).toBe(0.2);

        // The old code wrote min(zone, current) back over the user's value, so
        // this returned 0.2 forever after.
        const afterLeaving = effectiveVolume(inputs({ userVolume: user, zoneFactor: NO_ZONE_ATTENUATION }));
        expect(afterLeaving).toBe(0.9);
    });

    it("does not ratchet: a louder area is reachable after a quieter one", () => {
        const user = 1;
        effectiveVolume(inputs({ userVolume: user, zoneFactor: 0.1 }));
        expect(effectiveVolume(inputs({ userVolume: user, zoneFactor: 0.8 }))).toBe(0.8);
    });

    it("does not desync the duck when the slider moves while ducked", () => {
        // Duck, then the user slides up, then the duck ends. The old code
        // restored by doubling whatever the value had become, so this drifted.
        expect(effectiveVolume(inputs({ userVolume: 0.4, ducked: true }))).toBeCloseTo(0.2);
        expect(effectiveVolume(inputs({ userVolume: 0.9, ducked: true }))).toBeCloseTo(0.45);
        expect(effectiveVolume(inputs({ userVolume: 0.9, ducked: false }))).toBe(0.9);
    });

    it("survives repeated duck cycles without drift", () => {
        const state = inputs({ userVolume: 0.6 });
        for (let i = 0; i < 50; i++) {
            effectiveVolume({ ...state, ducked: true });
            effectiveVolume({ ...state, ducked: false });
        }
        expect(effectiveVolume(state)).toBe(0.6);
    });
});
