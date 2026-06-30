"""Stroke-weight calibration tool for Moxy's hand-drawn glyphs (@ $ & 2 4 5 7).

Two jobs:

  measure   Rasterize glyphs from a BUILT font and report each one's dominant
            perpendicular stroke thickness, so you can check the drawn glyphs
            sit at the same weight as Recursive's own (the reference) glyphs.

  calibrate Recompute the ``_CALIB`` blend coefficients in scripts/glyph_tweaks.py
            from the current design masters, targeting the reference stems
            (thin=50 @wght300, light=81 @wght375, heavy=140). Run this after
            editing any _X_LIGHT / _X_HEAVY master so the calibration follows.

The metric is orientation-robust: rasterize the outline (even-odd scanline fill),
then for every ink pixel take the minimum run length across horizontal / vertical
/ both diagonals (diagonals scaled by sqrt2). That is the local perpendicular
stroke thickness regardless of stroke angle. We report the median over the glyph.

Usage:
    venv/bin/python scripts/dev/calibrate_stems.py measure  <font.ttf> [axes]
    venv/bin/python scripts/dev/calibrate_stems.py calibrate

      [axes] = comma list for a variable font, e.g. CASL=0,wght=375,slnt=0,CRSV=0.5
"""
from __future__ import annotations

import importlib.util
import os
import sys
from collections import Counter

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.varLib.instancer import instantiateVariableFont

SQRT2 = 2 ** 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
TWEAKS = os.path.join(HERE, "..", "glyph_tweaks.py")

REF_GLYPHS = ["zero", "one", "three", "eight", "l", "n", "S"]
CUSTOM_GLYPHS = ["two", "four", "five", "seven", "at", "ampersand", "dollar"]

# calibration targets (perpendicular stem, 600-cell raster units)
TARGETS = {"thin": 50, "light": 81, "heavy": 140}


# ----------------------------------------------------------------------------- raster

def flatten(glyphset, name, steps=12):
    pen = DecomposingRecordingPen(glyphset)
    glyphset[name].draw(pen)
    contours, cur, last = [], [], None

    def quad(p0, p1, p2):
        out = []
        for i in range(1, steps + 1):
            t = i / steps; mt = 1 - t
            out.append((mt*mt*p0[0] + 2*mt*t*p1[0] + t*t*p2[0],
                        mt*mt*p0[1] + 2*mt*t*p1[1] + t*t*p2[1]))
        return out

    def cubic(p0, p1, p2, p3):
        out = []
        for i in range(1, steps + 1):
            t = i / steps; mt = 1 - t
            out.append((mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0],
                        mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]))
        return out

    for op, args in pen.value:
        if op == "moveTo":
            if cur:
                contours.append(cur)
            cur = [args[0]]; last = args[0]
        elif op == "lineTo":
            cur.append(args[0]); last = args[0]
        elif op == "qCurveTo":
            pts = list(args)
            end = pts[-1] if pts[-1] is not None else cur[0]
            offs = pts[:-1] if pts[-1] is not None else pts
            prev = last
            for i, off in enumerate(offs):
                mid = end if i == len(offs) - 1 else ((off[0]+offs[i+1][0])/2, (off[1]+offs[i+1][1])/2)
                cur.extend(quad(prev, off, mid)); prev = mid
            last = end
        elif op == "curveTo":
            cur.extend(cubic(last, args[0], args[1], args[2])); last = args[-1]
        elif op == "closePath":
            if cur:
                contours.append(cur)
            cur = []
    if cur:
        contours.append(cur)
    return contours


def raster(contours):
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    if not xs:
        return None
    minx, maxx, miny, maxy = int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))
    W, H = maxx - minx + 2, maxy - miny + 2
    grid = [bytearray(W) for _ in range(H)]
    edges = [(a, b) for c in contours for a, b in zip(c, c[1:] + c[:1]) if a[1] != b[1]]
    for row in range(H):
        y = miny + row + 0.5
        xi = sorted(a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0])
                    for a, b in edges if (a[1] <= y < b[1]) or (b[1] <= y < a[1]))
        for k in range(0, len(xi) - 1, 2):
            for col in range(max(0, int(round(xi[k] - minx))), min(W, int(round(xi[k+1] - minx)))):
                grid[row][col] = 1
    return grid, W, H


