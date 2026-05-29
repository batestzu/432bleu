#!/usr/bin/env python3
"""
VSPOT Club Tileset Generator
Output: club_tileset.png  (256 x 160 px — 8 cols x 5 rows x 32 px tiles)

Tile index (col, row):
  Row 0 — Stage Equipment
    (0,0) Amp cabinet       (1,0) Floor monitor     (2,0) Mic stand
    (3,0) Drum kit          (4,0) DJ booth           (5,0) CDJ/turntable
    (6,0) Mixer             (7,0) Guitar stand
  Row 1 — Speakers & Barriers
    (0,1) Speaker stack     (1,1) Subwoofer          (2,1) Stage monitor sm
    (3,1) Barrier L end     (4,1) Barrier mid         (5,1) Barrier R end
    (6,1) Smoke machine     (7,1) Haze/fog
  Row 2 — Lighting
    (0,2) Truss horiz       (1,2) Truss vert          (2,2) Truss corner
    (3,2) Par can           (4,2) Moving head         (5,2) LED bar
    (6,2) Disco ball        (7,2) Laser unit
  Row 3 — Decor & Furniture
    (0,3) Neon sign horiz   (1,3) Neon sign corner    (2,3) VIP booth seat
    (3,3) Bar counter       (4,3) Bar stool            (5,3) Dance floor A (pink)
    (6,3) Dance floor B (cyan) (7,3) Stage edge lit
  Row 4 — Structural
    (0,4) Stage stairs L    (1,4) Stage stairs R       (2,4) Backdrop dark
    (3,4) Backdrop glow     (4,4) Floor cable           (5,4) Power strip
    (6,4) Security desk     (7,4) Merch table
"""
from PIL import Image, ImageDraw

T = 32
COLS, ROWS = 8, 5

# ── Palette ───────────────────────────────────────────────────────────────────
TR    = (0,   0,   0,   0)    # transparent
BODY  = (22,  20,  40,  255)  # equipment dark body
BODY2 = (38,  35,  65,  255)  # equipment mid body
BODY3 = (62,  58,  95,  255)  # equipment highlight face
METAL = (82,  85, 112,  255)  # metal
MTL2  = (148, 155, 182, 255)  # metal highlight
WHT   = (232, 238, 255,  255) # bright white
FLR   = (18,  15,  32,  255)  # dark stage floor

PINK  = (255,  18, 185,  255) # neon pink
PINK2 = (185,   8, 130,  255) # pink mid
PINK3 = (80,    3,  55,  255) # pink glow dim
CYAN  = (0,  225, 255,  255)  # neon cyan
CYAN2 = (0,  155, 195,  255)  # cyan mid
CYAN3 = (0,   55,  75,  255)  # cyan glow dim
PURP  = (190,   0, 255,  255) # neon purple
PURP2 = (125,   0, 185,  255) # purple mid
PURP3 = (50,    0,  80,  255) # purple glow dim
YELL  = (255, 235,   0,  255) # neon yellow
YELL2 = (200, 180,   0,  255) # yellow mid
ORAN  = (255, 120,   0,  255) # neon orange
ORAN2 = (180,  80,   0,  255) # orange mid
RED   = (255,  25,  45,  255) # neon red
RED2  = (170,  10,  25,  255) # red mid
GRN   = (0,  255, 115,  255)  # neon green
GRN2  = (0,  175,  75,  255)  # green mid

img = Image.new("RGBA", (T * COLS, T * ROWS), TR)
draw = ImageDraw.Draw(img)

def ox(tx): return tx * T
def oy(ty): return ty * T

def R(tx, ty, x1, y1, x2, y2, c):
    draw.rectangle([ox(tx)+x1, oy(ty)+y1, ox(tx)+x2, oy(ty)+y2], fill=c)

def E(tx, ty, x1, y1, x2, y2, c, outline=None, ow=1):
    draw.ellipse([ox(tx)+x1, oy(ty)+y1, ox(tx)+x2, oy(ty)+y2],
                 fill=c, outline=outline, width=ow)

def P(tx, ty, x, y, c):
    img.putpixel((ox(tx)+x, oy(ty)+y), c)

