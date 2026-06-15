"""
Extend Recursive's arrow ligatures to arbitrary length in both directions, using
the same Lilex ``.seq`` pieces as join_dashes.

Recursive ligates ``->`` ``-->`` ``<-`` but nothing longer, and has no ``<--`` at
all (it renders ``<`` followed by dashes). Lilex builds arrows of any length from
seq pieces, e.g.::

    --->    hyphen_start.seq  hyphen_middle.seq*  greater_hyphen_end.seq
    <----   less_hyphen_start.seq  hyphen_middle.seq*  hyphen_end.seq

This module runs *after* join_dashes (so hyphen runs have already been connected
into start/middle/end seq glyphs) and appends calt rules that:

  * cap a connected run (>= 4 hyphens) with an arrowhead when it abuts ``>`` / ``<``
    -- this gives arbitrarily long ``--->``..  and ``<----``.. arrows for free;
  * handle the exact 3-length cases ``--->`` ``<--`` ``<---``, which Recursive
    turns into its bounded ``--``/``---`` glyphs rather than seq pieces, by
    blanking the leftover glyph (to Recursive's ``LIG`` spacer) and swapping the
    cap glyph for a purpose-built backward-drawing arrow.

The GSUB is edited by hand (append-only) for the same reason as join_dashes:
feaLib's addOpenTypeFeatures would clobber Recursive's existing ligatures.

Gated by join_dashes succeeding, so it shares the same weight match + heavy-weight
fallback. Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt).
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.tables import otTables as ot
from fontTools.otlLib import builder as otl

from join_dashes import _sheared, _add_glyph, _single_sub_lookup


def _chain_multi(backtrack, input_, lookahead, records, glyph_map):
    """ChainContextSubst format 3 applying several nested lookups at given positions."""
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


def extend_arrows(
    target_font: TTFont,
    *,
    source_path: str,
    slant: float,
    matched_wght: int,
) -> dict:
    """Append longer/missing arrow ligatures. Assumes join_dashes already ran."""
    source_font = instancer.instantiateVariableFont(
        TTFont(source_path), {"wght": matched_wght}, inplace=False
    )
    sglyf = source_font["glyf"]
    sgs = source_font.getGlyphSet()
    shear = math.tan(math.radians(-slant))

    # Arrowhead seq pieces (targets of the infinite-length rules).
    for name in ("greater_hyphen_end.seq", "less_hyphen_start.seq"):
        glyph, _ = _sheared(sglyf, sgs, [name], shear)
        _add_glyph(target_font, name, glyph)

    # Purpose-built backward-drawing arrows for the 3-length cases. Composed from
    # seq pieces at their natural cell offsets (last piece at the substituted cell).
    def make(name, parts):
        glyph, _ = _sheared(sglyf, sgs, parts, shear)
        _add_glyph(target_font, name, glyph)

    make(
        "hyphen_hyphen_hyphen_greater.code",
        ["hyphen_start.seq", "hyphen_middle.seq", "hyphen_middle.seq", "greater_hyphen_end.seq"],
    )
    make(
        "less_hyphen_hyphen.code",
        ["less_hyphen_start.seq", "hyphen_middle.seq", "hyphen_end.seq"],
    )
    make(
        "less_hyphen_hyphen_hyphen.code",
        ["less_hyphen_start.seq", "hyphen_middle.seq", "hyphen_middle.seq", "hyphen_end.seq"],
    )

    gsub = target_font["GSUB"].table
    LL = gsub.LookupList.Lookup

    def add_ss(mapping):
        i = len(LL)
        LL.append(_single_sub_lookup(mapping))
        return i

    i_end_to_mid = add_ss({"hyphen_end.seq": "hyphen_middle.seq"})
    i_gt_head = add_ss({"greater": "greater_hyphen_end.seq"})
    i_less_head = add_ss({"less": "less_hyphen_start.seq"})
    i_start_to_mid = add_ss({"hyphen_start.seq": "hyphen_middle.seq"})
    i_less_blank = add_ss({"less": "LIG"})
    i_code3_blank = add_ss({"hyphen_hyphen_hyphen.code": "LIG"})
    i_gt_arrow3 = add_ss({"greater": "hyphen_hyphen_hyphen_greater.code"})
    i_code2_larrow = add_ss({"hyphen_hyphen.code": "less_hyphen_hyphen.code"})
    i_code3_larrow = add_ss({"hyphen_hyphen_hyphen.code": "less_hyphen_hyphen_hyphen.code"})

    gm = target_font.getReverseGlyphMap(rebuild=True)
    chain = ot.Lookup()
    chain.LookupType = 6
    chain.LookupFlag = 0
    chain.SubTable = [
        # right arrow, run >= 4 + ">" : cap the connected run with an arrowhead
        _chain_multi([], [["hyphen_end.seq"], ["greater"]], [],
                     [(0, i_end_to_mid), (1, i_gt_head)], gm),
        # left arrow, "<" + run >= 4 : turn "<" into the arrowhead, run start into shaft
        _chain_multi([], [["less"], ["hyphen_start.seq"]], [],
                     [(0, i_less_head), (1, i_start_to_mid)], gm),
        # "--->" : Recursive made [LIG LIG hyphen_hyphen_hyphen.code greater]
        _chain_multi([], [["hyphen_hyphen_hyphen.code"], ["greater"]], [],
                     [(0, i_code3_blank), (1, i_gt_arrow3)], gm),
        # "<--" : [less LIG hyphen_hyphen.code]
        _chain_multi([], [["less"], ["LIG"], ["hyphen_hyphen.code"]], [],
                     [(0, i_less_blank), (2, i_code2_larrow)], gm),
        # "<---" : [less LIG LIG hyphen_hyphen_hyphen.code]
        _chain_multi([], [["less"], ["LIG"], ["LIG"], ["hyphen_hyphen_hyphen.code"]], [],
                     [(0, i_less_blank), (3, i_code3_larrow)], gm),
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
