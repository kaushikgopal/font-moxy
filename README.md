# Moxy

```
   __  __   ___  __  __  __   __
  |  \/  | / _ \ \ \/ /  \ \ / /
  | |\/| || (_) | >  <    \ V /
  |_|  |_| \___/ /_/\_\    |_|
```

**Moxy** is a monospaced coding font. It's built on
[Recursive](https://www.recursive.design/) (Recursive Mono Casual) and folds in a
handful of code-friendly glyph tweaks borrowed from
[Lilex](https://github.com/mishamyrt/Lilex) — curvy parentheses, connected
dashes, connected bars, a thin "escape" backslash, extra arrow characters, and
Recursive-style long arrows.

Out of the box Moxy gives you the opinionated, customized look. If you ever want
plain Recursive back, it's one or two font-features away (variable font only — see
[What's different](#whats-different-from-recursive)).

## Install

**Homebrew (recommended):**

```bash
brew install --cask kaushikgopal/tools/font-moxy
```

> Upgrading from the old `font-recursive-kg` cask? Run
> `brew uninstall --cask font-recursive-kg` first, then install `font-moxy`.

**Manual:** download the latest `moxy-<version>.zip` from
[Releases](https://github.com/kaushikgopal/font-moxy/releases/latest), unzip, and
install the `.ttf` files (macOS: open them in Font Book).

The cask ships eight static styles — Regular, Italic, Semibold, Semibold Italic,
Bold, Bold Italic, Black, Black Italic.

### Use it

Set the family name to **`Moxy`** in your editor / terminal. In
[Ghostty](https://ghostty.org):

```ini
font-family = Moxy
```

Most editors enable contextual ligatures (`calt`) by default, which is what Moxy
uses for connected dashes, long arrows, and the rest. In VS Code, turn them on
with:

```jsonc
"editor.fontLigatures": true
```

## What's different from Recursive

Compared to stock Recursive Mono Casual, Moxy changes these by default:

| | Recursive | Moxy (default) |
|---|---|---|
| Parentheses `( )` | upright | curvier (Lilex cv13) |
| `---` / `----…` | separate dashes | one connected line |
| `\|>` `<\|` | bar + arrow | connected (Lilex cv11) |
| Escape `\` in `\n` `\t` … | normal weight | thinner (escape-only) |
| Long arrows `--->` `<---` `<-->` | break apart | connect at any length |
| `f r L Z 0 1` | Recursive default | simplified f/r, serifless L/Z, dotted 0, simplified 1 |
| Extra arrows (↩ ↪ ↰ ⇄ …) | absent | 12 added |

The **variable font** (see [CUSTOMIZING.md](CUSTOMIZING.md)) additionally lets you
dial these back toward Recursive with opt-in features:

- `lilx` — turn **off** the Lilex tweaks (parens, connected dashes/bars, thin
  backslash) and get Recursive's shapes back.
- `ss13` — "Alt. Recursive choices": restore Recursive's `f r L Z 0 1`.
- `ss03 / ss06 / ss08 / ss10 / ss11` — restore one letterform at a time.

Enabling `lilx` **and** `ss13` returns the (revertible) glyphs to pristine
Recursive. In Ghostty:

```ini
# plain Recursive look from the Moxy variable font
font-feature = lilx, ss13
```

> The added arrow characters and the long-arrow fix are additive and always on.
> These toggles live in the **variable font**; the static styles shipped via the
> cask are frozen to the look you see by default.

## Everything else is Recursive

Moxy inherits Recursive's design and its five variable axes
(Monospace, Casual, Weight, Slant, Cursive) in the variable font. For the full
story on Recursive, see [recursive.design](https://www.recursive.design/).

## Build / customize from source

Moxy is generated from the Recursive variable font plus a small set of scripts.
See **[CUSTOMIZING.md](CUSTOMIZING.md)** to build the static fonts, build the
variable font, tweak which features are baked in, or cut a release.

## Attribution & license

Moxy stands on the shoulders of two open-source typefaces — please keep their
notices when redistributing:

- **[Recursive](https://github.com/arrowtype/recursive)** by Arrow Type / Stephen
  Nixon — the base design and variable font (SIL Open Font License 1.1).
- **[Lilex](https://github.com/mishamyrt/Lilex)** by Mikhael Khrustik — the
  borrowed code glyphs (SIL Open Font License 1.1). The OFL text ships in the
  release as `Lilex-OFL.txt`.

Neither Recursive nor Lilex carries a Reserved Font Name, so the "Moxy" naming is
OFL-compliant. The build tooling in this repository is MIT licensed (see
[`LICENSE`](LICENSE)).

Issues with the build workflow → file them here. Issues with the underlying
shapes → upstream at [Recursive](https://github.com/arrowtype/recursive/issues)
or [Lilex](https://github.com/mishamyrt/Lilex/issues).
