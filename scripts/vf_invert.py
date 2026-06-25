"""
Invert the variable-font defaults so the *customized* "Moxy" look is the DEFAULT
and the feature tags become *reverts* back toward Recursive (plan "Option B").

Runs once, late in scripts/build-variable-font.py's ``build()`` — after ``lilx``,
``ss13`` and the long-arrow fix are built, before the mono-default rebase. It does
NOT add glyphs (only cmap edits + appended GSUB lookups), so no ``repair_hvar`` is
needed afterwards.

Mechanism, by category (all empirically verified with uharfbuzz at MONO 0/1):

* Base-glyph swaps (curvy parens; the 12 added arrows) → moved to the **cmap**,
  so they are the default independent of any shaper feature logic.
* Letterforms (Recursive's own ss02/03/06/09/10/11: single-story g, simplified
  f/r, simplified 6&9, dotted 0, simplified 1) → their FORWARD single-sub lookups
  are registered under a new default-on ``calt`` (HarfBuzz/CoreText apply ``calt``
  by default), so the simplified forms are default and still compose with
  ``rvrn``/MONO. The ``ssNN`` tags (and ``ss13``) are rebuilt as the REVERSE
  (simplified→Recursive). Because the forward maps are many-to-one (``f`` and
  ``f.mono`` both → ``f.simple``), the reverse is tuned to the canonical default
  location (MONO=1, Mono): it restores the ``.mono`` form. See DEVIATION in the
  implementation notes.
* Extra non-ssNN single-sub features (e.g. ``titl`` — Recursive's titling Q,
  Q→Q.titl) → handled the same way: forward lookup moved into the default-on
  ``calt`` (fancy form is default), feature rebuilt as the REVERSE. These are NOT
  rolled into the ``ss13`` bundle — each stays its own runtime revert toggle.
* Contextual / ligature tweaks (connected dashes, connected bars, thin escape
  backslash) + Recursive's own code ligatures (``dlig``) + the long-arrow fix →
  all registered under the new default-on ``calt`` so the full Moxy look (incl.
  ligatures) renders with zero config. ``lilx`` is rebuilt as the REVERSE: a
  Type-4 ligature lookup that re-forms ``backslash_X.code`` from
  ``[backslash.lilx, X]`` (GATE-2), then unconditional single-subs that send every
  Moxy-only glyph (``*.lilx``, ``*.seq``) back to its Recursive original.

Net result: bare font = Moxy; ``lilx`` reverts the Lilex tweaks; ``ss13`` (UI name
"Alt. Recursive choices") reverts all the bundled letterforms; each ``ssNN``
reverts one; each extra tag (e.g. ``titl``) reverts its own glyph.
``lilx``+``ss13`` together return the revertible glyph set to pristine Recursive
(the 12 arrows + long arrows are additive, always-on).
"""

from __future__ import annotations

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.otlLib import builder as otl

from vf_lilex import append_lookup, single_sub_lookup, add_feature, feature_lookup_indices

# Escape letters that Recursive ligates as backslash_X.code; the lilx multiple-sub
# decomposes those to [backslash.lilx, <plain letter>], so the revert re-ligates
# the SAME plain letters.
ESCAPE_LETTERS = ["b", "n", "r", "t", "v"]

PAREN_CODEPOINTS = {"parenleft": 0x28, "parenright": 0x29}


# ----------------------------------------------------------------------------
# small GSUB helpers


def _ligature_lookup(mapping: dict[tuple, str]) -> ot.Lookup:
    """Type-4 ligature lookup. `mapping` keys are component tuples."""
    lk = ot.Lookup()
    lk.LookupType = 4
    lk.LookupFlag = 0
    lk.SubTable = [otl.buildLigatureSubstSubtable(mapping)]
    lk.SubTableCount = 1
    return lk


def _set_feature_lookups(font: TTFont, tag: str, indices: list[int]) -> None:
    """Replace the LookupListIndex of every FeatureRecord with `tag`."""
    gsub = font["GSUB"].table
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag == tag:
            fr.Feature.LookupListIndex = list(indices)
            fr.Feature.LookupCount = len(indices)


def _gather_mapping(font: TTFont, lookup_indices: list[int]) -> dict[str, str]:
    """Union of all Type-1 single-sub mappings across `lookup_indices`."""
    LL = font["GSUB"].table.LookupList.Lookup
    out: dict[str, str] = {}
    for i in lookup_indices:
        lk = LL[i]
        if lk.LookupType == 1:
            for st in lk.SubTable:
                out.update(st.mapping)
    return out


def _invert_forward(forward: dict[str, str], glyphs: set[str]) -> dict[str, str]:
    """Invert a many-to-one forward map (base/.mono → alt) into alt → base,
    preferring the ``.mono`` source so the revert is correct at the MONO=1 default.
    """
    by_target: dict[str, list[str]] = {}
    for src, dst in forward.items():
        by_target.setdefault(dst, []).append(src)
    rev: dict[str, str] = {}
    for target, sources in by_target.items():
        if target not in glyphs:
            continue
        mono = [s for s in sources if s.endswith(".mono")]
        # prefer the .mono source (canonical MONO=1 form); else the shortest base
        chosen = mono[0] if mono else sorted(sources, key=len)[0]
        rev[target] = chosen
    return rev


# ----------------------------------------------------------------------------


