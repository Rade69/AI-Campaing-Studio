# Q12 Decision — chosen library

## Decision: **Trafilatura** (>=1.6; benchmarked 2.2.0)

`MainContentExtractor` (S2-G4) uses **Trafilatura** as its extraction engine.
`readability-lxml` is dropped from the production plan (kept only as a
benchmark reference inside this spike).

## Rationale

1. **F1 margin exceeds the tie-breaker threshold.** On 6 real, structurally
   diverse BHS pages, Trafilatura averages **F1 0.978** vs readability-lxml
   **0.891** (~9.7% relative). The contract's tie-breaker (<5% F1 → smaller
   bundle wins) is not triggered; the F1 gap alone decides it.

2. **More robust on the two hard cases.** readability-lxml collapses on the
   two pages that actually stress content extraction:
   - `nezavisne.com`: readability precision 0.621 (pulled the "Nove vijesti",
     share and follow blocks into the body); Trafilatura 0.989.
   - `oslobodjenje.ba` long-form: readability recall 0.561 (kept ~half the
     body); Trafilatura 0.969.
   Trafilatura stays ≥0.94 F1 on every page; readability ranges 0.703–1.000.

3. **Speed parity.** ~0.077 s/file (Trafilatura) vs ~0.087 s/file
   (readability) — a wash; no reason to prefer readability for latency.

4. **Bundle-size cost accepted.** Trafilatura is the heavier dependency (base
   requires: `certifi`, `charset_normalizer`, `courlan`, `htmldate`,
   `justext`, `lxml`, `urllib3`; `htmldate`/`courlan` pull dateparser/babel/
   tld transitively). readability-lxml is lighter (`lxml`, `cssselect`,
   `chardet`). This is the one real downside, but the F1 gap is large enough
   that it does not change the decision — and the library is declared as an
   *optional* `extraction` extra, so it never weighs on installs that don't
   need content extraction.

## Config carried into production

Trafilatura is used in precision-favoring mode to keep boilerplate out of the
main content:

```python
bare_extraction(
    html,
    include_comments=False,
    include_tables=False,
    favor_precision=True,
)
```

`favor_precision=True` trades a little recall for materially fewer false
positives (nav/footer/ads) — the right bias for a fact-extraction pipeline
where a spurious chunk is worse than a missing sentence.
