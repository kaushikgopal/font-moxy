"""
Variable-font helpers for the Recursive KG VF build (scripts/build-variable-font.py).

Unlike the static build (which instantiates 8 fixed instances and *freezes* the
Lilex tweaks into ``calt``), the VF keeps all five Recursive axes live and exposes
the Lilex tweaks as **opt-in** OpenType features. The default font is therefore
pristine, fully-variable Recursive; nothing is baked.

The hard part this module solves is grafting a borrowed Lilex outline as a NEW
alternate glyph (e.g. ``parenleft.lilx``) that *varies across the Recursive axes*
— it thickens with ``wght`` and shears with ``slnt`` — so the opt-in feature still
interpolates cleanly everywhere. The recipe (proven by the spike):

  * Instance Lilex at the ``wght`` whose stroke matches Recursive at the axis
    DEFAULT (wght 300) → that outline becomes the alternate's default geometry.
  * Instance Lilex at the ``wght`` matching Recursive at wght max (1000, which
    Lilex can only meet up to its own 700 cap) → the heavy master.
  * gvar ``TupleVariation({"wght": (0, 1, 1)}, deltas)`` where deltas are the
    per-point (heavy - light) differences, plus four zero phantom-point deltas.
  * A second ``TupleVariation({"slnt": (-1, -1, 0)}, shear_deltas)`` leans the
    glyph for italics (shear = tan 15°, applied to the light geometry).

MONO/CASL/CRSV are left un-varied on the borrowed glyphs (a single curvy paren
shape across MONO/CASL is fine); their *advance* is fixed at the 600-unit cell.
New glyphs would otherwise misbehave under HVAR (see ``repair_hvar`` below), so
each is pinned to a zero-delta advance entry — fixed 600/1200/1800 at every axis
location, exactly the monospace behaviour we want. The pristine originals are
never touched.

All GSUB edits are hand-built (otlLib/otTables), append-only. feaLib's
addOpenTypeFeatures rewrites ``calt`` and silently disables Recursive's existing
ligatures, so it must not be used.

Lilex is SIL OFL 1.1 (see font-data/Lilex-OFL.txt); keep that notice on builds.
"""

from __future__ import annotations

import math
from typing import Sequence

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.otlLib import builder as otl
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

from borrow_glyphs import _measure_stroke, _match_source_weight, CELL

# slnt axis: default 0, min -15. Italic peak is the normalised min (-1); the lean
# is a forward shear of tan(15°).
SLNT_SHEAR = math.tan(math.radians(15))


# ----------------------------------------------------------------------------
# Lilex instance cache

_LILEX_CACHE: dict[tuple[str, int], TTFont] = {}


def lilex_instance(source_path: str, wght: int) -> TTFont:
    key = (source_path, wght)
    if key not in _LILEX_CACHE:
        _LILEX_CACHE[key] = instancer.instantiateVariableFont(
            TTFont(source_path), {"wght": wght}, inplace=False
        )
    return _LILEX_CACHE[key]


# ----------------------------------------------------------------------------
# Weight anchors: match Lilex to Recursive at the wght axis endpoints.

_REC_INST_CACHE: dict[tuple[str, frozenset], TTFont] = {}


def _recursive_instance(recursive_path: str, loc: dict) -> TTFont:
    key = (recursive_path, frozenset(loc.items()))
    if key not in _REC_INST_CACHE:
        _REC_INST_CACHE[key] = instancer.instantiateVariableFont(
            TTFont(recursive_path), loc, inplace=False
        )
    return _REC_INST_CACHE[key]


def wght_anchors(
    recursive_path: str,
    *,
    target_glyph: str,
    source_path: str,
    probe_source: str,
    axis: str,
    loc: dict | None = None,
) -> tuple[int, int]:
    """Return (light_wght, heavy_wght) Lilex weights whose `probe_source` stroke
    matches Recursive's `target_glyph` stroke at wght 300 (axis default) and 1000
    (axis max). `loc` pins the other axes for measuring (default: all OG defaults).
    """
    base = dict(loc or {})
    light_loc = dict(base)
    heavy_loc = dict(base, wght=1000)
    sl = _measure_stroke(
        _recursive_instance(recursive_path, light_loc)["glyf"][target_glyph],
        _recursive_instance(recursive_path, light_loc).getGlyphSet(),
        axis,
    )
    sh = _measure_stroke(
        _recursive_instance(recursive_path, heavy_loc)["glyf"][target_glyph],
        _recursive_instance(recursive_path, heavy_loc).getGlyphSet(),
        axis,
    )
    light_w, _ = _match_source_weight(source_path, probe_source, axis, sl)
    heavy_w, _ = _match_source_weight(source_path, probe_source, axis, sh)
    return light_w, heavy_w