def L(tx, ty, x1, y1, x2, y2, c, w=1):
    draw.line([ox(tx)+x1, oy(ty)+y1, ox(tx)+x2, oy(ty)+y2], fill=c, width=w)

def bg(tx, ty, c=FLR):
    R(tx, ty, 0, 0, T-1, T-1, c)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 0 — Stage Equipment
# ══════════════════════════════════════════════════════════════════════════════

# (0,0) Amp cabinet  – top-down: you see the top face + front face strip
bg(0, 0)
R(0,0, 3,2, 28,21, BODY2)          # top face
R(0,0, 4,3, 27,20, BODY)           # speaker grill area
for gy in range(4, 20, 3):          # grill dots
    for gx in range(5, 27, 3):
        R(0,0, gx,gy, gx+1,gy+1, BODY2)
R(0,0, 3,2, 28,2,  BODY3)          # top edge highlight
R(0,0, 3,2, 3,21,  BODY3)          # left edge highlight
R(0,0, 28,2, 28,21, METAL)         # right shadow
R(0,0, 3,21, 28,21, METAL)         # bottom shadow
R(0,0, 3,22, 28,29, BODY)          # front face strip
R(0,0, 3,22, 28,22, BODY3)         # front top highlight
P(0,0, 9,25,  CYAN2)               # knob 1
P(0,0, 15,25, YELL2)               # knob 2
P(0,0, 21,25, PINK2)               # knob 3
R(0,0, 3,29, 28,30, METAL)         # base plate

# (1,0) Floor monitor (wedge) – top-down: wider at front (bottom), narrow at back
bg(1, 0)
pts = [(4,4),(27,4),(29,28),(2,28)]
draw.polygon([(ox(1)+x, oy(0)+y) for x,y in pts], fill=BODY2)
R(1,0, 5,5, 26,8, BODY3)           # back edge highlight
R(1,0, 5,9, 26,26, BODY)           # grill
for gy in range(10, 26, 3):
    for gx in range(6, 26, 3):
        R(1,0, gx,gy, gx+1,gy+1, BODY2)
R(1,0, 3,28, 28,29, METAL)         # front base

# (2,0) Mic stand – top-down: base tripod + pole dot
bg(2, 0)
R(2,0, 15,4, 16,26, METAL)         # pole (vertical view = thin line)
L(2,0, 10,26, 22,26, METAL, 2)     # base bar
L(2,0, 10,26, 8,30, METAL, 2)      # leg L
L(2,0, 22,26, 24,30, METAL, 2)     # leg R
L(2,0, 16,26, 16,30, METAL, 2)     # leg C
E(2,0, 12,2, 19,9, METAL, MTL2, 1) # mic capsule top view
R(2,0, 14,2, 17,5, MTL2)           # mic body highlight

# (3,0) Drum kit – top-down view
bg(3, 0)
E(3,0, 8,10, 22,24, BODY2, METAL, 1)   # kick drum (big circle)
R(3,0, 13,15, 17,19, BODY3)            # kick head center
E(3,0, 2,2, 11,11, BODY2, METAL, 1)    # hi-hat (small)
E(3,0, 20,2, 29,11, BODY2, PINK2, 1)   # ride cymbal
E(3,0, 22,18, 29,25, BODY2, CYAN2, 1)  # crash cymbal
E(3,0, 3,19, 10,26, BODY, METAL, 1)    # snare
P(3,0, 6,22, MTL2)                     # snare center dot
L(3,0, 2,14, 12,10, METAL, 1)          # hi-hat stand
L(3,0, 24,14, 25,20, METAL, 1)         # ride stand

# (4,0) DJ booth – top-down view
bg(4, 0)
R(4,0, 2,6, 29,26, BODY2)              # booth top
R(4,0, 2,6, 29,6, BODY3)              # back edge
R(4,0, 2,6, 2,26, BODY3)              # left edge
R(4,0, 29,6, 29,26, METAL)            # right shadow
R(4,0, 2,26, 29,26, METAL)            # front shadow
R(4,0, 4,8, 14,24, BODY)              # CDJ zone L
R(4,0, 16,8, 26,24, BODY)             # CDJ zone R
E(4,0, 5,9, 13,23, BODY2, CYAN2, 1)   # CDJ L platter
E(4,0, 17,9, 25,23, BODY2, PINK2, 1)  # CDJ R platter
R(4,0, 14,10, 15,22, BODY3)           # mixer strip center

