"""
Borrow glyph outlines from another variable font and graft them into a generated
Recursive code-font instance.

This is used to bring in glyphs/shapes that simply do not exist anywhere inside the
Recursive variable font (so they cannot be enabled as a frozen OpenType feature like
the ss01-ss12 stylistic sets). Examples from Lilex:

  * cv13 "curvier parentheses"  (parenleft.cv13 / parenright.cv13)
  * the arrow characters         (arrowright -> uni2192, arrowleft -> uni2190)
  * the arrow ligature shapes    (-> --> <-), which Recursive draws as single
    backward-drawing glyphs but Lilex composes from .seq parts.

Both Recursive and Lilex are UPM 1000, TrueType (`glyf`) outlines, with a 600-unit
monospace cell, which makes a near drop-in transplant possible. The jobs this module
does are:

  1. Weight matching. Lilex's strokes are drawn thinner than Recursive's at
     comparable weights, so we instantiate the Lilex variable font at whatever `wght`
     makes a chosen *probe* glyph's stroke best match the corresponding Recursive
     stroke (clamped to the Lilex axis maximum). If even the best match is too far
     off (heavy weights), the swap is skipped and Recursive's native glyph is kept.

  2. Slant matching. Recursive's italics are an oblique (slnt axis), not a true
     cursive. We shear the borrowed (upright) Lilex outline by the same angle so it
     leans with the rest of the instance.

  3. Composition. A target glyph may be built from several source glyphs laid out
     left-to-right across multiple cells. This is how Recursive's backward-drawing
     ligature glyphs (e.g. `hyphen_greater.code` for `->`) are reproduced from
     Lilex's `.seq` parts (e.g. greater_hyphen_start.seq + greater_hyphen_end.seq).

The borrowed outline is positioned onto the glyph it replaces (single glyphs are
centred; composed multi-cell glyphs are aligned to the original's left ink edge) and
its advance width is preserved, so monospacing is untouched.

Lilex is licensed under the SIL Open Font License 1.1 (see font-data/Lilex-OFL.txt).
Distributed builds must retain that notice.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

CELL = 600  # Recursive/Lilex monospace advance width


# --------------------------------------------------------------------------------------
# Geometry helpers


def _flatten_segments(glyph, glyph_set, transform=None, steps: int = 40):
    """Flatten a glyph's contours into straight line segments (quadratics sampled)."""
    rec = RecordingPen()
    pen = TransformPen(rec, transform) if transform is not None else rec
    glyph.draw(pen, glyph_set)
    segments = []
    cur = None
    start = None

    def add_quad(p0, ctrl, p1):
        prev = p0
        for j in range(1, steps + 1):
            t = j / steps
            mt = 1 - t
            x = mt * mt * p0[0] + 2 * mt * t * ctrl[0] + t * t * p1[0]
            y = mt * mt * p0[1] + 2 * mt * t * ctrl[1] + t * t * p1[1]
            segments.append((prev, (x, y)))
            prev = (x, y)
        return p1

    for op, args in rec.value:
        if op == "moveTo":
            cur = args[0]
            start = cur
        elif op == "lineTo":
            segments.append((cur, args[0]))
            cur = args[0]
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:  # fully off-curve closed contour: ignore for measuring
                continue
            on_end = pts[-1]
            offs = pts[:-1]
            p0 = cur
            for i, off in enumerate(offs):
                if i == len(offs) - 1:
                    p1 = on_end
                else:
                    nxt = offs[i + 1]
                    p1 = ((off[0] + nxt[0]) / 2.0, (off[1] + nxt[1]) / 2.0)
                p0 = add_quad(p0, off, p1)
            cur = on_end
        elif op in ("closePath", "endPath"):
            if cur and start and cur != start:
                segments.append((cur, start))
            cur = start
    return segments


def _deslant_transform(slant: float):
    """Affine that removes a Recursive oblique lean (slnt is negative for a lean)."""
    if not slant:
        return None
    return (1.0, 0.0, math.tan(math.radians(slant)), 1.0, 0.0, 0.0)


