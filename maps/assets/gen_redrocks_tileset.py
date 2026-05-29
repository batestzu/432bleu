#!/usr/bin/env python3
"""
VSPOT Red Rocks Bonus Map Tileset Generator
Output: redrocks_tileset.png  (256 x 160 px — 8 cols x 5 rows x 32 px)

Tile index (col, row):
  Row 0 — Rock Faces & Ground
    (0,0) Rock face dark        (1,0) Rock face mid         (2,0) Rock face light
    (3,0) Rock ledge top        (4,0) Rock corner NE         (5,0) Rock corner NW
    (6,0) Dirt/dust ground      (7,0) Scrub grass patch
  Row 1 — Seating & Walkways
    (0,1) Concrete seat row (L) (1,1) Concrete seat row (M) (2,1) Concrete seat row (R)
    (3,1) Aisle walkway         (4,1) Seat (empty)           (5,1) Seat (occupied silhouette)
    (6,1) Handrail L            (7,1) Handrail R
  Row 2 — Stage Area
    (0,2) Stage platform        (1,2) Stage lip lit           (2,2) Stage monitor SM
    (3,2) Outdoor speaker tower (4,2) Stage amp stack         (5,2) Outdoor light rig
    (6,2) Backstage curtain     (7,2) Mixing desk (outdoor)
  Row 3 — Nature & Sky
    (0,3) Sky night stars       (1,3) Sky twilight purple     (2,3) Pine tree
    (3,3) Pine tree dark        (4,3) Cactus / scrub          (5,3) Boulders cluster
    (6,3) Moon                  (7,3) Stars scatter
  Row 4 — Atmosphere & Misc
    (0,4) Crowd barrier RR      (1,4) Photo pit floor         (2,4) Spotlight beam (warm)
    (3,4) Spotlight beam (cool) (4,4) Smoke trail             (5,4) Merch/food stall
    (6,4) Entrance arch L       (7,4) Entrance arch R
"""
from PIL import Image, ImageDraw
import math, random

random.seed(42)

T = 32
COLS, ROWS = 8, 5

# ── Palette ───────────────────────────────────────────────────────────────────
TR    = (0,   0,   0,   0)

# Rock/earth tones
ROCK1 = (90,  30,  15, 255)   # darkest red sandstone
ROCK2 = (140, 55,  28, 255)   # mid red
ROCK3 = (185, 90,  45, 255)   # lighter sandstone
ROCK4 = (220, 140, 75, 255)   # highlight orange
ROCK5 = (240, 185, 110, 255)  # very light catch
DIRT  = (110, 72,  40, 255)   # dirt/dust
DIRT2 = (145, 100, 60, 255)   # lighter dirt
GRAS1 = (35,  60,  25, 255)   # dark scrub
GRAS2 = (55,  90,  35, 255)   # mid scrub
GRAS3 = (80,  120, 50, 255)   # light scrub
SAND  = (195, 165, 110, 255)  # sandy ground
SAND2 = (225, 200, 145, 255)  # light sand

# Concrete / stadium
CON1  = (62,  65,  72, 255)   # dark concrete
CON2  = (88,  92,  102,255)   # mid concrete
CON3  = (120, 125, 138,255)   # light concrete
CON4  = (155, 160, 175,255)   # highlight
SEAT1 = (35,  45,  90, 255)   # seat plastic dark
SEAT2 = (55,  70,  140,255)   # seat plastic lit

# Sky
SKY1  = (8,   6,   25, 255)   # deep night
SKY2  = (20,  10,  55, 255)   # dark purple sky
SKY3  = (55,  20,  85, 255)   # twilight purple
SKY4  = (110, 45,  80, 255)   # horizon pink
SKY5  = (200, 100, 60, 255)   # sunset orange glow
STAR  = (240, 238, 255,255)   # star white
STAR2 = (200, 190, 255,255)   # star dim
MOON1 = (235, 235, 200,255)   # moon
MOON2 = (210, 208, 165,255)   # moon shadow