def invert_defaults(
    font: TTFont,
    ss_tags: list[str] | None = None,
    extra_tags: list[str] | None = None,
    code_ligatures: bool = True,
) -> None:
    ss_tags = list(ss_tags or ["ss02", "ss03", "ss06", "ss09", "ss10", "ss11"])
    extra_tags = list(extra_tags or [])
    gsub = font["GSUB"].table
    LL = gsub.LookupList.Lookup
    go = set(font.getGlyphOrder())
    cmap_tables = [t for t in font["cmap"].tables if t.isUnicode()]

    # ---- classify the existing lilx forward lookups -----------------------
    lilx_idx = feature_lookup_indices(font, ["lilx"])
    paren_map: dict[str, str] = {}     # base -> .lilx  (→ cmap default + revert)
    arrow_off_map: dict[str, str] = {}  # uniXXXX.off -> uniXXXX (→ cmap straight)
    connected_fwd: list[int] = []       # → move into default-on calt
    moxy_reverse: dict[str, str] = {}   # Moxy-only glyph -> Recursive original

    for li in lilx_idx:
        lk = LL[li]
        if lk.LookupType == 1:
            m = dict(lk.SubTable[0].mapping)
            if set(m).issubset({"parenleft", "parenright"}):
                paren_map.update(m)                       # parens → cmap
            elif all(k.endswith(".off") for k in m):
                arrow_off_map.update(m)                   # arrows → cmap
            else:                                          # bars, --- : connected
                connected_fwd.append(li)
                moxy_reverse.update({a: b for b, a in m.items()})
        else:
            connected_fwd.append(li)                       # chains + backslash mult

    # connected-dash chain emits .seq pieces; thin-backslash chain emits
    # backslash.lilx — add their unconditional reverse single-subs.
    for seq in ("hyphen_start.seq", "hyphen_middle.seq", "hyphen_end.seq"):
        if seq in go:
            moxy_reverse[seq] = "hyphen"
    if "backslash.lilx" in go:
        moxy_reverse["backslash.lilx"] = "backslash"
    for base, alt in paren_map.items():
        moxy_reverse[alt] = base

    # ---- 1. parens: curvy is the default (cmap) ---------------------------
    for base, alt in paren_map.items():
        cp = PAREN_CODEPOINTS[base]
        for t in cmap_tables:
            if cp in t.cmap:
                t.cmap[cp] = alt

    # ---- 2. arrows: always-on (cmap straight to the real glyph) -----------
    for t in cmap_tables:
        for cp, g in list(t.cmap.items()):
            if g in arrow_off_map:
                t.cmap[cp] = arrow_off_map[g]

    # ---- 3. letterforms: forward → default; build reverse per ssNN --------
    ss_fwd_by_tag = {tag: feature_lookup_indices(font, [tag]) for tag in ss_tags}
    extra_fwd_by_tag = {tag: feature_lookup_indices(font, [tag]) for tag in extra_tags}
    all_ss_fwd = sorted({i for v in ss_fwd_by_tag.values() for i in v})
    all_extra_fwd = sorted({i for v in extra_fwd_by_tag.values() for i in v})

    # ---- 4. Recursive ligatures + long arrows (currently in dlig) ---------
    dlig_fwd = feature_lookup_indices(font, ["dlig"]) if code_ligatures else []

    # ---- 5. NEW default-on calt = dlig + ss-forward + extra-forward + connected ----
    # Sorted by lookup index so existing ordering invariants hold (Recursive
    # ligatures + long arrows run before the lilx-derived connected subs).
    calt_lookups = sorted(set(dlig_fwd) | set(all_ss_fwd) | set(all_extra_fwd) | set(connected_fwd))
    add_feature(font, feature_tag="calt", lookup_indices=calt_lookups)

    # ---- 6. rebuild lilx as the REVERT of the Lilex tweaks ----------------
    lilx_revert: list[int] = []
    relig = {
        (alt_bs, letter): f"backslash_{letter}.code"
        for letter in ESCAPE_LETTERS
        for alt_bs in ["backslash.lilx"]
        if f"backslash_{letter}.code" in go and letter in go
    }
    if relig:
        lilx_revert.append(append_lookup(font, _ligature_lookup(relig)))
    if moxy_reverse:
        lilx_revert.append(append_lookup(font, single_sub_lookup(moxy_reverse)))
    _set_feature_lookups(font, "lilx", lilx_revert)

    # ---- 7. letterform reverts: ssNN (one each) + ss13 (all ssNN) ---------
    ss13_revert: list[int] = []
    for tag in ss_tags:
        rev = _invert_forward(_gather_mapping(font, ss_fwd_by_tag[tag]), go)
        if not rev:
            continue
        idx = append_lookup(font, single_sub_lookup(rev))
        _set_feature_lookups(font, tag, [idx])
        ss13_revert.append(idx)
    _set_feature_lookups(font, "ss13", ss13_revert)

    # ---- 8. extra (non-ssNN) reverts: one each, NOT bundled into ss13 ----
    extra_revert_tags: list[str] = []
    for tag in extra_tags:
        rev = _invert_forward(_gather_mapping(font, extra_fwd_by_tag[tag]), go)
        if not rev:
            continue
        idx = append_lookup(font, single_sub_lookup(rev))
        _set_feature_lookups(font, tag, [idx])
        extra_revert_tags.append(tag)

    font.getReverseGlyphMap(rebuild=True)

    extra_str = f"; extra reverts={extra_revert_tags}" if extra_revert_tags else ""
    print(f"  • inverted defaults: parens+{len(arrow_off_map)} arrows -> cmap; "
          f"calt(default-on) lookups={len(calt_lookups)}; "
          f"lilx revert lookups={lilx_revert}; ss13 revert lookups={ss13_revert}"
          f"{extra_str}")
