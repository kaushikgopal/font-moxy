"""Glyph tweaks for Moxy.

Moxy adjusts a few of Recursive's glyphs toward shapes Kaush prefers. Two
strategies:

* **Reshape** — derive the new shape geometrically from Recursive's own outline
  (no external font, no hand-authored bezier). OFL-clean and shippable.
* **Graft** — replace the glyph with one borrowed from another font. The outline
  is curve-converted (cu2qu) if needed, scaled into Moxy's 1000-UPM / 600 cell,
  and given weight + slant variation.

The following grafts are baked in (called unconditionally from the builds, so
they're part of Moxy's design, not a configurable option): ``%`` (connected
diagonal), ``/`` and ``\\`` (clean straight slashes), ``✓`` (fuller check mark),
``•`` (fuller bullet), and ``@`` ``&`` ``$`` (reference at-sign, ampersand, and
dollar). The variable-font build rebuilds gvar from the reference masters; the
static build interpolates those same masters by the instance's weight and shears
for italic. ``@`` ``&`` ``$`` use a single-master graft (slant-only variation)
because the reference font's weight masters aren't point-compatible for those
glyphs.
"""

from __future__ import annotations

import itertools
import math
import os

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.varLib import instancer
from fontTools.varLib.models import VariationModel, supportScalar

AXIS_ORDER = ["MONO", "CASL", "wght", "slnt", "CRSV"]

# Recursive wght axis spans 300..1000; normalise a user weight into [0, 1].
_WGHT_MIN, _WGHT_MAX = 300.0, 1000.0


def _wght_t(wght: float) -> float:
    return max(0.0, min(1.0, (wght - _WGHT_MIN) / (_WGHT_MAX - _WGHT_MIN)))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# --------------------------------------------------------------------------------------
# Geometry helpers


def _contours(end_pts):
    out, start = [], 0
    for end in end_pts:
        out.append((start, end + 1))
        start = end + 1
    return out


def _bbox(coords, sl):
    pts = coords[sl[0]:sl[1]]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _inside(a, b):
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


# --------------------------------------------------------------------------------------
# percent: two stubby diagonal bars -> one continuous overshooting slash; dots
# shrunk and pushed into the corners.


def percent_params(wght: float) -> dict:
    """Weight-aware reshape parameters for ``%`` (see module docstring)."""
    t = _wght_t(wght)
    return dict(
        dot_scale=_lerp(0.85, 0.82, t),    # shrink dots about their centres
        dot_push=_lerp(50.0, 75.0, t),     # push dots into corners (font units)
        extend=_lerp(62.0, 40.0, t),       # slash overshoot past the dots
        thick_scale=_lerp(1.0, 0.90, t),   # thin the slash a touch when heavy
    )