def _measure_stroke(glyph, glyph_set, axis: str, slant: float = 0.0):
    """Measure the stroke thickness of a glyph.

    axis="horizontal": width of the contour at mid-height (for vertical strokes such
        as parentheses).
    axis="vertical": thickness of a horizontal bar, taken as the median vertical
        extent across the central span (for dashes / arrow shafts).

    The glyph is de-slanted first so italics measure the same as their upright peers.
    """
    if glyph.numberOfContours == 0:
        return None
    segments = _flatten_segments(glyph, glyph_set, transform=_deslant_transform(slant))
    if not segments:
        return None
    xs_all = [p[0] for seg in segments for p in seg]
    ys_all = [p[1] for seg in segments for p in seg]
    x_min, x_max = min(xs_all), max(xs_all)
    y_min, y_max = min(ys_all), max(ys_all)

    if axis == "horizontal":
        y = y_min + (y_max - y_min) * 0.5
        xs = []
        for (x0, y0), (x1, y1) in segments:
            if y0 != y1 and (y0 - y) * (y1 - y) <= 0:
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        return (max(xs) - min(xs)) if len(xs) >= 2 else None

    # axis == "vertical": sample several vertical scan lines, take the median thickness
    width = x_max - x_min
    thicknesses = []
    k = 0.20
    while k <= 0.80:
        x = x_min + width * k
        ys = []
        for (x0, y0), (x1, y1) in segments:
            if x0 != x1 and (x0 - x) * (x1 - x) <= 0:
                t = (x - x0) / (x1 - x0)
                ys.append(y0 + t * (y1 - y0))
        if len(ys) >= 2:
            thicknesses.append(max(ys) - min(ys))
        k += 0.05
    if not thicknesses:
        return None
    thicknesses.sort()
    return thicknesses[len(thicknesses) // 2]


def _bounds_under(parts, glyph_set, source_glyf, affines):
    """Combined bounds of several source glyphs, each drawn under its own affine."""
    pen = BoundsPen(glyph_set)
    for part, affine in zip(parts, affines):
        source_glyf[part].draw(TransformPen(pen, affine), glyph_set)
    return pen.bounds


# --------------------------------------------------------------------------------------
# Source weight calibration (cached per source font + probe + axis)

_STROKE_TABLE_CACHE: dict[tuple, list[tuple[int, float]]] = {}


def _source_stroke_table(source_path: str, probe_glyph: str, axis: str, step: int = 25):
    """Build (and cache) a [(wght, stroke), ...] table for the source probe glyph."""
    key = (source_path, probe_glyph, axis, step)
    if key in _STROKE_TABLE_CACHE:
        return _STROKE_TABLE_CACHE[key]

    axis_rec = {a.axisTag: a for a in TTFont(source_path)["fvar"].axes}["wght"]
    lo, hi = int(axis_rec.minValue), int(axis_rec.maxValue)

    table = []
    w = lo
    while w <= hi:
        inst = instancer.instantiateVariableFont(
            TTFont(source_path), {"wght": w}, inplace=False
        )
        s = _measure_stroke(inst["glyf"][probe_glyph], inst.getGlyphSet(), axis)
        if s is not None:
            table.append((w, s))
        w += step
    _STROKE_TABLE_CACHE[key] = table
    return table


def _match_source_weight(
    source_path: str, probe_glyph: str, axis: str, target_stroke: float
) -> tuple[int, float]:
    """Find the source `wght` whose probe-glyph stroke best matches target_stroke.

    Returns (wght, stroke_at_that_wght). Because the source axis is bounded, the
    returned stroke may still be lighter than target_stroke; the caller decides
    whether the residual mismatch is acceptable.
    """
    table = _source_stroke_table(source_path, probe_glyph, axis)
    return min(table, key=lambda ws: abs(ws[1] - target_stroke))


# --------------------------------------------------------------------------------------
# Public API


def borrow_glyphs(
    target_font: TTFont,
    *,
    source_path: str,
    glyph_map: Mapping[str, object],
    slant: float = 0.0,
    probe: Mapping[str, str] | None = None,
    max_stroke_mismatch: float | None = 0.12,
    align: str | None = None,
) -> dict:
    """Replace glyphs in `target_font` with outlines borrowed from `source_path`.

    Parameters
    ----------
    target_font:
        An open TTFont (a generated Recursive instance), modified in place.
    source_path:
        Path to the source variable font (e.g. font-data/Lilex[wght].ttf).
    glyph_map:
        Mapping of target_glyph_name -> source spec. The source spec is either:
          * a single source glyph name (str): grafted and centred onto the target; or
          * a list of source glyph names: laid out left-to-right across consecutive
            cells and merged into one outline, aligned to the target's left ink edge.
            Used to reproduce Recursive's backward-drawing ligature glyphs.
    slant:
        Recursive `slnt` value of this instance (-15 for italics, 0 upright). The
        borrowed outline is sheared by the equivalent angle so it leans correctly.
    probe:
        {"target": str, "source": str, "axis": "horizontal"|"vertical"} describing how
        to weight-match. Defaults to measuring the first mapped glyph horizontally.
    max_stroke_mismatch:
        If set, the whole spec is skipped (target keeps its native glyphs) when the
        closest achievable source stroke differs from the target stroke by more than
        this fraction. This is what makes heavy weights fall back to Recursive's own
        glyphs when Lilex can't be drawn heavy enough. None disables the check.

    Returns a small dict describing what was done (for logging).
    """
    items = list(glyph_map.items())
    if not items:
        return {"replaced": [], "skipped": [], "matched_wght": None, "reason": "empty map"}

    target_glyf = target_font["glyf"]
    target_glyph_set = target_font.getGlyphSet()
    target_hmtx = target_font["hmtx"]
    target_names = [t for t, _ in items]

    # --- 1. weight matching -------------------------------------------------------
    if probe:
        probe_target = probe["target"]
        probe_source = probe["source"]
        probe_axis = probe.get("axis", "horizontal")
    else:
        probe_target = items[0][0]
        spec = items[0][1]
        probe_source = spec if isinstance(spec, str) else spec[0]
        probe_axis = "horizontal"

    target_stroke = _measure_stroke(
        target_glyf[probe_target], target_glyph_set, probe_axis, slant
    )

    if target_stroke is None:
        matched_wght = int(
            {a.axisTag: a for a in TTFont(source_path)["fvar"].axes}["wght"].defaultValue
        )
        matched_stroke = None
        mismatch = None
    else:
        matched_wght, matched_stroke = _match_source_weight(
            source_path, probe_source, probe_axis, target_stroke
        )
        mismatch = abs(matched_stroke - target_stroke) / target_stroke
        if max_stroke_mismatch is not None and mismatch > max_stroke_mismatch:
            return {
                "replaced": [],
                "skipped": target_names,
                "matched_wght": matched_wght,
                "target_stroke": target_stroke,
                "source_stroke": matched_stroke,
                "mismatch": mismatch,
                "reason": "stroke mismatch over threshold",
            }

    source_font = instancer.instantiateVariableFont(
        TTFont(source_path), {"wght": matched_wght}, inplace=False
    )
    source_glyf = source_font["glyf"]
    source_glyph_set = source_font.getGlyphSet()

    # Recursive slnt is negative for a forward (rightward) lean.
    shear = math.tan(math.radians(-slant))

    # --- 2. graft each glyph ------------------------------------------------------
    replaced = []
    for target_name, spec in items:
        if target_name not in target_glyf:
            raise KeyError(f"target glyph '{target_name}' not found in target font")
        parts = [spec] if isinstance(spec, str) else list(spec)
        for p in parts:
            if p not in source_glyf:
                raise KeyError(f"source glyph '{p}' not found in {source_path}")

        n = len(parts)
        composed = n > 1

        # Per-part affine before final alignment. The target glyph's origin sits at
        # the *last* cell, so part i (0-based) is drawn dx = (i - (n-1)) * CELL away.
        # Shear is applied before this horizontal offset.
        part_affines = []
        for i in range(n):
            dx = (i - (n - 1)) * CELL
            part_affines.append((1.0, 0.0, shear, 1.0, dx, 0.0))

        src_bounds = _bounds_under(parts, source_glyph_set, source_glyf, part_affines)

        tgt_glyph = target_glyf[target_name]
        tgt_glyph.recalcBounds(target_glyf)

        if src_bounds is not None:
            s_x0, s_y0, s_x1, s_y1 = src_bounds
            # Alignment mode: "preserve" keeps the source's own coordinates (for
            # backward-drawing single glyphs like |> that already use the same
            # multi-cell convention); "leftedge" (default for composed) matches the
            # original glyph's left ink edge; "center" (default for single) centres.
            mode = align or ("leftedge" if composed else "center")
            if mode == "preserve":
                dx = dy = 0.0
            else:
                s_cy = (s_y0 + s_y1) / 2.0
                tgt_cy = (tgt_glyph.yMin + tgt_glyph.yMax) / 2.0
                dy = tgt_cy - s_cy
                if mode == "leftedge":
                    # Align the merged outline's left ink edge to the original glyph's,
                    # reproducing how Recursive's arrow covers its preceding cell(s).
                    dx = tgt_glyph.xMin - s_x0
                else:  # center
                    s_cx = (s_x0 + s_x1) / 2.0
                    tgt_cx = (tgt_glyph.xMin + tgt_glyph.xMax) / 2.0
                    dx = tgt_cx - s_cx
        else:
            dx = dy = 0.0

        pen = TTGlyphPen(source_glyph_set)
        for part, (a, b, c, d, e, f) in zip(parts, part_affines):
            source_glyf[part].draw(
                TransformPen(pen, (a, b, c, d, e + dx, f + dy)), source_glyph_set
            )
        new_glyph = pen.glyph()
        new_glyph.recalcBounds(target_glyf)

        target_glyf[target_name] = new_glyph
        old_advance = target_hmtx.metrics[target_name][0]
        new_lsb = new_glyph.xMin if new_glyph.numberOfContours else 0
        target_hmtx.metrics[target_name] = (old_advance, new_lsb)
        replaced.append(target_name)

    return {
        "replaced": replaced,
        "skipped": [],
        "matched_wght": matched_wght,
        "target_stroke": target_stroke,
        "source_stroke": matched_stroke,
        "mismatch": mismatch,
        "reason": "ok",
    }
