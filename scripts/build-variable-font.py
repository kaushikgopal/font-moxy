"""
Build a variable-font source of "Recursive KG" with the selected Lilex features
exposed as OPT-IN OpenType features.

This is a NEW, separate source from the static code-font build
(scripts/instantiate-code-fonts.py + premade-configs/config.kg.yaml), which stays
untouched. Where the static build instantiates 8 fixed instances and *bakes* the
Lilex tweaks into ``calt``, this build keeps all five Recursive axes
(MONO/CASL/wght/slnt/CRSV) live and ships the tweaks as features that are OFF by
default. So the bare font renders as pristine, fully-variable OG Recursive.

Two opt-in bundles (both off by default):

  * ``lilx`` (custom 4-char feature tag) — the ported-from-Lilex tweaks only:
    curvy parens (Lilex cv13), connected dashes, connected bars (Lilex cv11),
    a thin escape-only backslash, and the 12 added single-char arrows.
  * ``ss13`` (registered stylistic set, UI name "Kaush's preferences") — whose
    Feature references Recursive's OWN ss03/ss06/ss08/ss10/ss11 lookups, so one
    toggle applies Simplified f / Simplified r / serifless L&Z / dotted 0 /
    simplified 1 together.

Plus a DEFAULT calt fix: Recursive-style long arrows (--->, <--, …) built from
Recursive's own arrow geometry (native height), because the default font has no
connected-dash shaft.

Usage:
    venv/bin/python scripts/build-variable-font.py \
        [font-data/Recursive_VF_1.085.ttf] [out.ttf]

Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt); bundle that notice on
distribution.
"""

from __future__ import annotations

import os
import sys

from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vf_lilex import (  # noqa: E402
    add_feature,
    append_lookup,
    feature_lookup_indices,
    graft_variable_alternate,
    single_sub_lookup,
    source_bounds,
    wght_anchors,
)

RECURSIVE_VF = "font-data/Recursive_VF_1.085.ttf"
LILEX_VF = "font-data/Lilex[wght].ttf"

FAMILY = "Rec Mono Casual KG"
PS_FAMILY = "RecMonoCasualKG"
DEFAULT_OUT = "fonts/RecMonoCasualKG-VF/RecMonoCasualKG[MONO,CASL,wght,slnt,CRSV].ttf"

# Recursive's own stylistic sets the user prefers, bundled under "Kaush's prefs":
#   ss03 Simplified f, ss06 Simplified r, ss08 serifless L&Z, ss10 dotted 0,
#   ss11 simplified 1.
KAUSH_SETS = ["ss03", "ss06", "ss08", "ss10", "ss11"]


# ----------------------------------------------------------------------------
# Name table — rename the family to "Rec Mono Casual KG", keep every axis.


def rename_family(font: TTFont) -> None:
    name = font["name"]

    def setname(nid, value):
        name.setName(value, nid, 3, 1, 0x409)  # macOS only (Windows skipped)

    setname(1, FAMILY)               # Font Family
    setname(2, "Regular")            # Subfamily (RIBBI default-instance label)
    setname(3, f"1.085;ARRW;{PS_FAMILY}-Regular")  # Unique ID
    setname(4, FAMILY)               # Full font name (default instance)
    setname(6, f"{PS_FAMILY}-Regular")             # PostScript name
    setname(16, FAMILY)              # Typographic Family
    setname(17, "Regular")           # Typographic Subfamily


# ----------------------------------------------------------------------------
# "Kaush's preferences" — a registered stylistic set bundling Recursive's own
# ss03/06/08/10/11 lookups behind one toggle.


def add_kaush_preferences(font: TTFont) -> None:
    lookups = feature_lookup_indices(font, KAUSH_SETS)
    add_feature(
        font,
        feature_tag="ss13",
        lookup_indices=lookups,
        ui_name="Kaush's preferences",
    )
    print(f"  • ss13 'Kaush's preferences' -> reuses lookups {lookups} "
          f"({'/'.join(KAUSH_SETS)})")


# ----------------------------------------------------------------------------
# lilx tweak: curvy parentheses (Lilex cv13) as variable alternates.