def reshape_percent_outline(coords, end_pts, flags, *, dot_scale, dot_push,
                            extend, thick_scale):
    """Pure geometry: reshape a ``percent`` outline.

    Input is Recursive's 6-contour ``%`` (two dots = outer ring + inner counter,
    plus two diagonal bars). Output is 5 contours (the two dots unchanged in
    topology, plus ONE straight slash parallelogram). The transform is derived
    entirely from the glyph's own geometry, so it works at any weight/slant.

    Returns ``(new_coords, new_end_pts, new_flags)``.
    """
    slices = _contours(end_pts)
    boxes = [_bbox(coords, s) for s in slices]

    counters, outers, pairs = set(), set(), {}
    for i in range(len(slices)):
        for j in range(len(slices)):
            if i != j and _inside(boxes[i], boxes[j]):
                counters.add(i)
                outers.add(j)
                pairs.setdefault(j, []).append(i)
                break
    bars = [i for i in range(len(slices)) if i not in counters and i not in outers]
    if len(bars) != 2 or len(outers) != 2:
        raise ValueError(
            f"unexpected percent structure: {len(outers)} dots, {len(bars)} bars"
        )

    def centroid(i):
        pts = coords[slices[i][0]:slices[i][1]]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    ca, cb = centroid(bars[0]), centroid(bars[1])
    clo, chi = (ca, cb) if ca[1] < cb[1] else (cb, ca)
    vx, vy = chi[0] - clo[0], chi[1] - clo[1]
    length = math.hypot(vx, vy) or 1.0
    ux, uy = vx / length, vy / length     # along the slash (lower-left -> upper-right)
    px, py = -uy, ux                       # perpendicular (up-left)

    new_coords, new_flags, new_end_pts = [], [], []

    # dots: shrink about their own centre, push along +/- perpendicular into corners
    dot_centers = {o: ((boxes[o][0] + boxes[o][2]) / 2, (boxes[o][1] + boxes[o][3]) / 2)
                   for o in outers}
    top_y = max(c[1] for c in dot_centers.values())
    for o in sorted(outers):
        cx, cy = dot_centers[o]
        sign = 1.0 if cy == top_y else -1.0    # top dot pushes up-left, bottom down-right
        dx, dy = px * dot_push * sign, py * dot_push * sign
        for ci in [o] + pairs[o]:
            a, b = slices[ci]
            for k in range(a, b):
                x, y = coords[k]
                new_coords.append((cx + (x - cx) * dot_scale + dx,
                                   cy + (y - cy) * dot_scale + dy))
                new_flags.append(flags[k])
            new_end_pts.append(len(new_coords) - 1)

    # slash: one straight parallelogram spanning both bars' full extent + overshoot.
    on_pts, all_t = [], []
    for bi in bars:
        a, b = slices[bi]
        for k in range(a, b):
            x, y = coords[k]
            all_t.append(x * ux + y * uy)
            if flags[k] & 1:                    # on-curve corner
                on_pts.append((x * ux + y * uy, x * px + y * py))
    t_min, t_max = min(all_t) - extend, max(all_t) + extend
    s_lo = min(p[1] for p in on_pts)
    s_hi = max(p[1] for p in on_pts)
    s_mid = (s_lo + s_hi) / 2
    s_lo = s_mid + (s_lo - s_mid) * thick_scale
    s_hi = s_mid + (s_hi - s_mid) * thick_scale
    for t, s in [(t_min, s_lo), (t_min, s_hi), (t_max, s_hi), (t_max, s_lo)]:
        new_coords.append((t * ux + s * px, t * uy + s * py))
        new_flags.append(1)
    new_end_pts.append(len(new_coords) - 1)

    return new_coords, new_end_pts, new_flags


# --------------------------------------------------------------------------------------
# Applying a reshape to a glyph: static (one instance) and variable (gvar rebuild).


_CELL = 600  # Moxy is pure monospace: every glyph advances one 600-unit cell.


def _zero_hvar_index(hvar_table):
    """Find an all-zero-delta variation index in HVAR (Recursive has one)."""
    for outer, ivd in enumerate(hvar_table.VarStore.VarData):
        for inner, row in enumerate(ivd.Item):
            if all(d == 0 for d in row):
                return (outer << 16) | inner
    return None


def _write_outline(font, glyph_name, new_coords, new_end_pts, new_flags):
    glyf = font["glyf"]
    g = glyf[glyph_name]
    g.coordinates = g.coordinates.__class__(new_coords)
    g.endPtsOfContours = new_end_pts
    g.flags = g.flags.__class__(bytearray(new_flags))
    g.numberOfContours = len(new_end_pts)
    g.recalcBounds(glyf)
    lsb = g.xMin if g.numberOfContours else 0
    # Pure-mono: pin the advance to the 600 cell. The source glyph's own default
    # may be a proportional width (e.g. JetBrains/Recursive U = 650 in Sans); force
    # 600 and clear any advance VARIATION (gvar phantom deltas are already zeroed;
    # also point HVAR at a zero-delta index) so instancing can't restore the wide
    # advance and break monospacing.
    font["hmtx"].metrics[glyph_name] = (_CELL, lsb)
    if "HVAR" in font:
        awm = font["HVAR"].table.AdvWidthMap
        if awm is not None and hasattr(awm, "mapping"):
            zero_idx = _zero_hvar_index(font["HVAR"].table)
            if zero_idx is not None:
                awm.mapping[glyph_name] = zero_idx


def reshape_percent_instance(font, wght: float = 400.0):
    """Static build: reshape the already-instanced ``percent`` in place."""
    g = font["glyf"]["percent"]
    params = percent_params(wght)
    nc, ne, nf = reshape_percent_outline(
        [tuple(p) for p in g.coordinates],
        list(g.endPtsOfContours),
        list(g.flags),
        **params,
    )
    _write_outline(font, "percent", nc, ne, nf)