# ----------------------------------------------------------------------------
# Geometry: decompose Lilex source glyph(s) to a simple contour outline.


def _decompose_parts(font: TTFont, parts: Sequence[str], shear: float,
                     dx: float = 0.0, dy: float = 0.0):
    """Draw `parts` (tiled left-to-right across cells) into one simple TTGlyph.

    Composites are decomposed to contours so the result references no component
    glyphs. A common (dx, dy) translation is applied to every part — passing the
    same offset to every master keeps gvar deltas (differences) unchanged.
    Returns (glyph, raw_coords, bounds). `raw_coords` is the flat list of point
    coordinates (no phantom points) used for gvar delta maths.
    """
    gs = font.getGlyphSet()
    n = len(parts)
    pen = TTGlyphPen(gs)
    bpen = BoundsPen(gs)
    for i, part in enumerate(parts):
        cell_dx = (i - (n - 1)) * CELL + dx
        aff = (1.0, 0.0, shear, 1.0, cell_dx, dy)
        rec = DecomposingRecordingPen(gs)
        font["glyf"][part].draw(rec, gs)
        rec.replay(TransformPen(pen, aff))
        rec.replay(TransformPen(bpen, aff))
    glyph = pen.glyph()
    coords = [tuple(p) for p in glyph.coordinates] if glyph.numberOfContours > 0 else []
    return glyph, coords, bpen.bounds


def source_bounds(source_path: str, wght: int, glyphs: Sequence[str]):
    """Combined bounds of `glyphs` (tiled across cells) at a Lilex wght."""
    font = lilex_instance(source_path, wght)
    _, _, bounds = _decompose_parts(font, glyphs, 0.0)
    return bounds


# ----------------------------------------------------------------------------
# The core recipe: graft a Lilex glyph as a variable alternate.


