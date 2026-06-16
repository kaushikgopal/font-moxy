---
title: Recursive KG — Lilex customizations (static build) + Variable Font
kind: software
status: in_progress
mode: feature
created: 2026-06-15
updated: 2026-06-15
repo: recursive-code-config
source_inputs:
  - Multi-session chat: customize Recursive KG with selected Lilex features
  - Lilex (OFL-1.1) https://github.com/mishamyrt/Lilex — vendored as font-data/Lilex[wght].ttf
---

# Recursive KG — Lilex customizations + Variable Font

## Goal

Two bodies of work:

1. **Static build (in progress):** bring selected Lilex features into the
   existing static `RecursiveKG` code fonts — curvy parens, connected dashes,
   Recursive-style infinite long arrows, connected bars, extra single-char
   arrows, and an opt-in thin backslash — while keeping Recursive's native
   look for everything else. **Nearly done**; one task remains (thin-backslash
   escape-only logic).

2. **Variable font (Task B, not started):** produce a NEW variable-font source
   of Recursive KG (full 5 axes) where the Lilex tweaks are **opt-in** OpenType
   features and the default is pristine variable Recursive. Keep the static
   build as-is alongside it.

## Background

- `recursive-code-config` instantiates static code-font instances from the
  Recursive variable font (`font-data/Recursive_VF_1.085.ttf`) via
  `scripts/instantiate-code-fonts.py`, driven by `premade-configs/config.kg.yaml`.
- The KG build produces 8 static instances (Regular/Italic/Semibold/SemiboldItalic/
  Bold/BoldItalic/Black/BlackItalic) at MONO=1, CASL=0.5 (roman) / 0 (italic),
  wght 375/500/700/900, slnt 0/−15, CRSV 0. It **freezes** stylistic sets
  (ss03/ss06/ss08/ss10/ss11) and code ligatures into `calt`.
- Lilex is vendored at `font-data/Lilex[wght].ttf` (+ `font-data/Lilex-OFL.txt`).
  Both fonts are UPM 1000, TrueType `glyf`, 600-unit mono cell.
- User works on **macOS only** (Windows compatibility not required — can simplify
  name-table / OS-specific handling).

## Constraints

- Preserve **monospacing**: every glyph keeps its 600-unit advance. Multi-cell
  ligatures draw backward/forward into neighbor cells via Recursive's `LIG`
  spacer glyph but never change advances.
- Lilex is OFL-1.1: keep `font-data/Lilex-OFL.txt`; bundle its copyright when
  distributing (homebrew/GitHub release). Renamed family avoids reserved names.
- Borrowed-glyph weight matching: Lilex strokes are lighter than Recursive's
  heavy weights, so heavy weights (Black) **fall back** to native Recursive.
- Don't install fonts to `~/Library/Fonts` until the very end (user request).
- `Pillow` + `uharfbuzz` are pip-installed in `venv` for DEV PREVIEW/SHAPING ONLY
  (NOT in `requirements.txt`). Remove them at the very end.
- Render/shape previews go in the macOS temp dir
  `/var/folders/f3/p5rxs9dj525c_g8rmz_b2tg00000gp/T/opencode` (NOT the repo).

## Existing Patterns

Build pipeline in `scripts/instantiate-code-fonts.py` `splitFont()` loop, per instance:
1. `instancer.instantiateVariableFont(varfont, axisLocation, OverlapMode.REMOVE)`
   (axisLocation has wght/CASL/MONO/slnt/CRSV) → `instanceFont.save(outputPath)`
2. name-table renames (RecursiveKG)
3. `freeze_features(outputPath, ["rvrn"]+Features, target="calt", single_sub=True)`
   — bakes ssXX + rvrn into calt; frozen feature records get tag `DELT`.
4. `dlig2calt(outputPath)` — converts dlig ligatures to calt using the `LIG`
   spacer mechanism: leading chars of a ligature → `LIG` (blank, adv 600), the
   LAST char → a backward-drawing `.code` glyph (adv 600, negative lsb) that
   draws the whole ligature over the preceding cells.