# Stage
STG1  = (28,  25,  45, 255)   # stage dark surface
STG2  = (45,  42,  68, 255)   # stage surface
STG3  = (68,  65,  95, 255)   # stage highlight
METAL = (82,  86, 112, 255)
MTL2  = (148, 155,180, 255)
BODY  = (22,  20,  40, 255)
BODY2 = (38,  35,  65, 255)
BODY3 = (62,  58,  95, 255)
WHT   = (235, 240,255, 255)
PINE1 = (18,  40,  22, 255)   # dark pine
PINE2 = (28,  62,  32, 255)   # mid pine
PINE3 = (42,  85,  45, 255)   # light pine

# Neons (used on stage tiles)
PINK  = (255, 18, 185,255)
CYAN  = (0,  225,255, 255)
YELL  = (255,235,  0, 255)
ORAN  = (255,120,  0, 255)
RED   = (255, 25, 45, 255)

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

def fill(tx, ty, c):
    R(tx, ty, 0, 0, T-1, T-1, c)

def noise_fill(tx, ty, c1, c2, seed=0):
    """Fill tile with noisy texture between two colors."""
    r2 = random.Random(seed)
    for y in range(T):
        for x in range(T):
            t = r2.random()
            col = tuple(int(c1[i]*(1-t) + c2[i]*t) for i in range(3)) + (255,)
            img.putpixel((ox(tx)+x, oy(ty)+y), col)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 0 — Rock Faces & Ground
# ══════════════════════════════════════════════════════════════════════════════

# (0,0) Rock face – darkest (vertical cliff face, slight texture)
noise_fill(0, 0, ROCK1, (70,22,10,255), seed=1)
for _ in range(12):
    rx = random.randint(0, 30); ry = random.randint(0, 30)
    rw = random.randint(2, 8); rh = random.randint(1, 3)
    shade = (ROCK2 if random.random() > 0.5 else (60,18,8,255))
    R(0,0, rx,ry, min(31,rx+rw),min(31,ry+rh), shade)
# vertical crack
L(0,0, 10,0, 8,31, (55,15,8,255), 1)
L(0,0, 22,0, 25,31, (55,15,8,255), 1)

# (1,0) Rock face – mid tone
noise_fill(1, 0, ROCK2, ROCK1, seed=2)
for _ in range(10):
    rx = random.randint(0,30); ry = random.randint(0,30)
    R(1,0, rx,ry, min(31,rx+random.randint(3,9)),min(31,ry+2),
      ROCK3 if random.random()>0.5 else ROCK1)
L(1,0, 18,0, 15,31, ROCK1, 1)

# (2,0) Rock face – light / sunlit
noise_fill(2, 0, ROCK3, ROCK2, seed=3)
for _ in range(8):
    rx = random.randint(0,29); ry = random.randint(0,29)
    R(2,0, rx,ry, min(31,rx+random.randint(2,7)),min(31,ry+2), ROCK4)
# highlight streak
L(2,0, 5,0, 3,31, ROCK4, 2)

# (3,0) Rock ledge top – transition from face to top surface
noise_fill(3, 0, ROCK2, ROCK1, seed=4)
R(3,0, 0,0, 31,6, ROCK3)              # top surface
noise_fill_rect = [(rx, ry) for rx in range(0,32,4) for ry in range(0,7)]
for rx, ry in noise_fill_rect:
    if random.random() > 0.6:
        P(3,0, rx, ry, ROCK4)
R(3,0, 0,7, 31,9, ROCK2)              # ledge shadow edge
for _ in range(6):
    rx = random.randint(0,30)
    R(3,0, rx,10, min(31,rx+random.randint(2,6)),12, ROCK1)

# (4,0) Rock corner – top-right (NE)
noise_fill(4, 0, ROCK2, ROCK1, seed=5)
R(4,0, 0,0, 20,6, ROCK3)              # top surface part
R(4,0, 20,0, 31,31, ROCK1)            # right cliff
R(4,0, 20,7, 22,31, (65,20,10,255))   # corner shadow
R(4,0, 0,7, 20,9, ROCK2)

