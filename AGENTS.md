# Moxy — agent notes

Moxy is built on Recursive + Lilex. The build INVERTS Recursive's feature
meanings, so **state the desired LOOK, never the feature tag** — "ss08" in
Recursive means *no-serif* L&Z, and Moxy had it default-on, so "apply ss08
for serif L&Z" is backwards. Say "I want serif L&Z" and let the agent map it.

## Requesting a default change

Three scopes — say which:
- **"default moxy"** = both `premade-configs/config.moxy-vf.yaml` AND
  `premade-configs/config.moxy.yaml`
- **"VF only"** = just the VF config
- **"static only"** = just `config.moxy.yaml` (what the homebrew cask ships)

## Glyph defaults — say the look, this is the action

| Glyph(s) | Desired look | Recursive feature | Moxy action (add to / remove from `Features:`) |
|---|---|---|---|
| g | single-story | `ss02` | add `ss02` |
| L, Z | serifed (Recursive default) | — | ensure `ss08` is NOT listed |
| L, Z | serifless | `ss08` | add `ss08` |
| f | simplified | `ss03` | add `ss03` |
| r | simplified | `ss06` | add `ss06` |
| 6, 9 | simplified | `ss09` | add `ss09` |
| 0 | dotted | `ss10` | add `ss10` |
| 1 | simplified | `ss11` | add `ss11` |
| a | single-story | `ss01` | add `ss01` |
| @ | simplified | `ss12` | add `ss12` |
| Q | fancy long-tail (titling) | `titl` | VF: add to `Extra Features:`; static: add to `Features:` |

To REVERT a Moxy default back to Recursive: remove the row from `Features:`.

Notes:
- `ss04` (simp i), `ss05` (simp l), `ss07` (italic diagonals) exist but are
  broken upstream (Recursive issue #4) — avoid unless confirmed fixed.
- `titl` is the only non-ssNN tag today; in the VF it gets its own revert
  toggle (NOT part of the `ss13` bundle). Other non-ssNN single-sub features
  would use the same `Extra Features:` path.
- In the VF, `ss13` = "revert ALL bundled ssNN at once." The bundle is
  whatever is listed in `Features:`. So adding/removing an ssNN there also
  adds/removes it from the ss13 revert.

## Axis defaults

- **VF default**: `Default Axis Location` in `config.moxy-vf.yaml`, and the
  matching `Named Instances` block (keep them in sync, or macOS CoreText
  snaps the default to Recursive's own named instance with the wrong name).
- **Static per-style**: the `Fonts:` block in `config.moxy.yaml`
  (Regular/Italic/Bold/Bold Italic each have their own CASL/wght/slnt/CRSV).

## Build & install

- `make build` — static fonts + install to `~/Library/Fonts`
- `make install-vf` — VF + install to `~/Library/Fonts`
- `make package` — cut a release (bump `Version:` in `config.moxy.yaml` first)

## Verifying after a change

Shape-check the built font with HarfBuzz to confirm a glyph's default and its
revert behave as intended (see the session anchored at `cff7ffb` for a worked
example). The pattern:

```python
import uharfbuzz as hb
from fontTools.ttLib import TTFont
font = TTFont(path)
face = hb.Face(hb.Blob.from_file_path(path))
hf = hb.Font(face)
def shape(t, feat=None):
    b = hb.Buffer(); b.add_utf8(t.encode()); b.guess_segment_properties()
    hb.shape(hf, b, feat or {})
    return [font.getGlyphName(g.codepoint) for g in b.glyph_infos]
# default vs +ss13 / +titl / +ssNN
```
