import { describe, expect, it } from "vitest";
import { singleRoomRedirect } from "../../src/pusher/services/SingleRoom";

const START = "/~/concert.wam";
const VENUE = "https://play.432bleu.com/~/concert.wam";

describe("singleRoomRedirect", () => {
    it("leaves the start room alone", () => {
        expect(singleRoomRedirect(VENUE, START)).toBeUndefined();
    });
    it("leaves the start room alone with a login token and entry point", () => {
        expect(singleRoomRedirect(VENUE + "?token=abc#stage", START)).toBeUndefined();
    });
    it("sends the legacy static-map room to the venue", () => {
        expect(singleRoomRedirect("https://play.432bleu.com/_/global/maps.432bleu.com/concert.json", START)).toBe(
            VENUE
        );
    });
    it("catches the legacy room under any scope, which the Caddy exact-path rule misses", () => {
        expect(singleRoomRedirect("https://play.432bleu.com/_/anything/maps.432bleu.com/concert.json", START)).toBe(
            VENUE
        );
    });
    it("sends other map-storage paths, .tmj and trailing slashes to the venue", () => {
        expect(singleRoomRedirect("https://play.432bleu.com/~/concert.tmj", START)).toBe(VENUE);
        expect(singleRoomRedirect("https://play.432bleu.com/~/other.wam", START)).toBe(VENUE);
        expect(singleRoomRedirect("https://play.432bleu.com/~/concert.wam/", START)).toBe(VENUE);
    });
    it("sends admin-style and bare-origin URLs to the venue", () => {
        expect(singleRoomRedirect("https://play.432bleu.com/@/org/world/room", START)).toBe(VENUE);
        expect(singleRoomRedirect("https://play.432bleu.com/", START)).toBe(VENUE);
    });
    it("keeps the login token and the entry point across the redirect", () => {
        expect(
            singleRoomRedirect("https://play.432bleu.com/_/global/maps.432bleu.com/concert.json?token=abc#stage", START)
        ).toBe(VENUE + "?token=abc#stage");
    });
    it("accepts an absolute START_ROOM_URL and keeps the visitor's own origin", () => {
        expect(singleRoomRedirect("http://play.workadventure.localhost/~/x.wam", VENUE)).toBe(
            "http://play.workadventure.localhost/~/concert.wam"
        );
    });
});
