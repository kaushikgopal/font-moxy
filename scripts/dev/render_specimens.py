#!/usr/bin/env python3
"""Deterministically render Moxy's README branding images from a markdown spec.

Content lives in ``branding/specimens.md`` (wordmark, tagline, code lines, the
comparison rows); this script only owns the *presentation* (layout + the Cobalt2
palette). Same spec + same fonts => same PNGs.

Run via ``make images-branding`` (installs Pillow, a dev-only dep). Outputs to
``images/``.
"""
import os
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "branding/specimens.md")
MOXY = os.path.join(ROOT, "fonts/Moxy-VF/Moxy[MONO,CASL,wght,slnt,CRSV].ttf")
REC = os.path.join(ROOT, "font-data/Recursive_VF_1.085.ttf")
S = 2  # supersample, then downscale for crisp anti-aliasing

# Cobalt2 palette (Wes Bos) — deep navy + signature gold.
PAL = {
    "bg":      "#193549",
    "card":    "#122738",
    "text":    "#ffffff",
    "muted":   "#6c8b9f",
    "dim":     "#3b5364",
    "yellow":  "#ffc600",   # signature accent (wordmark, "Moxy")
    "orange":  "#ff9d00",
    "peach":   "#ff9d00",   # alias
    "green":   "#3ad900",
    "blue":    "#9effff",
    "pink":    "#ff628c",
    "mauve":   "#ff628c",   # alias
    "comment": "#0088ff",
}
DOTS = ["#ff5f56", "#ffbd2e", "#27c93f"]  # mac traffic lights


# ----------------------------------------------------------------- spec parsing
def split_row(line):
    line = line.strip().strip("|")
    return [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", line)]

def is_sep(cells):
    return all(re.fullmatch(r":?-+:?", c or "") for c in cells)

def parse(path):
    sections, cur, in_fence = [], None, False
    for raw in open(path, encoding="utf-8").read().splitlines():
        head = re.match(r"^##\s+(\S+)\s*(?:->|→)\s*(.+?)\s*$", raw)
        if head and not in_fence:
            cur = {"id": head.group(1), "out": head.group(2),
                   "params": {}, "code": [], "_rows": []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        if raw.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            cur["code"].append(raw)
            continue
        p = re.match(r"^-\s+([\w ]+?):\s*(.*)$", raw)
        if p:
            cur["params"][p.group(1).strip()] = p.group(2).strip()
            continue
        if raw.lstrip().startswith("|"):
            cur["_rows"].append(split_row(raw))
    for s in sections:
        data = [r for r in s["_rows"] if not is_sep(r)]
        s["rows"] = data[1:]  # drop the header row
    return sections


# ----------------------------------------------------------------- render utils
def font(path, px, axes):
    f = ImageFont.truetype(path, px * S)
    try:
        f.set_variation_by_axes(axes)
    except Exception as e:
        print("axes warn:", e)
    return f

def moxy(px, wght=400):  return font(MOXY, px, [1, 0.5, wght, 0, 0])
def rec(px, wght=400):   return font(REC, px, [1, 0.5, wght, 0, 0])

def draw(d, xy, s, f, fill, feats=("calt",)):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, features=list(feats))

def textlen(d, s, f, feats=("calt",)):
    return d.textlength(s, font=f, features=list(feats)) / S

def save(img, out):
    path = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w, h = img.size
    img.resize((w // S, h // S), Image.LANCZOS).save(path)
    print("wrote", os.path.relpath(path, ROOT))


# ----------------------------------------------------------------- renderers
def render_specimen(sec):
    wordmark = sec["params"].get("wordmark", "Moxy")
    tagline = [t.strip() for t in sec["params"].get("tagline", "").split("|") if t.strip()]
    lines = sec["code"]

    W = 1280
    card_x, card_y, card_w = 64, 270, W - 128
    lh, pad_top, pad_bot = 42, 58, 30
    card_h = pad_top + len(lines) * lh + pad_bot
    H = card_y + card_h + 60

    img = Image.new("RGB", (W * S, H * S), PAL["bg"])
    d = ImageDraw.Draw(img)

    draw(d, (card_x, 70), wordmark, moxy(150, 850), PAL["yellow"])
    wm = textlen(d, wordmark, moxy(150, 850))
    for i, t in enumerate(tagline[:2]):
        draw(d, (card_x + wm + 28, 150 + i * 38), t, moxy(30, 420), PAL["muted"])

    d.rounded_rectangle(
        [card_x * S, card_y * S, (card_x + card_w) * S, (card_y + card_h) * S],
        radius=16 * S, fill=PAL["card"])
    for i, c in enumerate(DOTS):
        x = card_x + 24 + i * 26
        d.ellipse([x * S, (card_y + 22) * S, (x + 14) * S, (card_y + 36) * S], fill=c)

    cf = moxy(26, 430)
    for i, line in enumerate(lines):
        m = re.match(r"^\[(\w+)\](.*)$", line)
        color, txt = (PAL.get(m.group(1), PAL["text"]), m.group(2)) if m else (PAL["text"], line)
        draw(d, (card_x + 30, card_y + pad_top + i * lh), txt, cf, color)
    save(img, sec["out"])


def render_comparison(sec):
    title = sec["params"].get("title", "What's different from Recursive")
    rows = sec["rows"]

    W = 1280
    top, rh, lblx, colL, colR = 132, 70, 64, 470, 880
    H = top + rh * len(rows) + 40
    img = Image.new("RGB", (W * S, H * S), PAL["bg"])
    d = ImageDraw.Draw(img)

    draw(d, (lblx, 40), title, moxy(34, 800), PAL["text"])
    draw(d, (colL, 96), "Recursive", moxy(22, 600), PAL["muted"])
    draw(d, (colR, 96), "Moxy", moxy(22, 700), PAL["yellow"])
    d.line([(colR - 30) * S, top * S, (colR - 30) * S, (H - 30) * S], fill=PAL["dim"], width=S)

    rf, mf = rec(30, 430), moxy(30, 430)
    for i, row in enumerate(rows):
        label, sample = (row + ["", ""])[:2]
        y = top + i * rh
        if i:
            d.line([lblx * S, (y - 8) * S, (W - 40) * S, (y - 8) * S], fill="#23394a", width=S)
        draw(d, (lblx, y + 8), label, moxy(20, 430), PAL["dim"])
        draw(d, (colL, y + 2), sample, rf, PAL["muted"], feats=("dlig", "calt"))
        draw(d, (colR, y + 2), sample, mf, PAL["text"], feats=("calt",))
    save(img, sec["out"])


RENDERERS = {"specimen": render_specimen, "comparison": render_comparison}

if __name__ == "__main__":
    for sec in parse(SPEC):
        r = RENDERERS.get(sec["id"])
        if r:
            r(sec)
        else:
            print("skip unknown section:", sec["id"])
