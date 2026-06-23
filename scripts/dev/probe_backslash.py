#!/usr/bin/env python3
"""Quick shaping probe for the thin-escape backslash in Moxy.

Requires uharfbuzz (dev-only dependency):
    venv/bin/python -m pip install uharfbuzz
"""
import os
import uharfbuzz as hb
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VF = os.path.join(ROOT, "fonts", "Moxy-VF", "Moxy[CASL,wght,slnt,CRSV].ttf")

# The raw string content (without the r prefix)
text = r"\[(?:[^][]|\\[\[\]]|(?R))*\]"
print("Input string:", text)
print("Codepoints:", [hex(ord(c)) for c in text])


def make_reporter(font_path, axes=None):
    tt = TTFont(font_path)
    glyph_order = tt.getGlyphOrder()
    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    font = hb.Font(face)
    if axes:
        font.set_variations(axes)

    def glyph_name(gid):
        return glyph_order[gid] if gid < len(glyph_order) else f"gid{gid}"

    def report(label, features):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, features=features)
        infos = buf.glyph_infos
        positions = buf.glyph_positions
        print(f"\n{label}:")
        for i, (info, pos) in enumerate(zip(infos, positions)):
            glyph = glyph_name(info.codepoint)
            char = text[info.cluster] if info.cluster < len(text) else "?"
            mark = "  <-- backslash" if char == "\\" else ""
            print(f"  {i:2d}: cluster={info.cluster:2d} char={char!r:5} glyph={glyph:30} advance={pos.x_advance:4}{mark}")

    return report


# Variable font: default Moxy axes (pure-mono, no MONO axis), thin backslash in default-on calt
vf_report = make_reporter(VF, {"CASL": 0.5, "wght": 400.0, "slnt": 0.0, "CRSV": 0.0})
vf_report("VF with calt (default Moxy look)", {"calt": 1})
vf_report("VF with calt + lilx (revert to Recursive)", {"calt": 1, "lilx": 1})

# Static font: thin backslash is behind ss03
STATIC = os.path.join(ROOT, "fonts", "Moxy-Static", "Moxy-Static-Regular-1.085.ttf")
if os.path.exists(STATIC):
    static_report = make_reporter(STATIC)
    static_report("Static with default features (ss03 off)", {})
    static_report("Static with ss03 on", {"ss03": 1, "calt": 1})
