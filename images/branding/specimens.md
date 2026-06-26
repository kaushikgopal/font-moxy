# Moxy branding specimens

Source of truth for the README images. Run `make images-branding` to regenerate
them **deterministically** from this file (same input + same fonts → same PNGs).

Format:

- Each `## <id> -> <output-path>` heading defines one image. `<id>` selects the
  renderer (`specimen`, `comparison`, or `opentype-features`); `<output-path>` is
  where the PNG is written.
- `- key: value` lines set parameters for that section.
- A fenced code block holds the specimen's code lines. Prefix a line with a color
  in brackets to tint it — one of: `text` (default), `muted`, `green`, `blue`,
  `peach`, `mauve`, `pink`. Moxy specimens use the full VF look (`calt`, `moxy`,
  `lilx`).
- A markdown table (`| label | sample |`) holds the comparison rows. The sample is
  drawn twice — once in Recursive, once in Moxy. Escape a literal pipe as `\|`.
- The OpenType feature table uses `{braces}` in the Active column to color the
  changed glyphs cyan.

## specimen -> images/specimen.png

- wordmark: Moxy
- tagline: a monospaced | coding font

```
fn pipe(xs):  xs |> map(f) |> sum             # lilx connected  |>
[green]contiguous lines: --------------------        # show as a single line
[peach]route: -> --> ---> -----> <- <-- <--- <-----  # long arrows
[blue]\n \r \o \t   r'\[(?:[^][]|\\[\[\]]|(?R))*\]' # thin escape  \\
[blue]but not windows paths => "C:\dev\moxy"        #
ids:  0 1 f r L Z   <=  >=  ===  ->  =>       # letterforms
```

## comparison -> images/comparison.png

- title:

| feature | sample |
| --- | --- |
| parentheses | (sum) |
| long arrows | start --------> end |
| connected bars | \|>   <\| |
| dashes | ---------- |
| escape  \ | "\n\t C:\dev" |
| letterforms | f r L Z 0 1 |
| extra arrows | ↩ ↪ ↰ ⇄ |

## opentype-features -> images/branding/opentype-features.png

- title: Moxy |> OpenType Features

| tag | description | default | active | active features | style | default features |
| --- | --- | --- | --- | --- | --- | --- |
| calt | Code ligatures | => && === | {=> && ===} | calt | mono | -calt |
| lilx | Lilex borrowings | (\|>) ---- "\n" | {(\|>) ---- "\n"} | lilx | mono |  |
| ss01 | Single-story 'a' | JavaScript | Jav{a}Script | ss01 | mono |  |
| ss02 | Single-story 'g' | Regex | Re{g}ex | ss02 | mono |  |
| ss03 | Recursive 'f' | justify-self | justi{f}y-self | ss03 | mono |  |
| ss04 | Simplified 'i' | function | funct{i}on | ss04 | mono |  |
| ss05 | Simplified 'l' | null | nu{ll} | ss05 | mono |  |
| ss06 | Recursive 'r' | Browser | Browse{r} | ss06 | mono |  |
| ss07 | Italic diagonals | kwxyz kwxyz | kwxyz {kwxyz} | ss07 | italic |  |
| ss08 | Recursive 'L' & 'Z' | nonZeroLib | non{Z}ero{L}ib | ss08 | mono |  |
| ss09 | Simplified six & nine | 6 ⁶ ₆ 9 ⁹ ₉ | {6 ⁶ ₆ 9 ⁹ ₉} | ss09 | mono |  |
| ss10 | Recursive zero | 0x30 | {0}x3{0} | ss10 | mono |  |
| ss11 | Recursive one | #123 | #{1}23 | ss11 | mono |  |
| ss12 | Simplified mono 'at' | @font-face | {@}font-face | ss12 | mono |  |
| ss13 | Recursive bundle | f r L Z 0 1 | {f r L Z 0 1} | ss13 | mono |  |
