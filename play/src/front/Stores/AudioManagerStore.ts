import type { Readable, Writable } from "svelte/store";
import { derived, get, writable } from "svelte/store";
import { Subject } from "rxjs";
import { localUserStore } from "../Connection/LocalUserStore";
import { effectiveVolume, NO_ZONE_ATTENUATION, shouldDuck } from "../Audio/VolumeModel";
import { videoStreamElementsStore } from "./PeerStore";
import { activeSecondaryZoneActionBarStore } from "./MenuStore";

/**
 * The inputs to the playback level, each owned by exactly one thing:
 * `userVolume` by the slider, `zoneFactor` by the map, `talking` by the peer
 * store. None of them is ever overwritten by the others -- the level itself is
 * derived, see audioManagerEffectiveVolumeStore and ../Audio/VolumeModel.
 */
export interface AudioManagerVolume {
    muted: boolean;
    /** The user's slider position. Persisted; only the user changes it. */
    userVolume: number;
    /** The current area's volume property, or 1 outside any audio zone. */
    zoneFactor: number;
    decreaseWhileTalking: boolean;
    loop: boolean;
    talking: boolean;
    paused: boolean;
    stopped: boolean;
}

function createAudioManagerVolumeStore() {
    const { subscribe, update } = writable<AudioManagerVolume>({
        muted: localUserStore.getAudioPlayerMuted(),
        // Seeded from storage here rather than in each component's onMount: two
        // components used to do it, and both applied a Math.min against the
        // current value, which is what made the level ratchet downwards.
        userVolume: localUserStore.getAudioPlayerVolume(),
        zoneFactor: NO_ZONE_ATTENUATION,
        decreaseWhileTalking: true,
        loop: false,
        talking: false,
        paused: false,
        stopped: false,
    });

    return {
        subscribe,
        setMuted: (newMute: boolean): void => {
            update((audioPlayerVolume: AudioManagerVolume) => {
                audioPlayerVolume.muted = newMute;
                return audioPlayerVolume;
            });
        },
        /** Called only in response to the user moving the slider. */
        setUserVolume: (newVolume: number): void => {
            update((audioPlayerVolume: AudioManagerVolume) => {
                audioPlayerVolume.userVolume = newVolume;
                return audioPlayerVolume;
            });
        },
        /** Called only by the map when entering or leaving an audio area. */
        setZoneFactor: (newZoneFactor: number): void => {
            update((audioPlayerVolume: AudioManagerVolume) => {
                audioPlayerVolume.zoneFactor = newZoneFactor;
                return audioPlayerVolume;
            });
        },
        setDecreaseWhileTalking: (newDecrease: boolean): void => {
            update((audioManagerVolume: AudioManagerVolume) => {
                audioManagerVolume.decreaseWhileTalking = newDecrease;
                return audioManagerVolume;
            });
        },
        setLoop: (newLoop: boolean): void => {
            update((audioManagerVolume: AudioManagerVolume) => {
                audioManagerVolume.loop = newLoop;
                return audioManagerVolume;
            });
        },
        setTalking: (newTalk: boolean): void => {
            update((audioManagerVolume: AudioManagerVolume) => {
                audioManagerVolume.talking = newTalk;
                return audioManagerVolume;
            });
        },
        // Function to pause the sound
        togglePause: (): void => {
            update((audioManagerVolume: AudioManagerVolume) => {
                audioManagerVolume.paused = !audioManagerVolume.paused;
                return audioManagerVolume;
            });
        },

        // Function to stop the sound
        stopSound: (newStopped: boolean): void => {
            update((audioManagerVolume: AudioManagerVolume) => {
                audioManagerVolume.stopped = newStopped;
                return audioManagerVolume;
            });
        },
    };
}

function createAudioManagerFileStore() {
    const { subscribe, update } = writable<string>("");

    return {
        subscribe,
        playAudio: (url: string | number | boolean, mapUrl: string, volume: number | undefined, loop = false): void => {
            update((file: string) => {
                const audioPath = String(url);

                file = new URL(audioPath, mapUrl).toString();

                // Record what the area asks for. It is combined with the user's
                // slider when the level is computed; it must never be written
                // over the slider, which is what the old Math.min did.
                audioManagerVolumeStore.setZoneFactor(volume ?? NO_ZONE_ATTENUATION);
                audioManagerVolumeStore.setLoop(loop);
                // Deliberately does NOT clear muted. `muted` is the user's own
                // setting; entering an area used to force it false, so a muted
                // visitor was un-muted by walking through a door. What stops
                // playback between areas is the file store going empty, not this
                // flag.
                audioManagerVolumeStore.stopSound(false);
                return file;
            });
        },
        unloadAudio: () => {
            update(() => {
                audioManagerVolumeStore.setLoop(false);
                audioManagerVolumeStore.setZoneFactor(NO_ZONE_ATTENUATION);
                // Nor does leaving an area mute the user. Clearing the file
                // store below is what releases the player.
                activeSecondaryZoneActionBarStore.set(undefined);
                return "";
            });
        },
    };
}

// Store deciding the visibility of the music icon in the action bar and its status
export const audioManagerVisibilityStore: Writable<"hidden" | "visible" | "disabledBySettings" | "error"> =
    writable("hidden");

export const audioManagerVolumeStore = createAudioManagerVolumeStore();

/**
 * The level to actually apply. Derived, so it recomputes when any input changes
 * and cannot be left stale by whichever component happened to run last.
 */
export const audioManagerEffectiveVolumeStore: Readable<number> = derived(
    audioManagerVolumeStore,
    ($volume) =>
        effectiveVolume({
            userVolume: $volume.userVolume,
            zoneFactor: $volume.zoneFactor,
            ducked: shouldDuck($volume.talking, $volume.decreaseWhileTalking),
            muted: $volume.muted,
        })
);

export const audioManagerFileStore = createAudioManagerFileStore();
export const audioManagerPlayerState: Writable<"loading" | "playing" | "not_allowed" | "error" | undefined> =
    writable(undefined);
// Store solely used to trigger a retry of the audio player (in case the browser blocked it the first time)
export const audioManagerRetryPlaySubject = new Subject<void>();

// Store for bubble sound preference
export const bubbleSoundStore = writable<"ding" | "wobble">(localUserStore.getBubbleSound());

// Not unsubscribing is ok, this is a singleton.
//eslint-disable-next-line svelte/no-ignored-unsubscribe
videoStreamElementsStore.subscribe((peerElements) => {
    audioManagerVolumeStore.setTalking(peerElements.length > 0);
});