def _rebuild_glyph_variable(font, glyph_name, outline_fn, params_fn):
    """Variable build: rebuild a glyph's outline + gvar from reshaped masters.

    ``outline_fn(coords, end_pts, flags, **params) -> (coords, end_pts, flags)``
    must produce identical topology for every master. ``params_fn(loc) -> dict``
    returns the reshape params for a (normalised) master location, allowing
    weight-aware tuning. The master set is derived from the glyph's existing gvar
    regions (so this adapts to whichever axes the glyph actually varies on).
    """
    glyf = font["glyf"]
    gvar = font["gvar"]
    g = glyf[glyph_name]
    base = [tuple(p) for p in g.coordinates]
    npts = len(base)
    tvs = gvar.variations.get(glyph_name, [])
    end_pts = list(g.endPtsOfContours)
    flags = list(g.flags)

    def orig_abs(loc):
        pts = [list(p) for p in base]
        for tv in tvs:
            scalar = supportScalar(loc, tv.axes)
            if not scalar:
                continue
            for i in range(npts):
                d = tv.coordinates[i]
                if d is not None:
                    pts[i][0] += scalar * d[0]
                    pts[i][1] += scalar * d[1]
        return [(x, y) for x, y in pts]

    # Master locations = default (origin) + each tuple's peak (deduped).
    locs = [{}]
    seen = {()}
    for tv in tvs:
        peak = {tag: lo_pk_hi[1] for tag, lo_pk_hi in tv.axes.items()}
        key = tuple(sorted(peak.items()))
        if key not in seen:
            seen.add(key)
            locs.append(peak)

    reshaped = {}
    new_end_pts = new_flags = None
    for loc in locs:
        nc, ne, nf = outline_fn(orig_abs(loc), end_pts, flags, **params_fn(loc))
        reshaped[tuple(sorted(loc.items()))] = nc
        new_end_pts, new_flags = ne, nf

    model = VariationModel(locs, axisOrder=AXIS_ORDER)
    n_new = new_end_pts[-1] + 1
    # getDeltas wants master values in the ORIGINAL `locs` order; returns deltas in
    # model.supports order.
    ordered = [reshaped[tuple(sorted(l.items()))] for l in locs]
    deltas_x = [model.getDeltas([ordered[m][i][0] for m in range(len(ordered))])
                for i in range(n_new)]
    deltas_y = [model.getDeltas([ordered[m][i][1] for m in range(len(ordered))])
                for i in range(n_new)]

    base_idx = model.supports.index({})
    default_coords = [(deltas_x[i][base_idx], deltas_y[i][base_idx]) for i in range(n_new)]
    _write_outline(font, glyph_name, default_coords, new_end_pts, new_flags)

    new_variations = []
    for sidx, support in enumerate(model.supports):
        if support == {}:
            continue
        coords = [(round(deltas_x[i][sidx]), round(deltas_y[i][sidx])) for i in range(n_new)]
        coords += [(0, 0)] * 4  # phantom points (advance is the constant 600 cell)
        new_variations.append(TupleVariation(dict(support), coords))
    gvar.variations[glyph_name] = new_variations


def rebuild_percent_variable(font):
    """Variable build: rebuild ``percent`` with the connected slash + corner dots."""
    _rebuild_glyph_variable(
        font, "percent", reshape_percent_outline,
        lambda loc: percent_params(_WGHT_MIN + loc.get("wght", 0.0) * (_WGHT_MAX - _WGHT_MIN)),
    )


# --------------------------------------------------------------------------------------
# Grafting a glyph from a reference font, with weight + slant variation. The
# outline is converted to quadratic if needed, scaled into Moxy's 1000-UPM / 600
# cell, and sheared to produce the slant master.

_SHEAR_15 = math.tan(math.radians(15))   # Recursive slnt=-15 ≈ 15° forward lean
_MOXY_CAP = 700.0


