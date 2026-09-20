<svelte:options immutable={true} />

<script lang="ts">
    import { createEventDispatcher, onDestroy, onMount } from "svelte";
    import Debug from "debug";
    import * as Sentry from "@sentry/svelte";
    import type { Readable } from "svelte/store";
    import { attachVolume, type VolumeHandle } from "../../../Audio/VolumeChain";

    export let streamStore: Readable<MediaStream | undefined>;
    export let outputDeviceId: string | undefined = undefined;
    export let isBlocked: Readable<boolean>;

    const debug = Debug("AudioStream");

    const dispatch = createEventDispatcher<{
        selectOutputAudioDeviceError: void;
    }>();

    export let volume: Readable<number>;
    let audioElement: HTMLAudioElement;
    let volumeHandle: VolumeHandle | undefined;

    // Writing audioElement.volume directly is inert on iOS, so the level goes
    // through a chain that falls back to a GainNode where that is the case.
    // See ../../../Audio/VolumeChain.ts for why the path is chosen the way it is.
    function ensureVolumeHandle() {
        if (!audioElement || volumeHandle || destroyed) {
            return;
        }
        volumeHandle = attachVolume({ element: audioElement, stream }, $volume);
        debug("Volume path", volumeHandle.usesGain ? "gain" : "element");
    }

    $: {
        if (audioElement && !destroyed) {
            ensureVolumeHandle();
            volumeHandle?.setLevel($volume);
        }
    }

    let lastRequestedDeviceId: string | undefined;

    async function safeSetSinkId(deviceId: string, el: HTMLAudioElement) {
        if (destroyed) {
            return false;
        }
        if (lastRequestedDeviceId === deviceId) {
            return true;
        }
        if (typeof el.setSinkId !== "function") {
            return false;
        }
        lastRequestedDeviceId = deviceId;
        try {
            debug("Setting output device to ", deviceId);
            await el.setSinkId(deviceId);
            debug("Output device set to ", deviceId);
            return true;
        } catch (e) {
            if (destroyed) {
                return false;
            }

            Sentry.captureException(e);
            if (e instanceof DOMException && e.name === "AbortError") {
                // An error occurred while setting the sinkId. Let's fall back to default.
                console.warn("Error setting the audio output device. We fallback to default.");

                try {
                    lastRequestedDeviceId = "";
                    await el.setSinkId("");
                } catch (e) {
                    console.error("Error resetting the audio output device: ", e);
                }

                dispatch("selectOutputAudioDeviceError");
                return false;
            }
            console.error("Error setting the audio output device: ", e);
            return false;
        }
    }

    $: {
        if (outputDeviceId && audioElement) {
            safeSetSinkId(outputDeviceId, audioElement).catch((e) => {
                console.error("Error setting the audio output device: ", e);
                Sentry.captureException(e);
            });
        }
    }

    let destroyed = false;

    $: stream = $streamStore ? $streamStore : undefined;

    $: if (audioElement && stream) {
        if (audioElement.srcObject !== stream) {
            audioElement.srcObject = stream;
            // The gain path holds a source node built from the stream, so it has
            // to be rebuilt when the stream is replaced.
            volumeHandle?.setStream(stream);
        }
    }

    onMount(() => {
        (async () => {
            if (outputDeviceId) {
                // Because of a bug in Chrome, we need to wait for setSinkId to resolve before setting the srcObject.
                await safeSetSinkId(outputDeviceId, audioElement);
                if (destroyed || !audioElement) {
                    return;
                }
                audioElement.srcObject = stream ?? null;
                ensureVolumeHandle();
                volumeHandle?.setStream(stream);
                volumeHandle?.setLevel($volume);
            }
        })().catch((e) => {
            console.error(e);
            Sentry.captureException(e);
        });
    });

    onDestroy(() => {
        destroyed = true;
        volumeHandle?.detach();
        volumeHandle = undefined;
    });
</script>

{#if !$isBlocked}
    <audio bind:this={audioElement} autoplay={true} />
{/if}