# (5,0) CDJ / turntable – top-down close-up
bg(5, 0)
R(5,0, 2,2, 29,29, BODY)
R(5,0, 2,2, 29,2, BODY2)
R(5,0, 2,2, 2,29, BODY2)
R(5,0, 29,2, 29,29, METAL)
E(5,0, 5,5, 26,26, BODY2, CYAN, 1)    # platter
E(5,0, 12,12, 19,19, BODY3, CYAN2, 1) # platter center
P(5,0, 15,15, CYAN)                    # platter dot
R(5,0, 3,3, 8,8, BODY3)              # jog/cue buttons area
P(5,0, 5,5, YELL)                     # cue btn
P(5,0, 7,5, RED)                      # play btn

# (6,0) Mixer – top-down
bg(6, 0)
R(6,0, 5,2, 26,29, BODY2)
R(6,0, 5,2, 26,2, BODY3)
R(6,0, 5,2, 5,29, BODY3)
R(6,0, 26,2, 26,29, METAL)
# channel faders
for cx in [7, 12, 17, 22]:
    R(6,0, cx,4, cx+2,28, BODY)
    R(6,0, cx,16, cx+2,18, WHT)        # fader cap
# crossfader
R(6,0, 7,25, 24,27, BODY)
R(6,0, 14,25, 16,27, METAL)
# EQ knobs
for kx in [8, 13, 18, 23]:
    P(6,0, kx,8, PINK2)
    P(6,0, kx,11, CYAN2)
    P(6,0, kx,14, YELL2)

# (7,0) Guitar stand + guitar – top-down
bg(7, 0)
R(7,0, 13,2, 18,28, BODY2)            # stand pole
L(7,0, 10,4, 21,4, METAL, 2)          # stand top bar
L(7,0, 10,26, 21,26, METAL, 2)        # stand bottom bar
# guitar silhouette (top-down, lying on stand)
E(7,0, 5,12, 13,22, BODY3, METAL, 1)  # body lower bout
E(7,0, 7,7, 12,14, BODY3, METAL, 1)   # body upper bout
R(7,0, 9,4, 11,8, BODY3)              # neck
R(7,0, 9,2, 11,4, METAL)              # headstock
P(7,0, 9,3, YELL2)                    # tuner
P(7,0, 11,3, YELL2)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 1 — Speakers & Barriers
# ══════════════════════════════════════════════════════════════════════════════

# (0,1) Speaker stack – large (top-down, 2 stacked cabs)
bg(0, 1)
R(0,1, 3,2, 28,15, BODY2)             # top cab
R(0,1, 4,3, 27,14, BODY)
for gy in range(4,14,2):
    for gx in range(5,27,3):
        R(0,1, gx,gy, gx+1,gy, BODY2)
R(0,1, 3,2, 28,2, BODY3)
R(0,1, 3,2, 3,15, BODY3)
R(0,1, 28,2, 28,15, METAL)
R(0,1, 3,15, 28,15, METAL)
R(0,1, 3,17, 28,29, BODY2)            # bottom cab (sub/horn)
R(0,1, 4,18, 27,28, BODY)
E(0,1, 9,19, 22,27, BODY2, METAL, 1)  # horn ellipse
R(0,1, 3,17, 28,17, BODY3)
R(0,1, 3,17, 3,29, BODY3)
R(0,1, 28,17, 28,29, METAL)
R(0,1, 3,29, 28,29, METAL)

# (1,1) Subwoofer – large square cab with big driver
bg(1, 1)
R(1,1, 2,2, 29,29, BODY2)
R(1,1, 3,3, 28,28, BODY)
E(1,1, 5,5, 26,26, BODY2, METAL, 2)   # woofer surround
E(1,1, 10,10, 21,21, BODY, METAL, 1)  # cone
E(1,1, 13,13, 18,18, BODY3, MTL2, 1)  # dustcap
R(1,1, 2,2, 29,2, BODY3)
R(1,1, 2,2, 2,29, BODY3)
R(1,1, 29,2, 29,29, METAL)
R(1,1, 2,29, 29,29, METAL)

