"""
Add an optional OpenType stylistic set whose substitutions use glyphs borrowed
from another font.

Unlike the always-on borrows, this stays a real, toggleable feature in the
output: it does nothing unless the application enables the feature tag. Used for
Lilex's "thin backslash" (its ss03), so backslash only becomes thin when the user
turns the set on (e.g. font-feature-settings "ss03").

The new glyph(s) are imported weight-matched + sheared; a single-substitution
lookup and a stylistic-set FeatureRecord are appended by hand and wired into every
script's language systems, with a UI name added to the name table so editors can
label the set.

Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt).
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.tables import otTables as ot

from borrow_glyphs import _measure_stroke, _match_source_weight
from join_dashes import _sheared, _add_glyph, _single_sub_lookup


def _free_name_id(font) -> int:
    used = {r.nameID for r in font["name"].names}
    nid = 256
    while nid in used:
        nid += 1
    return nid


def add_stylistic_set(
    target_font: TTFont,
    *,
    source_path: str,
    feature_tag: str,
    ui_name: str,
    glyph_map: dict,
    slant: float = 0.0,
) -> dict:
    """Import glyphs and expose them as an optional stylistic set `feature_tag`.

    glyph_map maps target glyph -> source glyph; a backslash-thin style maps
    {"backslash": "backslash.ss03"}. The imported alternates get a ".thin"-style
    suffix derived from the feature tag to avoid name clashes.
    """
    # Weight-match via the hyphen so the imported alternate scales with the
    # instance but keeps the source's (intentionally thin) proportions.
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

    # Import alternates and build the base->alternate name mapping.
    mapping = {}
    for base, src in glyph_map.items():
        alt = f"{base}.{feature_tag}"
        glyph, _ = _sheared(sglyf, sgs, [src], shear)
        _add_glyph(target_font, alt, glyph)
        mapping[base] = alt

    gsub = target_font["GSUB"].table
    LL = gsub.LookupList.Lookup
    lookup_index = len(LL)
    LL.append(_single_sub_lookup(mapping))
    gsub.LookupList.LookupCount = len(LL)

    # Build the stylistic-set feature with a UI name.
    name_id = _free_name_id(target_font)
    target_font["name"].setName(ui_name, name_id, 3, 1, 0x409)
    target_font["name"].setName(ui_name, name_id, 1, 0, 0)

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

    # Wire the feature into every language system so applications can select it.
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
