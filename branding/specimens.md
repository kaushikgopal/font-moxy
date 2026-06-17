# Moxy branding specimens

Source of truth for the README images. Run `make images-branding` to regenerate
them **deterministically** from this file (same input + same fonts → same PNGs).

Format:

- Each `## <id> -> <output-path>` heading defines one image. `<id>` selects the
  renderer (`specimen` or `comparison`); `<output-path>` is where the PNG is written.
- `- key: value` lines set parameters for that section.
- A fenced code block holds the specimen's code lines. Prefix a line with a color
  in brackets to tint it — one of: `text` (default), `muted`, `green`, `blue`,
  `peach`, `mauve`, `pink`. Lines are rendered verbatim (ligatures via `calt`).
- A markdown table (`| label | sample |`) holds the comparison rows. The sample is
  drawn twice — once in Recursive, once in Moxy. Escape a literal pipe as `\|`.

## specimen -> images/specimen.png

- wordmark: Moxy
- tagline: a monospaced | coding font

```
fn pipe(xs):  xs |> map(f) |> sum             # connected  |>
[green]contiguous lines: --------------------        # show as a single line
[peach]route: -> --> ---> -----> <- <-- <--- <-----  # long arrows
[blue]\n \r \o \t   r'\[(?:[^][]|\\[\[\]]|(?R))*\]' # thin escape  \\
[blue]but not windows paths => "C:\dev\moxy"        #
ids:  0 1 f r L Z   <=  >=  ===  ->  =>       # letterforms
```

## comparison -> images/comparison.png

- title: What's different from Recursive

| feature | sample |
| --- | --- |
| parentheses | (sum) |
| long arrows | start --------> end |
| connected bars | \|>   <\| |
| dashes | ---------- |
| escape  \ | "\n\t C:\dev" |
| letterforms | f r L Z 0 1 |
| extra arrows | ↩ ↪ ↰ ⇄ |