# (5,0) Rock corner – top-left (NW)
noise_fill(5, 0, ROCK2, ROCK1, seed=6)
R(5,0, 12,0, 31,6, ROCK3)
R(5,0, 0,0, 12,31, ROCK1)
R(5,0, 12,7, 14,31, (65,20,10,255))
R(5,0, 12,7, 31,9, ROCK2)

# (6,0) Dirt / dust ground
noise_fill(6, 0, DIRT, DIRT2, seed=7)
for _ in range(15):
    rx = random.randint(0,30); ry = random.randint(0,30)
    P(6,0, rx,ry, SAND)

# (7,0) Scrub grass patch
noise_fill(7, 0, DIRT, (90,58,30,255), seed=8)
# grass tufts
for _ in range(18):
    gx = random.randint(1,30); gy = random.randint(2,30)
    gh = random.randint(2,5)
    col = GRAS2 if random.random()>0.4 else GRAS3
    L(7,0, gx,gy, gx,gy-gh, col, 1)
    if random.random()>0.5:
        L(7,0, gx+1,gy,gx+2,gy-gh+1, GRAS1, 1)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 1 — Seating & Walkways
# ══════════════════════════════════════════════════════════════════════════════

# (0,1) Concrete seat row – left end
fill(0, 1, CON1)
# tiered steps going down-right perspective
R(0,1, 0,0, 31,6, CON2)               # row top surface
R(0,1, 0,7, 31,9, CON1)               # riser face
R(0,1, 0,10, 31,16, CON3)             # next tier
R(0,1, 0,17, 31,19, CON1)
R(0,1, 0,20, 31,26, CON2)
R(0,1, 0,27, 31,29, CON1)
R(0,1, 0,30, 31,31, CON3)
# seats on tiers
for sx in [3, 10, 17, 24]:
    R(0,1, sx,2, sx+4,5, SEAT1)
    R(0,1, sx+1,2, sx+3,4, SEAT2)
for sx in [3, 10, 17, 24]:
    R(0,1, sx,12, sx+4,15, SEAT1)
    R(0,1, sx+1,12, sx+3,14, SEAT2)
# left edge wall
R(0,1, 0,0, 2,31, CON1)
R(0,1, 0,0, 2,0, CON4)

# (1,1) Concrete seat row – middle (same as 0 but no left-wall emphasis)
fill(1, 1, CON1)
R(1,1, 0,0, 31,6, CON2)
R(1,1, 0,7, 31,9, CON1)
R(1,1, 0,10, 31,16, CON3)
R(1,1, 0,17, 31,19, CON1)
R(1,1, 0,20, 31,26, CON2)
R(1,1, 0,27, 31,29, CON1)
R(1,1, 0,30, 31,31, CON3)
for sx in [3, 10, 17, 24]:
    R(1,1, sx,2, sx+4,5, SEAT1)
    R(1,1, sx+1,2, sx+3,4, SEAT2)
for sx in [3, 10, 17, 24]:
    R(1,1, sx,12, sx+4,15, SEAT1)
    R(1,1, sx+1,12, sx+3,14, SEAT2)

# (2,1) Concrete seat row – right end (mirror of left)
fill(2, 1, CON1)
R(2,1, 0,0, 31,6, CON2)
R(2,1, 0,7, 31,9, CON1)
R(2,1, 0,10, 31,16, CON3)
R(2,1, 0,17, 31,19, CON1)
R(2,1, 0,20, 31,26, CON2)
R(2,1, 0,27, 31,29, CON1)
R(2,1, 0,30, 31,31, CON3)
for sx in [3, 10, 17, 24]:
    R(2,1, sx,2, sx+4,5, SEAT1)
    R(2,1, sx+1,2, sx+3,4, SEAT2)
for sx in [3, 10, 17, 24]:
    R(2,1, sx,12, sx+4,15, SEAT1)
    R(2,1, sx+1,12, sx+3,14, SEAT2)
R(2,1, 29,0, 31,31, CON1)
R(2,1, 31,0, 31,31, CON4)