# (2,1) Stage monitor small
bg(2, 1)
pts2 = [(3,6),(28,6),(30,26),(1,26)]
draw.polygon([(ox(2)+x, oy(1)+y) for x,y in pts2], fill=BODY2)
R(2,1, 4,7, 27,10, BODY3)
R(2,1, 4,11, 27,24, BODY)
for gy in range(12,24,2):
    for gx in range(5,27,3):
        R(2,1, gx,gy, gx+1,gy, BODY2)
R(2,1, 2,26, 29,27, METAL)

# (3,1) Barrier left end
bg(3, 1)
R(3,1, 12,2, 16,29, METAL)            # vertical post
R(3,1, 12,2, 28,4, METAL)             # top rail going right
R(3,1, 12,14, 28,16, METAL)           # mid rail
R(3,1, 12,26, 28,28, METAL)           # bottom rail
R(3,1, 12,2, 14,29, MTL2)             # post highlight
R(3,1, 12,2, 28,2, MTL2)              # rail top highlight
R(3,1, 12,14, 28,14, MTL2)
R(3,1, 12,26, 28,26, MTL2)
R(3,1, 8,26, 12,29, METAL)            # foot L
R(3,1, 16,26, 20,29, METAL)           # foot R

# (4,1) Barrier middle
bg(4, 1)
R(4,1, 0,2, 31,4, METAL)              # top rail
R(4,1, 0,14, 31,16, METAL)            # mid rail
R(4,1, 0,26, 31,28, METAL)            # bottom rail
R(4,1, 0,2, 31,2, MTL2)
R(4,1, 0,14, 31,14, MTL2)
R(4,1, 0,26, 31,26, MTL2)
for px2 in [6, 16, 26]:               # vertical spacers
    R(4,1, px2,2, px2+1,28, METAL)

# (5,1) Barrier right end (mirror of left)
bg(5, 1)
R(5,1, 15,2, 19,29, METAL)
R(5,1, 3,2, 19,4, METAL)
R(5,1, 3,14, 19,16, METAL)
R(5,1, 3,26, 19,28, METAL)
R(5,1, 17,2, 19,29, MTL2)
R(5,1, 3,2, 19,2, MTL2)
R(5,1, 3,14, 19,14, MTL2)
R(5,1, 3,26, 19,26, MTL2)
R(5,1, 11,26, 15,29, METAL)
R(5,1, 19,26, 23,29, METAL)

# (6,1) Smoke machine
bg(6, 1)
R(6,1, 4,10, 27,27, BODY2)            # body
R(6,1, 4,10, 27,10, BODY3)
R(6,1, 4,10, 4,27, BODY3)
R(6,1, 27,10, 27,27, METAL)
R(6,1, 4,27, 27,27, METAL)
R(6,1, 11,4, 20,10, BODY3)            # nozzle
R(6,1, 12,2, 19,4, METAL)             # nozzle tip
# status LEDs
P(6,1, 8,13, GRN)
P(6,1, 8,16, YELL)
P(6,1, 8,19, RED)
R(6,1, 11,22, 24,25, BODY)            # vent

# (7,1) Haze / fog (semi-transparent cloud effect)
# Use light RGBA values to simulate fog
for fy in range(0, T):
    for fx in range(0, T):
        dist = ((fx - 15)**2 + (fy - 15)**2)**0.5
        alpha = max(0, int(120 - dist * 5))
        if alpha > 0:
            img.putpixel((ox(7)+fx, oy(1)+fy), (200, 210, 235, alpha))

# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 — Lighting
# ══════════════════════════════════════════════════════════════════════════════

# (0,2) Truss segment – horizontal
bg(0, 2)
R(0,2, 0,8, 31,12, METAL)             # top chord
R(0,2, 0,19, 31,23, METAL)            # bottom chord
R(0,2, 0,8, 31,8, MTL2)               # highlights
R(0,2, 0,19, 31,19, MTL2)
for kx in range(4, 30, 8):            # diagonal bracing
    L(0,2, kx,12, kx+4,19, METAL, 1)
    L(0,2, kx+4,12, kx,19, METAL, 1)

