#!/usr/bin/env python3
"""Generate bleu-props.png/.tsx — custom fantasy-concert props for the 432 BLEU map lab.

Art is drawn at 16px base scale, then upscaled 2x nearest-neighbor so it matches the
chunky look of the other 2x-upscaled 16px tilesets (zelda-like, scifi).

Sheet layout (32px tiles after upscale, 6 cols x 4 rows):
  rows 0-1 (tall, 1x2): speaker | crystal light | harp | banner | crystal mic
  row  2  (1x1): wedge monitor | blue torch | lute | drum | rune amp
  row  3: DJ console (2x1) | goblet | martini | horn tankard
"""
from PIL import Image, ImageDraw
import os

P = dict(
    k=(24, 24, 32, 255),     # outline
    D=(51, 51, 63, 255),     # dark stone
    G=(77, 77, 94, 255),     # mid stone
    L=(113, 113, 138, 255),  # light stone
    w=(79, 49, 32, 255),     # dark wood
    W=(122, 78, 44, 255),    # mid wood
    V=(160, 108, 60, 255),   # light wood
    c=(111, 240, 230, 255),  # bright cyan (brand glow)
    C=(47, 179, 172, 255),   # mid cyan
    t=(23, 99, 95, 255),     # dark teal
    p=(192, 122, 232, 255),  # bright purple
    P=(135, 70, 184, 255),   # mid purple
    y=(242, 201, 76, 255),   # gold
    Y=(176, 138, 46, 255),   # dark gold
    x=(245, 245, 245, 255),  # white
    B=(46, 79, 201, 255),    # brand blue
    b=(28, 47, 122, 255),    # dark blue
    g=(216, 238, 245, 150),  # glass
    f=(111, 240, 230, 80),   # faint cyan glow
)


