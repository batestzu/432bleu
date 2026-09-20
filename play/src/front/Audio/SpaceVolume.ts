import type { Readable } from "svelte/store";
import { derived } from "svelte/store";
import type { SpaceInterface } from "../Space/SpaceInterface";
import { megaphoneSpaceStore } from "../Stores/MegaphoneStore";
import { isMegaphoneSpace } from "./VolumeModel";
import { volumeMegaphoneStore, volumeProximityDiscussionStore } from "../Stores/PeerStore";

/**
 * Which slider governs a stream.
 *
 * This used to be decided by the TRANSPORT carrying the audio: RemotePeer read
 * the proximity slider, LiveKitParticipant read the megaphone slider. That
 * assumed LiveKit meant megaphone and WebRTC meant proximity, and it is not
 * true -- the back picks the transport by user count and pushes SWITCH_MESSAGE,
 * so a small room falls back to WebRTC and the megaphone ends up governed by
 * the proximity slider, while a large room can put proximity chat under the
 * megaphone slider.
 *
 * The question that actually matters is which SPACE the stream belongs to, so
 * that is what this asks. Falls back to the proximity slider when there is no
 * megaphone space, which is the common case.
 */
export function volumeStoreForSpace(space: SpaceInterface | undefined): Readable<number> {
    return derived(
        [megaphoneSpaceStore, volumeMegaphoneStore, volumeProximityDiscussionStore],
        ([$megaphoneSpace, $megaphoneVolume, $proximityVolume]) =>
            isMegaphoneSpace(space, $megaphoneSpace) ? $megaphoneVolume : $proximityVolume
    );
}
