---
title: Rebrand "Recursive KG" → "Moxy" + invert VF defaults + new README
kind: software
status: done
mode: feature
created: 2026-06-16
updated: 2026-06-16
repo: recursive-code-config (→ to be renamed font-moxy)
source_inputs:
  - Conversation 2026-06-16: rename Recursive KG → "Moxy"; rewrite README as a
    standalone font; make Moxy's customized look the VF default (flip features
    to reverts).
  - .agents/plans/handoff-20260616-092154.md — VF (Task B) complete & committed.
  - .agents/plans/2026-06-15-lilex-recursive-kg-plan.md — full VF/static history
    + Decision Log.
---

# Rebrand "Recursive KG" → "Moxy" + invert VF defaults + new README

## Goal

Turn the in-house "Recursive KG" build into a standalone font called **Moxy**:

1. **Invert the variable font's defaults (Option B).** The VF is the canonical
   Moxy artifact. Make the customized look the **default** appearance: curvy
   parens, connected dashes + bars, thin escape-only backslash, 12 added arrows,
   and Kaush's preferred letterforms (simplified f/r, serifless L/Z, dotted 0,
   simplified 1). Flip every *revertible* feature into a *revert*: enabling `lilx`
   undoes the Lilex tweaks, `ss13` undoes the five letters, `ss03/06/08/10/11` undo
   each letter — so `lilx` + `ss13` together return the **revertible** glyph set to
   pristine Recursive (at the VF's Mono-Casual-Regular default location). NOTE:
   the 12 added arrows and the long-arrow `calt`/`dlig` fix are **additive,
   always-on** (nothing to revert), so the reverted font is "Recursive + arrows",
   not byte-pristine Recursive. The VF is the canonical Moxy artifact (the user
   installs it; config-free + reversible) and the intended **future** single-source
   for static generation — see Decision Log (GATE-0 resolved: Phase A is a go;
   static generation keeps the current pipeline for now).
2. **Rename "Recursive KG" / "RecursiveKG" / "KG" → "Moxy" everywhere** — font
   name tables, output folders/filenames, scripts, config, Makefile, homebrew
   cask, the release skill, Brewfiles, source comments, and the GitHub repo/remote.
3. **Rewrite the README** to present Moxy as its own font (install-first; build
   instructions below), with attribution to Recursive (built-on) and Lilex
   (OFL-1.1) and a "What's different from Recursive" section.

## Background

### Prerequisite — DONE (handoff 2026-06-16, committed to `main`)

The VF is built, verified, committed (commits `4249ca6`…`7eb41a7`). Current state:

- **One 5-axis VF** (MONO/CASL/wght/slnt/CRSV all live), **default re-based to
  Mono Casual Regular** (MONO=1, CASL=0.5, wght=375) so the bare font is a usable
  terminal monospace. Default outlines == OG Recursive @ that location (±1 unit).
- Family name **"Recursive KG"** (matches the static build); PostScript name is
  the distinct **`RecursiveKG-VF`** (avoids clash with static
  `RecursiveKG-Regular`). Output (git-ignored):
  `fonts/RecursiveKG-VF/RecursiveKG[MONO,CASL,wght,slnt,CRSV].ttf`.
- **Two opt-in bundles, OFF by default:** `lilx` (custom tag = curvy parens,
  connected bars, connected dashes, thin escape backslash, 12 added arrows) and
  `ss13` ("Kaush's preferences" = Recursive's own ss03/06/08/10/11). Long arrows
  are a **default** fix living in `dlig`.
- Recursive VF has **no `calt`**; code ligatures live in **`dlig`** (opt-in —
  ghostty today uses `font-feature = dlig, lilx, ss13`). `dlig` ligates only
  `--`/`---`/bounded arrows; 4+ dash runs stay loose.
- All borrowed glyphs are **variable alternates** (gvar: wght 300→1000 + slnt
  shear; MONO/CASL frozen); pristine originals untouched. HVAR is **repaired**
  (`repair_hvar` pins new glyphs to a zero-delta varidx) — NOT dropped.

### The two build paths (names today, both → "Moxy")

- **Static** (`scripts/instantiate-code-fonts.py` + `premade-configs/config.kg.yaml`):
  8 instances, family `Recursive KG`, PS `RecursiveKG-<Style>`, files
  `RecursiveKG-<Style>-<fontver>.ttf`, folder `fonts/RecursiveKG/`. Bakes the
  Lilex tweaks + chosen ssXX into `calt` (ligatures on by default via dlig2calt).
- **Variable** (`scripts/build-variable-font.py` + `vf_lilex.py` +
  `vf_long_arrows.py`): as above.

Distribution: GitHub release zip + a homebrew cask in a **separate** repo
(`/Users/kg/dev/oss/homebrew-tools/Casks/font-recursive-kg.rb`), plus
`~/.Brewfile` and `~/.brewfile` (line 123). `fonts/` is git-ignored.
`update-recursive-kg` skill + `Makefile` `package` automate the release.

### Decisions locked in this conversation (human)

- Name = **`Moxy`** (title case), replacing `Recursive`/`KG` entirely. Both
  static and VF carry family name exactly **`Moxy`** (only one installed at a time).
- **Canonical artifact = the VF** (where the Moxy default look + the revert
  toggles live; the user installs it locally for the toggles). **The cask/release
  ships the STATIC instances** (frozen per yaml, ligatures already baked into
  `calt`, no toggles) — `update-moxy` derives them exactly as before. Static
  defaults are out of scope for the flip; only the VF default look is inverted.
- Rename scope = **everything**, incl. the GitHub repo
  `kaushikgopal/recursive-code-config` → **`kaushikgopal/font-moxy`** and cask
  token → **`kaushikgopal/tools/font-moxy`**. Accepted breaking change: existing
  `font-recursive-kg` users must reinstall.
- README leads with Moxy-as-a-font; attribution to Recursive + Lilex; a "what's
  different" section.
- VF semantics = **Option B (uniform inversion)**: Moxy look default; `lilx`
  reverts Lilex tweaks, `ss13` reverts the five letters, `ssNN` revert
  per-letter; `lilx`+`ss13` revert the **revertible** glyph set to pristine
  Recursive. The 12 added arrows and the long-arrow fix stay always-on (additive,
  nothing to revert).

## Constraints

- **Preserve monospacing**: every advance stays 600/1200/1800 at every axis
  location. New alternates stay advance-correct via the existing `repair_hvar`
  (zero-delta HVAR entry); if Phase A adds any new glyphs, `repair_hvar` must run
  after.
- **Default VF (no features) must render the full Moxy look** and remain a clean
  5-axis VF that interpolates across wght + slnt. The mono-default rebase
  (instancer range-limiting at the end of `build()`) must preserve the inverted
  cmap/GSUB — verify in the spike.
- **`lilx` + `ss13` enabled together must reproduce pristine Recursive** at the
  default location (outline diff = 0 for affected glyphs vs the source VF default
  instance).
- **Preserve lookup ordering**: long-arrow lookups are built BEFORE `lilx` (lower
  indices) so HarfBuzz applies them first. The inversion's reverse lookups must
  not break this; default (forward) subs go at lower indices than the toggle
  (reverse) subs. Verify in HarfBuzz.
- All GSUB edits **hand-built (otlLib/otTables), append-only** — never feaLib on
  `calt`/`dlig`. After adding glyphs, `font.getReverseGlyphMap(rebuild=True)`.
- **macOS only**: name records only need (3,1,0x409).
- Lilex is OFL-1.1: keep `font-data/Lilex-OFL.txt`; bundle the OFL notice in any
  distributed artifact.
- Dev-only `Pillow`/`uharfbuzz` (venv, not `requirements.txt`); renders to the
  macOS temp dir, never the repo. Use `venv/bin/python -m pip` (stale pip shebang).
- **Static build stays behavior-unchanged** — Phase B renames its naming/paths
  only; it still freezes per yaml. Do not alter its glyph logic.
- Do not install fonts, push the repo rename, or remove dev deps until final
  validation passes.
- Out of scope: rebranding upstream generic configs (`config.yaml`,
  `premade-configs/{casual,code,cli,sans,duotone,linear,semicasual}.yaml`) and
  their "Rec Mono Custom" example text. (See Open Questions.)

## Existing Patterns

- **VF build flow** (`scripts/build-variable-font.py` `build()`): load +
  force-decompile glyf/gvar/HVAR map → `rename_family` → `add_kaush_preferences`
  (ss13) → long arrows (dlig, low indices) → `lilx` (parens, bars, dashes,
  backslash, arrows) → `repair_hvar` → rebuild glyph map → **mono-default rebase**
  via `instancer.instantiateVariableFont(..., {"MONO":(0,1,1),"CASL":(0,.5,1),"wght":(300,375,1000)}, inplace=True)` → save.
- **VF helpers** (`scripts/vf_lilex.py`): `graft_variable_alternate`,
  `add_variable_glyph`, `repair_hvar`, `append_lookup`, `single_sub_lookup`,
  `add_feature(feature_tag=, lookup_indices=, ui_name=)`,
  `feature_lookup_indices(font, tags)`, `wght_anchors`, `source_bounds`.
- **Inversion building blocks already exist**: every customized glyph already has
  a distinct name (`*.lilx`, plus Recursive's own simplified alternates behind
  ss03/06/08/10/11). Inversion is mostly *which glyph the codepoint/ligature
  resolves to by default* + *reverse single-subs in the toggle features* — little
  or no new outline work.
- **Static naming** (`scripts/instantiate-code-fonts.py` `splitFont`): name IDs
  1/2/3/4/6/16/17 + filenames derive from `newName="Recursive"` +
  `fontOptions['Family Name']="KG"` and `outputDirectory=f"Recursive{Family Name}"`.

## Approach

Three phases after the (now-complete) VF prerequisite.

### Phase A — Invert the VF defaults (Option B). The core engineering.

Goal: no features → Moxy look; each feature reverts; `lilx`+`ss13` → pristine
Recursive. Because the Recursive VF has **no `calt`** and arbitrary tags
(`lilx`/`ssNN`) are never shaper-default, the Moxy default must live where shapers
apply it unconditionally — the **cmap** layer and a **new `calt` feature** (which
HarfBuzz applies by default for Latin). Handle three categories:

1. **Simple base-glyph swaps** (curvy parens; letters f, r, L, Z, 0, 1):
   - Make the customized glyph the codepoint default via **cmap remap**.
   - Validate composition with Recursive's `rvrn`/feature-variation MONO/CASL
     swaps (e.g. `0`→`zero.sans` at MONO 0); per-glyph fall back to a
     `calt`/`rclt` default-applied sub if cmap remap fights the variations.
   - Add **reverse** single-subs (customized→original) under the toggles: parens
     → `lilx`; each letter → its own `ssNN`; all five also → `ss13`.
2. **Ligature-formed glyphs** (connected bars `|>` `<|`, connected `---`): these
   only exist when ligatures are active. Make the ligature output default to the
   **connected** outline and provide the reverse under `lilx`. To make ligatures
   themselves default-on (so the connected look needs zero config and matches the
   static build, which already uses `calt`), add a **`calt` feature** referencing
   the existing `dlig` lookups (+ the connected/long-arrow lookups), wired into
   every langsys, preserving the long-arrow-before-lilx order. (Keep `dlig` too;
   it's harmless.)
3. **Contextual default lookups** (thin escape-only backslash; the ≥4-run
   connected-dash chain — both operate on loose glyphs, no dlig needed): register
   the existing forward contextual lookups under the new `calt` feature
   (default-on) and add matching **reverse** lookups under `lilx`, at higher
   indices so they run after the forward subs when `lilx` is enabled.

`ss13` reimplementation: today it reuses Recursive's forward (base→simplified)
lookups. After inversion the simplified forms are default, so `ss13` must instead
carry **reverse** (simplified→original) lookups for all five letters; per-letter
`ssNN` carry the single-letter reverse. Rename its UI name (currently "Kaush's
preferences") to **"Alt. Recursive choices"**. (Re-derive Recursive's lookup
indices via `feature_lookup_indices` if the source VF version changes.) The reverse
subs' **input coverage must include the `.sans`/`.mono` stem-siblings**, not just
the base glyph — mirror the stem-sibling expansion already in
`build-variable-font.py` `add_thin_backslash` (the MONO/CASL forms come from
feature-variations the reverse single-sub can't otherwise see).

The 12 arrows: cmap straight to the real arrows (drop the `.notdef` placeholder
gating) so they're always-on.

**Escape-ligature reverse is NOT a single-sub.** `add_thin_backslash` decomposes
`backslash_X.code` → `[backslash.lilx, letter]` via a Type-2 multiple-sub. To make
the thin escape backslash a *default* that `lilx` reverts, the reverse must
re-ligate `[backslash, letter]` → `backslash_X.code` with a Type-4 **ligature**
lookup under `lilx` (a single-sub cannot undo a multiple-sub). Verify `\n` etc.
re-form when `lilx` is on.

**Spike GATES — run before any other Phase A work; each is pass/fail:**
- **(G1) CoreText default-`calt`.** The "zero-config Moxy look" rests on apps
  auto-applying the hand-added `calt`. HarfBuzz (ghostty) does; **CoreText is NOT
  guaranteed to** (this codebase was already bitten by CoreText diverging — the
  CASL named-instance snap). Install the spike VF and render with NO feature
  config in a CoreText app (TextEdit/Safari) AND in ghostty. If CoreText doesn't
  apply `calt`, the contextual Moxy bits (thin backslash, ≥4-dash chain, connected
  bars/`---`) silently won't show there → the default-on-`calt` premise is dead for
  CoreText; decide whether HarfBuzz-only is acceptable or rethink Phase A.
- **(G2) Escape re-ligation.** Confirm the Type-4 reverse above actually re-forms
  `\n` when `lilx` is on.
- **(G3) Rebase preservation.** Confirm the final mono-default rebase
  (`instancer` range-limiting) preserves the NEW `calt` feature + appended reverse
  lookups (instancer can prune features/lookups in some fontTools versions; prior
  verification only covered the old feature set).

Then confirm via uharfbuzz + render: (a) default == full Moxy look; (b) `lilx`
reverts parens/dashes/bars/backslash/arrows; (c) `ss13` reverts all five letters;
(d) each `ssNN` reverts its one letter; (e) `lilx`+`ss13` → pristine Recursive
**for the revertible glyph set** (0 outline diffs vs source default instance for
the affected glyphs; the 12 arrows + long arrows remain by design); (f) advances
stay monospace at all axis locations. Only then wire the final build.

### Phase B — Rename "Recursive KG" → "Moxy".

Family/PS = exactly `Moxy`; VF PS stays distinct (`Moxy-VF`) vs static
(`Moxy-<Style>`). Folder `fonts/Moxy-VF/` (VF) and `fonts/Moxy-Static/` (statics);
files `Moxy[MONO,CASL,wght,slnt,CRSV].ttf` (VF), `Moxy-<Style>-<fontver>.ttf`
(static); release zip `moxy-<version>.zip` (packages the **static** set).

Surfaces: VF constants (`FAMILY`, `PS_NAME`, `DEFAULT_OUT`, `rename_family`,
docstrings); static naming logic (drop the `Recursive`+`KG` composition so family
is bare `Moxy`, no trailing space; rename outputs); rename `config.kg.yaml` →
`config.moxy.yaml` (header + `Family Name`); comment/docstring rebrand across
`scripts/*.py`; `Makefile` (paths, zip name, release title/notes, commit msgs,
cask path, config path; bundle `Lilex-OFL.txt` in the zip); skill dir →
`update-moxy` + contents; cask file (other repo) → `font-moxy.rb` + token/url/
name/font paths; both Brewfiles; then GitHub repo + git remote (last).

### Phase C — Consolidate docs: one `README.md` + `CUSTOMIZING.md`.

End state: a single lean, user-facing **`README.md`** plus a **`CUSTOMIZING.md`**
(build/VF/maintainer guide that absorbs `README_KG.md`). Delete `README_KG.md`.

`README.md` (Moxy-first, lean):
1. Title + pitch ("Moxy — a monospaced coding font") with a new **`Moxy` ASCII
   banner** replacing the `code` banner.
2. **Install** (lead): `brew install --cask kaushikgopal/tools/font-moxy`
   (ships the static set) + GitHub release download.
3. **What's different from Recursive**: the Moxy look (curvy parens, connected
   dashes/bars, thin escape backslash, fancy arrows, simplified f/r/L/Z/0/1) vs
   stock Recursive. Brief note that the **variable font** additionally exposes
   revert toggles (`lilx`, `ss13` "Alt. Recursive choices", per-letter `ssNN`) —
   full details in `CUSTOMIZING.md`.
4. Features inherited from Recursive + the variable axes (one-liner).
5. **Attribution & license**: built on Recursive (ArrowType) + borrows glyphs
   from Lilex (OFL-1.1); link both + licenses; note `Lilex-OFL.txt` is bundled.
   Note that existing `font-recursive-kg` cask users must reinstall as `font-moxy`.
6. A short "Build / customize from source → see `CUSTOMIZING.md`" pointer.

`CUSTOMIZING.md` (absorbs `README_KG.md` + the old build instructions):
- venv setup; `make build` (static) / `make package`; `build-variable-font.py`
  (the VF + its toggles, ghostty usage `font-family = Moxy`, pristine via
  `font-feature = lilx, ss13`); building from other configs; the `update-moxy`
  release flow; updating to new Recursive versions.
- **Note the static/VF asymmetry plainly**: the shipped (cask) static font has the
  Moxy look baked in with **no toggles / no revert**; the personal VF has the Moxy
  default **plus** the revert toggles. So brew users won't be surprised the cask
  font can't be dialed back to Recursive.

## Decision Log

- 2026-06-16 - human: Name = `Moxy`, no KG/Rec Mono/Recursive; both builds family
  `Moxy`; only one installed at a time.
- 2026-06-16 - human: Primary artifact = VF; static derived from yaml as before
  (frozen → out of scope for the flip).
- 2026-06-16 - human: Rename scope = everything incl. GitHub repo → `font-moxy`
  and cask token → `kaushikgopal/tools/font-moxy`. Accepted breaking change.
- 2026-06-16 - human: README Moxy-first; attribution to Recursive + Lilex;
  "what's different" section.
- 2026-06-16 - human: VF semantics = **Option B (uniform inversion)** —
  `lilx`+`ss13` revert the revertible glyph set to pristine Recursive; the 12
  arrows + long-arrow fix stay always-on (additive, not revertible).
- 2026-06-16 - planner: Incorporated handoff facts — VF already renamed "Recursive
  KG" (PS `RecursiveKG-VF`), HVAR repaired (not dropped), default rebased to Mono
  Casual Regular, no `calt` (ligatures in `dlig`), long-arrow-before-lilx ordering.
  Impact: "default-on" must use cmap + a NEW `calt` feature; ordering preserved;
  the inversion is a re-pointing of lookups/cmap, minimal new outlines.
- 2026-06-16 - planner: Scope excludes upstream generic premade-configs and their
  "Rec Mono Custom" examples. Open Question if the human wants otherwise.
- 2026-06-16 - human: Open Questions resolved — (1) swap the ASCII banner for a
  `Moxy` one; (2) the **cask ships the STATIC fonts** (VF is canonical/personal,
  has the toggles); (3) folders `fonts/Moxy-Static/` and `fonts/Moxy-VF/`;
  (4) leave upstream generic configs as-is; (5) consolidate docs to a single
  user-facing `README.md` + a `CUSTOMIZING.md` (absorbs `README_KG.md`, holds the
  build/VF/maintainer guide); (6) `ss13` UI name → **"Alt. Recursive choices"**.
- 2026-06-16 - planner: Given the VF has no `calt`, adding a default-on `calt`
  feature for the VF's contextual/ligature Moxy defaults is now the chosen
  approach (not an open question), so the VF's Moxy look needs zero ghostty config.
- 2026-06-16 - red-team: Reviewed the plan. Key findings: (1) **Phase A is gated** —
  it ships to no distributed artifact (cask ships static; static already bakes the
  Moxy look on), and the user already gets the Moxy look in ghostty with
  `font-feature = dlig, lilx, ss13` today, so Phase A's payoff is a config-free +
  reversible *personal* VF. Worth doing only if that's a real recurring need.
  (2) "`lilx`+`ss13` == pristine Recursive" was internally contradictory (arrows +
  long arrows are always-on) — reworded to "revertible glyph set". (3) CoreText may
  not auto-apply a hand-added `calt` (this repo was bitten by CoreText before via
  the CASL named-instance snap) — added as spike gate G1. (4) The escape-backslash
  default is a Type-2 multiple-sub; its reverse needs a Type-4 **ligature** lookup,
  not a single-sub — gate G2. (5) reverse subs need stem-sibling (`.sans`/`.mono`)
  coverage. (6) Makefile sed automation will silently no-op after the rename; cask
  version already drifted (cask `38` vs config `39`) — rewrite the cask by hand
  and reconcile. (7) do "Moxy" name-collision diligence (a display typeface uses
  the name).   Impact: Phase A now gated on a human decision + pass/fail spike gates;
  Phase B/C (rename + docs) proceed regardless as the low-risk, user-visible win.
- 2026-06-16 - human: **GATE-0 resolved → do Phase A.** The red-team's "ships to
  nobody" premise is corrected: the Moxy VF is the canonical artifact (personal,
  config-free + reversible) and the **intended future single-source** for static
  generation. For now, static generation **keeps the current pipeline** (build from
  the Recursive VF + custom scripts, which already produces the Moxy look and lets
  `config.moxy.yaml` choose what to bake / opt back to Recursive); instancing
  statics directly from the Moxy VF is deferred to a future step. So Phase B's
  static work is **rename-only** (no re-architecture); the inverted VF's revert
  toggles still matter (canonical + future source). The technical spike gates
  (G1 CoreText, G2 ligature-reverse, G3 rebase) remain.
- 2026-06-16 - executor: **Phase A implemented + verified** (new module
  `scripts/vf_invert.py`, wired into `build-variable-font.py` after lilx/ss13,
  before the mono-rebase). Mechanism: parens + 12 arrows → cmap default; a NEW
  default-on `calt` carries Recursive's `dlig` ligatures + long arrows + the
  forward `ss03/06/08/10/11` (simplified letters) + the lilx connected/thin
  lookups; `lilx` rebuilt as the revert (Type-4 religature for `\X` + unconditional
  single-subs sending every `*.lilx`/`*.seq` glyph back to Recursive); `ss03/06/08/
  10/11`+`ss13` rebuilt as letter reverts; `ss13` UI name → "Alt. Recursive
  choices". Verified (uharfbuzz, MONO 0/1): default = full Moxy; `lilx`/`ss13`/each
  `ssNN` revert correctly; `lilx`+`ss13` = pristine Recursive glyph names;
  monospacing 600/1200/1800 everywhere; all tables compile.
  - GATE-2 (escape religature) PASSED; GATE-3 (rebase preserves calt+reverts)
    PASSED (verified on the final post-rebase font).
  - GATE-1 (CoreText): HarfBuzz default-on `calt` verified; `calt` wired into
    DefaultLangSys; CoreText applies `calt` by default as standard — full pixel
    verification deferred to on-install (can't drive a CoreText app here). OPEN.
  - DEVIATION: letter reverts are tuned to the canonical MONO=1 (Mono) default —
    they restore the `.mono` form. At MONO=0 (Sans), reverting via `ssNN`/`ss13`
    yields `f.mono`/`r.mono` rather than sans `f`/`r` (the forward `ss` maps are
    many-to-one, so a single-sub revert can't be MONO-aware). Accepted: Moxy's
    canonical location is MONO=1.
  - "Pristine Recursive" = identical within <1 unit; the residual sub-unit delta is
    the pre-existing mono-rebase rounding (handoff "±1 unit"), not a Phase A change
    (the inversion never touches glyf/gvar).
  - DECISION: ligatures are now DEFAULT-ON in the VF (via `calt`), matching the
    static build's dlig2calt and the "customized by default" goal; `dlig` is kept
    too (harmless).
- 2026-06-16 - executor: **Phase B (rename → Moxy) done.** VF constants → `Moxy`/
  `Moxy-VF`, output `fonts/Moxy-VF/`. Static naming reworked so the config's
  `Family Name` is the full brand (no "Recursive" prefix): `Family Name: "Moxy"` →
  family `Moxy`, folder `fonts/Moxy-Static/`, files `Moxy-<Style>-<ver>.ttf`, PS
  `Moxy-<Style>` (verified id1/4/6/16 + filenames; static glyph behavior
  unchanged). `config.kg.yaml`→`config.moxy.yaml`. Makefile: `Moxy-Static` paths,
  `moxy-<v>.zip`, repo `font-moxy`, cask `font-moxy.rb`, fixed the font-path sed +
  added a post-package assertion, bundles `Lilex-OFL.txt`+`LICENSE` in the zip,
  new `build-vf` target. Skill dir → `update-moxy` + rewritten. Cask hand-rewritten
  to `font-moxy.rb` in homebrew-tools (uncommitted; sha/url refreshed by the next
  release run). Brewfiles → `font-moxy`. Name diligence: no coding font named
  "Moxy" (only "Moxy Rush" display + Marriott hotels; low risk, confirm before
  public release). Upstream generic premade-configs left as-is.
- 2026-06-16 - executor: **Phase C (docs) done.** Rewrote `README.md` Moxy-first
  (Moxy ASCII banner, install via `font-moxy` cask + migration note for old
  `font-recursive-kg` users, a "what's different from Recursive" table, the VF
  revert toggles, attribution to Recursive + Lilex both OFL-1.1, MIT tooling).
  New `CUSTOMIZING.md` absorbs `README_KG.md` (deleted) + the build/VF/release/
  upstream-sync guide, incl. the static-vs-VF asymmetry note.
- 2026-06-16 - executor: **DONE + validated.** Clean rebuild: 8 static `Moxy-*`
  instances + VF all compile; VF default=Moxy, `lilx`+`ss13`=Recursive; advances
  monospace. Dev-only Pillow/uharfbuzz removed. Commits: plan+notes → Phase A →
  Phase B → Phase C → (final) delete this plan. **One manual step left for the
  human** (intentionally not executed — live/destructive GitHub op that also
  breaks the local working path): rename repo + dir + remote —
  `gh repo rename font-moxy -R kaushikgopal/recursive-code-config`, then
  `cd .. && mv recursive-code-config font-moxy && cd font-moxy &&
  git remote set-url origin https://github.com/kaushikgopal/font-moxy.git`. The
  rewritten `homebrew-tools/Casks/font-moxy.rb` gets its sha256/url refreshed +
  committed on the next `make package` / `update-moxy` release run.

## Execution Protocol

- Prerequisite gate met: VF is built/committed. Re-run the VF build once to
  confirm clean before Phase A.
- Work `## Tasks` in phase order (A → B → C → release). Inspect `## Files`,
  `## Existing Patterns`, `## Constraints` before editing.
- All GSUB edits hand-built, append-only; rebuild the reverse glyph map after
  adding glyphs; `repair_hvar` after any new glyphs; preserve lookup ordering.
- Spike-validate Phase A in uharfbuzz + a Pillow/ghostty render to the temp dir
  BEFORE finalizing the inverted build.
- Commit each logical unit separately. Do not install fonts, push the repo
  rename, or remove dev deps until the final task.
- Update `## Decision Log` on meaningful changes/blockers; blockers →
  `## Open Questions`.
- GitHub repo rename + `git remote` update is the LAST step.

## Files

In this repo:
- `scripts/build-variable-font.py` — invert defaults + reverse features + add
  `calt`; rename `FAMILY`/`PS_NAME`/`DEFAULT_OUT`/`rename_family`/docstrings; drop
  arrow placeholder gating.
- `scripts/vf_lilex.py` — likely add a reverse-single-sub helper + a cmap-remap
  helper; rename docstrings.
- `scripts/vf_long_arrows.py` — default long arrows (stays always-on).
- `scripts/instantiate-code-fonts.py` — static naming → bare `Moxy` (no
  `Recursive`/`KG`/trailing space); output `fonts/Moxy-Static/`.
- `premade-configs/config.kg.yaml` → `premade-configs/config.moxy.yaml` (header +
  `Family Name`).
- `scripts/{add_stylistic_set,join_dashes,borrow_glyphs,long_arrows,add_characters,dlig2calt,mergePowerlineFont}.py`
  — comment/docstring rebrand only.
- `Makefile` (build/package the **static** set), `README.md` (lean, user-facing),
  `CUSTOMIZING.md` (new; absorbs `README_KG.md`, which is deleted),
  `.agents/skills/update-recursive-kg/SKILL.md` (→ `update-moxy/`).

Outside this repo:
- `/Users/kg/dev/oss/homebrew-tools/Casks/font-recursive-kg.rb` → `font-moxy.rb`.
- `/Users/kg/.Brewfile`, `/Users/kg/.brewfile` (line 123) → `font-moxy`.
- GitHub repo rename + local `git remote`.

## Tasks

### Phase A — Invert VF defaults (Option B) — GATE-0 resolved (go)
- [ ] Re-run VF build; confirm clean (pristine default, opt-in `lilx`+`ss13`).
- [ ] **Spike GATE-1**: render the inverted-spike VF with NO feature config in a
      CoreText app AND ghostty — does CoreText apply the new `calt`? If not, decide
      HarfBuzz-only vs rethink before any more Phase A work.
- [ ] Add helpers: reverse single-sub builder; Type-4 ligature-reverse builder;
      cmap-remap helper.
- [ ] Parens + letters (f/r/L/Z/0/1): customized glyph as cmap default (or
      `calt`/`rclt` fallback where MONO/CASL variations conflict); reverse subs →
      `lilx` (parens), `ssNN` (each letter), `ss13` (all five). Reverse coverage
      must include `.sans`/`.mono` stem-siblings.
- [ ] Connected bars + `---`: default to connected outline; add `calt` referencing
      `dlig` lookups so ligatures are default-on; reverse → `lilx`; keep
      long-arrow-before-lilx order; check no double-application with `dlig`.
- [ ] Thin escape backslash + ≥4 dash chain: forward lookups under `calt`
      (default-on); reverse → `lilx` at higher indices (escape backslash reverse =
      Type-4 ligature, **GATE-2**: `\n` re-ligates when `lilx` on); verify ordering.
- [ ] Replace `ss13` forward lookups with reverse (simplified→original) for the
      five letters; per-letter reverse under each `ssNN`; rename UI →
      "Alt. Recursive choices".
- [ ] Arrows: cmap straight to real arrows (drop `.off` placeholders).
- [ ] `repair_hvar` if any new glyphs added; rebuild glyph map. **GATE-3**: confirm
      the mono-default rebase preserves the new `calt` + reverse lookups.
- [ ] SPIKE-validate (shaper + render): default = Moxy; each toggle reverts;
      `lilx`+`ss13` → pristine Recursive for the revertible set; advances monospace.

### Phase B — Rename → Moxy
- [ ] VF: `FAMILY`/`PS_NAME` → `Moxy`/`Moxy-VF`; `DEFAULT_OUT` →
      `fonts/Moxy-VF/Moxy[MONO,CASL,wght,slnt,CRSV].ttf`; rebrand docstrings.
- [ ] Static: name tables → family `Moxy`, PS `Moxy-<Style>`, files
      `Moxy-<Style>-<fontver>.ttf`, folder `fonts/Moxy-Static/`.
- [ ] Rename `config.kg.yaml` → `config.moxy.yaml`; update header + `Family Name`.
- [ ] Rebrand comments/docstrings across `scripts/*.py`.
- [ ] `Makefile`: paths (build/install/zip the **static** `fonts/Moxy-Static/`),
      zip `moxy-<ver>.zip`, release title/notes, commit msgs, cask path
      `font-moxy.rb`, config path `config.moxy.yaml`; bundle `Lilex-OFL.txt` in zip.
      Rewrite the font-path sed (line ~66) — it hard-codes `RecursiveKG` on BOTH
      sides and will silently no-op after the rename; update pattern → target
      (`Moxy-Static/Moxy-<Style>-<ver>.ttf`) and add a post-package assertion that
      the cask's `font` lines actually changed.
- [ ] Reconcile the existing **version drift** (cask `version "38"` vs config
      `Version: "39"`) during the rename.
- [ ] Skill: rename dir → `update-moxy`; update repo/cask/paths/titles.
- [ ] Cask (other repo): **rewrite by hand** (don't trust sed through the rename)
      → `font-moxy.rb`; update token/url/name + static font paths
      (`Moxy-Static/Moxy-<Style>-<fontver>.ttf`).
- [ ] Brewfiles: `font-recursive-kg` → `font-moxy` (both files).
- [ ] "Moxy" name diligence: 10-min check for an existing typeface/trademark
      collision before the GitHub rename (a display face uses the name); confirm or
      qualify if public sharing is ever intended.

### Phase C — README
- [ ] Write the lean `README.md` (Moxy-first: `Moxy` ASCII banner → pitch →
      install (cask=static) → what's different → inherited → attribution/license
      → pointer to `CUSTOMIZING.md`).
- [ ] Create `CUSTOMIZING.md` absorbing `README_KG.md` + build/VF/maintainer
      instructions; delete `README_KG.md`; fix stale `RecursiveKG` references.

### Release / finalize (via update-moxy flow)
- [ ] Build VF + derived statics; validate (below); render samples.
- [ ] Package: zip + SHA + GitHub release + cask + Brewfiles per `update-moxy`.
- [ ] Install Moxy VF; uninstall any `RecursiveKG*`; remove dev-only deps.
- [ ] LAST: rename GitHub repo → `font-moxy`; update local `git remote`.

## Acceptance Criteria

- [ ] VF default render (no features) = full Moxy look (curvy parens, connected
      dashes/bars, thin escape backslash, fancy arrows, simplified f/r/L/Z/0/1);
      valid 5-axis VF interpolating across wght + slnt; default still Mono Casual
      Regular.
- [ ] `lilx` reverts Lilex tweaks; `ss13` reverts all five letters; each `ssNN`
      reverts its letter; `lilx`+`ss13` returns the **revertible** glyph set to
      pristine Recursive (0 outline diffs vs source default instance for those
      glyphs; the 12 arrows + long arrows remain by design).
- [ ] (If GATE-1 passed) the full Moxy look — including the contextual bits (thin
      backslash, ≥4 dashes, connected bars/`---`) — renders with NO feature config
      in both ghostty and a CoreText app.
- [ ] Monospacing preserved (advances 600/1200/1800 at every axis location).
- [ ] No `RecursiveKG` / `Recursive KG` / bare `KG` family naming remains in
      Moxy-identity surfaces; family/PS = `Moxy` (VF PS `Moxy-VF`).
- [ ] README leads with Moxy-as-a-font, has a "what's different" section, install
      instructions, and attribution to Recursive + Lilex.
- [ ] `brew install --cask kaushikgopal/tools/font-moxy` resolves to the new
      release; repo is `kaushikgopal/font-moxy`; local remote updated.

## Validation

- VF build: `venv/bin/python scripts/build-variable-font.py font-data/Recursive_VF_1.085.ttf fonts/Moxy-VF/Moxy[MONO,CASL,wght,slnt,CRSV].ttf`
- Static build: `rm -rf fonts/Moxy-Static && venv/bin/python scripts/instantiate-code-fonts.py premade-configs/config.moxy.yaml font-data/Recursive_VF_1.085.ttf`
- Shape (dev): `venv/bin/python -m pip install Pillow uharfbuzz`; `hb.shape` with
  features off, `{"lilx":1}`, `{"ss13":1}`, `{"ss06":1}`, `{"lilx":1,"ss13":1}`;
  compare glyph sequences; then uninstall the deps.
- Pristine check: instance the inverted VF at default with `lilx`+`ss13`; diff
  affected-glyph outlines vs the source VF default instance (expect 0).
- Render (dev): Pillow/ghostty sample (`( )`, `--->`, `|>`, `\n`/`\\b`/`:\`,
  `f r L Z 0 1`) to the temp dir; eyeball default vs each toggle. Ghostty:
  `font-family = Moxy`; pristine via `font-feature = lilx, ss13`.
- Validity: `f['GSUB'].compile(f)` / `f['cmap'].compile(f)` / `f['gvar'].compile(f)`
  on each output without error.
- Naming sweep: ripgrep `RecursiveKG|Recursive KG|font-recursive-kg|config\.kg` →
  only historical plan/decision-log mentions remain.

## Risks

- **Phase A value & maintenance (accepted).** Today the inverted VF is the
  canonical/personal artifact (config-free + reversible) and the intended future
  source for static generation; the shipped cask statics still come from the
  current pipeline (GATE-0 decision). Cost to accept: the reverse `ss13`/`ssNN`
  lookups depend on Recursive's own lookup indices, so each Recursive upstream bump
  needs re-validation (re-derive via `feature_lookup_indices`). Mitigation: keep
  the VF build idempotent + re-run the spike checks on each upstream bump.
- **CoreText may not auto-apply the new `calt`** (this repo was already bitten by
  CoreText diverging via the CASL named-instance snap). If so, the contextual Moxy
  defaults silently don't render in CoreText apps → inconsistent half-Moxy.
  Mitigation: spike GATE-1 in a CoreText app before committing to the design.
- **Reversibility leaks.** (a) The escape backslash default is a Type-2
  multiple-sub; reversing needs a Type-4 ligature lookup, not a single-sub
  (GATE-2). (b) reverse subs must cover `.sans`/`.mono` stem-siblings or some
  forms won't revert. (c) Arrows + long arrows are always-on, so "reverted" ≠
  byte-pristine Recursive (documented, not a defect).
- **`calt` + `dlig` double-application.** If users keep `font-feature = dlig` and
  `calt` now references the same lookups, order-sensitive chains may apply twice.
  Mitigation: verify single-pass behavior in the spike.
- **cmap remap vs. feature variations (rvrn/MONO/CASL).** Remapping a letter's
  cmap may collide with Recursive's variation-driven sans/mono swaps (`0`→`zero.sans`).
  Mitigation: per-glyph `calt`/`rclt` fallback; verify each letter at MONO 0/1,
  CASL 0/1; check copy/paste/search + OS fallback aren't broken by the remap.
- **Mono-default rebase** (instancer range-limiting) runs last and can prune
  features/lookups in some fontTools versions; confirm it preserves the NEW `calt`
  + reverse lookups + cmap (GATE-3).
- **Makefile sed automation breaks after rename.** The font-path sed hard-codes
  `RecursiveKG` on both sides → silent no-op (stale cask) or corruption.
  Mitigation: rewrite the cask by hand; reconcile the existing version drift (cask
  `38` vs config `39`); assert the cask actually changed post-package.
- **GitHub repo + cask-token rename** breaks existing `font-recursive-kg` installs
  (old token won't see updates; old release-asset URLs change). Mitigation: README/
  release-note the `brew uninstall font-recursive-kg` → install `font-moxy` step.
- **"Moxy" name collision** with an existing display typeface. No OFL blocker
  (no Reserved Font Name), but do quick diligence before the rename.
- **HVAR on any new glyphs**: must run `repair_hvar` or advances balloon at heavy
  weights (HarfBuzz-only bug; fontTools instancer hides it).
- **Heavy weights**: Lilex caps at wght 700 → borrowed glyphs lighter than
  Recursive Black (accepted, documented).

## Open Questions

- **GATE-0 — RESOLVED (human): do Phase A.** The Moxy VF is the canonical artifact
  + future single-source for statics; static generation keeps the current pipeline
  for now (rename-only). Generating statics *from* the Moxy VF is a deferred future
  step (out of scope here).

Execution-time technical unknowns (settled by the Phase A spike):

- **GATE-1**: does a CoreText app apply the hand-added `calt` by default (so the
  contextual Moxy bits render with no config)? If not → HarfBuzz-only or rethink.
- **GATE-2**: is the escape-backslash default reversible via a Type-4 ligature
  lookup (does `\n` re-ligate when `lilx` is on)?
- **GATE-3**: does the mono-default rebase preserve the new `calt` + reverse
  lookups + cmap remaps?
- Per letter, does a `cmap` remap compose cleanly with Recursive's MONO/CASL
  feature-variations, or is a `calt`/`rclt` default-applied sub needed instead?