def sprite(w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def speaker():  # 16x32 rune-woofer speaker stack
    im, d = sprite(16, 32)
    d.rounded_rectangle([1, 0, 14, 31], radius=2, fill=P["W"], outline=P["k"])
    d.rectangle([3, 2, 12, 29], fill=P["G"], outline=P["D"])
    d.point([(2, 1), (13, 1), (2, 30), (13, 30)], fill=P["y"])  # bolts
    # tweeter crystal
    d.polygon([(7, 3), (8, 3), (11, 6), (8, 10), (7, 10), (4, 6)], fill=P["C"], outline=P["k"])
    d.polygon([(7, 5), (8, 5), (9, 6), (8, 8), (7, 8), (6, 6)], fill=P["c"])
    d.point([(7, 4)], fill=P["x"])
    # rune woofer
    d.ellipse([2, 15, 13, 27], fill=P["t"], outline=P["k"])
    d.ellipse([4, 17, 11, 25], outline=P["C"])
    d.ellipse([6, 19, 9, 23], fill=P["C"])
    d.point([(7, 21), (8, 21)], fill=P["c"])
    d.point([(7, 16), (8, 16), (12, 21), (3, 21), (7, 26), (8, 26)], fill=P["c"])  # rune ticks
    return im


def crystal_light():  # 16x32 floating crystal spotlight + beam
    im, d = sprite(16, 32)
    for i, yy in enumerate(range(13, 32)):  # light cone, fading
        a = max(12, 70 - i * 3)
        half = 1 + i // 3
        d.line([(7 - half, yy), (8 + half, yy)], fill=(111, 240, 230, a))
    d.rectangle([6, 0, 9, 1], fill=P["G"], outline=P["k"])
    d.point([(7, 2), (8, 2)], fill=P["k"])  # chain
    d.polygon([(7, 3), (8, 3), (12, 8), (8, 14), (7, 14), (3, 8)], fill=P["c"], outline=P["k"])
    d.polygon([(8, 4), (11, 8), (8, 13)], fill=P["C"])  # right facet shade
    d.line([(6, 5), (5, 7)], fill=P["x"])  # sparkle
    d.point([(2, 4), (13, 11)], fill=P["f"])
    return im


def harp():  # 16x32 gilded floor harp
    im, d = sprite(16, 32)
    d.polygon([(0, 29), (15, 29), (13, 26), (2, 26)], fill=P["W"], outline=P["k"])
    d.arc([2, 1, 17, 17], 190, 320, fill=P["k"], width=4)  # neck outline
    d.arc([3, 2, 16, 16], 195, 315, fill=P["y"], width=2)  # gold neck
    d.rectangle([2, 8, 4, 26], fill=P["y"], outline=P["k"])
    d.line([(4, 9), (4, 25)], fill=P["Y"])  # column shade
    d.polygon([(12, 11), (14, 13), (14, 26), (12, 26)], fill=P["Y"], outline=P["k"])
    for sx, ty in ((6, 6), (8, 7), (10, 9)):  # strings
        d.line([(sx, ty), (sx, 25)], fill=(245, 245, 245, 190))
    d.point([(3, 7), (13, 12)], fill=P["c"])
    return im


def banner():  # 16x32 hanging brand banner w/ music-note rune
    im, d = sprite(16, 32)
    d.rectangle([1, 0, 14, 1], fill=P["W"], outline=P["k"])
    d.point([(0, 0), (15, 0), (0, 1), (15, 1)], fill=P["y"])  # finials
    d.rectangle([3, 3, 12, 27], fill=P["B"])
    d.line([(3, 3), (3, 27)], fill=P["b"])
    d.line([(12, 3), (12, 27)], fill=P["b"])
    d.line([(3, 3), (12, 3)], fill=P["y"])  # trim
    d.point([(5, 2), (10, 2)], fill=P["k"])  # hangers
    d.polygon([(5, 27), (10, 27), (8, 22), (7, 22)], fill=(0, 0, 0, 0))  # swallowtail notch
    # music-note rune
    d.line([(9, 10), (9, 16)], fill=P["c"])
    d.ellipse([6, 15, 9, 18], fill=P["c"])
    d.point([(10, 10), (11, 11), (11, 12)], fill=P["c"])
    d.point([(7, 16)], fill=P["x"])
    return im


def crystal_mic():  # 16x32 voice-crystal on a stand
    im, d = sprite(16, 32)
    d.point([(3, 4), (12, 7), (5, 0), (11, 1), (2, 9)], fill=P["f"])  # drifting motes
    d.line([(7, 26), (3, 30)], fill=P["G"], width=2)
    d.line([(8, 26), (12, 30)], fill=P["G"], width=2)
    d.rectangle([7, 12, 8, 27], fill=P["G"])
    d.line([(7, 12), (7, 26)], fill=P["L"])
    d.rectangle([6, 10, 9, 11], fill=P["y"], outline=P["Y"])  # mount ring
    d.polygon([(7, 2), (8, 2), (11, 6), (8, 10), (7, 10), (4, 6)], fill=P["c"], outline=P["k"])
    d.polygon([(8, 3), (10, 6), (8, 9)], fill=P["C"])
    d.point([(6, 4)], fill=P["x"])
    return im


def wedge():  # 16x16 stage monitor wedge (viewed from front-above)
    im, d = sprite(16, 16)
    d.polygon([(2, 4), (13, 4), (15, 10), (15, 15), (0, 15), (0, 10)], fill=P["D"], outline=P["k"])
    d.polygon([(3, 5), (12, 5), (14, 10), (1, 10)], fill=P["G"])  # slanted grill face
    d.line([(3, 5), (12, 5)], fill=P["L"])  # top edge highlight
    for sx in (4, 6, 8, 10):
        d.line([(sx, 6), (sx + 1, 9)], fill=P["t"])
    d.line([(1, 11), (14, 11)], fill=P["k"])  # face/body seam
    d.point([(2, 13)], fill=P["c"])  # indicator gem
    return im


def torch():  # 16x16 wall torch, blue flame
    im, d = sprite(16, 16)
    d.ellipse([4, 1, 11, 8], fill=(111, 240, 230, 45))
    d.rectangle([6, 12, 9, 15], fill=P["G"], outline=P["k"])
    d.polygon([(5, 9), (10, 9), (9, 12), (6, 12)], fill=P["Y"], outline=P["k"])
    d.polygon([(7, 1), (10, 4), (9, 8), (6, 8), (5, 4)], fill=P["C"])
    d.polygon([(7, 3), (9, 5), (8, 7), (7, 7), (6, 5)], fill=P["c"])
    d.point([(7, 5), (8, 6)], fill=P["x"])
    return im


def lute():  # 16x16 bard's lute
    im, d = sprite(16, 16)
    d.rectangle([0, 0, 2, 2], fill=P["w"], outline=P["k"])  # pegbox
    d.line([(2, 2), (6, 7)], fill=P["w"], width=2)          # neck
    d.ellipse([4, 6, 14, 15], fill=P["V"], outline=P["k"])  # body
    d.arc([5, 8, 13, 15], 20, 160, fill=P["W"])             # body shade
    d.ellipse([8, 9, 11, 12], fill=P["w"], outline=P["k"])  # soundhole
    d.rectangle([12, 10, 13, 12], fill=P["w"])              # bridge
    d.line([(2, 2), (12, 10)], fill=(245, 245, 245, 170))   # strings
    d.line([(2, 3), (12, 11)], fill=(245, 245, 245, 120))
    return im


def drum():  # 16x16 floor drum
    im, d = sprite(16, 16)
    d.rectangle([2, 6, 13, 14], fill=P["V"], outline=P["k"])
    for sx in (4, 7, 10):  # lacing
        d.line([(sx, 7), (sx + 1, 13)], fill=P["Y"])
    d.line([(3, 14), (12, 14)], fill=P["w"])
    d.ellipse([2, 3, 13, 9], fill=P["x"], outline=P["k"])  # head
    d.ellipse([3, 4, 12, 8], outline=P["L"])
    return im


def amp():  # 16x16 rune amplifier
    im, d = sprite(16, 16)
    d.rounded_rectangle([1, 2, 14, 14], radius=2, fill=P["W"], outline=P["k"])
    d.rectangle([2, 3, 13, 5], fill=P["w"])
    d.rectangle([3, 3, 4, 4], fill=P["y"])
    d.rectangle([7, 3, 8, 4], fill=P["y"])
    d.rectangle([11, 3, 12, 4], fill=P["Y"])
    d.rectangle([3, 6, 12, 13], fill=P["G"], outline=P["D"])
    d.ellipse([5, 7, 10, 12], fill=P["t"], outline=P["k"])
    d.ellipse([6, 8, 9, 11], outline=P["C"])
    d.point([(7, 9), (8, 10)], fill=P["c"])
    return im


def dj_console():  # 32x16 arcane DJ altar, two rune turntables
    im, d = sprite(32, 16)
    d.rounded_rectangle([0, 2, 31, 8], radius=1, fill=P["L"], outline=P["k"])
    d.rectangle([1, 9, 30, 14], fill=P["G"], outline=P["k"])
    d.rectangle([2, 14, 5, 15], fill=P["D"])
    d.rectangle([26, 14, 29, 15], fill=P["D"])
    for ox in (3, 21):  # turntables
        d.ellipse([ox, 3, ox + 7, 8], fill=P["t"], outline=P["k"])
        d.ellipse([ox + 2, 4, ox + 5, 7], outline=P["C"])
        d.point([(ox + 3, 5), (ox + 4, 6)], fill=P["c"])
    d.rectangle([13, 3, 18, 7], fill=P["D"], outline=P["k"])  # fader panel
    d.point([(14, 4), (16, 4), (14, 6)], fill=P["y"])
    d.point([(17, 5)], fill=P["p"])
    d.polygon([(15, 10), (16, 11), (15, 12), (14, 11)], fill=P["c"])  # front rune
    d.point([(7, 11), (24, 11)], fill=P["C"])
    return im


def goblet():  # 16x16 Bleu Elixir — glowing cyan goblet
    im, d = sprite(16, 16)
    d.point([(5, 0), (10, 1), (7, 0)], fill=P["f"])  # rising fizz
    d.polygon([(3, 2), (12, 2), (11, 6), (9, 8), (6, 8), (4, 6)], fill=P["c"], outline=P["k"])
    d.line([(5, 3), (10, 3)], fill=P["x"])
    d.point([(7, 5), (9, 4), (5, 5)], fill=P["x"])  # bubbles
    d.rectangle([7, 9, 8, 11], fill=P["y"])
    d.rectangle([4, 12, 11, 13], fill=P["y"], outline=P["Y"])
    return im


def martini():  # 16x16 purple potion martini, crystal garnish
    im, d = sprite(16, 16)
    d.polygon([(2, 3), (13, 3), (8, 8), (7, 8)], fill=P["g"])
    d.polygon([(3, 3), (12, 3), (8, 6), (7, 6)], fill=P["p"])
    d.line([(5, 4), (7, 4)], fill=P["x"])  # swirl
    d.point([(9, 5)], fill=P["x"])
    d.line([(2, 2), (13, 2)], fill=P["k"])  # rim
    d.line([(2, 3), (7, 8)], fill=P["k"])
    d.line([(13, 3), (8, 8)], fill=P["k"])
    d.line([(9, 4), (12, 1)], fill=P["k"])  # pick
    d.polygon([(12, 0), (13, 1), (12, 2), (11, 1)], fill=P["c"])  # crystal garnish
    d.rectangle([7, 9, 8, 12], fill=P["L"])
    d.rectangle([4, 13, 11, 14], fill=P["L"], outline=P["k"])
    return im


def horn():  # 16x16 foaming horn tankard
    im, d = sprite(16, 16)
    d.point([(8, 0), (10, 1)], fill=P["f"])  # steam
    # body: wide mouth top-left tapering to a curled gold tip bottom-right
    d.polygon([(2, 2), (8, 2), (11, 4), (13, 7), (13, 11), (11, 14), (8, 14), (8, 12),
               (10, 10), (10, 7), (7, 5), (2, 5)], fill=P["V"], outline=P["k"])
    d.line([(3, 3), (6, 3)], fill=P["W"])  # inner shade under rim
    d.line([(11, 5), (12, 7)], fill=P["Y"])   # gold band
    d.line([(12, 10), (11, 12)], fill=P["Y"])  # gold band
    d.point([(9, 13), (8, 14), (9, 14)], fill=P["y"])  # metal tip
    d.ellipse([1, 0, 8, 3], fill=P["x"], outline=P["k"])  # foam cap over mouth
    d.point([(3, 0), (6, 1)], fill=P["c"])  # sparkling foam
    return im


def bar_piece(kind):  # 16x16 counter: wood top, runed stone front; mid tiles seamlessly
    im, d = sprite(16, 16)
    d.line([(0, 0), (15, 0)], fill=P["k"])
    d.rectangle([0, 1, 15, 4], fill=P["V"])          # wood top
    d.point([(3, 2), (9, 3), (13, 2)], fill=P["w"])  # grain
    d.line([(0, 5), (15, 5)], fill=P["w"])           # lip
    d.rectangle([0, 6, 15, 14], fill=P["G"])         # stone front
    d.line([(0, 10), (15, 10)], fill=P["D"])         # brick courses
    for sx in (4, 12):
        d.line([(sx, 6), (sx, 9)], fill=P["D"])
    for sx in (0, 8):
        d.line([(sx, 11), (sx, 14)], fill=P["D"])
    d.polygon([(7, 7), (8, 7), (9, 8), (8, 9), (7, 9), (6, 8)], fill=P["C"])  # rune inlay
    d.point([(7, 8), (8, 8)], fill=P["c"])
    d.line([(0, 15), (15, 15)], fill=P["k"])
    if kind == "left":
        d.line([(0, 0), (0, 15)], fill=P["k"])
        d.line([(1, 1), (1, 4)], fill=P["w"])
        d.line([(1, 6), (1, 14)], fill=P["D"])
    if kind == "right":
        d.line([(15, 0), (15, 15)], fill=P["k"])
        d.line([(14, 1), (14, 4)], fill=P["w"])
        d.line([(14, 6), (14, 14)], fill=P["D"])
    return im


def keg():  # 16x16 keg with cyan drip tap
    im, d = sprite(16, 16)
    d.rounded_rectangle([3, 2, 12, 13], radius=2, fill=P["V"], outline=P["k"])
    d.point([(6, 4), (9, 8), (6, 10)], fill=P["W"])  # staves
    d.line([(3, 4), (12, 4)], fill=P["Y"])           # hoops
    d.line([(3, 11), (12, 11)], fill=P["Y"])
    d.line([(4, 3), (4, 10)], fill=(245, 245, 245, 90))  # sheen
    d.rectangle([7, 13, 8, 14], fill=P["Y"])         # tap
    d.point([(7, 15)], fill=P["c"])                  # drip
    return im


def bottles():  # 16x16 potion-bottle trio for the countertop
    im, d = sprite(16, 16)
    d.point([(3, 1), (8, 0), (13, 2)], fill=P["f"])
    d.rectangle([1, 7, 4, 13], fill=P["c"], outline=P["k"])   # cyan flask
    d.rectangle([2, 4, 3, 6], fill=P["c"])
    d.point([(2, 3), (3, 3)], fill=P["w"])
    d.point([(2, 8)], fill=P["x"])
    d.rectangle([6, 4, 9, 13], fill=P["p"], outline=P["k"])   # tall purple
    d.rectangle([7, 2, 8, 3], fill=P["p"])
    d.point([(7, 1), (8, 1)], fill=P["w"])
    d.point([(7, 5)], fill=P["x"])
    d.ellipse([11, 8, 14, 13], fill=P["y"], outline=P["k"])   # round gold
    d.rectangle([12, 6, 13, 7], fill=P["Y"])
    d.point([(12, 5)], fill=P["w"])
    d.point([(12, 9)], fill=P["x"])
    return im


def backbar():  # 16x32 back-bar hutch, niches of glowing bottles + mini kegs
    im, d = sprite(16, 32)
    d.rectangle([1, 0, 14, 31], fill=P["w"], outline=P["k"])
    d.rectangle([2, 1, 13, 30], fill=P["W"])
    d.point([(2, 1), (13, 1)], fill=P["y"])  # crown studs
    for top, bot in ((2, 9), (12, 19)):      # two bottle niches
        d.rectangle([3, top, 12, bot], fill=P["D"])
    d.rectangle([2, 10, 13, 11], fill=P["w"])  # shelf boards
    d.rectangle([2, 20, 13, 21], fill=P["w"])
    # niche 1 bottles (no outlines — 2px bottles must keep their glow color)
    d.rectangle([4, 5, 5, 9], fill=P["c"])
    d.rectangle([7, 4, 8, 9], fill=P["p"])
    d.rectangle([10, 6, 11, 9], fill=P["y"])
    d.point([(4, 5), (7, 4), (10, 6)], fill=P["x"])
    d.point([(5, 3), (10, 4)], fill=P["f"])
    # niche 2 bottles
    d.rectangle([4, 15, 5, 19], fill=P["y"])
    d.rectangle([7, 14, 8, 19], fill=P["c"])
    d.rectangle([10, 16, 11, 19], fill=P["p"])
    d.point([(4, 15), (7, 14), (10, 16)], fill=P["x"])
    d.point([(8, 12), (5, 13)], fill=P["f"])
    # bottom: two mini kegs
    d.rectangle([3, 23, 12, 29], fill=P["D"])
    d.rounded_rectangle([3, 23, 7, 29], radius=1, fill=P["V"], outline=P["k"])
    d.rounded_rectangle([8, 23, 12, 29], radius=1, fill=P["V"], outline=P["k"])
    d.line([(4, 25), (6, 25)], fill=P["Y"])
    d.line([(9, 25), (11, 25)], fill=P["Y"])
    d.point([(5, 28), (10, 28)], fill=P["Y"])
    return im


def main():
    base = Image.new("RGBA", (96, 80), (0, 0, 0, 0))
    tall = [speaker(), crystal_light(), harp(), banner(), crystal_mic()]
    for i, s in enumerate(tall):
        base.paste(s, (i * 16, 0))
    base.paste(backbar(), (80, 0))
    row2 = [wedge(), torch(), lute(), drum(), amp()]
    for i, s in enumerate(row2):
        base.paste(s, (i * 16, 32))
    base.paste(dj_console(), (0, 48))
    for i, s in enumerate([goblet(), martini(), horn()]):
        base.paste(s, ((2 + i) * 16, 48))
    row4 = [bar_piece("left"), bar_piece("mid"), bar_piece("right"), keg(), bottles()]
    for i, s in enumerate(row4):
        base.paste(s, (i * 16, 64))

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "tilesets", "bleu-props.png")
    sheet = base.resize((192, 160), Image.NEAREST)
    sheet.save(out)

    tsx = '''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.8" tiledversion="1.8.0" name="bleu-props" tilewidth="32" tileheight="32" tilecount="30" columns="6">
 <image source="bleu-props.png" width="192" height="160"/>
</tileset>
'''
    open(os.path.join(here, "..", "tilesets", "bleu-props.tsx"), "w").write(tsx)

    # 4x preview on dark background for eyeballing
    prev = Image.new("RGBA", sheet.size, (34, 34, 44, 255))
    prev.alpha_composite(sheet)
    prev.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(
        os.path.join(here, "preview.png"))
    print("wrote bleu-props.png (192x160, 30 tiles), bleu-props.tsx, tools/preview.png")


if __name__ == "__main__":
    main()
