/**
 * 432 Bleu is one venue, so every room URL has to land in the same GameRoom. The back keys
 * rooms by URL: two people holding different links to the same map stand in separate copies
 * of it and never see each other. On 2026-09-03 the host spent the run-up to doors in
 * /_/global/maps.432bleu.com/concert.json while the audience was in /~/concert.wam.
 *
 * Returns the URL to redirect to, or undefined when playUri is already the start room.
 * Only the path changes: ?token= carries the login and #name picks the entry point.
 */
export function singleRoomRedirect(playUri: string, startRoomUrl: string): string | undefined {
    const url = new URL(playUri);
    const startPath = new URL(startRoomUrl, url).pathname;
    if (url.pathname === startPath) {
        return undefined;
    }
    url.pathname = startPath;
    return url.toString();
}
