#!/usr/bin/env python3
"""Deterministically render Moxy's README branding images from a markdown spec.

Content lives in ``images/branding/specimens.md`` (wordmark, tagline, code lines,
comparison rows, and OpenType feature rows); this script only owns the
*presentation* (layout + the Cobalt2 palette). Same spec + same fonts => same
PNGs.

Run via ``make images-branding`` (installs Pillow, a dev-only dep).
"""
import os
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "images/branding/specimens.md")
MOXY = os.path.join(ROOT, "fonts/Moxy-VF/Moxy[CASL,wght,slnt,CRSV].ttf")
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
MOXY_FEATURES = ("calt", "moxy", "lilx")


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

def moxy(px, wght=400, mono=1, casl=0.5, slnt=0, crsv=0):
    # Moxy is pure-mono: the MONO axis is gone (always Mono). `mono` is accepted
    # for backward-compat but ignored; axis order is now CASL, wght, slnt, CRSV.
    return font(MOXY, px, [casl, wght, slnt, crsv])
def rec(px, wght=400):   return font(REC, px, [1, 0.5, wght, 0, 0])

def draw(d, xy, s, f, fill, feats=("calt",)):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, features=list(feats))

def textlen(d, s, f, feats=("calt",)):
    return d.textlength(s, font=f, features=list(feats)) / S

def parse_features(s):
    return tuple(p.strip() for p in s.split(",") if p.strip())

def rich_parts(s):
    parts, buf, highlight = [], [], False
    for ch in s:
        if ch == "{":
            if buf:
                parts.append(("".join(buf), highlight))
                buf = []
            highlight = True
        elif ch == "}":
            if buf:
                parts.append(("".join(buf), highlight))
                buf = []
            highlight = False
        else:
            buf.append(ch)
    if buf:
        parts.append(("".join(buf), highlight))
    return parts

def draw_rich(d, xy, s, f, fill, accent, feats=()):
    x, y = xy
    for text, highlight in rich_parts(s):
        draw(d, (x, y), text, f, accent if highlight else fill, feats=feats)
        x += textlen(d, text, f, feats=feats)

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
        draw(d, (card_x + 30, card_y + pad_top + i * lh), txt, cf, color,
             feats=MOXY_FEATURES)
    save(img, sec["out"])


def render_comparison(sec):
    title = sec["params"].get("title", "What's different from Recursive")
    rows = sec["rows"]
    has_title = bool(title.strip())

    W = 1280
    top, rh, lblx, colL, colR = (132 if has_title else 96), 70, 64, 470, 880
    H = top + rh * len(rows) + 40
    img = Image.new("RGB", (W * S, H * S), PAL["bg"])
    d = ImageDraw.Draw(img)

    if has_title:
        draw(d, (lblx, 40), title, moxy(34, 800), PAL["text"])
    draw(d, (colL, top - 36), "Recursive", moxy(22, 600), PAL["muted"])
    draw(d, (colR, top - 36), "Moxy", moxy(22, 700), PAL["yellow"])
    d.line([(colR - 30) * S, top * S, (colR - 30) * S, (H - 30) * S], fill=PAL["dim"], width=S)

    rf, mf = rec(30, 430), moxy(30, 430)
    for i, row in enumerate(rows):
        label, sample = (row + ["", ""])[:2]
        y = top + i * rh
        if i:
            d.line([lblx * S, (y - 8) * S, (W - 40) * S, (y - 8) * S], fill="#23394a", width=S)
        draw(d, (lblx, y + 8), label, moxy(20, 430), PAL["dim"])
        draw(d, (colL, y + 2), sample, rf, PAL["muted"], feats=("dlig", "calt"))
        draw(d, (colR, y + 2), sample, mf, PAL["text"], feats=MOXY_FEATURES)
    save(img, sec["out"])


def render_opentype_features(sec):
    title = sec["params"].get("title", "Moxy > OpenType Features")
    rows = sec["rows"]

    W = 1240
    x_tag, x_desc, x_default, x_active = 66, 300, 724, 986
    title_y, header_y, row_top = 54, 132, 188
    row_h, bottom = 66, 34
    H = row_top + len(rows) * row_h + bottom
    img = Image.new("RGB", (W * S, H * S), PAL["bg"])
    d = ImageDraw.Draw(img)

    title_f = moxy(25, 800)
    head_f = moxy(23, 760)
    tag_f = moxy(25, 760)
    desc_f = moxy(25, 420)
    sample_f = moxy(26, 650)
    sample_italic = moxy(26, 650, slnt=-15, crsv=1)
    sample_sans = moxy(26, 650, mono=0)
    sample_sans_italic = moxy(26, 650, mono=0, slnt=-15, crsv=1)

    draw(d, (x_tag, title_y), title, title_f, PAL["text"], feats=MOXY_FEATURES)
    draw(d, (x_default, header_y), "Default", head_f, PAL["text"], feats=())
    draw(d, (x_active, header_y), "Active", head_f, PAL["text"], feats=())
    d.line([0, (row_top - 8) * S, W * S, (row_top - 8) * S], fill=PAL["dim"], width=S)

    for i, row in enumerate(rows):
        cells = (row + [""] * 7)[:7]
        tag, label, default, active, active_feats, style, default_feats = cells
        y = row_top + i * row_h
        f = {
            "italic": sample_italic,
            "sans": sample_sans,
            "sans-italic": sample_sans_italic,
        }.get(style, sample_f)
        draw(d, (x_tag, y + 19), tag, tag_f, PAL["text"], feats=())
        draw(d, (x_desc, y + 19), label, desc_f, PAL["muted"], feats=())
        draw_rich(d, (x_default, y + 18), default, f, PAL["text"],
                  PAL["blue"], feats=parse_features(default_feats))
        draw_rich(d, (x_active, y + 18), active, f, PAL["text"],
                  PAL["blue"], feats=parse_features(active_feats))
        d.line([0, (y + row_h) * S, W * S, (y + row_h) * S], fill=PAL["dim"], width=S)

    save(img, sec["out"])


RENDERERS = {
    "specimen": render_specimen,
    "comparison": render_comparison,
    "opentype-features": render_opentype_features,
}

if __name__ == "__main__":
    for sec in parse(SPEC):
        r = RENDERERS.get(sec["id"])
        if r:
            r(sec)
        else:
            print("skip unknown section:", sec["id"])