def graft_variable_alternate(
    target_font: TTFont,
    *,
    source_path: str,
    alt_name: str,
    source_glyphs: Sequence[str],
    light_wght: int,
    heavy_wght: int,
    advance: int = CELL,
    dx: float = 0.0,
    dy: float = 0.0,
    add_slnt: bool = True,
    mono_wght: int | None = None,
    monoheavy_wght: int | None = None,
) -> dict:
    """Create `alt_name` as a variable copy of Lilex `source_glyphs`.

    The default geometry is Lilex at `light_wght`; a wght TupleVariation morphs it
    toward Lilex at `heavy_wght` as Recursive's wght goes 300→1000. An optional
    slnt TupleVariation leans it for italics. The original target glyph is never
    touched — this is a brand-new alternate the opt-in feature substitutes to.

    If `mono_wght` is given, a MONO TupleVariation (and the wght×MONO corner from
    `monoheavy_wght`) thickens the glyph as MONO 0→1, matching Recursive's own
    heavier mono strokes. Pass advance and (dx, dy) to size/align multi-cell
    outlines onto Recursive's ligature cell.
    """
    light = lilex_instance(source_path, light_wght)
    heavy = lilex_instance(source_path, heavy_wght)

    lg, lcoords, _ = _decompose_parts(light, source_glyphs, 0.0, dx, dy)
    hg, hcoords, _ = _decompose_parts(heavy, source_glyphs, 0.0, dx, dy)
    if len(lcoords) != len(hcoords):
        raise ValueError(
            f"{alt_name}: light/heavy point count mismatch "
            f"({len(lcoords)} vs {len(hcoords)})"
        )

    # default geometry = the light master
    lg.recalcBounds(target_font["glyf"])
    target_font["glyf"][alt_name] = lg
    target_font["hmtx"].metrics[alt_name] = (
        advance, lg.xMin if lg.numberOfContours > 0 else 0
    )
    order = target_font.getGlyphOrder()
    if alt_name not in order:
        target_font.setGlyphOrder(list(order) + [alt_name])

    npts = len(lcoords)
    variations = []

    # wght: light -> heavy (peak at normalised wght +1, the axis max 1000)
    wght_deltas = [
        (round(hcoords[i][0] - lcoords[i][0]), round(hcoords[i][1] - lcoords[i][1]))
        for i in range(npts)
    ] + [(0, 0)] * 4
    variations.append(TupleVariation({"wght": (0.0, 1.0, 1.0)}, wght_deltas))

    # MONO (optional): light -> mono master at MONO +1
    if mono_wght is not None:
        mono = lilex_instance(source_path, mono_wght)
        _, mcoords, _ = _decompose_parts(mono, source_glyphs, 0.0, dx, dy)
        mono_deltas = [
            (round(mcoords[i][0] - lcoords[i][0]), round(mcoords[i][1] - lcoords[i][1]))
            for i in range(npts)
        ] + [(0, 0)] * 4
        variations.append(TupleVariation({"MONO": (0.0, 1.0, 1.0)}, mono_deltas))

        # wght x MONO corner so the (wght=1, MONO=1) corner lands on its own master
        if monoheavy_wght is not None:
            mh = lilex_instance(source_path, monoheavy_wght)
            _, mhcoords, _ = _decompose_parts(mh, source_glyphs, 0.0, dx, dy)
            corner = [
                (
                    round(mhcoords[i][0] - hcoords[i][0] - mcoords[i][0] + lcoords[i][0]),
                    round(mhcoords[i][1] - hcoords[i][1] - mcoords[i][1] + lcoords[i][1]),
                )
                for i in range(npts)
            ] + [(0, 0)] * 4
            variations.append(
                TupleVariation(
                    {"wght": (0.0, 1.0, 1.0), "MONO": (0.0, 1.0, 1.0)}, corner
                )
            )

    # slnt: forward shear for italics (peak at normalised slnt -1, the axis min)
    if add_slnt:
        slnt_deltas = [
            (round(SLNT_SHEAR * lcoords[i][1]), 0) for i in range(npts)
        ] + [(0, 0)] * 4
        variations.append(TupleVariation({"slnt": (-1.0, -1.0, 0.0)}, slnt_deltas))

    target_font["gvar"].variations[alt_name] = variations
    return {"alt": alt_name, "npts": npts, "tuples": len(variations)}


def add_variable_glyph(
    font: TTFont,
    name: str,
    *,
    light_glyph,
    light_coords: Sequence[tuple],
    heavy_coords: Sequence[tuple],
    advance: int = CELL,
    add_slnt: bool = True,
) -> None:
    """Register `name` from a pre-built light TTGlyph + light/heavy point coords.

    For hand-welded glyphs (the long-arrow caps/shaft) whose outline is built at
    Recursive's light (wght 300) and heavy (1000) masters: the default geometry is
    the light glyph, a wght TupleVariation morphs it to heavy, and an optional slnt
    shear leans it. Advance is fixed (new glyphs are out of HVAR). Point structures
    must match between light and heavy.
    """
    if len(light_coords) != len(heavy_coords):
        raise ValueError(
            f"{name}: light/heavy point count mismatch "
            f"({len(light_coords)} vs {len(heavy_coords)})"
        )
    light_glyph.recalcBounds(font["glyf"])
    font["glyf"][name] = light_glyph
    font["hmtx"].metrics[name] = (
        advance, light_glyph.xMin if light_glyph.numberOfContours > 0 else 0
    )
    if name not in font.getGlyphOrder():
        font.setGlyphOrder(list(font.getGlyphOrder()) + [name])

    npts = len(light_coords)
    wght_deltas = [
        (round(heavy_coords[i][0] - light_coords[i][0]),
         round(heavy_coords[i][1] - light_coords[i][1]))
        for i in range(npts)
    ] + [(0, 0)] * 4
    variations = [TupleVariation({"wght": (0.0, 1.0, 1.0)}, wght_deltas)]
    if add_slnt:
        slnt_deltas = [
            (round(SLNT_SHEAR * light_coords[i][1]), 0) for i in range(npts)
        ] + [(0, 0)] * 4
        variations.append(TupleVariation({"slnt": (-1.0, -1.0, 0.0)}, slnt_deltas))
    font["gvar"].variations[name] = variations