# (1,2) Truss segment – vertical
bg(1, 2)
R(1,2, 8,0, 12,31, METAL)
R(1,2, 19,0, 23,31, METAL)
R(1,2, 8,0, 8,31, MTL2)
R(1,2, 19,0, 19,31, MTL2)
for ky in range(4, 30, 8):
    L(1,2, 12,ky, 19,ky+4, METAL, 1)
    L(1,2, 12,ky+4, 19,ky, METAL, 1)

# (2,2) Truss corner (L-shape)
bg(2, 2)
R(2,2, 8,8, 31,12, METAL)
R(2,2, 8,12, 12,31, METAL)
R(2,2, 8,8, 31,8, MTL2)
R(2,2, 8,8, 8,31, MTL2)
R(2,2, 19,8, 23,12, BODY3)            # inner brace
R(2,2, 8,19, 12,23, BODY3)

# (3,2) Par can light (hanging, top-down – you see the lens circle)
bg(3, 2)
R(3,2, 10,2, 21,8, BODY)              # yoke bar
R(3,2, 13,2, 18,4, METAL)             # clamp
E(3,2, 5,8, 26,29, BODY2, METAL, 2)   # housing
E(3,2, 9,12, 22,25, ORAN, YELL, 2)    # lens (orange warm light)
E(3,2, 13,16, 18,21, YELL, WHT, 1)    # center bright

# (4,2) Moving head light (top-down)
bg(4, 2)
R(4,2, 10,2, 21,6, BODY)              # yoke
R(4,2, 13,2, 18,4, METAL)             # clamp
E(4,2, 6,6, 25,25, BODY2, METAL, 1)   # housing round
E(4,2, 10,10, 21,21, CYAN, PURP, 2)   # lens (cool moving head)
E(4,2, 14,14, 17,17, WHT, CYAN, 1)    # center bright
R(4,2, 8,25, 23,28, BODY3)            # base plate

# (5,2) LED bar
bg(5, 2)
R(5,2, 1,10, 30,21, BODY)             # bar housing
R(5,2, 1,10, 30,10, BODY2)            # top
R(5,2, 1,21, 30,21, METAL)            # bottom shadow
# LED dots – multi-color
leds = [RED, ORAN, YELL, GRN, CYAN, PURP, PINK, WHT]
for i, lc in enumerate(leds):
    lx = 3 + i * 3
    E(5,2, lx,13, lx+2,18, lc)

# (6,2) Disco ball
bg(6, 2)
E(6,2, 5,3, 26,24, BODY2, METAL, 1)   # ball
# facets
colors = [PINK, CYAN, YELL, PURP, RED, GRN, ORAN, WHT]
import math
for i in range(20):
    ang = i * math.pi * 2 / 20
    r2 = 9
    fx = int(15 + r2 * math.cos(ang))
    fy = int(13 + r2 * math.sin(ang))
    c = colors[i % len(colors)]
    R(6,2, fx-1,fy-1, fx+1,fy+1, c)
# beam rays
for i in range(8):
    ang = i * math.pi * 2 / 8
    bx = int(15 + 13 * math.cos(ang))
    by = int(13 + 13 * math.sin(ang))
    img.putpixel((ox(6)+bx, oy(2)+by), colors[i])
R(6,2, 12,24, 19,28, METAL)           # hanging wire/stem

# (7,2) Laser unit
bg(7, 2)
R(7,2, 5,10, 26,22, BODY2)            # housing
R(7,2, 5,10, 26,10, BODY3)
R(7,2, 5,10, 5,22, BODY3)
R(7,2, 26,10, 26,22, METAL)
R(7,2, 5,22, 26,22, METAL)
E(7,2, 12,13, 19,19, BODY, GRN, 2)    # aperture
P(7,2, 15,16, GRN)                    # active dot
# laser beams going out
L(7,2, 15,13, 15,4, GRN, 1)           # beam up
L(7,2, 15,19, 2,28, GRN2, 1)          # beam lower-left
L(7,2, 15,19, 28,28, CYAN2, 1)        # beam lower-right
R(7,2, 6,23, 25,28, BODY)             # base
P(7,2, 9,25, GRN)                     # status LED


# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 — Decor & Furniture
# ══════════════════════════════════════════════════════════════════════════════

# (0,3) Neon sign – horizontal bar
bg(0, 3)
R(0,3, 0,9, 31,22, BODY)              # sign backing dark
R(0,3, 2,11, 29,20, BODY2)            # inner
# neon tube outline
R(0,3, 2,11, 29,11, PINK)
R(0,3, 2,20, 29,20, PINK)
R(0,3, 2,11, 2,20, PINK)
R(0,3, 29,11, 29,20, PINK)
# glow
R(0,3, 3,12, 28,19, PINK3)
# text pixels "♪♪" implied by dot pattern
for tx2 in [8,10,18,20]:
    R(0,3, tx2,13, tx2+1,18, PINK2)
R(0,3, 0,9, 31,9, BODY3)              # top mount
R(0,3, 0,22, 31,22, BODY3)            # bottom mount

# (1,3) Neon sign – corner piece
bg(1, 3)
R(1,3, 0,9, 16,22, BODY)
R(1,3, 9,9, 22,22, BODY)
R(1,3, 0,9, 16,11, PINK)              # top rail horiz
R(1,3, 0,20, 16,22, PINK)             # bottom rail horiz
R(1,3, 9,9, 11,22, PINK)              # vert rail
R(1,3, 20,9, 22,22, PINK)             # right vert
R(1,3, 1,12, 15,19, PINK3)
R(1,3, 12,10, 19,21, PINK3)

# (2,3) VIP booth seat – top-down (cushion view)
bg(2, 3)
R(2,3, 2,8, 29,28, (55, 20, 70, 255))  # velvet seat dark purple
R(2,3, 3,9, 28,27, (80, 30, 100, 255)) # velvet lighter
R(2,3, 2,6, 29,8, (30, 28, 50, 255))   # back cushion
R(2,3, 2,6, 29,6, PURP2)               # back top edge
R(2,3, 2,8, 2,28, PURP3)               # side shadow
R(2,3, 29,8, 29,28, BODY)              # side shadow R
# tufting dots
for ty2 in [14,21]:
    for tx2 in [8,15,22]:
        P(2,3, tx2,ty2, PURP2)

# (3,3) Bar counter – segment top-down
bg(3, 3)
R(3,3, 0,2, 31,8, (60, 40, 20, 255))   # counter top wood
R(3,3, 0,2, 31,2, (100, 68, 30, 255))  # wood highlight
R(3,3, 0,3, 31,3, (80, 54, 22, 255))
R(3,3, 0,8, 31,28, (35, 28, 18, 255))  # bar front dark wood
R(3,3, 0,8, 31,8, (70, 52, 25, 255))   # top of front
# wood grain lines
for gy in range(10, 27, 4):
    R(3,3, 2,gy, 29,gy, (45, 35, 20, 255))
# bottles silhouetted on counter
for bx in [4, 10, 17, 24]:
    R(3,3, bx,3, bx+2,7, (30,50,80,255))

# (4,3) Bar stool – top-down (you see the round seat)
bg(4, 3)
E(4,3, 7,5, 24,22, (65, 30, 10, 255), (90, 52, 18, 255), 1)  # seat
E(4,3, 10,8, 21,19, (50, 22, 6, 255))                          # seat inner
L(4,3, 15,22, 8,30, (60, 42, 18, 255), 2)                     # leg L
L(4,3, 15,22, 22,30, (60, 42, 18, 255), 2)                    # leg R

