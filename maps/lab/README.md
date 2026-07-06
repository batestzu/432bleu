# Map Lab — experimental maps, isolated from concert.json

Work in Tiled locally: `tiled test-map.json`

## Rules of the road
- Everything in `maps/lab/` is invisible to visitors until pushed AND someone opens the lab URL directly — the live `concert.json` is never touched.
- Test in browser (after git push local → git pull on VPS, no rebuild needed):
  `https://play.432bleu.com/_/global/maps.432bleu.com/lab/test-map.json`
- WorkAdventure requires: orientation **orthogonal**, 32×32 tiles, a `start` tile layer
  (tiles there = spawn points), a `floorLayer` objectgroup, and collision painted with
  tiles that have the `collides=true` property (use the red "C" tile in `wa-zones`).
- Keep tile art on the square grid ("3/4 top-down"); true diamond-isometric geometry is
  not supported by the engine.

## Tilesets
| Tileset | Source | License |
|---|---|---|
| `castle-dungeon/` | @sythpixie "isometric castle dungeon" | Free; **credit @sythpixie required for commercial use**, no resale. See its README.txt |
| `zelda-like/` | ArMM1998, opengameart.org/content/zelda-like-tilesets-and-sprites | CC0 |
| `scifi/` | Buch, opengameart.org/content/sci-fi-interior-tiles | CC0 |
| `wa-zones.png` | generated in-house | — |
| `bleu-props.png` | generated in-house (`tools/make_props.py` — edit + rerun to tweak) | — |

`bleu-props` (fantasy concert gear, 32px grid, tall props span 2 tiles):
rows 0-1: rune speaker · crystal stage light w/ beam · gilded harp · 432 note banner ·
voice-crystal mic stand · back-bar potion shelf — row 2: monitor wedge · blue-flame torch ·
lute · drum · rune amp — row 3: arcane DJ console (2 wide) · Bleu Elixir goblet · potion
martini · foaming horn tankard — row 4: bar counter left/mid/right (mid tiles seamlessly,
any length) · keg · bottle trio.

The `*-32.png` files are 2× nearest-neighbor upscales of the original 16px art
(WorkAdventure needs a 32px grid); originals kept alongside in `zelda-like/gfx/` and
`scifi/scifitiles-sheet.png`. Master copies of downloaded packs live in
`~/Desktop/432 Bleu Designs/pixel-art/` and `~/Downloads/`.

`castle-dungeon/stuff.png` (props sheet) is not grid-aligned — add it in Tiled as an
image collection tileset if needed, or slice individual props out as needed.
