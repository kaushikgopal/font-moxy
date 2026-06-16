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

import copy
import os
import sys
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.otlLib import builder as otl

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
# lilx tweak: connected dashes (--- and longer), Lilex-style.


def add_connected_dashes(font: TTFont, recursive_path: str) -> list[int]:
    """Connect hyphen runs Lilex-style (--- and longer), as opt-in variable glyphs.

    Recursive's dlig ligates only ``--`` and ``---`` (runs of 4+ stay as loose
    ``hyphen`` glyphs). So, like the static build, lilx:
      * substitutes the dlig-formed hyphen_hyphen_hyphen.code -> a connected 3-cell
        bar (.lilx) for ``---``;
      * runs a chain that re-cuts loose runs of >= 4 hyphens into Lilex's
        start/middle/end .seq pieces.
    ``--`` is left as Recursive draws it (two dashes, like Lilex). Variable seq
    pieces + connected bar thicken with wght and shear with slnt.
    """
    from join_dashes import _chain3

    light, heavy = wght_anchors(
        recursive_path,
        target_glyph="hyphen",
        source_path=LILEX_VF,
        probe_source="hyphen",
        axis="vertical",
    )

    # Vertical align: shift Lilex seq pieces onto Recursive's hyphen centre so
    # the joined run sits at the dash height (≈ -6 units).
    rec = TTFont(recursive_path)
    rg = rec["glyf"]
    h = rg["hyphen"]; h.recalcBounds(rg)
    rec_dash_cy = (h.yMin + h.yMax) / 2.0
    seq = ["hyphen_start.seq", "hyphen_middle.seq", "hyphen_end.seq"]
    mid_b = source_bounds(LILEX_VF, light, ["hyphen_middle.seq"])
    dy = rec_dash_cy - (mid_b[1] + mid_b[3]) / 2.0

    for name in seq:
        graft_variable_alternate(
            font,
            source_path=LILEX_VF,
            alt_name=name,
            source_glyphs=[name],
            light_wght=light,
            heavy_wght=heavy,
            dy=dy,
        )

    # Connected "---": tile the three seq pieces onto Recursive's 1800-unit
    # hyphen_hyphen_hyphen.code ink cell.
    tri = rg["hyphen_hyphen_hyphen.code"]; tri.recalcBounds(rg)
    tiled = source_bounds(LILEX_VF, light, seq)
    dx3 = tri.xMin - tiled[0]
    code_lilx = "hyphen_hyphen_hyphen.code.lilx"
    graft_variable_alternate(
        font,
        source_path=LILEX_VF,
        alt_name=code_lilx,
        source_glyphs=seq,
        light_wght=light,
        heavy_wght=heavy,
        advance=rec["hmtx"].metrics["hyphen_hyphen_hyphen.code"][0],
        dx=dx3,
        dy=dy,
    )

    glyph_map = font.getReverseGlyphMap(rebuild=True)

    # lilx lookups: the --- single-sub, three seq single-subs, and a chain.
    lookups: list[int] = []
    i_tri = append_lookup(
        font, single_sub_lookup({"hyphen_hyphen_hyphen.code": code_lilx})
    )
    lookups.append(i_tri)

    i_start = append_lookup(font, single_sub_lookup({"hyphen": "hyphen_start.seq"}))
    i_mid = append_lookup(font, single_sub_lookup({"hyphen": "hyphen_middle.seq"}))
    i_end = append_lookup(font, single_sub_lookup({"hyphen": "hyphen_end.seq"}))

    seq_back = ["hyphen_start.seq", "hyphen_middle.seq"]
    min_run = 4
    start_lookahead = [["hyphen"]] * (min_run - 1)
    chain = ot.Lookup()
    chain.LookupType = 6
    chain.LookupFlag = 0
    chain.SubTable = [
        _chain3([seq_back], [["hyphen"]], [["hyphen"]], i_mid, glyph_map),  # middle
        _chain3([seq_back], [["hyphen"]], [], i_end, glyph_map),            # end
        _chain3([], [["hyphen"]], start_lookahead, i_start, glyph_map),     # start
    ]
    chain.SubTableCount = len(chain.SubTable)
    i_chain = append_lookup(font, chain)
    lookups.append(i_chain)

    print(f"  • connected dashes: Lilex wght {light}->{heavy}, "
          f"lookups {lookups} (+inner {[i_start, i_mid, i_end]})")
    return lookups