5. `mergePowerlineFont(...)` (Nerd/Powerline glyphs)
6. reopen as `monoFont`; **OUR borrow/join/arrow/character/stylistic-set steps
   run here** (after dlig2calt, before final table fixes + save + ttfautohint).
7. OS/2/post/STAT fixes, line-height/char-spacing multipliers, fsSelection,
   save, `ttfautohint`.

Our scripts (all run on `monoFont` in step 6, config-driven):
- `scripts/borrow_glyphs.py` — graft Lilex outlines onto existing target glyphs.
  Weight-matches by measuring stroke (`_measure_stroke`, axis horizontal/vertical,
  slant-aware de-slant), `_match_source_weight`. Supports single-glyph
  (center align), multi-glyph compose (leftedge align), and `align="preserve"`
  (copy native position, for backward-drawing single glyphs like `|>`). Skips
  when `max_stroke_mismatch` exceeded → native fallback. Helpers used elsewhere:
  `_measure_stroke`, `_match_source_weight`, `CELL`.
- `scripts/join_dashes.py` — connects hyphen runs. Imports Lilex
  `hyphen_start/middle/end.seq` (weight-matched, sheared), re-cuts `---`
  (hyphen_hyphen_hyphen.code) to a joined bar, appends a hand-built `calt`
  chain lookup (otlLib) for runs ≥4. `--` left as native (2 dashes, like Lilex).
  Shared helpers: `_sheared`, `_add_glyph`, `_single_sub_lookup`. KEY: GSUB is
  edited by hand (append-only) — feaLib's `addOpenTypeFeatures` REWRITES `calt`
  and silently disables Recursive's existing ligatures (do NOT use it).
- `scripts/add_characters.py` — add brand-new cmap'd glyphs Recursive lacks
  (12 fancy single-char arrows uni21A9…uni21C6). Always added (no fallback) since
  no native glyph exists. Decomposes composites via DecomposingRecordingPen
  (in `_sheared`).
- `scripts/long_arrows.py` — Recursive-style infinite long arrows. Instances
  native Recursive at the instance's axisLocation, lowers its `>`/`<` arrowheads
  to the connected-dash shaft height, welds a shaft bar (CLOCKWISE winding so it
  unions with the arrowhead, not cancels), appends `calt` rules: `>` after a
  connected run → right cap; `<` before a connected run → left cap. Gated on
  join_dashes success (needs the shaft). Long arrows sit ~42u lower than native
  short arrows (accepted trade-off for infinite length).
- `scripts/add_stylistic_set.py` — adds a REAL toggleable OpenType stylistic set
  (off by default). Imports alternates, appends single-sub lookup + a
  FeatureRecord wired into every langsys + name-table UI name. Used for thin
  backslash (`ss03`). **NEEDS the escape-only contextual rewrite (pending task).**

KEY TECHNICAL LEARNINGS (do not relearn the hard way):
- feaLib `addOpenTypeFeatures` clobbers existing `calt` — always hand-edit GSUB
  (otlLib + otTables, append-only). After adding glyphs, call
  `font.getReverseGlyphMap(rebuild=True)` or compile/cmap KeyErrors on the new
  glyph names (stale cache).
- TrueType winding: outer contours CW (y-up). A CCW welded rectangle CANCELS
  overlap (non-zero winding → hole). Draw welded bars CW.
- Recursive geometry (Regular, mono casual): hyphen y260–340 (center ~300);
  dash seq pieces y265–347 (center ~306); native ARROW shaft y308–389
  (center ~348). So arrows sit higher than dashes by design — that's why long
  arrows (built on the dash shaft) sit lower than native short arrows.
- Recursive native arrow ligatures `->`,`-->`,`<-` are 2/3-cell glyphs; after
  dlig2calt they become `[LIG…, <name>.code]` backward-drawing (adv 600).