def thickness_median(grid, W, H):
    INF = 10 ** 9
    h = [[INF]*W for _ in range(H)]; v = [[INF]*W for _ in range(H)]
    d1 = [[INF]*W for _ in range(H)]; d2 = [[INF]*W for _ in range(H)]

    def fill(line, target, scale):
        i, n = 0, len(line)
        while i < n:
            r, c = line[i]
            if grid[r][c]:
                j = i
                while j < n and grid[line[j][0]][line[j][1]]:
                    j += 1
                length = (j - i) * scale
                for k in range(i, j):
                    rr, cc = line[k]
                    if length < target[rr][cc]:
                        target[rr][cc] = length
                i = j
            else:
                i += 1

    for r in range(H):
        fill([(r, c) for c in range(W)], h, 1.0)
    for c in range(W):
        fill([(r, c) for r in range(H)], v, 1.0)
    for start in range(-(H - 1), W):
        line, r, c = [], (0 if start >= 0 else -start), (start if start >= 0 else 0)
        while r < H and c < W:
            line.append((r, c)); r += 1; c += 1
        fill(line, d1, SQRT2)
    for start in range(0, W + H - 1):
        line, r, c = [], 0, start
        while r < H and c >= 0:
            if c < W:
                line.append((r, c))
            r += 1; c -= 1
        fill(line, d2, SQRT2)

    vals = [round(min(h[r][c], v[r][c], d1[r][c], d2[r][c]))
            for r in range(H) for c in range(W) if grid[r][c]]
    vals = [x for x in vals if x >= 4] or vals
    return sorted(vals)[len(vals) // 2] if vals else None


def stem_of_contours(contours, scale=1.0):
    if scale != 1.0:
        contours = [[(x*scale, y*scale) for x, y in c] for c in contours]
    r = raster(contours)
    if not r:
        return None
    return thickness_median(*r) / scale


def stem_of_glyph(glyphset, name):
    return stem_of_contours(flatten(glyphset, name))


# ----------------------------------------------------------------------------- commands

def cmd_measure(path, axes):
    f = TTFont(path)
    if "fvar" in f and axes:
        loc = dict(kv.split("=") for kv in axes.split(","))
        instantiateVariableFont(f, {k: float(v) for k, v in loc.items()}, inplace=True)
    gs = f.getGlyphSet()
    print(f"== {os.path.basename(path)}  {axes or ''}")
    refs = []
    print("  -- reference (untouched Recursive) --")
    for n in REF_GLYPHS:
        if n in gs:
            s = stem_of_glyph(gs, n); refs.append(s)
            print(f"    {n:10s} {s}")
    if refs:
        refs.sort()
        print(f"    >> reference median ~= {refs[len(refs)//2]}")
    print("  -- custom (Moxy-drawn) --")
    for n in CUSTOM_GLYPHS:
        if n in gs:
            print(f"    {n:10s} {stem_of_glyph(gs, n)}")


def _blend(a, b, t):
    return [(a[i][0] + (b[i][0]-a[i][0])*t, a[i][1] + (b[i][1]-a[i][1])*t) for i in range(len(a))]


def _find_coeff(L, H, ep, target):
    ts = [-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 1.0, 1.4, 1.9, 2.4]
    pts = [(t, stem_of_contours(_split(_blend(L, H, t), ep))) for t in ts]
    for i in range(len(pts) - 1):
        (t0, s0), (t1, s1) = pts[i], pts[i + 1]
        if s0 is not None and s1 is not None and s0 <= target <= s1 and s1 != s0:
            return t0 + (t1 - t0) * (target - s0) / (s1 - s0)
    (t0, s0), (t1, s1) = (pts[0], pts[1]) if target < (pts[0][1] or 0) else (pts[-2], pts[-1])
    return t0 + (t1 - t0) * (target - s0) / (s1 - s0)


def _split(coords, end_pts):
    out, s = [], 0
    for e in end_pts:
        out.append(coords[s:e + 1]); s = e + 1
    return out


def cmd_calibrate():
    spec = importlib.util.spec_from_file_location("gt", TWEAKS)
    gt = importlib.util.module_from_spec(spec); spec.loader.exec_module(gt)
    G = {
        "two": (gt._TWO_LIGHT, gt._TWO_HEAVY, gt._TWO_END_PTS),
        "four": (gt._FOUR_LIGHT, gt._FOUR_HEAVY, gt._FOUR_END_PTS),
        "five": (gt._FIVE_LIGHT, gt._FIVE_HEAVY, gt._FIVE_END_PTS),
        "seven": (gt._SEVEN_LIGHT, gt._SEVEN_HEAVY, gt._SEVEN_END_PTS),
        "ampersand": (gt._AMP_LIGHT, gt._AMP_HEAVY, gt._AMP_END_PTS),
        "at": (gt._AT_LIGHT, gt._AT_HEAVY, gt._AT_END_PTS),
        "dollar": (gt._DOLLAR_LIGHT, gt._DOLLAR_HEAVY, gt._DOLLAR_END_PTS),
    }
    print("Paste into _CALIB in scripts/glyph_tweaks.py:")
    print("_CALIB = {")
    for name, (L, H, ep) in G.items():
        if name == "dollar":
            L = gt._widen_dollar_bar(L, 274.8, 332.5, 84.0)
            H = gt._widen_dollar_bar(H, 269.9, 338.3, 150.0)
        ct = _find_coeff(L, H, ep, TARGETS["thin"])
        cl = _find_coeff(L, H, ep, TARGETS["light"])
        ch = 1.0 if name == "at" else _find_coeff(L, H, ep, TARGETS["heavy"])
        print(f'    "{name}":{" "*(12-len(name))}({ct:+.2f}, {cl:+.2f}, {ch:+.2f}),')
    print("}")
    print("\n(@ heavy is capped at 1.0 — its spiral self-intersects past its heavy master.)")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "measure":
        cmd_measure(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif len(sys.argv) >= 2 and sys.argv[1] == "calibrate":
        cmd_calibrate()
    else:
        print(__doc__)