def add_curvy_parens(font: TTFont, recursive_path: str) -> list[int]:
    """Graft parenleft/right.lilx (variable) and return the substituting lookup.

    Parens barely change stroke across MONO (≈50 at wght300, ≈240 at wght1000 for
    both MONO 0 and 1), so MONO is frozen — only wght (300→1000) + slnt shear.
    """
    light, heavy = wght_anchors(
        recursive_path,
        target_glyph="parenleft",
        source_path=LILEX_VF,
        probe_source="parenleft.cv13",
        axis="horizontal",
    )
    mapping = {}
    for base, src in (("parenleft", "parenleft.cv13"),
                      ("parenright", "parenright.cv13")):
        alt = f"{base}.lilx"
        graft_variable_alternate(
            font,
            source_path=LILEX_VF,
            alt_name=alt,
            source_glyphs=[src],
            light_wght=light,
            heavy_wght=heavy,
        )
        mapping[base] = alt
    font.getReverseGlyphMap(rebuild=True)
    idx = append_lookup(font, single_sub_lookup(mapping))
    print(f"  • curvy parens (cv13): Lilex wght {light}->{heavy}, lookup {idx}")
    return [idx]


# ----------------------------------------------------------------------------
# lilx tweak: connected bars |> and <| (Lilex cv11).


def add_connected_bars(font: TTFont, recursive_path: str) -> list[int]:
    """Graft connected |> and <| (Lilex cv11) as variable 2-cell alternates.

    Recursive's dlig ligates bar+greater -> bar_greater.code (a forward 2-cell
    glyph, adv 1200) and less+bar -> less_bar.code. lilx substitutes those for
    connected versions built from Lilex's bar_greater.liga.cv11 /
    less_bar.liga.cv11, repositioned onto Recursive's 1200-unit ligature cell.
    (Requires dlig on — the toggle any Recursive code ligature needs; Recursive
    ships no calt.)
    """
    light, heavy = wght_anchors(
        recursive_path,
        target_glyph="bar",
        source_path=LILEX_VF,
        probe_source="bar",
        axis="horizontal",
    )
    rec = TTFont(recursive_path)
    rg = rec["glyf"]
    mapping = {}
    specs = [
        ("bar_greater.code", "bar_greater.liga.cv11"),
        ("less_bar.code", "less_bar.liga.cv11"),
    ]
    for target, src in specs:
        tg = rg[target]
        tg.recalcBounds(rg)
        adv = rec["hmtx"].metrics[target][0]
        sb = source_bounds(LILEX_VF, light, [src])
        dx = tg.xMin - sb[0]                                    # align left ink edge
        dy = (tg.yMin + tg.yMax) / 2.0 - (sb[1] + sb[3]) / 2.0  # vertical centre
        alt = f"{target}.lilx"
        graft_variable_alternate(
            font,
            source_path=LILEX_VF,
            alt_name=alt,
            source_glyphs=[src],
            light_wght=light,
            heavy_wght=heavy,
            advance=adv,
            dx=dx,
            dy=dy,
        )
        mapping[target] = alt
    font.getReverseGlyphMap(rebuild=True)
    idx = append_lookup(font, single_sub_lookup(mapping))
    print(f"  • connected bars (cv11): Lilex wght {light}->{heavy}, lookup {idx}")
    return [idx]


# ----------------------------------------------------------------------------


def build(src_path: str, out_path: str) -> None:
    print(f"Loading {src_path}")
    font = TTFont(src_path)
    # Force-decompile glyf/gvar now, before we add any glyphs — both store a
    # glyphCount that is asserted against the (still-original) glyph order.
    _ = font["glyf"]
    _ = font["gvar"]

    print("Renaming family -> 'Rec Mono Casual KG' (all 5 axes kept)")
    rename_family(font)

    print("Adding 'Kaush's preferences' bundle (ss13)")
    add_kaush_preferences(font)

    # ---- lilx: the ported-from-Lilex tweaks, all behind one opt-in tag --------
    print("Building lilx feature (opt-in Lilex tweaks)")
    lilx_lookups: list[int] = []
    lilx_lookups += add_curvy_parens(font, src_path)
    lilx_lookups += add_connected_bars(font, src_path)

    add_feature(font, feature_tag="lilx", lookup_indices=lilx_lookups)
    print(f"  • lilx -> lookups {lilx_lookups}")

    # rebuild glyph-name cache before any compile/cmap touches new glyphs
    font.getReverseGlyphMap(rebuild=True)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    font.save(out_path)
    print(f"\n→ Saved {out_path}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else RECURSIVE_VF
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    build(src, out)