# ----------------------------------------------------------------------------
# HVAR repair (keep the table; make new glyphs advance-correct).


def repair_hvar(font: TTFont) -> int:
    """Point every glyph missing from HVAR's AdvWidthMap at a zero-delta entry.

    Recursive ships HVAR (advance-width variations) alongside gvar; HarfBuzz reads
    advances from HVAR. Its AdvWidthMap only covers the ORIGINAL glyphs, and per the
    DeltaSetIndexMap spec, glyph IDs beyond the map repeat the LAST entry — which
    carries a +700 wght delta — so our fixed-advance alternates wrongly grow to 800
    at heavy weights. (fontTools' instancer hides this; it maps HVAR by glyph name.)

    Rather than drop HVAR, we map every new glyph at a zero-delta variation index,
    so its advance stays the static hmtx value (600/1200/1800) at every axis
    location. Recursive already has such an entry (the one .notdef uses); we find it
    dynamically. Returns the number of glyphs newly mapped.
    """
    if "HVAR" not in font:
        return 0
    hvar = font["HVAR"].table
    awm = hvar.AdvWidthMap
    if awm is None or not hasattr(awm, "mapping"):
        return 0

    zero_idx = None
    for outer, ivd in enumerate(hvar.VarStore.VarData):
        for inner, row in enumerate(ivd.Item):
            if all(d == 0 for d in row):
                zero_idx = (outer << 16) | inner
                break
        if zero_idx is not None:
            break
    if zero_idx is None:
        raise RuntimeError("no zero-delta HVAR variation index to map new glyphs to")

    mapping = awm.mapping
    added = 0
    for g in font.getGlyphOrder():
        if g not in mapping:
            mapping[g] = zero_idx
            added += 1
    return added


# ----------------------------------------------------------------------------
# GSUB plumbing (hand-built, append-only).


def append_lookup(font: TTFont, lookup: ot.Lookup) -> int:
    """Append a Lookup to GSUB's LookupList; return its index."""
    LL = font["GSUB"].table.LookupList.Lookup
    i = len(LL)
    LL.append(lookup)
    font["GSUB"].table.LookupList.LookupCount = len(LL)
    return i


def single_sub_lookup(mapping: dict[str, str]) -> ot.Lookup:
    lk = ot.Lookup()
    lk.LookupType = 1
    lk.LookupFlag = 0
    lk.SubTable = [otl.buildSingleSubstSubtable(mapping)]
    lk.SubTableCount = 1
    return lk


def free_name_id(font: TTFont) -> int:
    used = {r.nameID for r in font["name"].names}
    nid = 256
    while nid in used:
        nid += 1
    return nid


def add_feature(
    font: TTFont,
    *,
    feature_tag: str,
    lookup_indices: Sequence[int],
    ui_name: str | None = None,
) -> int:
    """Append a FeatureRecord wired into every langsys of every script.

    If `ui_name` is given, attach FeatureParamsStylisticSet with a macOS UI name
    (used for registered stylistic sets like ss13 "Kaush's preferences").
    Returns the new feature index.
    """
    gsub = font["GSUB"].table

    feature = ot.Feature()
    if ui_name is not None:
        name_id = free_name_id(font)
        font["name"].setName(ui_name, name_id, 3, 1, 0x409)
        params = ot.FeatureParamsStylisticSet()
        params.Version = 0
        params.UINameID = name_id
        feature.FeatureParams = params
    else:
        feature.FeatureParams = None
    feature.LookupListIndex = list(lookup_indices)
    feature.LookupCount = len(feature.LookupListIndex)

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

    return feature_index


def feature_lookup_indices(font: TTFont, tags: Sequence[str]) -> list[int]:
    """Collect (in order, de-duplicated) the lookup indices used by `tags`."""
    gsub = font["GSUB"].table
    out: list[int] = []
    for tag in tags:
        for fr in gsub.FeatureList.FeatureRecord:
            if fr.FeatureTag == tag:
                for i in fr.Feature.LookupListIndex:
                    if i not in out:
                        out.append(i)
    return out