def _quad_outline(src_font, glyph_name, scale, cell=600, max_err=1.0, xscale=1.0):
    """Convert a source glyph to quadratic, scale it, and centre it in the cell.

    Returns ``(coords, end_pts, flags)``. cu2qu runs at the source's native scale
    (so the point structure matches across weights of the same design), then the
    resulting points are scaled — keeping every master point-compatible. ``xscale``
    widens the glyph horizontally about its centre (>1 = wider + thicker stems), to
    fit a narrow source glyph to Moxy's denser cell.
    """
    pen_glyph = TTGlyphPen(None)
    src_font.getGlyphSet()[glyph_name].draw(Cu2QuPen(pen_glyph, max_err))
    g = pen_glyph.glyph()
    coords = [(p[0] * scale, p[1] * scale) for p in g.coordinates]
    if xscale != 1.0:
        xs = [c[0] for c in coords]
        cx = (min(xs) + max(xs)) / 2
        coords = [(cx + (x - cx) * xscale, y) for x, y in coords]
    flags = list(g.flags)
    end_pts = list(g.endPtsOfContours)
    xs = [c[0] for c in coords]
    dx = (cell - (max(xs) - min(xs))) / 2 - min(xs)   # centre horizontally in the cell
    coords = [(x + dx, y) for x, y in coords]
    return coords, end_pts, flags


def _shear(coords, shear):
    return [(x + shear * y, y) for x, y in coords]


def _install_variable_glyph(font, glyph_name, locs, coords_by_loc, end_pts, flags):
    """Replace a glyph's outline + gvar from externally-built, point-compatible
    masters. ``locs`` are normalised locations; ``coords_by_loc`` is keyed by
    ``tuple(sorted(loc.items()))``."""
    n = end_pts[-1] + 1
    model = VariationModel(locs, axisOrder=AXIS_ORDER)
    ordered = [coords_by_loc[tuple(sorted(l.items()))] for l in locs]
    deltas_x = [model.getDeltas([ordered[m][i][0] for m in range(len(ordered))])
                for i in range(n)]
    deltas_y = [model.getDeltas([ordered[m][i][1] for m in range(len(ordered))])
                for i in range(n)]
    base_idx = model.supports.index({})
    default_coords = [(deltas_x[i][base_idx], deltas_y[i][base_idx]) for i in range(n)]
    _write_outline(font, glyph_name, default_coords, end_pts, flags)

    new_variations = []
    for sidx, support in enumerate(model.supports):
        if support == {}:
            continue
        coords = [(round(deltas_x[i][sidx]), round(deltas_y[i][sidx])) for i in range(n)]
        coords += [(0, 0)] * 4  # phantom points (advance stays the 600 cell)
        new_variations.append(TupleVariation(dict(support), coords))
    font["gvar"].variations[glyph_name] = new_variations


def _source_scale(src_font):
    """Uniform scale to map a source font onto Moxy's cap height (700)."""
    return _MOXY_CAP / src_font["OS/2"].sCapHeight


def _graft_glyph_variable(font, glyph_name, light_src, heavy_src, max_err=1.0, xscale=1.0):
    """Replace ``glyph_name`` with the source's outline, varying on wght (light→
    heavy masters) and slnt (sheared italic). ``light_src`` / ``heavy_src`` are
    open TTFonts of the same family (so they're point-compatible after cu2qu).
    ``xscale`` widens the glyph horizontally (to fit a narrow source to Moxy). The
    grafted glyph does NOT vary on CASL/CRSV (the source look is constant)."""
    scale = _source_scale(light_src)
    light, end_pts, flags = _quad_outline(light_src, glyph_name, scale, max_err=max_err, xscale=xscale)
    heavy, end2, _ = _quad_outline(heavy_src, glyph_name, scale, max_err=max_err, xscale=xscale)
    if end_pts != end2 or len(light) != len(heavy):
        raise ValueError(
            f"graft masters for {glyph_name!r} not point-compatible: "
            f"{len(light)} vs {len(heavy)} pts ({end_pts} vs {end2})"
        )
    locs = [{}, {"wght": 1.0}, {"slnt": -1.0}, {"wght": 1.0, "slnt": -1.0}]
    coords_by_loc = {
        (): light,
        (("wght", 1.0),): heavy,
        (("slnt", -1.0),): _shear(light, _SHEAR_15),
        (("slnt", -1.0), ("wght", 1.0)): _shear(heavy, _SHEAR_15),
    }
    _install_variable_glyph(font, glyph_name, locs, coords_by_loc, end_pts, flags)