# ----------------------------------------------------------------------------
# lilx tweak: thin escape-only backslash (Lilex ss03 glyph).


def add_thin_backslash(font: TTFont, recursive_path: str) -> list[int]:
    """Thin the backslash, but ONLY when it acts as an escape (Lilex glyph).

    Reuses the static build's escape-only contextual logic (add_stylistic_set):
    thin when the backslash is followed by an escape character, but not a Windows
    drive path (``:\\``) and not the 2nd of a consecutive pair (``\\\\``). Escape
    chars are resolved through GSUB single-subs so the ss13 forms (r.simple etc.)
    are covered too. With dlig on, Recursive ligates \\b \\n \\r \\t \\v into
    backslash_X.code (just backslash+letter, no special drawing), so a multiple-sub
    decomposes those to thin-backslash + the base letter.
    """
    from add_stylistic_set import (
        _resolve_glyphs, _ignore_subtable, _sub_subtable, DEFAULT_ESCAPE_CHARS,
    )

    light, heavy = wght_anchors(
        recursive_path,
        target_glyph="hyphen",
        source_path=LILEX_VF,
        probe_source="hyphen",
        axis="vertical",
    )
    alt = "backslash.lilx"
    graft_variable_alternate(
        font,
        source_path=LILEX_VF,
        alt_name=alt,
        source_glyphs=["backslash.ss03"],
        light_wght=light,
        heavy_wght=heavy,
    )
    gm = font.getReverseGlyphMap(rebuild=True)

    base = "backslash"
    inner = append_lookup(font, single_sub_lookup({base: alt}))

    colon = font.getBestCmap().get(ord(":"))
    escape_cov: set[str] = set()
    for ch in DEFAULT_ESCAPE_CHARS:
        escape_cov |= _resolve_glyphs(font, ch)
    escape_cov.add(base)  # so `\\` (backslash before backslash) thins the first

    # _resolve_glyphs follows GSUB single-subs, but the MONO/CASL forms (e.g.
    # '0' -> zero.sans at MONO 0) come from FEATURE VARIATIONS it can't see. Expand
    # to every stem-sibling so escapes thin at all axis locations (\0 \1 \r etc.).
    stem_index: dict[str, list[str]] = {}
    for g in font.getGlyphOrder():
        stem_index.setdefault(g.split(".")[0], []).append(g)
    for g in list(escape_cov):
        escape_cov.update(stem_index.get(g.split(".")[0], []))

    chain = ot.Lookup()
    chain.LookupType = 6
    chain.LookupFlag = 0
    subtables = []
    if colon:  # don't thin a drive-path backslash ( :\ )
        subtables.append(_ignore_subtable([[colon]], [[base]], gm))
    # don't thin the 2nd of a consecutive pair (it's the escaped literal)
    subtables.append(_ignore_subtable([[alt]], [[base]], gm))
    # thin when followed by an escape character
    subtables.append(_sub_subtable([[base]], [sorted(escape_cov)], inner, gm))
    chain.SubTable = subtables
    chain.SubTableCount = len(subtables)
    lookups = [append_lookup(font, chain)]

    # dlig escape ligatures -> thin backslash + base letter
    cmap = font.getBestCmap()
    decomp = {}
    for ch in "bnrtv":
        code = f"backslash_{ch}.code"
        letter = cmap.get(ord(ch))
        if code in font["glyf"] and letter:
            decomp[code] = [alt, letter]
    if decomp:
        mult = ot.Lookup()
        mult.LookupType = 2
        mult.LookupFlag = 0
        mult.SubTable = [otl.buildMultipleSubstSubtable(decomp)]
        mult.SubTableCount = 1
        lookups.append(append_lookup(font, mult))

    print(f"  • thin backslash (escape-only): Lilex wght {light}->{heavy}, "
          f"lookups {lookups}")
    return lookups


# ----------------------------------------------------------------------------
# lilx tweak: 12 added single-char arrows Recursive lacks (gated, not default).

# Lilex glyph names == uniXXXX of the hooked / looping / circular / double arrows.
ARROW_GLYPHS = [
    "uni21A9", "uni21AA", "uni21B0", "uni21B1", "uni21B2", "uni21B3",
    "uni21B6", "uni21B7", "uni21BA", "uni21BB", "uni21C4", "uni21C6",
]


