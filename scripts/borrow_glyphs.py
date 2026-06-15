"""
Borrow glyph outlines from another variable font and graft them into a generated
Recursive code-font instance.

This is used to bring in glyphs that simply do not exist anywhere inside the
Recursive variable font (so they cannot be enabled as a frozen OpenType feature
like the ss01-ss12 stylistic sets). The canonical example is Lilex's "curvier
parentheses" (its cv13 character variant: parenleft.cv13 / parenright.cv13).

Both Recursive and Lilex are UPM 1000, TrueType (`glyf`) outlines, with a 600-unit
monospace cell, which makes a near drop-in transplant possible. The two remaining
jobs this module does are:

  1. Weight matching. Lilex's parens are drawn much thinner than Recursive's at
     comparable weights, so we instantiate the Lilex variable font at whatever
     `wght` makes its paren stroke best match the stroke of the Recursive paren we
     are replacing (clamped to the Lilex axis maximum).

  2. Slant matching. Recursive's italics are an oblique (slnt axis), not a true
     cursive. We shear the borrowed (upright) Lilex glyph by the same angle so it
     leans with the rest of the instance.

The borrowed outline is then re-centred (horizontally + vertically) onto the
optical position of the glyph it replaces and its advance width is preserved, so
monospacing is untouched.

Lilex is licensed under the SIL Open Font License 1.1 (see
font-data/Lilex-OFL.txt). Distributed builds must retain that notice.
"""

from __future__ import annotations

import math
from typing import Iterable

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen


# --------------------------------------------------------------------------------------
# Geometry helpers


def _flatten_segments(glyph, glyph_set, steps: int = 40):
    """Flatten a glyph's contours into straight line segments (quadratics sampled)."""
    rec = RecordingPen()
    glyph.draw(rec, glyph_set)
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


def _stroke_thickness(font: TTFont, glyph_name: str, frac: float = 0.5):
    """Horizontal stroke thickness of a paren-like glyph at a fraction of its height.

    Measured as (max - min) x of all contour crossings of a horizontal scan line, so
    coincident vertices at the scan height do not corrupt the result.
    """
    glyf = font["glyf"]
    glyph_set = font.getGlyphSet()
    glyph = glyf[glyph_name]
    if glyph.numberOfContours == 0:
        return None
    y = glyph.yMin + (glyph.yMax - glyph.yMin) * frac
    xs = []
    for (x0, y0), (x1, y1) in _flatten_segments(glyph, glyph_set):
        if y0 != y1 and (y0 - y) * (y1 - y) <= 0:
            t = (y - y0) / (y1 - y0)
            xs.append(x0 + t * (x1 - x0))
    if len(xs) < 2:
        return None
    return max(xs) - min(xs)


def _glyph_bounds(glyph, glyph_set, transform=None):
    """Return (xMin, yMin, xMax, yMax) of a glyph, optionally under an affine."""
    pen = BoundsPen(glyph_set)
    if transform is not None:
        glyph.draw(TransformPen(pen, transform), glyph_set)
    else:
        glyph.draw(pen, glyph_set)
    return pen.bounds  # may be None for empty glyphs


# --------------------------------------------------------------------------------------
# Source weight calibration (cached per source font path)

_STROKE_TABLE_CACHE: dict[tuple, list[tuple[int, float]]] = {}


def _source_stroke_table(source_path: str, probe_glyph: str, step: int = 25):
    """Build (and cache) a [(wght, stroke_thickness), ...] table for the source font."""
    key = (source_path, probe_glyph, step)
    if key in _STROKE_TABLE_CACHE:
        return _STROKE_TABLE_CACHE[key]

    base = TTFont(source_path)
    axis = {a.axisTag: a for a in base["fvar"].axes}["wght"]
    lo, hi = int(axis.minValue), int(axis.maxValue)

    table = []
    w = lo
    while w <= hi:
        inst = instancer.instantiateVariableFont(
            TTFont(source_path), {"wght": w}, inplace=False
        )
        s = _stroke_thickness(inst, probe_glyph)
        if s is not None:
            table.append((w, s))
        w += step
    _STROKE_TABLE_CACHE[key] = table
    return table


def _match_source_weight(
    source_path: str, probe_glyph: str, target_stroke: float
) -> tuple[int, float]:
    """Find the source `wght` whose probe-glyph stroke best matches target_stroke.

    Returns (wght, stroke_at_that_wght). Because the source axis is bounded, the
    returned stroke may still be lighter (or heavier) than target_stroke; the caller
    decides whether the residual mismatch is acceptable.
    """
    table = _source_stroke_table(source_path, probe_glyph)
    best_w, best_stroke = min(table, key=lambda ws: abs(ws[1] - target_stroke))
    return best_w, best_stroke


