"""
Recursive-style long arrows of arbitrary length, built on the connected-dash shaft.

Recursive natively ligates only -> --> (right) and <- (left). Longer arrows
(--->, <--, <---, …) don't form. This module fixes that *in Recursive's own
style* by reusing the connected-dash shaft (from join_dashes, already infinite)
and capping it with Recursive's own arrowhead:

  * a right cap (Recursive's > arrowhead) replaces the trailing `>`, drawing
    backward over the connected shaft;
  * a left cap (Recursive's < arrowhead) replaces the leading `<`, drawing
    forward over the connected shaft.

Both caps are lowered to the dash shaft height so they connect cleanly, which is
why long arrows sit slightly lower than the native short ones (an accepted
trade-off for truly-infinite length without violating monospacing — every glyph
keeps its 600-unit cell).

The arrowheads come from Recursive itself (instanced natively at the same axis
location), so no weight matching or fallback is needed for the heads; the shaft
relies on join_dashes (which does fall back at heavy weights), so this runs only
when join_dashes succeeded.
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.tables import otTables as ot
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

from join_dashes import _add_glyph, _single_sub_lookup

CELL = 600


def _shaft_y(native_font, arrow_name):
    """Return (yMin, yMax, centre) of the arrow's shaft contour (the wide bar)."""
    glyf = native_font["glyf"]
    g = glyf[arrow_name]
    rec = DecomposingRecordingPen(native_font.getGlyphSet())
    g.draw(rec, native_font.getGlyphSet())
    contours = []
    cur = []
    for op, args in rec.value:
        if op == "moveTo":
            if cur:
                contours.append(cur)
            cur = [args[0]]
        elif op == "lineTo":
            cur.append(args[0])
        elif op == "qCurveTo":
            cur += [p for p in args if p]
        elif op in ("closePath", "endPath"):
            if cur:
                contours.append(cur)
            cur = []
    # shaft = contour with the smallest y-extent (the bar); head has the big extent
    best = None
    for c in contours:
        ys = [p[1] for p in c]
        extent = max(ys) - min(ys)
        if best is None or extent < best[0]:
            best = (extent, min(ys), max(ys))
    return best[1], best[2], (best[1] + best[2]) / 2.0


def _cap_glyph(native_font, arrow_name, *, dx, dy, shear, bar):
    """Transform a native arrow into a cap glyph and weld on a shaft bar.

    bar = (x0, x1, y0, y1) rectangle added (in final glyph coords) so the cap's
    shaft reliably overlaps the connected dash shaft.
    """
    gs = native_font.getGlyphSet()
    pen = TTGlyphPen(gs)
    affine = (1.0, 0.0, shear, 1.0, dx, dy)
    rec = DecomposingRecordingPen(gs)
    native_font["glyf"][arrow_name].draw(rec, gs)
    rec.replay(TransformPen(pen, affine))
    x0, x1, y0, y1 = bar
    # Clockwise (y-up) so it has the same winding as the arrow's outer contours
    # and unions with them (a CCW bar would cancel the overlap and leave a gap).
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()
    return pen.glyph()


def _chain(backtrack, input_, lookahead, records, glyph_map):
    from fontTools.otlLib import builder as otl
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


def long_arrows(target_font: TTFont, *, recursive_vf_path: str, axis_location: dict) -> dict:
    """Add infinite Recursive-style long arrows. Assumes join_dashes already ran."""
    native = instancer.instantiateVariableFont(
        TTFont(recursive_vf_path), axis_location, inplace=False
    )

    # dash shaft height in the *target* (where join_dashes' seq pieces sit)
    tgt_glyf = target_font["glyf"]
    mid = tgt_glyf["hyphen_middle.seq"]
    mid.recalcBounds(tgt_glyf)
    dash_y0, dash_y1 = mid.yMin, mid.yMax
    dash_cy = (dash_y0 + dash_y1) / 2.0

    slant = axis_location.get("slnt", 0)
    shear = math.tan(math.radians(-slant))

    # --- right cap (from native -> ), drawn backward over the > cell ---
    _, _, r_cy = _shaft_y(native, "hyphen_greater.code")
    # native -> spans x[104,1093] (2 cells). Place head tip just inside the > cell
    # and let the shaft run back into the previous cell.
    r_dx = -560.0
    r_dy = dash_cy - r_cy
    # shaft bar: from one cell back up to the head base, at dash height
    right_cap = _cap_glyph(
        native, "hyphen_greater.code",
        dx=r_dx, dy=r_dy, shear=shear,
        bar=(-CELL - 40, 200, dash_y0, dash_y1),
    )
    _add_glyph(target_font, "rightarrow_long.code", right_cap)

    # --- left cap (from native <- ), drawn forward from the < cell ---
    _, _, l_cy = _shaft_y(native, "less_hyphen.code")
    l_dx = 0.0
    l_dy = dash_cy - l_cy
    # shaft bar: from just inside the < cell out across two full cells, at dash
    # height — long enough to cover the separated "--" of the 2-hyphen case.
    left_cap = _cap_glyph(
        native, "less_hyphen.code",
        dx=l_dx, dy=l_dy, shear=shear,
        bar=(380, 3 * CELL + 20, dash_y0, dash_y1),
    )
    _add_glyph(target_font, "leftarrow_long.code", left_cap)

    # --- GSUB ---
    gsub = target_font["GSUB"].table
    LL = gsub.LookupList.Lookup

    def add_ss(mapping):
        i = len(LL)
        LL.append(_single_sub_lookup(mapping))
        return i

    i_gt_cap = add_ss({"greater": "rightarrow_long.code"})
    i_less_cap = add_ss({"less": "leftarrow_long.code"})
    gm = target_font.getReverseGlyphMap(rebuild=True)

    chain = ot.Lookup()
    chain.LookupType = 6
    chain.LookupFlag = 0
    chain.SubTable = [
        # right: a connected-shaft end piece (or the --- glyph) followed by '>'
        _chain([["hyphen_end.seq", "hyphen_hyphen_hyphen.code"]], [["greater"]], [],
               [(0, i_gt_cap)], gm),
        # left: '<' followed by a connected shaft (>=4 hyphens -> start.seq)
        _chain([], [["less"]], [["hyphen_start.seq"]], [(0, i_less_cap)], gm),
        # left: '<' followed by the 3-hyphen --- glyph (LIG LIG code)
        _chain([], [["less"]], [["LIG"], ["LIG"], ["hyphen_hyphen_hyphen.code"]],
               [(0, i_less_cap)], gm),
        # left: '<' followed by the 2-hyphen -- glyph (LIG code)
        _chain([], [["less"]], [["LIG"], ["hyphen_hyphen.code"]], [(0, i_less_cap)], gm),
    ]
    chain.SubTableCount = len(chain.SubTable)
    i_chain = len(LL)
    LL.append(chain)
    gsub.LookupList.LookupCount = len(LL)

    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag == "calt" and i_chain not in fr.Feature.LookupListIndex:
            fr.Feature.LookupListIndex.append(i_chain)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)

    return {"done": True}