# (3,1) Aisle walkway – concrete
noise_fill(3, 1, CON2, CON1, seed=20)
# edge lines
R(3,1, 0,0, 2,31, CON1)
R(3,1, 29,0, 31,31, CON1)
R(3,1, 0,0, 31,0, CON4)
R(3,1, 0,31, 31,31, CON4)
# step edge marks
for sy in range(6, 30, 10):
    R(3,1, 3,sy, 28,sy+1, CON3)
    P(3,1, 5,sy, (255,220,0,255))      # glow step marker L
    P(3,1, 26,sy, (255,220,0,255))     # glow step marker R

# (4,1) Seat – empty (single seat tile, top-down)
fill(4, 1, CON1)
R(4,1, 4,10, 27,26, SEAT1)            # seat
R(4,1, 4,6, 27,10, (28,25,45,255))    # seat back
R(4,1, 4,6, 27,6, SEAT2)              # top of back
R(4,1, 4,10, 4,26, (20,18,38,255))    # shadow L
R(4,1, 27,10, 27,26, (20,18,38,255))  # shadow R
R(4,1, 4,26, 27,27, CON2)             # seat front

# (5,1) Seat – occupied (person silhouette top-down)
fill(5, 1, CON1)
R(5,1, 4,10, 27,26, SEAT1)
R(5,1, 4,6, 27,10, (28,25,45,255))
R(5,1, 4,6, 27,6, SEAT2)
# person: rounded head + shoulders
E(5,1, 10,12, 21,23, (55,42,35,255))  # body
E(5,1, 12,10, 19,17, (200,160,120,255)) # head
R(5,1, 4,26, 27,27, CON2)

# (6,1) Handrail – left
fill(6, 1, CON1)
R(6,1, 12,0, 16,31, METAL)            # post
R(6,1, 12,0, 16,0, MTL2)
# angled rail going down-right
L(6,1, 14,0, 31,16, METAL, 3)
L(6,1, 14,0, 31,16, MTL2, 1)
# base footing
R(6,1, 9,28, 19,31, METAL)

# (7,1) Handrail – right (mirror)
fill(7, 1, CON1)
R(7,1, 15,0, 19,31, METAL)
R(7,1, 15,0, 19,0, MTL2)
L(7,1, 17,0, 0,16, METAL, 3)
L(7,1, 17,0, 0,16, MTL2, 1)
R(7,1, 12,28, 22,31, METAL)


# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 — Stage Area
# ══════════════════════════════════════════════════════════════════════════════

# (0,2) Stage platform – outdoor (raw wood/steel deck)
fill(0, 2, STG1)
# deck planks running horizontal
for y in range(0, 32, 4):
    R(0,2, 0,y, 31,y+2, STG2)
    R(0,2, 0,y, 31,y, STG3)
# plank nails/screws
for nx in range(3, 30, 6):
    for ny in range(1, 30, 4):
        P(0,2, nx,ny, METAL)

# (1,2) Stage lip lit – outdoor (front edge with warm footlights)
fill(1, 2, STG1)
R(1,2, 0,0, 31,22, STG2)              # stage surface
for y in range(0, 22, 4):
    R(1,2, 0,y, 31,y+2, STG2)
    R(1,2, 0,y, 31,y, STG3)
R(1,2, 0,23, 31,28, (38,30,18,255))   # front face
R(1,2, 0,23, 31,23, ROCK4)            # warm edge highlight
# footlights
for fx in range(3, 30, 5):
    P(1,2, fx,24, YELL)
    P(1,2, fx+1,24, ORAN)

# (2,2) Outdoor stage monitor small
fill(2, 2, STG1)
pts = [(3,8),(28,8),(30,26),(1,26)]
draw.polygon([(ox(2)+x, oy(2)+y) for x,y in pts], fill=BODY2)
R(2,2, 4,9, 27,12, BODY2)
R(2,2, 4,13, 27,24, BODY)
for gy in range(14,24,2):
    for gx in range(5,27,3):
        R(2,2, gx,gy, gx+1,gy, BODY2)