# --------------------------------------------------------------------------------------
# Public API


def borrow_glyphs(
    target_font: TTFont,
    *,
    source_path: str,
    glyph_map: Iterable[tuple[str, str]],
    slant: float = 0.0,
    probe_pair: tuple[str, str] | None = None,
    max_stroke_mismatch: float | None = 0.12,
) -> dict:
    """Replace glyphs in `target_font` with outlines borrowed from `source_path`.

    Parameters
    ----------
    target_font:
        An open TTFont (a generated Recursive instance) modified in place.
    source_path:
        Path to the source variable font (e.g. font-data/Lilex[wght].ttf).
    glyph_map:
        Iterable of (target_glyph_name, source_glyph_name) pairs. The source glyph's
        outline is grafted onto the target glyph.
    slant:
        Recursive `slnt` value of this instance (e.g. -15 for italics, 0 for upright).
        The borrowed outline is sheared by the equivalent angle so it leans correctly.
    probe_pair:
        (target_glyph, source_glyph) used to calibrate weight matching. Defaults to
        the first pair in glyph_map.
    max_stroke_mismatch:
        If set, the swap is skipped entirely (the target keeps its native glyphs)
        when the closest achievable source stroke differs from the target stroke by
        more than this fraction. This is what makes heavy weights fall back to
        Recursive's own parens when Lilex simply can't be drawn heavy enough. Set to
        None to always swap regardless of weight match.

    Returns a small dict describing what was done (handy for logging).
    """
    glyph_map = list(glyph_map)
    if not glyph_map:
        return {"replaced": [], "skipped": [], "matched_wght": None, "reason": "empty map"}

    target_glyf = target_font["glyf"]
    target_glyph_set = target_font.getGlyphSet()
    target_hmtx = target_font["hmtx"]

    # --- 1. choose the source weight that matches the target paren stroke ---
    probe_target, probe_source = probe_pair or glyph_map[0]
    target_stroke = _stroke_thickness(target_font, probe_target)
    target_names = [t for t, _ in glyph_map]

    if target_stroke is None:
        # Fall back to the source axis default if we cannot measure.
        matched_wght = int(
            {a.axisTag: a for a in TTFont(source_path)["fvar"].axes}["wght"].defaultValue
        )
        matched_stroke = None
        mismatch = None
    else:
        matched_wght, matched_stroke = _match_source_weight(
            source_path, probe_source, target_stroke
        )
        mismatch = abs(matched_stroke - target_stroke) / target_stroke

        # If even the best source weight is too far from the target stroke, keep the
        # target's native glyphs rather than grafting in a mismatched outline.
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

    # shear: Recursive slnt is negative for a forward (rightward) lean.
    shear = math.tan(math.radians(-slant))

    replaced = []
    for target_name, source_name in glyph_map:
        if source_name not in source_glyf:
            raise KeyError(f"source glyph '{source_name}' not found in {source_path}")
        if target_name not in target_glyf:
            raise KeyError(f"target glyph '{target_name}' not found in target font")

        src_glyph = source_glyf[source_name]

        # Bounds of the *sheared* source outline (linear part only, no translation yet).
        linear = (1.0, 0.0, shear, 1.0, 0.0, 0.0)
        s_bounds = _glyph_bounds(src_glyph, source_glyph_set, linear)

        # Optical target: centre of the glyph we are replacing.
        tgt_glyph = target_glyf[target_name]
        tgt_glyph.recalcBounds(target_glyf)
        tgt_cx = (tgt_glyph.xMin + tgt_glyph.xMax) / 2.0
        tgt_cy = (tgt_glyph.yMin + tgt_glyph.yMax) / 2.0

        if s_bounds is not None:
            s_cx = (s_bounds[0] + s_bounds[2]) / 2.0
            s_cy = (s_bounds[1] + s_bounds[3]) / 2.0
            dx = tgt_cx - s_cx
            dy = tgt_cy - s_cy
        else:
            dx = dy = 0.0

        # Combined affine: shear (linear) then translate. Because the translation is
        # applied after the linear part, it folds straight into the matrix offsets.
        affine = (1.0, 0.0, shear, 1.0, dx, dy)

        pen = TTGlyphPen(target_glyph_set)
        src_glyph.draw(TransformPen(pen, affine), source_glyph_set)
        new_glyph = pen.glyph()
        new_glyph.recalcBounds(target_glyf)

        target_glyf[target_name] = new_glyph

        # Preserve the target's advance width (monospacing); reset lsb to the new xMin.
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
