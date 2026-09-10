"""Q12 spike benchmark: Trafilatura vs readability-lxml on real BHS pages.

Measures token-level precision / recall / F1 of each extractor against the
manually-annotated ground-truth body text (``ground-truth/*.txt``), plus
per-file wall-clock speed. Deterministic: same input -> same output.
"""
import re
import time
from collections import Counter
from pathlib import Path

from lxml import html as lxml_html
from readability import Document
from trafilatura import bare_extraction

HERE = Path(__file__).parent
CORPUS = HERE / "corpus"
GT = HERE / "ground-truth"

PAGES = [
    "klix.ba-article",
    "nezavisne.com-article",
    "akta.ba-article",
    "oslobodjenje.ba-magazin",
    "ekupi.ba-product",
    "turizam.rs-property",
]

RUNS = 5  # speed averaged over N runs per page


def normalize(text: str) -> Counter[str]:
    """Lowercase, strip punctuation, whitespace-tokenize into a multiset."""
    low = text.lower()
    low = re.sub(r"[^\w\s]", " ", low, flags=re.UNICODE)
    toks = low.split()
    return Counter(toks)


def trafilatura_text(html: str) -> str:
    res = bare_extraction(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if not res or not getattr(res, "text", None):
        return ""
    return res.text


def readability_text(html: str) -> str:
    doc = Document(html)
    summary = doc.summary()
    if not summary:
        return ""
    return lxml_html.fromstring(summary).text_content()


def score(extracted: str, gt: str) -> tuple[float, float, float]:
    c_ext = normalize(extracted)
    c_gt = normalize(gt)
    if not c_ext or not c_gt:
        return (0.0, 0.0, 0.0)
    tp = sum((c_ext & c_gt).values())
    precision = tp / sum(c_ext.values())
    recall = tp / sum(c_gt.values())
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return (precision, recall, f1)


def run_one(html: str, fn) -> tuple[str, float]:
    t0 = time.perf_counter()
    text = fn(html)
    return text, time.perf_counter() - t0


def main() -> None:
    print(f"{'page':26} {'extractor':14} {'P':>6} {'R':>6} {'F1':>6} {'sec':>7}")
    print("-" * 70)
    totals = {"trafilatura": [], "readability": []}
    for slug in PAGES:
        html = (CORPUS / f"{slug}.html").read_text(encoding="utf-8")
        gt = (GT / f"{slug}.txt").read_text(encoding="utf-8")

        t_text, t_sec = run_one(html, trafilatura_text)
        r_text, r_sec = run_one(html, readability_text)
        for _ in range(RUNS - 1):
            run_one(html, trafilatura_text)
            run_one(html, readability_text)

        for label, text, sec in [("trafilatura", t_text, t_sec), ("readability", r_text, r_sec)]:
            p, rec, f1 = score(text, gt)
            totals[label].append((p, rec, f1, sec))
            print(f"{slug:26} {label:14} {p:6.3f} {rec:6.3f} {f1:6.3f} {sec:7.4f}")
        print()

    print("=" * 70)
    for label, rows in totals.items():
        avg_p = sum(r[0] for r in rows) / len(rows)
        avg_r = sum(r[1] for r in rows) / len(rows)
        avg_f1 = sum(r[2] for r in rows) / len(rows)
        avg_sec = sum(r[3] for r in rows) / len(rows)
        print(f"{label:14} avg P={avg_p:.3f} R={avg_r:.3f} F1={avg_f1:.3f} sec={avg_sec:.4f}")


if __name__ == "__main__":
    main()