_REF_DIR = "/Library/Fonts"
_REF_LIGHT = f"{_REF_DIR}/SF-Mono-Regular.otf"
_REF_HEAVY = f"{_REF_DIR}/SF-Mono-Heavy.otf"
_REF_SEMIBOLD = f"{_REF_DIR}/SF-Mono-Semibold.otf"


def graft_glyphs_jetbrains(font, glyph_names, jb_vf=None):
    """Graft glyphs from JetBrains Mono (wght 400→800, sheared italic).

    JetBrains Mono is OFL — these grafts may ship (with attribution)."""
    jb_vf = jb_vf or os.path.expanduser("~/Library/Fonts/JetBrainsMono[wght]-KG.ttf")
    light = instancer.instantiateVariableFont(TTFont(jb_vf), {"wght": 400}, inplace=False)
    heavy = instancer.instantiateVariableFont(TTFont(jb_vf), {"wght": 800}, inplace=False)
    for name in glyph_names:
        _graft_glyph_variable(font, name, light, heavy)


# --------------------------------------------------------------------------------------
# Baked-in Moxy glyph tweaks. Called unconditionally from the variable-font build.

def graft_percent(font):
    """Replace ``%`` with Moxy's connected diagonal design."""
    _graft_glyph_variable(font, "percent", TTFont(_REF_LIGHT), TTFont(_REF_HEAVY))


def graft_slash(font):
    """Replace ``/`` with Moxy's clean straight slash (no brushy flair)."""
    _graft_glyph_variable(font, "slash", TTFont(_REF_LIGHT), TTFont(_REF_HEAVY))


def graft_backslash(font):
    """Replace ``\\`` with Moxy's clean straight backslash (no brushy flair).

    All composites (backslash.code, .case, and the \\b \\n \\r \\t \\v escape
    ligatures) reference ``backslash`` as a component, so they inherit this
    automatically.
    """
    _graft_glyph_variable(font, "backslash", TTFont(_REF_LIGHT), TTFont(_REF_HEAVY))


def graft_checkmark(font):
    """Replace ``✓`` (U+2713) with Moxy's fuller check mark.

    Recursive's own check is a brushy 42-point stroke; the grafted one is a
    clean 6-point check that sits better next to code. No composites reference
    it.
    """
    _graft_glyph_variable(font, "uni2713", TTFont(_REF_LIGHT), TTFont(_REF_HEAVY))


def graft_bullet(font):
    """Replace ``•`` (U+2022) with Moxy's fuller bullet.

    A fuller circle than Recursive's. The composites ``bullet.case`` and
    ``uni2219`` (bullet operator) reference ``bullet`` as a component, so they
    inherit this automatically.
    """
    _graft_glyph_variable(font, "bullet", TTFont(_REF_LIGHT), TTFont(_REF_HEAVY))


def _graft_glyph_single_master_variable(font, glyph_name, src_font):
    """Replace ``glyph_name`` with a single reference outline — no weight
    variation, only slant. Used when the reference font's weight masters aren't
    point-compatible for this glyph (so ``_graft_glyph_variable`` can't
    interpolate). The glyph stays constant across wght; italic still shears."""
    scale = _source_scale(src_font)
    base, end_pts, flags = _quad_outline(src_font, glyph_name, scale)
    locs = [{}, {"slnt": -1.0}]
    coords_by_loc = {
        (): base,
        (("slnt", -1.0),): _shear(base, _SHEAR_15),
    }
    _install_variable_glyph(font, glyph_name, locs, coords_by_loc, end_pts, flags)


def graft_at(font):
    """Replace ``@`` with Moxy's reference at-sign.

    The composite ``at.case`` references ``at`` as a component, so it inherits.
    """
    _graft_glyph_single_master_variable(font, "at", TTFont(_REF_LIGHT))


def graft_ampersand(font):
    """Replace ``&`` with Moxy's reference ampersand."""
    _graft_glyph_single_master_variable(font, "ampersand", TTFont(_REF_LIGHT))


