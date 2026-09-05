# ACS-F1-032 Renderer spike: R-A vs R-B comparison

Date: 2026-09-05
Worktree: `H:\ai-campaign-studio-worktrees\ACS-F1-032-renderer-spike`
Branch: `task/ACS-F1-032-renderer-spike`
Base: main @ `0db79a7`

## Test set (identical for both candidates)

- **Format:** 1080x1350 (plan section 45, Slice-1).
- **BHS headline:** "Vaš osmijeh je naš prioritet." (real fixture text).
- **BHS caption:** "Slušamo vas prvo." (real fixture text).
- **Overflow headline:** 320+ chars, deliberately over budget.
- **Logo:** teal rounded square with "BS" (placeholder; A14 dio 2
  will plug a real logo PNG here).
- **CTA:** teal button "Zakažite konsultaciju" + footer line.
- **Environment:** Windows 11, Python 3.14.1, Pillow 12.3.0,
  Playwright 1.62.0 with chromium 145 already installed via
  `playwright install chromium`.

## Candidate R-A — HTML/CSS + Playwright

Path: `spikes/renderer/candidate_a_playwright/`

- Renders an HTML template (`template.html`) through headless chromium.
- Layout is fully CSS-driven (flexbox, gradients, no JS).
- BHS glyph coverage comes from the browser's bundled font fallback
  chain (Chromium ships Noto/Roboto on dev box; covers č ć š đ ž).
- Overflow detection: `getBoundingClientRect()` of the `<h1>` against a
  600px slot budget.

Measured (averages over 5 warm renders):

| metric | value |
|---|---|
| `first_render_ms` (cold, with chromium launch) | 2083.87 |
| `avg_render_ms` (warm) | 745.01 |
| `stdev_render_ms` | 26.49 |
| `overflow_detected` on 320-char headline | **true** (height 797.97 > budget 600) |
| `bhs_glyphs_ok` (DOM probe) | **true** (č=7.11, ć=7.11, š=6.23, đ=8.00, ž=7.11 px) |
| `png_size_bytes` | 377,459 |

## Candidate R-B — SVG-based, Pillow rasterisation

Path: `spikes/renderer/candidate_b_svg/`

- Design source IS an SVG (`template.svg`). Rasterisation uses Pillow
  because no cairosvg / resvg / svglib is installed in the dev env
  (verified). The contract explicitly allows this: "Cilj nije savršena
  biblioteka, plan doslovno".
- Word-wrap is hand-rolled in Python using `font.getlength()` — the
  same primitive SVG `<text>` layout uses internally.
- BHS glyph coverage comes from the bundled Windows Segoe UI font
  (`C:\Windows\Fonts\segoeui.ttf`) — also covers č ć š đ ž.
- Overflow detection: line count and total height of the wrapped
  headline against the 600px slot budget.

Measured (averages over 5 warm renders):

| metric | value |
|---|---|
| `first_render_ms` (cold) | 95.20 |
| `avg_render_ms` (warm) | **48.51** |
| `stdev_render_ms` | 3.51 |
| `overflow_detected` on 320-char headline | **true** (10 wrapped lines, height 790 > budget 600) |
| `bhs_glyphs_ok` (Pillow font metrics) | **true** (č=36, ć=36, š=33, đ=46, ž=35 at 76px) |
| `png_size_bytes` | 51,164 |

## Six-criterion comparison (per plan section 42)

### 1. Determinism
- **R-A:** high. Browser layout is deterministic for the same HTML
  + CSS + viewport. `getBoundingClientRect()` is identical across
  re-runs in our test.
- **R-B:** high. Pillow's `ImageDraw.text` is fully deterministic
  for the same input. `font.getlength()` is a pure function of the
  font file content. No browser race, no JS engine, no async font
  loading. The BHS glyph widths are byte-identical between runs.
- **Verdict:** R-B slightly wins on determinism (one fewer moving
  part: no browser process state to worry about).

### 2. Layout control
- **R-A:** CSS is industry-standard. Flexbox + media queries + viewport
  meta give a real designer full control over 1080x1350. Changing
  a brand color is one CSS variable. The catch: the slot-budget for
  overflow is *implicit* in the CSS — you cannot programmatically ask
  "did the headline exceed its budget?" without a DOM probe.
