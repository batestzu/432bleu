<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import { gameManager } from "../../Phaser/Game/GameManager";
    import { analyticsClient } from "../../Administration/AnalyticsClient";
    import {
        pwaInstallUiStore,
        initPwaInstallUiListeners,
        installPwaFromStore,
        continuePwaInBrowser,
        neverShowPwaPage,
    } from "../../Stores/PwaInstallStore";
    import { detectIos } from "../../Utils/PwaInstallEligibility";

    const sceneBg =
        gameManager.currentStartedRoom.backgroundSceneImage ??
        "https://maps.432bleu.com/assets/loading-bg.png";
    const brandLogo =
        gameManager.currentStartedRoom.loginSceneLogo ??
        "https://maps.432bleu.com/assets/brand-logo.png";

    let neverShowAgain = false;
    let unsubscribePwa: (() => void) | undefined;

    onMount(() => {
        unsubscribePwa = initPwaInstallUiListeners();
        analyticsClient.pwaInstallPromptShown(detectIos());
    });

    onDestroy(() => {
        unsubscribePwa?.();
    });

    async function handleInstall(): Promise<void> {
        await installPwaFromStore();
    }

    function handleContinue(): void {
        if (neverShowAgain) {
            neverShowPwaPage();
            return;
        }
        continuePwaInBrowser();
    }

    function toggleNeverShow(): void {
        neverShowAgain = !neverShowAgain;
    }
</script>

<div
    class="pwa-install-screen loginScene relative z-30 flex w-full h-full flex-col items-center justify-center overflow-y-auto pointer-events-auto"