- HarfBuzz right→left propagation isn't possible in `calt`; right arrows can't be
  built by leftward propagation, which is why long arrows reuse the (already
  infinite, left→right-built) dash shaft and just cap it.
- Lilex weight axis is 100–400–700; Recursive 300–1000. Weight match is by stroke
  thickness, not axis number. Lilex tops out lighter than Recursive Bold/Black.
- Recursive has NO cv* features; ssXX exist (ss01–12, ss20). cv/ss for new
  features must use tags that don't collide (esp. in the VF where features stay
  live; in the static build, frozen ss03 becomes DELT so tag ss03 is reusable).

## Approach

### Static build — DONE (committed)
- `77499a6` curvy parens (Lilex cv13) — Borrowed Glyphs, light/med weights, native fallback at Bold/Black.
- `7d448e7` connected dashes (`---`+), infinite.
- `56eda23` connected bars `|>` `<|` (Lilex cv11), align=preserve.
- `5c5ec10` single-char arrows: 10 directional swapped to Lilex + 12 new added (NOTE: arrow SWAPS were later reverted; the 12 ADDED arrows remain).
- `31168e4` REVERT Lilex arrow shapes (back to native Recursive arrows) + thin backslash; deleted scripts/extend_arrows.py.
- `6b62a2f` restore thin backslash (opt-in ss03) — not a bug, needs explicit enable.
- `cb97b10` Recursive-style infinite long arrows (both directions), scripts/long_arrows.py.

Current state of arrows: native short (`->`,`-->`,`<-`,`→`,`←`, single-chars),
plus Recursive-style infinite long (`--->`,`<--`,`<---`,…,double-ended `<--->`).
Curvy parens + connected dashes + connected bars + 12 added arrows retained.
Thin backslash is opt-in `ss03` (currently thins ALL backslashes — WRONG, see task).

### Static build — REMAINING TASK: thin-backslash "escape-only"
User decision (b): thin `\` **only when it serves as an escape**, i.e. when the
backslash is FOLLOWED by an escape character, and NOT the 2nd of a consecutive
pair (`\\b` → thin, normal, b), and NOT a Windows drive path `:\` (don't thin
a backslash PRECEDED by `:`). This is a CUSTOM contextual rule (Lilex itself
just thins everything except 2nd-of-pair).

Rewrite `add_stylistic_set.py` (or specialize for backslash) to build a
contextual `calt`-style stylistic-set lookup with subtables tried in order:
1. ignore: backtrack `[colon]`, input `[backslash]` → no-op (skip `:\` paths).
2. ignore: backtrack `[backslash.<tag>]`, input `[backslash]` → no-op (consecutive 2nd stays normal).
3. sub: input `[backslash]`, lookahead `[escape-char set]` → substitute to thin.
Escape-char lookahead set (chars after `\`): letters `a b e f n r t v`, regex
`d D w W s S B`, hex/unicode `x u U N`, digits `0-9`, backslash, quotes `" '`.
IMPORTANT: resolve each escape char to its CURRENT glyph(s) — frozen features
(ss06 r→…, ss10 0→…, ss11 1→…) substitute some chars in `calt` BEFORE `ss03`
applies (ss03 is a later lookup), so include base + substituted glyph names in
the lookahead coverage (gather single-sub chains from `calt`).
This stays a real opt-in stylistic set (enable in ghostty `font-feature = ss03`).
Mac-only: in `add_stylistic_set`, the Windows name record (platformID 1) can be
dropped; keep (3,1,0x409).

### Task B — Variable font (NOT STARTED)
- User answers: **(1) full 5-axis VF**, **(2) Lilex tweaks strictly OPT-IN**,
  **(3) keep static build as-is; create a NEW VF source**.
- Foundation proven: partial-instancing Recursive (pin MONO/CASL/CRSV, keep
  wght+slnt) yields a clean VF with gvar + all features live. For full 5-axis,
  keep all axes (essentially rename + add features).