R(2,2, 2,26, 29,27, METAL)

# (3,2) Outdoor speaker tower – tall PA system
fill(3, 2, STG1)
R(3,2, 8,0, 23,29, BODY2)             # tower body
R(3,2, 9,1, 22,28, BODY)
for gy in range(2, 28, 4):
    E(3,2, 10,gy, 21,gy+3, BODY2, METAL, 1)
R(3,2, 8,0, 23,0, BODY2)
R(3,2, 8,0, 8,29, BODY2)
R(3,2, 23,0, 23,29, METAL)
R(3,2, 8,29, 23,29, METAL)
# base feet
R(3,2, 5,29, 26,31, METAL)
R(3,2, 6,30, 9,31, BODY)
R(3,2, 22,30, 25,31, BODY)

# (4,2) Stage amp stack (outdoor / road case)
fill(4, 2, STG1)
R(4,2, 3,2, 28,29, BODY2)
# road case hardware: corner brackets
for cx,cy in [(3,2),(26,2),(3,27),(26,27)]:
    R(4,2, cx,cy, cx+3,cy+3, METAL)
# grill cloth
R(4,2, 5,5, 26,24, BODY)
for gy in range(6,24,3):
    for gx in range(6,26,3):
        R(4,2, gx,gy, gx+1,gy+1, BODY2)
# handle
R(4,2, 12,3, 19,4, METAL)
R(4,2, 3,2, 28,2, MTL2)
R(4,2, 3,2, 3,29, MTL2)
R(4,2, 28,2, 28,29, METAL)
R(4,2, 3,29, 28,29, METAL)

# (5,2) Outdoor light rig – on stanchion/stand
fill(5, 2, STG1)
L(5,2, 15,26, 15,10, METAL, 2)        # stanchion pole
R(5,2, 10,26, 20,28, METAL)           # base
R(5,2, 6,28, 8,30, METAL); R(5,2, 22,28, 24,30, METAL)  # feet
R(5,2, 4,8, 27,12, BODY2)             # top bar
R(5,2, 4,8, 27,8, BODY3)
for px2 in [6, 11, 16, 21]:
    E(5,2, px2,4, px2+4,12, ORAN, YELL, 1)  # par cans

# (6,2) Backstage curtain / leg
fill(6, 2, (15,12,25,255))
# black curtain with fold lines
for fx in range(0, 32, 4):
    shade = random.randint(0, 10)
    R(6,2, fx,0, fx+2,31, (10+shade, 8+shade, 18+shade, 255))