>
    <!-- Full-page background -->
    <div
        class="absolute inset-0 z-0 bg-cover bg-center h-full w-full"
        style="background-image: url('{sceneBg}');"
        aria-hidden="true"
    />
    <!-- Dark overlay -->
    <div
        class="absolute inset-0 z-[1] backdrop-blur-[3px] h-full w-full"
        style="background-color: rgba(2,6,10,0.88);"
        aria-hidden="true"
    />

    <div
        class="relative z-10 mx-auto flex w-full max-w-[min(480px,calc(100vw-2rem))] flex-col items-center gap-6 px-4 py-10"
    >
        <div
            class="w-full overflow-hidden rounded-2xl text-left"
            style="background: #04111c; border: 1px solid rgba(0,240,255,0.22); box-shadow: 0 0 48px rgba(0,240,255,0.07);"
        >
            <!-- Header -->
            <div
                class="relative flex flex-col items-center justify-center gap-4 px-6 py-8"
                style="background: linear-gradient(160deg, #0c2a3a 0%, #02060a 100%); border-bottom: 1px solid rgba(0,240,255,0.14);"
            >
                <!-- Corner brackets -->
                <svg class="absolute top-3 left-3" width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                    <path d="M2,2 L2,12 M2,2 L12,2" stroke="#00f0ff" stroke-width="1.5" opacity="0.65"/>
                </svg>
                <svg class="absolute top-3 right-3" width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                    <path d="M18,2 L18,12 M18,2 L8,2" stroke="#00f0ff" stroke-width="1.5" opacity="0.65"/>
                </svg>

                <img
                    draggable="false"
                    src={brandLogo}
                    alt="432 BLEU"
                    class="h-auto max-h-[80px] w-auto max-w-[200px] object-contain"
                />
                <div class="text-center">
                    <p class="m-0 text-xs tracking-[0.3em] uppercase" style="color: #5fe6dd; opacity: 0.75;">
                        RESONANT.OS · SECTOR 11
                    </p>
                    {#if $pwaInstallUiStore.isIos}
                        <p class="mt-2 m-0 text-sm italic" style="color: rgba(255,255,255,0.65);">
                            Add to your home screen for the full experience.
                        </p>
                    {:else}
                        <p class="mt-2 m-0 text-sm italic" style="color: rgba(255,255,255,0.65);">
                            Install for instant access on concert night.
                        </p>
                    {/if}
                </div>
            </div>

            <div class="flex flex-col gap-6 px-6 py-6">
                <!-- Feature list -->
                <ul class="m-0 flex list-none flex-col gap-4 p-0">
                    <li class="flex gap-4 items-start">
                        <span
                            class="flex h-9 w-9 shrink-0 items-center justify-center rounded"
                            style="background: rgba(0,240,255,0.08); border: 1px solid rgba(0,240,255,0.2);"
                            aria-hidden="true"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                                <polyline points="9 22 9 12 15 12 15 22"/>
                            </svg>
                        </span>
                        <div>
                            <p class="m-0 text-sm font-semibold text-white">Your backstage pass</p>
                            <p class="m-0 text-sm" style="color: rgba(255,255,255,0.55);">
                                Quick-launch 432 BLEU from your home screen — ticket in hand, every time.
                            </p>
                        </div>
                    </li>
                    <li class="flex gap-4 items-start">
                        <span
                            class="flex h-9 w-9 shrink-0 items-center justify-center rounded"
                            style="background: rgba(0,240,255,0.08); border: 1px solid rgba(0,240,255,0.2);"
                            aria-hidden="true"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="2" y="3" width="20" height="14" rx="2"/>
                                <line x1="8" y1="21" x2="16" y2="21"/>
                                <line x1="12" y1="17" x2="12" y2="21"/>
                            </svg>
                        </span>
                        <div>
                            <p class="m-0 text-sm font-semibold text-white">Full-screen stage</p>
                            <p class="m-0 text-sm" style="color: rgba(255,255,255,0.55);">
                                Immersive concert experience with no browser chrome in the way.
                            </p>
                        </div>
                    </li>
                    <li class="flex gap-4 items-start">
                        <span
                            class="flex h-9 w-9 shrink-0 items-center justify-center rounded"
                            style="background: rgba(0,240,255,0.08); border: 1px solid rgba(0,240,255,0.2);"
                            aria-hidden="true"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"/>
                                <polyline points="12 6 12 12 16 14"/>
                            </svg>
                        </span>
                        <div>
                            <p class="m-0 text-sm font-semibold text-white">Always in tune</p>
                            <p class="m-0 text-sm" style="color: rgba(255,255,255,0.55);">
                                Instant access to every 432 BLEU event without hunting for links.
                            </p>
                        </div>
                    </li>
                </ul>

                {#if $pwaInstallUiStore.isIos}
                    <div
                        class="rounded p-4 text-sm"
                        style="background: rgba(0,240,255,0.05); border: 1px solid rgba(0,240,255,0.15);"
                    >
                        <p class="m-0 font-semibold text-white">How to install on iOS:</p>
                        <ol class="m-0 mt-2 list-decimal space-y-1.5 pl-5" style="color: rgba(255,255,255,0.65);">
                            <li>Tap the Share button in Safari</li>
                            <li>Scroll down and tap "Add to Home Screen"</li>
                            <li>Tap "Add" to confirm</li>
                        </ol>
                    </div>
                {/if}

                <div class="flex flex-col gap-3">
                    {#if $pwaInstallUiStore.deferredPrompt && !$pwaInstallUiStore.isIos}
                        <button
                            type="button"
                            class="w-full rounded-lg px-4 py-3 text-sm font-semibold tracking-wide transition-all"
                            style="background: #00f0ff; color: #02060a;"
                            on:click={handleInstall}
                            disabled={$pwaInstallUiStore.installing}
                            data-testid="pwa-install-button"
                        >
                            {$pwaInstallUiStore.installing ? "Installing…" : "↓  Install App"}
                        </button>
                    {/if}

                    <button
                        type="button"
                        class="w-full rounded-lg px-4 py-3 text-sm font-semibold tracking-wide transition-all"
                        style="background: rgba(255,255,255,0.06); color: #fff; border: 1px solid rgba(255,255,255,0.12);"
                        on:click={handleContinue}
                        data-testid="pwa-install-skip"
                    >
                        Continue in browser
                    </button>

                    <div class="flex items-center justify-center pt-1">
                        <button
                            type="button"
                            role="switch"
                            aria-checked={neverShowAgain}
                            class="flex cursor-pointer items-center gap-3 border-0 bg-transparent p-0 text-sm focus:outline-none focus-visible:ring-2 rounded"
                            style="color: rgba(255,255,255,0.45);"
                            on:click={toggleNeverShow}
                            data-testid="pwa-install-never-show-input"
                        >
                            <span
                                class="relative inline-flex h-5 w-8 shrink-0 rounded-full transition-colors"
                                style="background: {neverShowAgain ? '#00f0ff' : 'rgba(255,255,255,0.2)'};"
                            >
                                <span
                                    class="pointer-events-none absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform {neverShowAgain
                                        ? 'translate-x-3'
                                        : 'translate-x-0'}"
                                />
                            </span>
                            Don't show again
                        </button>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div
                class="px-6 py-3 text-center"
                style="border-top: 1px solid rgba(0,240,255,0.1);"
            >
                <p class="m-0 text-xs tracking-[0.25em]" style="color: rgba(95,230,221,0.45);">
                    432.BLEU · THE ROOM IS LISTENING
                </p>
            </div>
        </div>
    </div>
</div>
