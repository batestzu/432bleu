<script lang="ts">
    import { fly } from "svelte/transition";

    const TICKET_URL = "https://boxoffice.432bleu.com";

    const events = [
        {
            artist: "Skyler Bates of Instant Shaman",
            title: "Global",
            date: new Date("2026-06-02T00:00:00"),
            description: "A worldwide virtual concert experience. Join from anywhere on the planet.",
            ticketUrl: TICKET_URL,
        },
    ];

    function formatDate(date: Date): string {
        return date.toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    function daysUntil(date: Date): number {
        const now = new Date();
        const diff = date.getTime() - now.getTime();
        return Math.ceil(diff / (1000 * 60 * 60 * 24));
    }
</script>

<div class="px-6 py-8 text-white" in:fly={{ x: 100, duration: 150 }}>
    <h2 class="text-2xl font-bold mb-6 text-white">Upcoming Events</h2>

    {#each events as event}
        {@const days = daysUntil(event.date)}
        <div class="rounded-xl bg-white/5 border border-white/10 overflow-hidden mb-4">
            <!-- Gradient header bar -->
            <div
                class="h-1 w-full"
                style="background: linear-gradient(90deg, #9af2e8, #00f0ff, #7a3bff, #ff2bd6);"
            />

            <div class="p-6">
                <div class="flex flex-col gap-4">
                    <!-- Artist + title -->
                    <div>
                        <p class="text-xs uppercase tracking-widest text-white/40 mb-1">Live Performance</p>
                        <h3 class="text-xl font-bold text-white leading-tight">{event.artist}</h3>
                        <p class="text-lg text-white/70 font-light italic">{event.title}</p>
                    </div>

                    <!-- Date + countdown -->
                    <div class="flex items-center gap-3">
                        <div class="flex flex-col">
                            <span class="text-sm font-semibold text-white/90">{formatDate(event.date)}</span>
                            {#if days > 0}
                                <span class="text-xs text-white/40">{days} day{days !== 1 ? "s" : ""} away</span>
                            {:else if days === 0}
                                <span class="text-xs text-[#9af2e8] font-semibold">Tonight!</span>
                            {:else}
                                <span class="text-xs text-white/40">Past event</span>
                            {/if}
                        </div>
                    </div>

                    <!-- Description -->
                    <p class="text-sm text-white/60 leading-relaxed">{event.description}</p>

                    <!-- Ticket button -->
                    <a
                        href={event.ticketUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="inline-flex items-center justify-center gap-2 rounded-lg px-6 py-3 text-sm font-bold uppercase tracking-wider text-white transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-[0.98]"
                        style="background: linear-gradient(135deg, #7a3bff, #00f0ff);"
                    >
                        <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"
                            />
                        </svg>
                        Get Tickets
                    </a>
                </div>
            </div>
        </div>
    {/each}

    {#if events.length === 0}
        <p class="text-white/40 text-sm">No upcoming events. Check back soon.</p>
    {/if}
</div>
