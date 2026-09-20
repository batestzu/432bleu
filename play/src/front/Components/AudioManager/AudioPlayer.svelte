<script lang="ts">
    import type { Unsubscriber } from "svelte/store";
    import { get } from "svelte/store";
    import { onDestroy, onMount, tick } from "svelte";
    import type { Subscription } from "rxjs";
    import type { AudioManagerVolume } from "../../Stores/AudioManagerStore";
    import {
        audioManagerEffectiveVolumeStore,
        audioManagerPlayerState,
        audioManagerRetryPlaySubject,
        audioManagerFileStore,
        audioManagerVisibilityStore,
        audioManagerVolumeStore,
    } from "../../Stores/AudioManagerStore";
    import { LL } from "../../../i18n/i18n-svelte";
    import { localUserStore } from "../../Connection/LocalUserStore";
    import { actionsMenuStore } from "../../Stores/ActionsMenuStore";
    import { warningMessageStore } from "../../Stores/ErrorStore";
    import { activeSecondaryZoneActionBarStore } from "../../Stores/MenuStore";
    import { gameManager } from "../../Phaser/Game/GameManager";

    let HTMLAudioPlayer: HTMLAudioElement;
    let unsubscriberFileStore: Unsubscriber | null = null;
    let unsubscriberVolumeStore: Unsubscriber | null = null;
    let unsubscriberEffectiveVolume: Unsubscriber | null = null;
    let retryPlayStoreSubscription: Subscription | null = null;

    /**
     * Stop playback and let go of the media resource, without destroying the
     * element. Pausing alone is not enough: the zone audio is a live stream, so a
     * merely-paused player holds its connection open for the rest of the session.
     * Clearing the source and re-loading releases both the connection and the
     * browser's audio stream, and the element stays available for the next zone.
     */
    function releasePlayer(): void {
        if (!HTMLAudioPlayer) return;
        HTMLAudioPlayer.onprogress = null;
        HTMLAudioPlayer.pause();
        HTMLAudioPlayer.removeAttribute("src");
        HTMLAudioPlayer.load();
    }

    onMount(() => {
        // The store seeds itself from localStorage. Re-applying it here with a
        // Math.min against the live value is what used to ratchet the level down.

        unsubscriberFileStore = audioManagerFileStore.subscribe((src: string) => {
            (async () => {
                if (src == "") {
                    // Left the audio zone.
                    releasePlayer();
                    return;
                }
                await tick();
                HTMLAudioPlayer.src = src;
                HTMLAudioPlayer.load();
                HTMLAudioPlayer.loop = get(audioManagerVolumeStore).loop;
                HTMLAudioPlayer.volume = get(audioManagerEffectiveVolumeStore);
                HTMLAudioPlayer.muted = get(audioManagerVolumeStore).muted;
                tryPlay();
            })().catch(console.error);
        });
        // The level is read from the derived store; nothing here modifies it.
        // This subscriber used to multiply the shared volume by 0.5 and 2.0 in
        // place, which desynced permanently if the slider moved while ducked.
        unsubscriberEffectiveVolume = audioManagerEffectiveVolumeStore.subscribe((level: number) => {
            if (HTMLAudioPlayer) {
                HTMLAudioPlayer.volume = level;
            }
        });

        unsubscriberVolumeStore = audioManagerVolumeStore.subscribe((audioManager: AudioManagerVolume) => {
            if (HTMLAudioPlayer) {
                // Mute is carried by the element's own muted property, not by a
                // level of zero. The two are not interchangeable: iOS ignores
                // writes to .volume but still honours .muted, so this is the
                // only mute that works on a phone. The derived level goes to
                // zero as well, which costs nothing and covers the case where
                // the element is swapped underneath us.
                HTMLAudioPlayer.muted = audioManager.muted;
                HTMLAudioPlayer.loop = audioManager.loop;
                // Use paused attribute to manage audio
                if (audioManager.stopped) {
                    // Done with this sound: let go of the stream and its connection.
                    releasePlayer();
                } else if (audioManager.paused) {
                    // Paused is resumable, so keep the source loaded.
                    HTMLAudioPlayer.pause();
                } else {
                    // This used to force muted = false on every store change,
                    // two lines after setting it from the store, so the mute
                    // button never silenced zone audio at all.
                    HTMLAudioPlayer.play().catch(console.error);
                }
            }
        });
        retryPlayStoreSubscription = audioManagerRetryPlaySubject.subscribe(() => {
            (async () => {
                await tick();
                tryPlay();
            })().catch(console.error);
        });
    });

    onDestroy(() => {
        if (unsubscriberFileStore) {
            unsubscriberFileStore();
        }
        if (unsubscriberVolumeStore) {
            unsubscriberVolumeStore();
        }
        if (unsubscriberEffectiveVolume) {
            unsubscriberEffectiveVolume();
        }
        retryPlayStoreSubscription?.unsubscribe();
        audioManagerPlayerState.set(undefined);

        // Release the media resource explicitly. Detaching an element that has
        // played leaves its audio stream held until GC, and GC may never come --
        // see the note on the <audio> tag below.
        if (HTMLAudioPlayer) {
            HTMLAudioPlayer.onended = null;
            HTMLAudioPlayer.onerror = null;
            HTMLAudioPlayer.onloadstart = null;
        }
        releasePlayer();
    });

    function tryPlay() {
        if (!HTMLAudioPlayer) return;
        HTMLAudioPlayer.onended = () => {
            // Fixme: this is a hack to close menu when audio is ends without cut the sound
            actionsMenuStore.clear();
            // Audiovisilibily is set to false when audio is ended
            audioManagerVisibilityStore.set("hidden");
            if ($activeSecondaryZoneActionBarStore === "audio-manager") {
                activeSecondaryZoneActionBarStore.set(undefined);
            }
        };

        HTMLAudioPlayer.onloadstart = () => {
            audioManagerPlayerState.set("loading");
        };
        HTMLAudioPlayer.onerror = (event, error) => {
            console.error("HTMLAudioPlayer.onerror", event, error);
            const gameScene = gameManager.getCurrentGameScene();
            if (!gameScene) return;
            gameScene.CurrentPlayer.playText("audio-not-allowed", $LL.audio.manager.notAllowed(), 10000, () => {
                // When user click, the message could be removed
                gameScene.CurrentPlayer.destroyText("audio-not-allowed");
                // When the user clicks on the message, we try to play the audio again
                tryPlay();
            });
        };
        HTMLAudioPlayer.onprogress = () => {
            console.log("HTMLAudioPlayer.onprogress");
            if ($audioManagerPlayerState === "loading") audioManagerPlayerState.set("playing");
        };

        HTMLAudioPlayer.play()
            .then(() => {
                audioManagerPlayerState.set("playing");
                audioManagerVisibilityStore.set("visible");
                activeSecondaryZoneActionBarStore.set("audio-manager");
            })
            .catch((e) => {
                // If the audio is stopped, we don't play it
                if (get(audioManagerVolumeStore).stopped) {
                    console.warn("The audio is stopped, so we don't play it. Error: ", e);
                    return;
                }
                if (e instanceof DOMException && e.name === "NotAllowedError") {
                    // The browser does not allow audio to be played, possibly because the user has not interacted with the page yet.
                    // Let's ask the user to interact with the page first.
                    audioManagerPlayerState.set("not_allowed");
                    console.warn("The audio could not be played: ", e.name, e);

                    // Show the message to user the audio player
                    const gameScene = gameManager.getCurrentGameScene();
                    if (gameScene) {
                        gameScene.CurrentPlayer.playText(
                            "audio-not-allowed",
                            $LL.audio.manager.notAllowed(),
                            10000,
                            () => {
                                // When user click, the message could be removed
                                gameScene.CurrentPlayer.destroyText("audio-not-allowed");
                                // When the user clicks on the message, we try to play the audio again
                                tryPlay();
                            }
                        );
                    }
                } else {
                    audioManagerPlayerState.set("error");
                    warningMessageStore.addWarningMessage($LL.audio.manager.error());
                    console.error("The audio could not be played: ", e.name, e);
                    audioManagerVisibilityStore.set("error");
                }
            });
    }
</script>

<!--
    This element is deliberately NOT inside an {#if}. It must be created once and
    reused for the whole session.

    It used to be gated on the zone store, so every entry to an audio zone built a
    fresh <audio> and every exit destroyed it. Destroying a media element that has
    played does not release its audio stream: Firefox keeps one per abandoned
    element, corked, until a garbage collection that is not guaranteed to come.
    PulseAudio caps a sink at 256 streams, and past that NOTHING on the machine can
    play audio at all -- which is how the venue went silent and stayed silent.

    Measured on Firefox 154: recreating the element 20 times leaks 20 streams,
    permanently. Reusing one element across the same 20 entries holds at one.

    The gate is also what made HTMLAudioPlayer undefined while the store
    subscriptions still held a reference, producing the "audio player is not
    paused, so we create a new one" warnings and the pause() TypeError beneath them.
-->
<audio preload="auto" class="audio-manager-audioplayer" bind:this={HTMLAudioPlayer} />
