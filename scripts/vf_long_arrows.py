"""
Default Recursive-style long arrows (--->, <--, <-->, … any length, both
directions) for the variable-font build.

Recursive natively ligates only -> --> <- (and the bare -< etc.); longer arrows
break (`--->` shapes as a 3-dash bar + a detached `>`). This repairs them in
Recursive's OWN style, at the native arrow shaft height — NOT under `lilx`: it's a
baseline ligature fix, so it's added to `dlig` (where Recursive's arrows live;
Recursive ships no `calt`). The default font has no connected-dash shaft, so the
shaft is synthesised from Recursive's --> shaft band and capped with Recursive's
own arrowheads.

Three variable building blocks (advance 600; vary wght 300→1000 + slnt shear;
MONO/CASL frozen — Recursive's arrow shaft band is MONO-invariant):
  arrow.shaft  a full-cell connecting bar at the arrow shaft band
  arrow.rcap   the > arrowhead + a backward shaft stub (replaces `greater`)
  arrow.lcap   the < arrowhead + a forward shaft stub (replaces `less`)

GSUB, two passes appended to dlig (operating on the post-dlig stream):
  pass 1  convert bare right-shaft dashes to arrow.shaft (bounded lookahead to the
          trailing `>`, up to MAX_RUN) incl. the hyphen_hyphen_hyphen.code bar via
          multiple-sub; and cap the leading `<` of left / double arrows.
  pass 2  cap the trailing `>`; and propagate the left shaft rightward from `<`
          (infinite, since the anchor is on the left).

Welded shaft bars are wound clockwise (y-up) so they union with the arrowheads.
HarfBuzz can't propagate right→left, so right arrows are bounded (MAX_RUN dashes);
left arrows are unbounded. This is the same family of facts the static
long_arrows.py relied on, rebuilt here at native arrow height for the VF default.
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.otlLib import builder as otl
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

from long_arrows import _shaft_y
from vf_lilex import (
    _recursive_instance,
    add_variable_glyph,
    append_lookup,
    single_sub_lookup,
)

CELL = 600
MAX_RUN = 14  # longest right-arrow dash run that still connects

SHAFT = "arrow.shaft"
RCAP = "arrow.rcap"
LCAP = "arrow.lcap"

# Post-dlig glyphs that read as "a stretch of dash" inside an arrow.
RIGHT_BACKTRACK = [SHAFT, "less_hyphen.code"]   # ends with a shaft, before `>`
LEFT_LOOKAHEAD = [                               # starts with a shaft, after `<`
    "hyphen", "hyphen_hyphen.code", "hyphen_hyphen_hyphen.code",
    "hyphen_greater.code", "hyphen_hyphen_greater.code",
]
LEFT_BACKTRACK = [LCAP, SHAFT]


# ----------------------------------------------------------------------------
# Geometry (built per Recursive instance, then made variable).


def _cap(inst, arrow_name, *, dx, shear, bar):
    """Transform a native Recursive arrow into a 1-cell cap + a welded shaft bar."""
    gs = inst.getGlyphSet()
    pen = TTGlyphPen(gs)
    rec = DecomposingRecordingPen(gs)
    inst["glyf"][arrow_name].draw(rec, gs)
    rec.replay(TransformPen(pen, (1.0, 0.0, shear, 1.0, dx, 0.0)))
    x0, x1, y0, y1 = bar
    # clockwise (y-up) so it unions with the arrowhead's outer contour
    pen.moveTo((x0, y0)); pen.lineTo((x0, y1)); pen.lineTo((x1, y1)); pen.lineTo((x1, y0))
    pen.closePath()
    return pen.glyph()


def _shaft(inst, shear, *, y0, y1, x0=-20, x1=620):
    pen = TTGlyphPen(inst.getGlyphSet())

    def p(x, y):
        return (x + shear * y, y)

    pen.moveTo(p(x0, y0)); pen.lineTo(p(x0, y1)); pen.lineTo(p(x1, y1)); pen.lineTo(p(x1, y0))
    pen.closePath()
    return pen.glyph()


def _coords(glyph):
    return [tuple(p) for p in glyph.coordinates] if glyph.numberOfContours > 0 else []


def _build_blocks(font: TTFont, recursive_path: str) -> None:
    """Build the variable arrow.shaft / arrow.rcap / arrow.lcap glyphs."""
    light = _recursive_instance(recursive_path, {"MONO": 1, "wght": 300})
    heavy = _recursive_instance(recursive_path, {"MONO": 1, "wght": 1000})

    def make(name, fn):
        lg = fn(light)
        hg = fn(heavy)
        add_variable_glyph(
            font, name, light_glyph=lg,
            light_coords=_coords(lg), heavy_coords=_coords(hg),
        )

    def shaft_fn(inst):
        y0, y1, _ = _shaft_y(inst, "hyphen_hyphen_greater.code")
        return _shaft(inst, 0.0, y0=y0, y1=y1)

    def rcap_fn(inst):
        y0, y1, _ = _shaft_y(inst, "hyphen_hyphen_greater.code")
        hg = inst["glyf"]["hyphen_greater.code"]; hg.recalcBounds(inst["glyf"])
        return _cap(inst, "hyphen_greater.code", dx=560 - hg.xMax, shear=0.0,
                    bar=(-620, 300, y0, y1))

    def lcap_fn(inst):
        y0, y1, _ = _shaft_y(inst, "hyphen_hyphen_greater.code")
        lh = inst["glyf"]["less_hyphen.code"]; lh.recalcBounds(inst["glyf"])
        return _cap(inst, "less_hyphen.code", dx=40 - lh.xMin, shear=0.0,
                    bar=(280, 620, y0, y1))

    make(SHAFT, shaft_fn)
    make(RCAP, rcap_fn)
    make(LCAP, lcap_fn)


# ----------------------------------------------------------------------------
# GSUB chains.


def _chain(backtrack, input_, lookahead, records, glyph_map):
    st = ot.ChainContextSubst()
    st.Format = 3
    st.BacktrackGlyphCount = len(backtrack)
    st.BacktrackCoverage = [otl.buildCoverage(set(g), glyph_map) for g in reversed(backtrack)]
    st.InputGlyphCount = len(input_)
    st.InputCoverage = [otl.buildCoverage(set(g), glyph_map) for g in input_]
    st.LookAheadGlyphCount = len(lookahead)
    st.LookAheadCoverage = [otl.buildCoverage(set(g), glyph_map) for g in lookahead]
    recs = []
    for seq_index, lookup_index in records:
        r = ot.SubstLookupRecord()
        r.SequenceIndex = seq_index
        r.LookupListIndex = lookup_index
        recs.append(r)
    st.SubstLookupRecord = recs
    st.SubstCount = len(recs)
    return st


def _multi_lookup(mapping):
    lk = ot.Lookup()
    lk.LookupType = 2
    lk.LookupFlag = 0
    lk.SubTable = [otl.buildMultipleSubstSubtable(mapping)]
    lk.SubTableCount = 1
    return lk


def long_arrows(font: TTFont, recursive_path: str) -> list[int]:
    """Build the blocks + wire the two dlig passes. Returns the dlig lookup indices."""
    _build_blocks(font, recursive_path)
    gm = font.getReverseGlyphMap(rebuild=True)

    # nested single/multiple subs (invoked only contextually)
    nl_gt = append_lookup(font, single_sub_lookup({"greater": RCAP}))
    nl_lt = append_lookup(font, single_sub_lookup({"less": LCAP}))
    nl_h = append_lookup(font, single_sub_lookup({"hyphen": SHAFT}))
    nl_hh = append_lookup(font, _multi_lookup({"hyphen_hyphen.code": [SHAFT, SHAFT]}))
    nl_hhh = append_lookup(font, _multi_lookup(
        {"hyphen_hyphen_hyphen.code": [SHAFT, SHAFT, SHAFT]}))

    # pass 1: right-shaft conversion + left cap
    p1 = ot.Lookup()
    p1.LookupType = 6
    p1.LookupFlag = 0
    subs = []
    # right shaft, loose hyphens: bounded lookahead to the trailing `>`
    for j in range(1, MAX_RUN + 1):
        subs.append(_chain([], [["hyphen"]], [["hyphen"]] * (j - 1) + [["greater"]],
                           [(0, nl_h)], gm))
    # right shaft, the 3-dash bar before `>`
    subs.append(_chain([], [["hyphen_hyphen_hyphen.code"]], [["greater"]], [(0, nl_hhh)], gm))
    # left cap: `<` that begins a left/double arrow
    subs.append(_chain([], [["less"]], [LEFT_LOOKAHEAD], [(0, nl_lt)], gm))
    p1.SubTable = subs
    p1.SubTableCount = len(subs)
    i_p1 = append_lookup(font, p1)

    # pass 2: right cap + left-shaft propagation
    p2 = ot.Lookup()
    p2.LookupType = 6
    p2.LookupFlag = 0
    subs2 = [
        _chain([RIGHT_BACKTRACK], [["greater"]], [], [(0, nl_gt)], gm),       # cap >
        _chain([LEFT_BACKTRACK], [["hyphen"]], [], [(0, nl_h)], gm),          # loose
        _chain([LEFT_BACKTRACK], [["hyphen_hyphen.code"]], [], [(0, nl_hh)], gm),
        _chain([LEFT_BACKTRACK], [["hyphen_hyphen_hyphen.code"]], [], [(0, nl_hhh)], gm),
    ]
    p2.SubTable = subs2
    p2.SubTableCount = len(subs2)
    i_p2 = append_lookup(font, p2)

    # wire both passes into dlig
    gsub = font["GSUB"].table
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag == "dlig":
            for idx in (i_p1, i_p2):
                if idx not in fr.Feature.LookupListIndex:
                    fr.Feature.LookupListIndex.append(idx)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)

    return [i_p1, i_p2]