R(6,2, 0,0, 2,31, (30,28,48,255))     # edge highlight
# subtle neon bleed from stage
for y in range(0, 32):
    alpha = max(0, 60 - y*2)
    if alpha > 0:
        cur = img.getpixel((ox(6)+31, oy(2)+y))
        img.putpixel((ox(6)+31, oy(2)+y),
                     (min(255,cur[0]+alpha//4), cur[1], min(255,cur[2]+alpha//3), 255))

# (7,2) Mixing desk (outdoor FOH) – top-down
fill(7, 2, STG1)
R(7,2, 1,5, 30,27, BODY2)
R(7,2, 1,5, 30,5, BODY2)
R(7,2, 1,5, 1,27, BODY2)
R(7,2, 30,5, 30,27, METAL)
R(7,2, 1,27, 30,27, METAL)
# fader channels
for cx in range(3, 28, 4):
    R(7,2, cx,7, cx+2,25, BODY)
    R(7,2, cx,16, cx+2,18, MTL2)
# master section
R(7,2, 24,7, 28,25, BODY)
R(7,2, 25,14, 27,17, WHT)
# laptop/screen
R(7,2, 3,2, 12,5, BODY)
R(7,2, 4,3, 11,4, (0,55,80,255))


# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 — Nature & Sky
# ══════════════════════════════════════════════════════════════════════════════

# (0,3) Sky – deep night with stars
fill(0, 3, SKY1)
rng = random.Random(30)
for _ in range(28):
    sx = rng.randint(0,31); sy = rng.randint(0,31)
    brightness = rng.random()
    col = STAR if brightness > 0.6 else STAR2
    P(0,3, sx,sy, col)
    if brightness > 0.85:
        if sx>0: P(0,3, sx-1,sy, (180,178,220,255))
        if sx<31: P(0,3, sx+1,sy, (180,178,220,255))

# (1,3) Sky – twilight purple/pink gradient
for y in range(T):
    t = y / 31.0
    r = int(SKY3[0]*(1-t) + SKY5[0]*t)
    g = int(SKY3[1]*(1-t) + SKY5[1]*t)
    b = int(SKY3[2]*(1-t) + SKY5[2]*t)
    R(1,3, 0,y, 31,y, (r,g,b,255))
# sparse stars in upper half
rng2 = random.Random(31)
for _ in range(12):
    sx = rng2.randint(0,31); sy = rng2.randint(0,14)
    P(1,3, sx,sy, STAR2)

# (2,3) Pine tree – tall
fill(2, 3, TR)
# trunk
R(2,3, 13,22, 18,30, (80,50,25,255))
R(2,3, 14,22, 17,30, (110,70,35,255))
# canopy layers
draw.polygon([(ox(2)+15,oy(3)+2),(ox(2)+4,oy(3)+16),(ox(2)+26,oy(3)+16)], fill=PINE2)
draw.polygon([(ox(2)+15,oy(3)+8),(ox(2)+5,oy(3)+20),(ox(2)+25,oy(3)+20)], fill=PINE2)
draw.polygon([(ox(2)+15,oy(3)+13),(ox(2)+4,oy(3)+24),(ox(2)+26,oy(3)+24)], fill=PINE3)
# highlights
draw.polygon([(ox(2)+15,oy(3)+2),(ox(2)+15,oy(3)+16),(ox(2)+19,oy(3)+16)], fill=PINE3)
draw.polygon([(ox(2)+15,oy(3)+8),(ox(2)+15,oy(3)+20),(ox(2)+19,oy(3)+20)], fill=PINE3)

# (3,3) Pine tree – dark (silhouette, backlit)
fill(3, 3, TR)
R(3,3, 13,23, 18,30, (45,28,12,255))
draw.polygon([(ox(3)+15,oy(3)+2),(ox(3)+4,oy(3)+16),(ox(3)+26,oy(3)+16)], fill=PINE1)
draw.polygon([(ox(3)+15,oy(3)+8),(ox(3)+5,oy(3)+20),(ox(3)+25,oy(3)+20)], fill=PINE1)
draw.polygon([(ox(3)+15,oy(3)+13),(ox(3)+4,oy(3)+24),(ox(3)+26,oy(3)+24)], fill=PINE1)
# backlit edge glow (warm orange from stage lights below)
L(3,3, 4,16, 26,16, (120,80,30,180), 1)

# (4,3) Cactus / scrub bush
fill(4, 3, TR)
noise_fill(4, 3, DIRT, (90,55,28,255), seed=40)
# cactus
R(4,3, 14,8, 17,26, GRAS1)            # main stem
R(4,3, 15,9, 16,25, GRAS2)            # highlight
R(4,3, 7,14, 14,17, GRAS1)            # arm L
R(4,3, 7,11, 10,14, GRAS1)
R(4,3, 17,14, 24,17, GRAS1)           # arm R
R(4,3, 21,11, 24,14, GRAS1)
# spines
for sy in range(10, 26, 4):
    P(4,3, 13,sy, ROCK5); P(4,3, 18,sy, ROCK5)
# ground scrub
for _ in range(8):
    gx = random.randint(1,30)
    L(4,3, gx,27, gx,25, GRAS2, 1)

# (5,3) Boulder cluster
fill(5, 3, TR)
noise_fill(5, 3, DIRT, (90,55,28,255), seed=50)
# boulders
E(5,3, 2,10, 16,24, ROCK2, ROCK1, 1)
R(5,3, 2,10, 14,17, ROCK3)
E(5,3, 12,14, 28,28, ROCK1, (55,15,8,255), 1)
R(5,3, 12,14, 26,22, ROCK2)
E(5,3, 6,4, 18,14, ROCK3, ROCK2, 1)
R(5,3, 6,4, 16,10, ROCK4)
# crack lines
L(5,3, 8,8, 5,20, (55,15,8,255), 1)
L(5,3, 20,16, 25,24, (55,15,8,255), 1)

# (6,3) Moon
fill(6, 3, SKY1)
# background stars
rng3 = random.Random(60)
for _ in range(15):
    sx = rng3.randint(0,31); sy = rng3.randint(0,31)
    P(6,3, sx,sy, STAR2)
E(6,3, 8,4, 23,19, MOON1)
E(6,3, 12,4, 27,18, SKY1)             # crescent cutout
# moon glow
for y in range(T):
    for x in range(T):
        dist = ((x-15)**2 + (y-11)**2)**0.5
        if 9 < dist < 18:
            alpha = int(40 - (dist-9)*4)
            if alpha > 0:
                cur = img.getpixel((ox(6)+x, oy(3)+y))
                img.putpixel((ox(6)+x, oy(3)+y),
                             (min(255,cur[0]+alpha),min(255,cur[1]+alpha),
                              min(255,cur[2]+alpha//2),255))

# (7,3) Stars scatter (dense star field)
fill(7, 3, SKY2)
rng4 = random.Random(70)
for _ in range(40):
    sx = rng4.randint(0,31); sy = rng4.randint(0,31)
    b = rng4.random()
    if b > 0.8: col = STAR
    elif b > 0.5: col = STAR2
    else: col = (150,145,200,255)
    P(7,3, sx,sy, col)
# milky way smear
for x in range(T):
    if rng4.random() > 0.55:
        y = int(8 + x*0.4 + rng4.randint(-3,3))
        if 0 <= y < T:
            alpha = rng4.randint(30,80)
            cur = img.getpixel((ox(7)+x, oy(3)+y))
            img.putpixel((ox(7)+x, oy(3)+y),
                         (min(255,cur[0]+alpha//3), min(255,cur[1]+alpha//4),
                          min(255,cur[2]+alpha), 255))


# ══════════════════════════════════════════════════════════════════════════════
# ROW 4 — Atmosphere & Misc
# ══════════════════════════════════════════════════════════════════════════════

# (0,4) Crowd barrier – Red Rocks style (galvanized steel)
fill(0, 4, DIRT)
R(0,4, 0,8, 31,10, MTL2)             # top rail
R(0,4, 0,18, 31,20, METAL)           # mid rail
R(0,4, 0,28, 31,30, METAL)           # bottom rail
R(0,4, 0,8, 31,8, WHT)               # top rail highlight
# vertical spacers
for vx in [5, 13, 21, 29]:
    R(0,4, vx,8, vx+1,30, METAL)
# feet
R(0,4, 2,29, 6,31, METAL)
R(0,4, 25,29, 29,31, METAL)

# (1,4) Photo pit floor – gravel/dirt
noise_fill(1, 4, (75,55,35,255), DIRT, seed=80)
for _ in range(20):
    gx = random.randint(0,30); gy = random.randint(0,30)
    P(1,4, gx,gy, SAND)
for _ in range(8):
    gx = random.randint(0,30); gy = random.randint(0,30)
    P(1,4, gx,gy, ROCK3)

# (2,4) Spotlight beam – warm (from above, top-down = wide circle)
fill(2, 4, STG1)
for y in range(T):
    for x in range(T):
        dist = ((x-15)**2 + (y-15)**2)**0.5
        if dist < 14:
            alpha = int(200 - dist*13)
            if alpha > 0:
                cur = img.getpixel((ox(2)+x, oy(4)+y))
                img.putpixel((ox(2)+x, oy(4)+y),
                             (min(255,cur[0]+int(ORAN[0]*alpha/255)),
                              min(255,cur[1]+int(ORAN[1]*alpha/255)),
                              min(255,cur[2]+int(ORAN[2]*alpha/255)), 255))

# (3,4) Spotlight beam – cool (cyan/blue)
fill(3, 4, STG1)
for y in range(T):
    for x in range(T):
        dist = ((x-15)**2 + (y-15)**2)**0.5
        if dist < 14:
            alpha = int(200 - dist*13)
            if alpha > 0:
                cur = img.getpixel((ox(3)+x, oy(4)+y))
                img.putpixel((ox(3)+x, oy(4)+y),
                             (min(255,cur[0]+int(CYAN[0]*alpha/255)),
                              min(255,cur[1]+int(CYAN[1]*alpha/255)),
                              min(255,cur[2]+int(CYAN[2]*alpha/255)), 255))

# (4,4) Smoke trail (vertical, rising from smoke machine)
for y in range(T):
    for x in range(T):
        dist = ((x-15)**2)**0.5
        fade = y / 31.0
        alpha = max(0, int(100 - dist*8 - fade*80))
        if alpha > 0:
            img.putpixel((ox(4)+x, oy(4)+y), (200,210,230,alpha))
# smoke machine base
R(4,4, 8,24, 23,31, BODY2)
R(4,4, 8,24, 23,24, BODY2)
P(4,4, 11,27, (0,200,100,255))

# (5,4) Merch / food stall – top-down
fill(5, 4, DIRT2)
R(5,4, 1,4, 30,20, (50,35,18,255))    # stall counter
R(5,4, 1,4, 30,4, (80,56,28,255))     # counter top edge
R(5,4, 1,4, 1,20, (80,56,28,255))
R(5,4, 30,4, 30,20, (30,20,10,255))
R(5,4, 1,20, 30,20, (30,20,10,255))
# awning/canopy
R(5,4, 0,0, 31,3, RED)
for ax in range(0, 32, 6):
    R(5,4, ax,0, ax+3,3, (200,20,35,255))
# items on counter
R(5,4, 4,6, 10,12, PINK)              # shirt
R(5,4, 13,6, 19,12, CYAN)             # shirt
E(5,4, 22,6, 28,12, BODY, METAL, 1)   # record
P(5,4, 10,15, WHT)                    # price tag
P(5,4, 17,15, WHT)

# (6,4) Entrance arch – left half
fill(6, 4, TR)
noise_fill(6, 4, ROCK2, ROCK1, seed=90)
# arch shape (left pillar + arch curve)
R(6,4, 0,0, 14,31, ROCK2)
R(6,4, 0,0, 14,0, ROCK3)
R(6,4, 0,0, 0,31, ROCK3)
R(6,4, 14,0, 14,31, ROCK1)
# arch detail
for y in range(5, 20, 4):
    R(6,4, 2,y, 12,y+1, ROCK3)
R(6,4, 2,2, 12,4, ROCK4)
# arch opening begins right side
draw.arc([ox(6)+14,oy(4)+0, ox(6)+44,oy(4)+30], start=90, end=180,
         fill=ROCK3, width=3)

# (7,4) Entrance arch – right half
fill(7, 4, TR)
noise_fill(7, 4, ROCK2, ROCK1, seed=91)
R(7,4, 17,0, 31,31, ROCK2)
R(7,4, 17,0, 31,0, ROCK3)
R(7,4, 31,0, 31,31, ROCK3)
R(7,4, 17,0, 17,31, ROCK1)
for y in range(5, 20, 4):
    R(7,4, 19,y, 29,y+1, ROCK3)
R(7,4, 19,2, 29,4, ROCK4)
draw.arc([ox(7)-12,oy(4)+0, ox(7)+17,oy(4)+30], start=0, end=90,
         fill=ROCK3, width=3)


# ── Save ──────────────────────────────────────────────────────────────────────
out_path = "/home/batestzu/vspot/workadventure/maps/assets/redrocks_tileset.png"
img.save(out_path)
print(f"Saved: {out_path}")
print(f"Size:  {img.size[0]}×{img.size[1]}  ({COLS}×{ROWS} tiles at {T}px)")