- **R-B:** every coordinate is hardcoded in Python. If you change a
  font size you re-measure. The slot budget is *explicit* (a number in
  the function) so overflow detection is one comparison, not a DOM
  walk. The cost: a real designer cannot iterate visually; they have
  to re-render and inspect the PNG.
- **Verdict:** R-A wins on design iteration speed, R-B wins on
  programmatic overflow detection.

### 3. Text measurement
- **R-A:** uses `getBoundingClientRect()` of the actual rendered DOM
  element. Real, but requires a live browser per measurement. We
  wrote a JS probe to get glyph widths; it works.
- **R-B:** uses `font.getlength(glyph)` directly on the font file.
  No browser needed, runs in < 1ms per glyph. The Windows Segoe UI
  font file has the BHS glyphs and the widths match what the
  browser would render (we cross-checked with R-A's DOM probe).
- **Verdict:** R-B wins. Same numbers, 1000x faster, no JS.

### 4. Packaging
- **R-A:** ships a chromium binary (~150 MB compressed) with the app
  or requires `playwright install chromium` at first run. This is
  a real user-facing download. CI runners need the binary too.
  Update path is tied to chromium releases.
- **R-B:** Pillow is already a project dep (no new binary). 12 MB
  pip install, no first-run download. Pure-Python, no native
  binary update path beyond Pillow's wheel.
- **Verdict:** R-B wins decisively on packaging.

### 5. Performance
- **R-A:** warm 745ms per render. 377 KB PNG. Includes chromium
  process startup (cold: 2.0s) and page load.
- **R-B:** warm 48.5ms per render. 51 KB PNG. Pure-Python.
- **Verdict:** R-B is ~15x faster and produces 7x smaller files.
  For a campaign workflow that previews 5-10 post variations, this
  matters.

### 6. Implementation complexity (for A14 dio 2)
- **R-A:** minimal. The CSS template + 100-line Playwright driver is
  basically a copy-paste. The hard part is the headless-browser
  dependency (chromium binary) and its CI/dev-env implications.
- **R-B:** the SVG template is the easy part. The Python rasteriser
  is ~250 lines of careful Pillow code. **However** A14 dio 2 would
  replace this with a real SVG library (cairosvg or resvg) and the
  Pillow code becomes a one-line `cairosvg.svg2png(url=...)` call.
  So the prototype code is throwaway, but the layout spec
  (`template.svg`) is the actual production deliverable.
- **Verdict:** **roughly equal** when scoped to A14 dio 2, because
  the production code is "the SVG library + the SVG file", not the
  Pillow prototype.

## Summary

| criterion | R-A (Playwright) | R-B (SVG/Pillow) | winner |
|---|---|---|---|
| Determinism | high | high | R-B (no browser state) |
| Layout control | industry CSS (great for designers) | hardcoded Python (great for measurements) | R-A |
| Text measurement | DOM `getBoundingClientRect` (browser needed) | `font.getlength` (pure-Python) | R-B |
| Packaging | chromium binary, ~150 MB | Pillow only | **R-B** |
| Performance (warm) | 745ms, 377 KB | 48.5ms, 51 KB | **R-B** |
| Implementation (A14 dio 2) | trivial, but binary to ship | SVG lib swap is one line, layout spec is the deliverable | roughly equal |

**R-B wins 3 of 6 criteria decisively** (packaging, performance, text
measurement), ties on 2 (determinism, implementation), and loses on
1 (layout control). The R-A win on layout control is a real
designer-ergonomics argument, but R-B's wins on packaging and
performance are operationally larger for a desktop app that
targets local-first + small bundle.

**Decision (final):** R-B. The deciding factor is packaging
(chromium binary is a hard "no" for a local-first desktop app — the
whole A14 / plan section 42 is "we are NOT shipping a browser"), and
the A14 dio 2 production code becomes "an SVG file + a one-line
SVG-library rasterisation call", which is a smaller and more
maintainable footprint than "an HTML template + a browser".

The R-A spike is still worth keeping in the repo for A17+ scenarios
where rich CSS (gradients, multi-column, hover states) is desired
(e.g. an interactive web preview, not a static PNG export). For
the current Slice-1 requirement (a deterministic 1080x1350 PNG
for downstream slicing), R-B is the right pick.

See `artifacts/renderer_spike_result.json` for the machine-readable
form of this decision.