def graft_dollar(font):
    """Replace ``$`` with Moxy's reference dollar sign."""
    _graft_glyph_single_master_variable(font, "dollar", TTFont(_REF_LIGHT))


# --------------------------------------------------------------------------------------
# Static-build counterparts. The variable build rebuilds gvar from light/heavy
# masters; the static build is already instanced, so it interpolates those same
# two masters by the instance's normalised weight and shears for italic.


def _graft_glyph_static(font, glyph_name, wght, slnt=0.0):
    """Static build: replace ``glyph_name`` with the reference outline at the
    given Recursive weight/slant. Interpolates the light→heavy masters by the
    weight's normalised position (mirroring ``_graft_glyph_variable``'s wght
    master) and shears for italic. For an already-instanced font (no gvar)."""
    light_src, heavy_src = TTFont(_REF_LIGHT), TTFont(_REF_HEAVY)
    scale = _source_scale(light_src)
    light, end_pts, flags = _quad_outline(light_src, glyph_name, scale)
    heavy, end2, _ = _quad_outline(heavy_src, glyph_name, scale)
    if end_pts != end2 or len(light) != len(heavy):
        raise ValueError(
            f"graft masters for {glyph_name!r} not point-compatible: "
            f"{len(light)} vs {len(heavy)} pts ({end_pts} vs {end2})"
        )
    t = _wght_t(wght)
    coords = [(_lerp(light[i][0], heavy[i][0], t),
               _lerp(light[i][1], heavy[i][1], t)) for i in range(len(light))]
    if slnt:
        coords = _shear(coords, math.tan(math.radians(-slnt)))
    _write_outline(font, glyph_name, coords, end_pts, flags)


def graft_checkmark_static(font, wght, slnt=0.0):
    """Static build: swap ``✓`` for Moxy's fuller check mark."""
    _graft_glyph_static(font, "uni2713", wght, slnt)


def graft_bullet_static(font, wght, slnt=0.0):
    """Static build: swap ``•`` for Moxy's fuller bullet."""
    _graft_glyph_static(font, "bullet", wght, slnt)


def graft_percent_static(font, wght, slnt=0.0):
    """Static build: swap ``%`` for Moxy's connected diagonal design."""
    _graft_glyph_static(font, "percent", wght, slnt)


def graft_slash_static(font, wght, slnt=0.0):
    """Static build: swap ``/`` for Moxy's clean straight slash."""
    _graft_glyph_static(font, "slash", wght, slnt)


def graft_backslash_static(font, wght, slnt=0.0):
    """Static build: swap ``\\`` for Moxy's clean straight backslash.

    Composites (backslash.code, .case, and the escape ligatures) reference
    ``backslash`` as a component, so they inherit automatically.
    """
    _graft_glyph_static(font, "backslash", wght, slnt)


def _pick_ref_static(wght):
    """Pick the closest reference weight for a static instance. Recursive's
    Regular (375) maps to the Regular master; Bold (600) maps to Semibold."""
    return TTFont(_REF_SEMIBOLD) if wght >= 550 else TTFont(_REF_LIGHT)


def _graft_glyph_single_master_static(font, glyph_name, wght, slnt=0.0):
    """Static build: replace ``glyph_name`` with a single reference outline at
    the closest reference weight, sheared for italic. No weight interpolation
    (the reference font's masters aren't point-compatible for these glyphs)."""
    src = _pick_ref_static(wght)
    scale = _source_scale(src)
    coords, end_pts, flags = _quad_outline(src, glyph_name, scale)
    if slnt:
        coords = _shear(coords, math.tan(math.radians(-slnt)))
    _write_outline(font, glyph_name, coords, end_pts, flags)


def graft_at_static(font, wght, slnt=0.0):
    """Static build: swap ``@`` for Moxy's reference at-sign."""
    _graft_glyph_single_master_static(font, "at", wght, slnt)


def graft_ampersand_static(font, wght, slnt=0.0):
    """Static build: swap ``&`` for Moxy's reference ampersand."""
    _graft_glyph_single_master_static(font, "ampersand", wght, slnt)


def graft_dollar_static(font, wght, slnt=0.0):
    """Static build: swap ``$`` for Moxy's reference dollar sign."""
    _graft_glyph_single_master_static(font, "dollar", wght, slnt)
