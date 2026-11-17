<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { LL } from "../../../i18n/i18n-svelte";
    import { IconX, IconSearch } from "@wa-icons";
    export let hasSearch: boolean;
    // True when the chat panel hides the action bar (always, on a phone). ChatSidebar then draws
    // the close X in the top corner, so the search button moves over to leave room for it.
    export let hasCloseChat: boolean;
    export let searchActive = false;

    type Events = {
        toggleSearch: void;
    };

    const dispatch = createEventDispatcher<Events>();

    function handleToggleSearch() {
        dispatch("toggleSearch");
    }
</script>

{#if hasSearch}
    <button
        class="p-3 hover:bg-white/10 rounded aspect-square w-12 h-12 relative z-50 {hasCloseChat ? 'me-12' : ''}"
        aria-label={searchActive ? $LL.chat.closeSearch() : $LL.chat.search()}
        on:click={handleToggleSearch}
    >
        {#if !searchActive}
            <IconSearch font-size="20" />
        {:else}
            <IconX font-size="20" />
        {/if}
    </button>
{/if}