- HARD PART (de-risk with a spike FIRST): graft Lilex glyphs as VARIABLE
  (interpolating gvar across wght, sheared across slnt). Lilex is variable, so
  sample at matching weights and build deltas. Opt-in framing means DEFAULT is
  pristine variable Recursive (correct at all weights); enabling a feature
  (cvXX/ssXX/calt) gives the Lilex flavor (which can be light at heavy weights —
  acceptable since opt-in).
- Opt-in feature tags must NOT collide with Recursive's live ssXX/rvrn in the VF
  (unlike the static build, nothing is frozen). Pick free tags (e.g. cv01+).
- Lilex ARROW tweaks are DROPPED entirely (user prefers native Recursive arrows);
  the long-arrow fix becomes a DEFAULT (it just repairs broken arrows). Opt-in
  set = curvy parens, connected dashes, connected bars, thin backslash.
- Spike plan: (i) confirm opt-in stylistic set toggles in ghostty (RESOLVED — it
  works, just needs explicit enable), (ii) graft one variable Lilex glyph (a
  paren) into the partial VF with correct gvar interpolation, render at several
  weights. If good, build against a lean checklist (parallelize independent
  glyph families). No heavy plan doc beyond this file.

## Decision Log

- 2026-06-15 - human: Prefer Recursive native arrow shapes; revert Lilex arrow
  swaps but keep connected dashes + add Recursive-style long arrows. Impact:
  reverted (31168e4), added long_arrows.py (cb97b10).
- 2026-06-15 - human: Long arrows option (b) — infinite via connected-dash shaft +
  lowered Recursive arrowhead caps; accept slight height drop vs short arrows.
  Reason: simpler + truly infinite; purer. Impact: long_arrows.py implemented.
- 2026-06-15 - executor: feaLib clobbers calt; switched all GSUB edits to
  hand-built otlLib append-only. Welded bars must be CW or they cancel.
- 2026-06-15 - human: thin backslash = escape-only (option b), NOT Lilex's
  thin-everything. Plus: Mac-only (skip Windows name records ok); don't thin
  `:\` (drive paths). Impact: pending add_stylistic_set rewrite.
- 2026-06-15 - human: thin backslash was never broken — it's opt-in, needs
  `font-feature = ss03` enabled. Resolves Task B opt-in viability red flag.
- 2026-06-15 - human: Task B = full 5-axis VF, opt-in Lilex tweaks, new VF source
  alongside the static build.

## Execution Protocol

- Work `## Tasks` in order. Inspect `## Files` + `## Existing Patterns` before editing.
- All GSUB edits hand-built (otlLib/otTables), append-only; never feaLib on existing calt.
- After adding glyphs to a font, `font.getReverseGlyphMap(rebuild=True)`.
- Build to verify: `rm -rf fonts/RecursiveKG && venv/bin/python scripts/instantiate-code-fonts.py premade-configs/config.kg.yaml font-data/Recursive_VF_1.085.ttf`
- Verify shaping with uharfbuzz; verify visuals with Pillow renders to the temp dir.
- Commit each logical feature separately with a descriptive message. Do NOT install
  fonts or remove Pillow/uharfbuzz until the final cleanup task.
- Update `## Decision Log` on meaningful changes/blockers.

## Files

- `premade-configs/config.kg.yaml` — build config (Borrowed Glyphs, Join Dashes, Add Characters, Stylistic Sets, Features).
- `scripts/instantiate-code-fonts.py` — pipeline; calls our modules in step 6.
- `scripts/borrow_glyphs.py` — graft outlines (+ shared `_measure_stroke`, `_match_source_weight`, `CELL`).
- `scripts/join_dashes.py` — dash joining (+ shared `_sheared`, `_add_glyph`, `_single_sub_lookup`).
- `scripts/long_arrows.py` — Recursive-style infinite long arrows.
- `scripts/add_characters.py` — new cmap'd glyphs (fancy arrows).
- `scripts/add_stylistic_set.py` — opt-in stylistic sets (thin backslash). REWRITE for escape-only.
- `font-data/Lilex[wght].ttf`, `font-data/Lilex-OFL.txt` — vendored Lilex.
- (Task B) NEW VF build script + config — to be created.

