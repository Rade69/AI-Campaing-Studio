# Extraction benchmark spike (Q12)

Private, throwaway benchmark for the S2-G4 "Trafilatura vs readability-lxml"
decision. Not production code — `pyproject.toml` excludes `spikes/` from ruff.

## Files

- `benchmark.py` — runs both libraries on the corpus, prints P/R/F1/speed.
- `result.md` — full per-page results + methodology.
- `chosen.md` — final decision + rationale (Trafilatura).
- `build_ground_truth.py` — regenerates `ground-truth/*.txt` (manual annotation).
- `fetch_corpus.py` — provenance of `corpus/*.html` (rate-limited download).
- `corpus/*.html` — raw HTML of 6 real BHS pages.
- `ground-truth/*.txt` — hand-annotated main content per page.

## Run

Both libraries are needed (trafilatura is the `extraction` extra; the loser
readability-lxml is a one-off spike dependency, not declared in the project):

```bash
pip install -e ".[extraction]" readability-lxml
python spikes/extraction-benchmark/benchmark.py
```

## Corpus provenance

Downloaded 2026-09-10 with a normal browser UA and ~1 req/sec rate limit. One
page (ekupi.ba) declares `charset=UTF-8` but `requests` mis-detects it as
MacRoman; its corpus copy was re-saved with explicit UTF-8 so both extractors
see valid text.