# (5,3) Dance floor tile A – lit (pink/magenta)
R(5,3, 0,0, 31,31, (15, 10, 28, 255))  # base
R(5,3, 1,1, 14,14, PINK3)              # panel A
R(5,3, 17,1, 30,14, (8, 6, 18, 255))   # panel B dark
R(5,3, 1,17, 14,30, (8, 6, 18, 255))   # panel C dark
R(5,3, 17,17, 30,30, PINK3)            # panel D
R(5,3, 0,0, 31,0, PINK2)               # grid lines
R(5,3, 0,15, 31,16, PINK2)
R(5,3, 0,31, 31,31, PINK2)
R(5,3, 0,0, 0,31, PINK2)
R(5,3, 15,0, 16,31, PINK2)
R(5,3, 31,0, 31,31, PINK2)
# lit panel glow center
E(5,3, 4,4, 12,12, PINK2)
E(5,3, 19,19, 27,27, PINK2)

# (6,3) Dance floor tile B – lit (cyan)
R(6,3, 0,0, 31,31, (8, 18, 28, 255))
R(6,3, 1,1, 14,14, (8, 6, 18, 255))
R(6,3, 17,1, 30,14, CYAN3)
R(6,3, 1,17, 14,30, CYAN3)
R(6,3, 17,17, 30,30, (8, 6, 18, 255))
R(6,3, 0,0, 31,0, CYAN2)
R(6,3, 0,15, 31,16, CYAN2)
R(6,3, 0,31, 31,31, CYAN2)
R(6,3, 0,0, 0,31, CYAN2)
R(6,3, 15,0, 16,31, CYAN2)
R(6,3, 31,0, 31,31, CYAN2)
E(6,3, 19,4, 27,12, CYAN2)
E(6,3, 4,19, 12,27, CYAN2)

# (7,3) Stage edge lit strip – front face with LED strip
bg(7, 3)
R(7,3, 0,0, 31,22, (28, 25, 45, 255))   # stage surface
R(7,3, 0,23, 31,28, BODY)               # front face
R(7,3, 0,23, 31,23, BODY3)              # edge highlight
# LED strip dots
led_cols3 = [RED, ORAN, YELL, GRN, CYAN, CYAN, PURP, PINK]
for i, lc in enumerate(led_cols3):
    lx = 2 + i * 4
    P(7,3, lx,25, lc)
    P(7,3, lx+1,25, lc)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 4 — Structural
# ══════════════════════════════════════════════════════════════════════════════

# (0,4) Stage stairs left
bg(0, 4)
R(0,4, 0,0, 31,31, (28,25,42,255))
R(0,4, 22,0, 31,7, (38,35,58,255))    # step 1 top
R(0,4, 14,8, 31,15, (48,45,70,255))   # step 2 top
R(0,4, 6,16, 31,23, (60,56,85,255))   # step 3 top
R(0,4, 0,24, 31,31, (70,66,100,255))  # step 4 top / landing
R(0,4, 30,0, 31,7, METAL)
R(0,4, 30,8, 31,15, METAL)
R(0,4, 30,16, 31,23, METAL)
R(0,4, 30,24, 31,31, METAL)

# (1,4) Stage stairs right
bg(1, 4)
R(1,4, 0,0, 31,31, (28,25,42,255))
R(1,4, 0,0, 9,7, (38,35,58,255))
R(1,4, 0,8, 17,15, (48,45,70,255))
R(1,4, 0,16, 25,23, (60,56,85,255))
R(1,4, 0,24, 31,31, (70,66,100,255))
R(1,4, 0,0, 1,7, METAL)
R(1,4, 0,8, 1,15, METAL)
R(1,4, 0,16, 1,23, METAL)
R(1,4, 0,24, 1,31, METAL)

# (2,4) Backdrop panel – dark
bg(2, 4)
R(2,4, 0,0, 31,31, (12,10,22,255))    # very dark bg fabric
R(2,4, 0,0, 2,31, BODY)               # left panel edge
R(2,4, 29,0, 31,31, BODY)             # right panel edge
R(2,4, 0,0, 31,1, BODY)               # top edge
# subtle fold lines
for fy in range(6, 30, 8):
    R(2,4, 3,fy, 28,fy, (20,18,35,255))

