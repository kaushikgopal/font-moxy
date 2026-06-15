"""
Add brand-new single-character glyphs (with cmap entries) borrowed from Lilex.

Used for the single-character arrows Lilex draws but Recursive doesn't have at all
(hooked / looping / circular / double arrows: U+21A9, U+21AA, U+21B0-B3, U+21B6,
U+21B7, U+21BA, U+21BB, U+21C4, U+21C6). The plain directional arrows that *do*
exist in Recursive are handled as normal outline swaps via borrow_glyphs.

Each glyph is weight-matched to the instance (via the hyphen) and sheared for
italics, then registered in the glyf/hmtx tables and mapped in every Unicode cmap
subtable. Because Recursive has no native version to fall back to, these are added
at every weight (clamped to Lilex's heaviest) rather than skipped on a mismatch --
a slightly light arrow beats a missing glyph (tofu).

Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt).
"""

from __future__ import annotations

import math

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from borrow_glyphs import _measure_stroke, _match_source_weight
from join_dashes import _sheared, _add_glyph


def add_characters(
    target_font: TTFont,
    *,
    source_path: str,
    glyph_names: list[str],
    slant: float = 0.0,
) -> dict:
    """Import `glyph_names` from Lilex as new cmap'd glyphs. Names must be uniXXXX."""
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

    cmap_tables = [t for t in target_font["cmap"].tables if t.isUnicode()]
    added = []
    for name in glyph_names:
        if name not in sglyf:
            raise KeyError(f"source glyph '{name}' not in {source_path}")
        if not name.startswith("uni"):
            raise ValueError(f"expected a uniXXXX glyph name, got '{name}'")
        codepoint = int(name[3:], 16)

        # Drawing through the source glyph set decomposes any composites to contours.
        glyph, _ = _sheared(sglyf, sgs, [name], shear)
        _add_glyph(target_font, name, glyph)
        for t in cmap_tables:
            t.cmap[codepoint] = name
        added.append(name)

    # Refresh the reverse glyph map so the new glyphs resolve when cmap/GSUB compile.
    target_font.getReverseGlyphMap(rebuild=True)
    return {"added": added, "matched_wght": matched_wght}
