#!/usr/bin/env python3
"""Generate README specimen images from the actual Moxy / Recursive fonts.
Dev-only (Pillow); not part of the build. Outputs PNGs into images/."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOXY = os.path.join(ROOT, "fonts/Moxy-VF/Moxy[MONO,CASL,wght,slnt,CRSV].ttf")
REC = os.path.join(ROOT, "font-data/Recursive_VF_1.085.ttf")
OUT = os.path.join(ROOT, "images")
os.makedirs(OUT, exist_ok=True)
S = 2  # supersample

# Catppuccin Mocha-ish palette
BG     = "#1e1e2e"
CARD   = "#181825"
TEXT   = "#cdd6f4"
MUTED  = "#7f849c"
DIM    = "#585b70"
PINK   = "#f5c2e7"
MAUVE  = "#cba6f7"
GREEN  = "#a6e3a1"
BLUE   = "#89b4fa"
PEACH  = "#fab387"

def font(path, px, axes):
    f = ImageFont.truetype(path, px * S)
    try:
        f.set_variation_by_axes(axes)
    except Exception as e:
        print("axes warn:", e)
    return f

def moxy(px, wght=400):   return font(MOXY, px, [1, 0.5, wght, 0, 0])
def rec(px, wght=400):    return font(REC,  px, [1, 0.5, wght, 0, 0])

def text(d, xy, s, f, fill, features=None):
    d.text((xy[0]*S, xy[1]*S), s, font=f, fill=fill,
           features=(features if features is not None else ["calt"]))

def width(d, s, f, features=None):
    return d.textlength(s, font=f, features=(features if features is not None else ["calt"]))

def finish(img, path):
    w, h = img.size
    img.resize((w//S, h//S), Image.LANCZOS).save(path)
    print("wrote", path)


# ---------------------------------------------------------------- HERO
def hero():
    W, H = 1280, 600
    img = Image.new("RGB", (W*S, H*S), BG)
    d = ImageDraw.Draw(img)

    # wordmark
    text(d, (64, 70), "Moxy", moxy(150, 850), PINK)
    wm = width(d, "Moxy", moxy(150, 850)) / S
    text(d, (64 + wm + 28, 150), "a monospaced", moxy(30, 420), MUTED)
    text(d, (64 + wm + 28, 188), "coding font", moxy(30, 420), MUTED)

    # terminal-ish card
    cx, cy, cw, ch = 64, 270, W-128, 268
    d.rounded_rectangle([cx*S, cy*S, (cx+cw)*S, (cy+ch)*S], radius=16*S, fill=CARD)
    for i, c in enumerate(["#f38ba8", "#f9e2af", "#a6e3a1"]):
        d.ellipse([(cx+24+i*26)*S, (cy+22)*S, (cx+24+i*26+14)*S, (cy+22+14)*S], fill=c)

    px, py, lh = cx+30, cy+58, 42
    cf = moxy(26, 430)
    # each line drawn whole so calt ligatures form; light syntax tint per line
    text(d, (px, py+0*lh),  "fn pipe(xs):  xs |> map(f) |> sum        # connected  |>", cf, TEXT)
    text(d, (px, py+1*lh),  "route:  start --------> end              # long arrows", cf, GREEN)
    text(d, (px, py+2*lh),  'path = \"C:\\dev\\moxy\"  != none           # thin escape  \\\\', cf, PEACH)
    text(d, (px, py+3*lh),  "ids:  0 1 f r L Z   <=  >=  ===  ->  =>   # letterforms", cf, BLUE)
    finish(img, os.path.join(OUT, "specimen.png"))


# ---------------------------------------------------------------- COMPARISON
def comparison():
    rows = [
        ("parentheses",   "(sum)",            "(sum)"),
        ("long arrows",   "start --------> end", "start --------> end"),
        ("connected bars","|>   <|",          "|>   <|"),
        ("dashes",        "----------",       "----------"),
        ("escape  \\",    "\"\\n\\t C:\\dev\"",  "\"\\n\\t C:\\dev\""),
        ("letterforms",   "f r L Z 0 1",      "f r L Z 0 1"),
        ("extra arrows",  "\u21a9 \u21aa \u21b0 \u21c4", "\u21a9 \u21aa \u21b0 \u21c4"),
    ]
    W = 1280
    top, rh, lblx, colL, colR = 132, 70, 64, 470, 880
    H = top + rh*len(rows) + 40
    img = Image.new("RGB", (W*S, H*S), BG)
    d = ImageDraw.Draw(img)

    text(d, (lblx, 40), "What's different from Recursive", moxy(34, 800), TEXT)
    # column headers
    text(d, (colL, 96), "Recursive", moxy(22, 600), MUTED)
    text(d, (colR, 96), "Moxy", moxy(22, 700), PINK)
    # divider before Moxy column
    d.line([(colR-30)*S, top*S, (colR-30)*S, (H-30)*S], fill=DIM, width=1*S)

    rf, mf = rec(30, 430), moxy(30, 430)
    for i, (label, lhs, rhs) in enumerate(rows):
        y = top + i*rh
        if i: d.line([lblx*S, (y-8)*S, (W-40)*S, (y-8)*S], fill="#313244", width=1*S)
        text(d, (lblx, y+8), label, moxy(20, 430), DIM, features=["calt"])
        # Recursive: its own ligatures (dlig); Moxy: default (calt)
        text(d, (colL, y+2), lhs, rf, MUTED, features=["dlig", "calt"])
        text(d, (colR, y+2), rhs, mf, TEXT, features=["calt"])
    finish(img, os.path.join(OUT, "comparison.png"))


if __name__ == "__main__":
    hero()
    comparison()