# (3,4) Backdrop panel – with glow (concert look)
bg(3, 4)
R(3,4, 0,0, 31,31, (10,8,20,255))
R(3,4, 0,0, 2,31, BODY)
R(3,4, 29,0, 31,31, BODY)
R(3,4, 0,0, 31,1, BODY)
# central glow
for gy in range(0, 32):
    for gx in range(0, 32):
        dist = ((gx-15)**2 + (gy-10)**2)**0.5
        if dist < 14:
            alpha = int(180 - dist * 12)
            if alpha > 0:
                cur = img.getpixel((ox(3)+gx, oy(4)+gy))
                blended = (
                    min(255, cur[0] + int(PURP[0]*alpha/255)),
                    min(255, cur[1] + int(PURP[1]*alpha/255)),
                    min(255, cur[2] + int(PURP[2]*alpha/255)),
                    255
                )
                img.putpixel((ox(3)+gx, oy(4)+gy), blended)

# (4,4) Floor cable / wire
bg(4, 4)
# coiled cable and straight runs
L(4,4, 2,16, 29,16, (40,38,55,255), 2)   # main cable run
L(4,4, 8,16, 8,28, (35,33,50,255), 2)    # branch down
L(4,4, 20,16, 20,8, (35,33,50,255), 2)   # branch up
# cable wrap/tie markers
for cx in [5, 14, 24]:
    R(4,4, cx,15, cx+1,17, YELL2)
E(4,4, 4,24, 12,30, TR, (40,38,55,255), 2)  # coiled end

# (5,4) Power strip / stage power
bg(5, 4)
R(5,4, 4,10, 27,22, BODY2)             # strip housing
R(5,4, 4,10, 27,10, BODY3)
R(5,4, 4,10, 4,22, BODY3)
R(5,4, 27,10, 27,22, METAL)
R(5,4, 4,22, 27,22, METAL)
# outlets
for ox2 in [7, 13, 19]:
    R(5,4, ox2,12, ox2+4,20, BODY)
    P(5,4, ox2+1,15, METAL)
    P(5,4, ox2+3,15, METAL)
# power LED
P(5,4, 25,16, GRN)
# cable
L(5,4, 15,22, 15,30, (40,38,55,255), 2)

# (6,4) Security desk / door – top-down
bg(6, 4)
R(6,4, 2,6, 29,26, (32,28,50,255))    # desk
R(6,4, 2,6, 29,6, BODY3)              # top edge
R(6,4, 2,6, 2,26, BODY3)
R(6,4, 29,6, 29,26, METAL)
R(6,4, 2,26, 29,26, METAL)
# monitor on desk
R(6,4, 16,8, 26,16, BODY)
R(6,4, 17,9, 25,15, CYAN3)            # screen glow
P(6,4, 20,12, CYAN)                   # screen content
P(6,4, 22,12, CYAN)
# radio/device
R(6,4, 5,9, 13,14, BODY2)
P(6,4, 10,11, RED)                    # status LED
# guest list clipboard
R(6,4, 5,17, 13,25, WHT)
R(6,4, 5,17, 13,17, METAL)
for ly in range(19, 25, 2):
    R(6,4, 6,ly, 12,ly, (200,200,220,255))

# (7,4) Merch table – top-down
bg(7, 4)
R(7,4, 1,6, 30,26, (40,28,18,255))    # table surface
R(7,4, 1,6, 30,6, (65,45,25,255))     # table top edge
R(7,4, 1,6, 1,26, (65,45,25,255))
R(7,4, 30,6, 30,26, (25,18,10,255))
R(7,4, 1,26, 30,26, (25,18,10,255))
# merch items: shirts (rectangles), vinyl (circles)
R(7,4, 3,9, 10,18, PINK3)             # shirt 1
R(7,4, 4,10, 9,17, PINK2)
R(7,4, 12,9, 19,18, CYAN3)            # shirt 2
R(7,4, 13,10, 18,17, CYAN2)
E(7,4, 21,9, 28,16, BODY, METAL, 1)   # vinyl record
E(7,4, 23,11, 26,14, BODY2)           # label
# price tags
P(7,4, 5,20, WHT)
P(7,4, 14,20, WHT)
P(7,4, 24,20, WHT)

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = "/home/batestzu/vspot/workadventure/maps/assets/club_tileset.png"
img.save(out_path)
print(f"Saved: {out_path}")
print(f"Size:  {img.size[0]}×{img.size[1]}  ({COLS}×{ROWS} tiles at {T}px)")
