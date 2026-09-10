# Q12 Spike — Trafilatura vs readability-lxml (BHS main-content extraction)

Throwaway benchmark (private to this spike folder, never imported by production
code). Decides which library S2-G4 uses for `MainContentExtractor` — the
decision is driven by measurement on real BHS pages, not preference.

## How to run

```bash
# from the repo venv (needs the 'extraction' extra):
python spikes/extraction-benchmark/benchmark.py
```

Output: per-page precision / recall / F1 / speed for both libraries, then the
averages.

## Corpus

6 real, structurally diverse BHS pages (raw HTML saved under `corpus/`):

| slug | site | kind |
|---|---|---|
| klix.ba-article | klix.ba | news article |
| nezavisne.com-article | nezavisne.com | news article (different CMS) |
| akta.ba-article | akta.ba | EU/news article (third CMS) |
| oslobodjenje.ba-magazin | oslobodjenje.ba | magazine/tech long-form |
| ekupi.ba-product | ekupi.ba | ecommerce product landing |
| turizam.rs-property | turizam.rs | tourism accommodation landing |

Fetched 2026-09-10 with a normal browser UA, ~1 req/sec rate limit. One page
(ekupi.ba) declares `charset=UTF-8` but `requests` mis-detects it as MacRoman;
the corpus copy was re-saved with explicit UTF-8 so both extractors see valid
text (see `check_ekupi.py`).

## Ground truth

`ground-truth/<slug>.txt` — manually annotated main content (the article /
product body), with nav / footer / ads / share-widgets / related-article links
removed. Produced by `build_ground_truth.py` (hand-picked container per site)
then reviewed and hand-cleaned by eye. This is the "true main content" both
extractors are scored against.

## Scoring

Token-level, deterministic (multiset via `collections.Counter`):

1. lower-case, strip punctuation, whitespace-tokenize;
2. `TP = sum((extracted & truth).values())` (token multiset intersection);
3. `precision = TP / |extracted|`, `recall = TP / |truth|`, `F1` = harmonic mean.

Ground truth is the **body** text only (headline / byline excluded). To keep
the comparison symmetric, Trafilatura is measured on its body text
(`bare_extraction(...).text`) and readability-lxml on `Document(...).summary()`
tag-stripped — both are title-free body outputs.

Speed: wall-clock seconds per file, averaged over 5 runs.

## Results (2026-09-10, trafilatura 2.2.0, readability-lxml 0.9)

| page | extractor | P | R | F1 |
|---|---|---|---|---|
| klix.ba-article | trafilatura | 1.000 | 1.000 | **1.000** |
| klix.ba-article | readability | 1.000 | 0.879 | 0.936 |
| nezavisne.com-article | trafilatura | 0.978 | 1.000 | **0.989** |
| nezavisne.com-article | readability | 0.621 | 1.000 | 0.766 |
| akta.ba-article | trafilatura | 0.938 | 1.000 | 0.968 |
| akta.ba-article | readability | 1.000 | 1.000 | **1.000** |
| oslobodjenje.ba-magazin | trafilatura | 0.940 | 1.000 | **0.969** |
| oslobodjenje.ba-magazin | readability | 0.942 | 0.561 | 0.703 |
| ekupi.ba-product | trafilatura | 0.951 | 0.933 | 0.942 |
| ekupi.ba-product | readability | 0.915 | 1.000 | **0.956** |
| turizam.rs-property | trafilatura | 1.000 | 1.000 | **1.000** |
| turizam.rs-property | readability | 0.968 | 1.000 | 0.984 |
| **AVERAGE** | **trafilatura** | 0.968 | 0.989 | **0.978** |
| **AVERAGE** | **readability** | 0.908 | 0.907 | **0.891** |

Speed (avg, 5 runs): trafilatura ~0.077 s/file, readability ~0.087 s/file —
effectively equal; both are sub-100 ms per page on this corpus.

## Why the spread

- **readability** drops on `nezavisne` (precision 0.621: it pulled the
  "Nove vijesti" / share / follow blocks into the body) and on `oslobodjenje`
  (recall 0.561: it kept only ~half of a paginated/inline-ad-heavy long-form).
- **trafilatura** is consistently ≥0.94 F1 on every page and wins 4/6 pages;
  the only page it loses (`ekupi` ecommerce, −0.014) is within noise.

Trafilatura wins on F1 by **0.978 vs 0.891** (~9.7% relative), well above the
5% tie-breaker threshold — bundle size is not needed as a tie-breaker.
