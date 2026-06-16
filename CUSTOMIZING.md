# Customizing & building Moxy

Moxy is generated from the Recursive variable font (`font-data/Recursive_VF_1.085.ttf`)
plus a set of scripts that graft in the Lilex tweaks. There are two artifacts:

- **Static fonts** (`fonts/Moxy-Static/`) — 8 frozen styles, built by
  `scripts/instantiate-code-fonts.py` from `premade-configs/config.moxy.yaml`.
  **This is what the homebrew cask ships.** The look is frozen per the config; there
  are no runtime toggles.
- **Variable font** (`fonts/Moxy-VF/`) — one 5-axis file built by
  `scripts/build-variable-font.py`. This is the canonical Moxy: it defaults to the
  Moxy look and exposes the `lilx` / `ss13` / `ssNN` reverts. Install it yourself if
  you want the toggles; it is not part of the cask.

> **Static vs variable, plainly:** the shipped static font has the Moxy look baked
> in with **no** way back to Recursive. The variable font has the same default look
> **plus** the revert toggles. (Generating the static styles directly from the
> variable font is a possible future step; today they're built independently.)

## Setup

Requires Python 3.11 and a checkout of this repo.

```bash
# one time
pyenv local 3.11.8                 # or otherwise use Python 3.11
python -m venv venv                # virtual environment named "venv"
source venv/bin/activate
pip install -r requirements.txt
```

`make setup` runs the equivalent steps.

## Build the static fonts (what ships)

```bash
make build      # builds fonts/Moxy-Static/ and installs to ~/Library/Fonts (macOS)
```

or directly:

```bash
venv/bin/python scripts/instantiate-code-fonts.py \
    premade-configs/config.moxy.yaml font-data/Recursive_VF_1.085.ttf
```

This produces `Moxy-{Regular,Italic,Semibold,SemiboldItalic,Bold,BoldItalic,Black,BlackItalic}-<fontver>.ttf`.

## Build the variable font (the canonical Moxy, with toggles)

```bash
make build-vf   # builds fonts/Moxy-VF/Moxy[MONO,CASL,wght,slnt,CRSV].ttf
```

or directly:

```bash
venv/bin/python scripts/build-variable-font.py
```

Install that `.ttf` manually to use the toggles. In Ghostty:

```ini
font-family = Moxy
# default = Moxy look; to get plain Recursive:
# font-feature = lilx, ss13
```

How the variable font is wired (see `scripts/vf_invert.py` for the details):

- The customized "Moxy" look is the **default** — curvy parens and the added arrows
  live in the `cmap`; connected dashes/bars, the thin escape backslash, the
  simplified letterforms, Recursive's own code ligatures, and the long-arrow fix all
  live in a default-on `calt` feature.
- The feature tags are **reverts**: `lilx` undoes the Lilex tweaks, `ss13`
  ("Alt. Recursive choices") undoes the five letterforms, and `ss03/06/08/10/11`
  undo one letter each. The 12 added arrows and the long-arrow fix are always on.
- Letterform reverts are tuned to the canonical `MONO=1` (Mono) default; reverting at
  `MONO=0` (Sans) restores the mono letter shapes.

## Tweak which features are baked into the static fonts

Edit `premade-configs/config.moxy.yaml`. It controls the family name, the eight
axis instances, line-height / spacing, and which features are frozen on:

- **Borrowed Glyphs / Join Dashes / Add Characters / Stylistic Sets** — the Lilex
  tweaks grafted in (curvy parens, connected dashes/bars, thin backslash, added
  arrows).
- **Features** (`ss03 ss06 ss08 ss10 ss11`) — Recursive's own stylistic sets frozen
  into the static output. Remove an entry to keep Recursive's plain form for that
  glyph instead; add others (see the comments in the file) to bake them on.

To experiment, duplicate the config with a new `Family Name` and point the build
script at it:

```bash
venv/bin/python scripts/instantiate-code-fonts.py premade-configs/<your-config>.yaml
```

## Cut a release

`make package` (or the `update-moxy` skill) builds the static set, zips it (with the
Lilex OFL notice + LICENSE), creates a GitHub release on `kaushikgopal/font-moxy`,
and updates the homebrew cask `font-moxy.rb`. The release version comes from
`Version:` in `config.moxy.yaml`.

## Updating to a new version of Recursive

1. Drop the latest `Recursive_VF_1.0xx.ttf` into `font-data/` and delete the old one.
2. Rebuild (`make build`, `make build-vf`).
3. Re-run the variable-font verification — the `ss13` revert reuses Recursive's own
   lookup indices, so confirm them after an upstream bump.

## Syncing with upstream Recursive tooling

This project began as a fork of
[arrowtype/recursive-code-config](https://github.com/arrowtype/recursive-code-config).
To pull in upstream build-tooling changes:

```bash
git remote add upstream https://github.com/arrowtype/recursive-code-config.git
git fetch upstream
git pull upstream main
```

## Notes

- `Pillow` and `uharfbuzz` are used only for dev-time rendering/shaping checks and
  are intentionally **not** in `requirements.txt`. Install them ad hoc
  (`venv/bin/python -m pip install Pillow uharfbuzz`) when verifying, then remove.
- The variable font carries all five Recursive axes (Monospace, Casual, Weight,
  Slant, Cursive); its default instance is Mono Casual Regular so the bare font is a
  usable terminal monospace.
