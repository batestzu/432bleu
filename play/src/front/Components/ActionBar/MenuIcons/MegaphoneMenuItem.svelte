<script lang="ts">
    import { analyticsClient } from "../../../Administration/AnalyticsClient";
    import ActionBarButton from "../ActionBarButton.svelte";
    import MegaphoneIcon from "../../Icons/MegaphoneIcon.svelte";
    import LL from "../../../../i18n/i18n-svelte";
    import {
        requestedMegaphoneStore,
        megaphoneSpaceStore,
        currentLiveStreamingSpaceStore,
    } from "../../../Stores/MegaphoneStore";
    import { streamingMegaphoneStore } from "../../../Stores/MediaStore";
</script>

<ActionBarButton
    on:click={() => {
        analyticsClient.stopMegaphone();
        // There are TWO ways to be live and they use different stores. The room-wide
        // megaphone (WAM settings.megaphone) lands in megaphoneSpaceStore; standing in a
        // speaker zone lands in currentLiveStreamingSpaceStore. Stopping only the former
        // meant a performer on the stage tile clicked this, saw the button toggle, and
        // kept broadcasting -- the optional chaining made the miss silent. Stop whichever
        // is actually live; calling stopStreaming on a space that is not streaming is a
        // no-op, so stopping both is safe.
        $megaphoneSpaceStore?.stopStreaming();
        $currentLiveStreamingSpaceStore?.stopStreaming();
        currentLiveStreamingSpaceStore.set(undefined);
        requestedMegaphoneStore.set(false);
        streamingMegaphoneStore.set(false);
    }}
    classList="group/btn-megaphone"
    tooltipTitle={$LL.actionbar.help.megaphone.title()}
    tooltipDesc={$LL.actionbar.help.megaphone.desc()}
    state={$requestedMegaphoneStore ? "forbidden" : "normal"}
    dataTestId="Megaphone-button"
    desc={$LL.actionbar.help.megaphone.desc()}
>
    <MegaphoneIcon />
</ActionBarButton>
