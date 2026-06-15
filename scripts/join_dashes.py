"""
Join runs of hyphens into a continuous line, the way Lilex does, by importing
Lilex's hyphen ``.seq`` pieces and wiring up contextual ``calt`` rules.

Recursive does not connect hyphen runs: ``----`` renders as four separate dashes.
Lilex builds an arbitrarily long connected line from three pieces that overhang
into neighbouring cells:

    hyphen_start.seq   left end  + bar reaching the right edge
    hyphen_middle.seq  bar spanning the whole cell (both edges)
    hyphen_end.seq     bar reaching the left edge + right end

A run of N hyphens becomes ``start (middle * (N-2)) end``.

What this module does to each generated Recursive instance:

  1. Weight-match Lilex to the instance (via the hyphen, a clean horizontal bar)
     and bail out entirely if Lilex can't be drawn heavy enough (heavy weights
     keep Recursive's native dashes -- same fallback rule as the other borrows).
  2. Import the three sheared ``hyphen_*.seq`` outlines as new glyphs.
  3. Re-cut Recursive's existing ``hyphen_hyphen_hyphen.code`` (the ``---``
     ligature) into a joined 3-cell bar, so ``---`` connects too. (``--`` is left
     as Recursive draws it -- Lilex doesn't join two hyphens either.)
  4. Append a contextual ``calt`` lookup that connects runs of *four or more*
     hyphens. It is appended after Recursive's own lookups (so the bounded
     ``--``/``---`` ligatures still fire first) and requires three hyphens of
     lookahead, which also stops it from touching the two hyphens in ``-->``.

The GSUB is edited by hand (append-only). feaLib's addOpenTypeFeatures rewrites
the whole calt feature and silently disables Recursive's existing ligatures, so
it must not be used here.

Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt); keep that notice on builds.
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.tables import otTables as ot
from fontTools.otlLib import builder as otl
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

from borrow_glyphs import _measure_stroke, _match_source_weight, CELL

SEQ_GLYPHS = ("hyphen_start.seq", "hyphen_middle.seq", "hyphen_end.seq")


def _sheared(source_glyf, source_gs, parts, shear, dx0=0.0, dy0=0.0):
    """Merge `parts` (laid out across cells) under shear; return a TTGlyph + bounds.

    Composite source glyphs are decomposed to contours, so the result never
    references component glyphs that may not exist in the target font.
    """
    n = len(parts)
    affines = []
    for i in range(n):
        dx = (i - (n - 1)) * CELL + dx0
        affines.append((1.0, 0.0, shear, 1.0, dx, dy0))
    bounds_pen = BoundsPen(source_gs)
    pen = TTGlyphPen(source_gs)
    for part, aff in zip(parts, affines):
        recorder = DecomposingRecordingPen(source_gs)
        source_glyf[part].draw(recorder, source_gs)
        recorder.replay(TransformPen(bounds_pen, aff))
        recorder.replay(TransformPen(pen, aff))
    glyph = pen.glyph()
    return glyph, bounds_pen.bounds


def _add_glyph(font, name, glyph, advance=CELL):
    glyph.recalcBounds(font["glyf"])
    font["glyf"][name] = glyph
    font["hmtx"].metrics[name] = (advance, glyph.xMin if glyph.numberOfContours else 0)
    order = font.getGlyphOrder()
    if name not in order:
        order = list(order) + [name]
        font.setGlyphOrder(order)


def _single_sub_lookup(mapping):
    lk = ot.Lookup()
    lk.LookupType = 1
    lk.LookupFlag = 0
    lk.SubTable = [otl.buildSingleSubstSubtable(mapping)]
    lk.SubTableCount = 1
    return lk


def _chain3(backtrack, input_, lookahead, lookup_index, glyph_map):
    """Build a ChainContextSubst format-3 subtable applying one nested lookup."""
    st = ot.ChainContextSubst()
    st.Format = 3
    # Backtrack coverage is stored nearest-input-first (reverse text order).
    st.BacktrackGlyphCount = len(backtrack)
    st.BacktrackCoverage = [otl.buildCoverage(set(g), glyph_map) for g in reversed(backtrack)]
    st.InputGlyphCount = len(input_)
    st.InputCoverage = [otl.buildCoverage(set(g), glyph_map) for g in input_]
    st.LookAheadGlyphCount = len(lookahead)
    st.LookAheadCoverage = [otl.buildCoverage(set(g), glyph_map) for g in lookahead]
    rec = ot.SubstLookupRecord()
    rec.SequenceIndex = 0
    rec.LookupListIndex = lookup_index
    st.SubstLookupRecord = [rec]
    st.SubstCount = 1
    return st


def _append_dash_calt(font, min_run=4):
    """Append a calt lookup that joins runs of >= min_run hyphens."""
    gsub = font["GSUB"].table
    LL = gsub.LookupList.Lookup

    i_start = len(LL); LL.append(_single_sub_lookup({"hyphen": "hyphen_start.seq"}))
    i_mid = len(LL); LL.append(_single_sub_lookup({"hyphen": "hyphen_middle.seq"}))
    i_end = len(LL); LL.append(_single_sub_lookup({"hyphen": "hyphen_end.seq"}))

    glyph_map = font.getReverseGlyphMap(rebuild=True)
    seq_back = ["hyphen_start.seq", "hyphen_middle.seq"]
    # START needs (min_run - 1) hyphens of lookahead, so only long runs trigger and
    # the two hyphens in "-->" are never mistaken for the start of a run.
    start_lookahead = [["hyphen"]] * (min_run - 1)

    chain = ot.Lookup()
    chain.LookupType = 6
    chain.LookupFlag = 0
    chain.SubTable = [
        # middle: hyphen between a seq-piece and another hyphen
        _chain3([seq_back], [["hyphen"]], [["hyphen"]], i_mid, glyph_map),
        # end: hyphen following a seq-piece (no further hyphen)
        _chain3([seq_back], [["hyphen"]], [], i_end, glyph_map),
        # start: a hyphen that begins a long-enough run
        _chain3([], [["hyphen"]], start_lookahead, i_start, glyph_map),
    ]
    chain.SubTableCount = len(chain.SubTable)
    i_chain = len(LL); LL.append(chain)
    gsub.LookupList.LookupCount = len(LL)

    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag == "calt" and i_chain not in fr.Feature.LookupListIndex:
            fr.Feature.LookupListIndex.append(i_chain)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)


def join_dashes(
    target_font: TTFont,
    *,
    source_path: str,
    slant: float = 0.0,
    max_stroke_mismatch: float | None = 0.18,
) -> dict:
    """Add Lilex-style hyphen-run joining to `target_font` (modified in place)."""
    target_stroke = _measure_stroke(
        target_font["glyf"]["hyphen"], target_font.getGlyphSet(), "vertical", slant
    )
    if target_stroke is None:
        return {"done": False, "reason": "could not measure hyphen"}

    matched_wght, matched_stroke = _match_source_weight(
        source_path, "hyphen", "vertical", target_stroke
    )
    mismatch = abs(matched_stroke - target_stroke) / target_stroke
    if max_stroke_mismatch is not None and mismatch > max_stroke_mismatch:
        return {
            "done": False,
            "reason": "stroke mismatch over threshold",
            "mismatch": mismatch,
            "matched_wght": matched_wght,
        }

    source_font = instancer.instantiateVariableFont(
        TTFont(source_path), {"wght": matched_wght}, inplace=False
    )
    source_glyf = source_font["glyf"]
    source_gs = source_font.getGlyphSet()
    shear = math.tan(math.radians(-slant))

    # 1) import the three seq pieces, sheared, keeping their tiling positions.
    for name in SEQ_GLYPHS:
        glyph, _ = _sheared(source_glyf, source_gs, [name], shear)
        _add_glyph(target_font, name, glyph)

    # 2) re-cut the "---" ligature glyph as a joined 3-cell bar.
    tgt_glyf = target_font["glyf"]
    code_name = "hyphen_hyphen_hyphen.code"
    if code_name in tgt_glyf:
        tgt = tgt_glyf[code_name]
        tgt.recalcBounds(tgt_glyf)
        glyph, bounds = _sheared(
            source_glyf, source_gs, list(SEQ_GLYPHS), shear
        )
        if bounds is not None:
            # align left ink edge + vertical centre to the original glyph
            dx = tgt.xMin - bounds[0]
            dy = (tgt.yMin + tgt.yMax) / 2.0 - (bounds[1] + bounds[3]) / 2.0
            glyph, _ = _sheared(source_glyf, source_gs, list(SEQ_GLYPHS), shear, dx, dy)
        adv = target_font["hmtx"].metrics[code_name][0]
        glyph.recalcBounds(tgt_glyf)
        tgt_glyf[code_name] = glyph
        target_font["hmtx"].metrics[code_name] = (
            adv, glyph.xMin if glyph.numberOfContours else 0
        )

    # 3) append the contextual lookup for runs of >= 4 hyphens.
    _append_dash_calt(target_font, min_run=4)

    return {
        "done": True,
        "matched_wght": matched_wght,
        "target_stroke": target_stroke,
        "source_stroke": matched_stroke,
        "mismatch": mismatch,
    }