def add_arrow_chars(font: TTFont, recursive_path: str) -> list[int]:
    """Add 12 fancy single-char arrows from Lilex, GATED behind lilx.

    Recursive maps none of these codepoints (they render as .notdef). To keep the
    default pristine, each codepoint is cmap'd to a placeholder (a copy of
    Recursive's own .notdef, so the bare font shows the same tofu OG does) and lilx
    single-subs the placeholder to the real, variable arrow. (Tradeoff: mapping
    these codepoints suppresses OS font-fallback for them when lilx is off — the
    cost of gating new-codepoint glyphs behind a GSUB feature, since cmap itself
    can't be feature-gated. Flip to always-on by cmapping straight to the arrow.)
    """
    light, heavy = wght_anchors(
        recursive_path,
        target_glyph="hyphen",
        source_path=LILEX_VF,
        probe_source="hyphen",
        axis="vertical",
    )
    notdef = font["glyf"][".notdef"]
    notdef_adv = font["hmtx"].metrics[".notdef"][0]
    cmap_tables = [t for t in font["cmap"].tables if t.isUnicode()]

    mapping = {}
    for name in ARROW_GLYPHS:
        cp = int(name[3:], 16)
        # placeholder = static copy of .notdef (matches OG tofu)
        ph = f"{name}.off"
        box = copy.deepcopy(notdef)
        box.recalcBounds(font["glyf"])
        font["glyf"][ph] = box
        font["hmtx"].metrics[ph] = (notdef_adv, box.xMin if box.numberOfContours > 0 else 0)
        if ph not in font.getGlyphOrder():
            font.setGlyphOrder(list(font.getGlyphOrder()) + [ph])
        font["gvar"].variations[ph] = []  # static box, no variation

        # real, variable arrow (reached only via lilx)
        graft_variable_alternate(
            font,
            source_path=LILEX_VF,
            alt_name=name,
            source_glyphs=[name],
            light_wght=light,
            heavy_wght=heavy,
        )
        for t in cmap_tables:
            t.cmap[cp] = ph
        mapping[ph] = name

    font.getReverseGlyphMap(rebuild=True)
    idx = append_lookup(font, single_sub_lookup(mapping))
    print(f"  • added {len(ARROW_GLYPHS)} arrows (gated): Lilex wght "
          f"{light}->{heavy}, lookup {idx}")
    return [idx]


# ----------------------------------------------------------------------------


def build(src_path: str, out_path: str) -> None:
    print(f"Loading {src_path}")
    font = TTFont(src_path)
    # Force-decompile glyf/gvar now, before we add any glyphs — both store a
    # glyphCount that is asserted against the (still-original) glyph order.
    _ = font["glyf"]
    _ = font["gvar"]

    # Drop HVAR. Recursive ships BOTH HVAR and gvar; HarfBuzz then reads advances
    # from HVAR. New alternate glyphs are absent from HVAR's AdvWidthMap, and the
    # spec maps out-of-range glyph IDs to the LAST entry — which carries a +700
    # wght advance delta, so our 600-unit alternates wrongly grow to 800 at heavier
    # weights. Without HVAR, advances come from gvar phantom points: existing
    # glyphs keep their (already-encoded) advance variation and our alternates,
    # whose phantom deltas are zero, stay a fixed 600/1200/1800 at every location.
    if "HVAR" in font:
        del font["HVAR"]
        print("Dropped HVAR (advances now from gvar phantom points; fixes "
              "new-glyph advance at heavy weights)")

    print("Renaming family -> 'Rec Mono Casual KG' (all 5 axes kept)")
    rename_family(font)

    print("Adding 'Kaush's preferences' bundle (ss13)")
    add_kaush_preferences(font)

    # ---- lilx: the ported-from-Lilex tweaks, all behind one opt-in tag --------
    print("Building lilx feature (opt-in Lilex tweaks)")
    lilx_lookups: list[int] = []
    lilx_lookups += add_curvy_parens(font, src_path)
    lilx_lookups += add_connected_bars(font, src_path)
    lilx_lookups += add_connected_dashes(font, src_path)
    lilx_lookups += add_thin_backslash(font, src_path)
    lilx_lookups += add_arrow_chars(font, src_path)

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
