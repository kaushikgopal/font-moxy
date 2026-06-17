"""
Add an optional OpenType stylistic set whose substitutions use glyphs borrowed
from another font.

Unlike the always-on borrows, this stays a real, toggleable feature in the
output: it does nothing unless the application enables the feature tag (e.g.
ghostty `font-feature = ss03`). Used for the "thin backslash" (Lilex ss03).

Two modes:
  * plain   - substitute base -> alternate unconditionally (single sub).
  * escape  - contextual: only substitute backslash when it acts as an escape,
              i.e. it is FOLLOWED by an escape character, and it is NOT the 2nd
              of a consecutive pair, and NOT a Windows drive path "`:\\`".
              (User decision: thin only when serving an escape function.)

GSUB is hand-built (otlLib/otTables), append-only — never feaLib, which would
rewrite calt and disable Recursive's existing ligatures.

macOS only: a single (3,1,0x409) name record is enough; we skip the Windows
(1,0) record.

Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt).
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.tables import otTables as ot
from fontTools.otlLib import builder as otl

from borrow_glyphs import _measure_stroke, _match_source_weight
from join_dashes import _sheared, _add_glyph, _single_sub_lookup

# Characters that, following a backslash, mean it is acting as an escape.
# C/JS escapes + regex classes/Unicode properties + hex/unicode + octal/backrefs +
# regex metacharacters + delimiter + backslash + quotes.
DEFAULT_ESCAPE_CHARS = (
    "abefnrtv"          # C/JS escapes
    "dDwWsSB"           # regex classes
    "xuUNpP"            # hex/unicode/Unicode properties
    "0123456789"        # octal/backrefs/numeric backrefs
    "\\\"'"              # backslash, quotes
    "[](){}?*+|^$./-"   # regex metacharacters + delimiter + hyphen
)


def _free_name_id(font) -> int:
    used = {r.nameID for r in font["name"].names}
    nid = 256
    while nid in used:
        nid += 1
    return nid


def _single_sub_map(font) -> dict[str, list[str]]:
    """Collect single-substitution mappings that apply UNCONDITIONALLY.

    Only lookups referenced *directly* by a feature (e.g. the frozen ssXX, like
    r -> r.simple) are included — not lookups invoked from chain contexts (e.g.
    the escape ligatures n -> backslash_n.code, which only fire after a backslash).
    This gives the glyph a character renders as in plain running text.
    """
    out: dict[str, list[str]] = {}
    gsub = font.get("GSUB")
    if not gsub:
        return out
    direct = set()
    for fr in gsub.table.FeatureList.FeatureRecord:
        direct.update(fr.Feature.LookupListIndex)
    for i in direct:
        lk = gsub.table.LookupList.Lookup[i]
        for st in lk.SubTable:
            sub, t = st, lk.LookupType
            if t == 7:  # extension
                sub, t = st.ExtSubTable, st.ExtSubTable.LookupType
            if t == 1 and getattr(sub, "mapping", None):
                for k, v in sub.mapping.items():
                    out.setdefault(k, []).append(v)
    return out


def _resolve_glyphs(font, char: str) -> set[str]:
    """All glyph names `char` may appear as (base + any single-sub it becomes)."""
    cmap = font.getBestCmap()
    base = cmap.get(ord(char))
    if not base:
        return set()
    single = _single_sub_map(font)
    seen, stack = set(), [base]
    while stack:
        g = stack.pop()
        if g in seen:
            continue
        seen.add(g)
        stack.extend(single.get(g, []))
    return seen


def _terminal_glyph(font, char: str):
    """The glyph `char` ends up as after following GSUB single-subs (frozen form)."""
    cmap = font.getBestCmap()
    g = cmap.get(ord(char))
    if not g:
        return None
    single = _single_sub_map(font)
    seen = set()
    while g in single and g not in seen:
        seen.add(g)
        g = single[g][0]
    return g


def _multi_sub_subtable(input_, records, glyph_map):
    """ChainContextSubst applying several nested single-subs at given input positions."""
    st = ot.ChainContextSubst()
    st.Format = 3
    st.BacktrackGlyphCount = 0
    st.BacktrackCoverage = []
    st.InputGlyphCount = len(input_)
    st.InputCoverage = [otl.buildCoverage(set(g), glyph_map) for g in input_]
    st.LookAheadGlyphCount = 0
    st.LookAheadCoverage = []
    recs = []
    for seq_index, lookup_index in records:
        r = ot.SubstLookupRecord()
        r.SequenceIndex = seq_index
        r.LookupListIndex = lookup_index
        recs.append(r)
    st.SubstLookupRecord = recs
    st.SubstCount = len(recs)
    return st


def _ignore_subtable(backtrack, input_, glyph_map):
    """ChainContextSubst that matches a context but applies nothing (an 'ignore')."""
    st = ot.ChainContextSubst()
    st.Format = 3
    st.BacktrackGlyphCount = len(backtrack)
    st.BacktrackCoverage = [otl.buildCoverage(set(g), glyph_map) for g in reversed(backtrack)]
    st.InputGlyphCount = len(input_)
    st.InputCoverage = [otl.buildCoverage(set(g), glyph_map) for g in input_]
    st.LookAheadGlyphCount = 0
    st.LookAheadCoverage = []
    st.SubstLookupRecord = []
    st.SubstCount = 0
    return st


def _sub_subtable(input_, lookahead, lookup_index, glyph_map):
    st = ot.ChainContextSubst()
    st.Format = 3
    st.BacktrackGlyphCount = 0
    st.BacktrackCoverage = []
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


def add_stylistic_set(
    target_font: TTFont,
    *,
    source_path: str,
    feature_tag: str,
    ui_name: str,
    glyph_map: dict,
    slant: float = 0.0,
    escape_only: bool = False,
    escape_chars: str = DEFAULT_ESCAPE_CHARS,
) -> dict:
    """Import glyphs and expose them as an optional stylistic set `feature_tag`.

    glyph_map maps target glyph -> source glyph (e.g. {"backslash": "backslash.ss03"}).
    Imported alternates get a `.<feature_tag>` suffix.

    escape_only (backslash): substitute only when the backslash is followed by an
    escape character, is not preceded by `:` (drive path), and is not the 2nd of
    a consecutive pair.
    """
    target_stroke = _measure_stroke(
        target_font["glyf"]["hyphen"], target_font.getGlyphSet(), "vertical", slant
    )
    if target_stroke is None:
        matched_wght = int(
            {a.axisTag: a for a in TTFont(source_path)["fvar"].axes}["wght"].defaultValue
        )
    else:
        matched_wght, _ = _match_source_weight(source_path, "hyphen", "vertical", target_stroke)

    source_font = instancer.instantiateVariableFont(
        TTFont(source_path), {"wght": matched_wght}, inplace=False
    )
    sglyf = source_font["glyf"]
    sgs = source_font.getGlyphSet()
    shear = math.tan(math.radians(-slant))

    mapping = {}
    for base, src in glyph_map.items():
        alt = f"{base}.{feature_tag}"
        glyph, _ = _sheared(sglyf, sgs, [src], shear)
        _add_glyph(target_font, alt, glyph)
        mapping[base] = alt

    gsub = target_font["GSUB"].table
    LL = gsub.LookupList.Lookup
    glyph_map_ids = target_font.getReverseGlyphMap(rebuild=True)

    if escape_only:
        # Inner single-sub (invoked contextually) + an ordered chain lookup.
        inner = len(LL)
        LL.append(_single_sub_lookup(mapping))

        base_glyph = next(iter(mapping))  # "backslash"
        alt_glyph = mapping[base_glyph]
        colon = target_font.getBestCmap().get(ord(":"))
        escape_cov = set()
        for ch in escape_chars:
            escape_cov |= _resolve_glyphs(target_font, ch)
        escape_cov.add(base_glyph)  # so `\\` (followed by a backslash) matches

        chain = ot.Lookup()
        chain.LookupType = 6
        chain.LookupFlag = 0
        subtables = []
        if colon:
            # don't thin a drive-path backslash ( :\ )
            subtables.append(_ignore_subtable([[colon]], [[base_glyph]], glyph_map_ids))
        # don't thin the 2nd of a consecutive pair (it's the escaped literal)
        subtables.append(_ignore_subtable([[alt_glyph]], [[base_glyph]], glyph_map_ids))
        # thin when followed by an escape character
        subtables.append(_sub_subtable([[base_glyph]], [sorted(escape_cov)], inner, glyph_map_ids))

        # Recursive ligates \b \n \r \t \v into combined glyphs (backslash_X.code,
        # preceded by the LIG spacer). Decompose those to thin backslash + the
        # plain letter so the common escapes get the thin backslash too.
        glyf = target_font["glyf"]
        lig_to_thin = None
        for ch in "bnrtv":
            code = f"backslash_{ch}.code"
            if code not in glyf or "LIG" not in glyf:
                continue
            letter = _terminal_glyph(target_font, ch)
            if not letter:
                continue
            if lig_to_thin is None:
                lig_to_thin = len(LL)
                LL.append(_single_sub_lookup({"LIG": alt_glyph}))
            code_to_letter = len(LL)
            LL.append(_single_sub_lookup({code: letter}))
            subtables.append(
                _multi_sub_subtable([["LIG"], [code]], [(0, lig_to_thin), (1, code_to_letter)],
                                    glyph_map_ids)
            )

        chain.SubTable = subtables
        chain.SubTableCount = len(subtables)

        lookup_index = len(LL)
        LL.append(chain)
    else:
        lookup_index = len(LL)
        LL.append(_single_sub_lookup(mapping))

    gsub.LookupList.LookupCount = len(LL)

    # Stylistic-set feature with a macOS UI name.
    name_id = _free_name_id(target_font)
    target_font["name"].setName(ui_name, name_id, 3, 1, 0x409)

    params = ot.FeatureParamsStylisticSet()
    params.Version = 0
    params.UINameID = name_id

    feature = ot.Feature()
    feature.FeatureParams = params
    feature.LookupListIndex = [lookup_index]
    feature.LookupCount = 1

    rec = ot.FeatureRecord()
    rec.FeatureTag = feature_tag
    rec.Feature = feature
    feature_index = len(gsub.FeatureList.FeatureRecord)
    gsub.FeatureList.FeatureRecord.append(rec)
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)

    for script_rec in gsub.ScriptList.ScriptRecord:
        script = script_rec.Script
        lang_systems = []
        if script.DefaultLangSys is not None:
            lang_systems.append(script.DefaultLangSys)
        lang_systems.extend(r.LangSys for r in script.LangSysRecord)
        for ls in lang_systems:
            if feature_index not in ls.FeatureIndex:
                ls.FeatureIndex.append(feature_index)
                ls.FeatureCount = len(ls.FeatureIndex)

    target_font.getReverseGlyphMap(rebuild=True)
    return {"feature": feature_tag, "added": list(mapping.values()), "matched_wght": matched_wght}