## Tasks

### Static build (finish)
- [ ] Rewrite `add_stylistic_set.py` for escape-only contextual thin backslash:
      ordered subtables (ignore `:\`, ignore consecutive 2nd, sub on escape-char
      lookahead). Resolve escape chars to base+substituted glyphs. Drop Windows
      name record (Mac-only).
- [ ] Add config keys to the `Stylistic Sets` thin-backslash entry to drive it
      (escape set / flags), or hardcode a sensible default in the module.
- [ ] Build; shape-verify: `\n \t \r \b \0 \1 \\ \\b`, `C:\Users`, `:\`, lone `\`,
      `i<5`, all 8 instances compile. Render preview.
- [ ] Commit.
- [ ] FINAL: install (`make build` or copy fonts/RecursiveKG/*.ttf to ~/Library/Fonts);
      then `venv/bin/python -m pip uninstall -y Pillow uharfbuzz`.

### Task B (variable font) — only after static build done + user go
- [ ] Spike: graft ONE variable Lilex glyph (paren) into a partial-instanced
      Recursive VF (pin MONO/CASL/CRSV or keep all 5 axes) with correct gvar
      across wght (+ shear across slnt). Render at several weights. Confirm
      interpolation is clean.
- [ ] Decide opt-in feature tags (conflict-free: cv01+). Design DEFAULT=pristine.
- [ ] New VF build script + config (or extend existing). Variable seq/paren/bar
      glyphs (gvar). Long-arrow fix as default. Lilex arrow tweaks dropped.
- [ ] Build VF; verify axes + each opt-in feature toggles in ghostty; validate.
- [ ] Commit; package/install per user.

## Acceptance Criteria

### Static build
- [ ] `\n` etc. thin only with `ss03` on; `:\` and lone `\` stay normal; `\\b` →
      thin+normal+b; `i<5`/`a<b` unaffected.
- [ ] Short arrows native; long arrows (`--->`,`<--`,…any length, both dirs) clean.
- [ ] Curvy parens, connected dashes, connected bars, 12 added arrows intact.
- [ ] All 8 instances compile; monospacing preserved.

### Task B
- [ ] VF with all 5 axes; default render = pristine Recursive; each Lilex tweak is
      an opt-in feature that toggles in ghostty; glyphs interpolate across weight.

## Validation

- Build: `rm -rf fonts/RecursiveKG && venv/bin/python scripts/instantiate-code-fonts.py premade-configs/config.kg.yaml font-data/Recursive_VF_1.085.ttf`
- Shape (dev): `uharfbuzz` `hb.shape(font, buf, {"calt":True[, "ss03":True]})`, print `font.glyph_to_string(gid)`.
- Render (dev): Pillow `ImageFont.truetype` (libraqm applies calt) → PNG in temp dir → read it.
- Validity: open each `fonts/RecursiveKG/*.ttf`, `f['GSUB'].compile(f)` / `f['cmap'].compile(f)`.

## Risks

- Escape-char lookahead missing substituted forms (frozen ss06/ss10/ss11) → some
  escapes (`\r \0 \1`) won't thin. Mitigation: resolve single-sub chains into the
  lookahead coverage.
- `:\` heuristic only catches the drive-letter backslash, not later path
  separators (`\Users`). User accepted "or something like that".
- Task B variable-glyph grafting (gvar) is unproven — spike before committing.
- Black/heavy weights: Lilex too light → fallback (dashes/long arrows revert to
  native). Accepted.

## Open Questions

- Task B: exact axis set to expose names/defaults; opt-in feature tags per tweak;
  whether to also vary the borrowed glyphs or freeze them at a reference weight
  (spike will inform).
- Escape-char set final membership (does the user want regex classes / quotes
  thinned?). Start with the default set; refine on review.
