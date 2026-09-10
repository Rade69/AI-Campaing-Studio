"""Generate ground-truth body text for each corpus page.

Manually-annotated main content: for each page I hand-pick the exact
container(s) that hold the article/product body and drop boilerplate (nav,
footer, ads, share widgets, related-article links). Output is written to
``ground-truth/<slug>.txt`` and then reviewed by eye before the benchmark
runs.
"""
import re
from pathlib import Path

from lxml import html

CORPUS = Path(__file__).parent / "corpus"
GT = Path(__file__).parent / "ground-truth"

AD_PATTERN = re.compile(r"googletag\.cmd\.push[^;]*;", re.S)
SCRIPT_PATTERN = re.compile(r"\b(function\s+\w+\(|document\.|window\.|\.addEventListener|fetch\(|setTimeout\(|if \().*", re.S)


def clean(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = s.replace("\u200b", "")
    s = AD_PATTERN.sub(" ", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def text_of(doc, selector: str) -> str:
    els = doc.cssselect(selector)
    if not els:
        raise ValueError(f"selector no match: {selector}")
    return clean(els[0].text_content())


def paragraphs_text(doc, indices: list[int]) -> str:
    ps = doc.cssselect("p")
    parts = [clean(ps[i].text_content()) for i in indices if i < len(ps)]
    return "\n\n".join(p for p in parts if p)


def build() -> None:
    klix = html.fromstring((CORPUS / "klix.ba-article.html").read_text(encoding="utf-8"))
    nez = html.fromstring((CORPUS / "nezavisne.com-article.html").read_text(encoding="utf-8"))
    akta = html.fromstring((CORPUS / "akta.ba-article.html").read_text(encoding="utf-8"))
    ekupi = html.fromstring((CORPUS / "ekupi.ba-product.html").read_text(encoding="utf-8"))
    turizam = html.fromstring((CORPUS / "turizam.rs-property.html").read_text(encoding="utf-8"))
    oslob = html.fromstring((CORPUS / "oslobodjenje.ba-magazin.html").read_text(encoding="utf-8"))

    gt = {
        "klix.ba-article": text_of(klix, "div[id=text]"),
        "nezavisne.com-article": text_of(nez, "[itemprop=articleBody]"),
        "akta.ba-article": text_of(akta, "div[id=PrintContent]"),
        "ekupi.ba-product": text_of(ekupi, "article"),
        "turizam.rs-property": text_of(turizam, "div[id*=content]"),
        "oslobodjenje.ba-magazin": paragraphs_text(oslob, list(range(1, 11))),
    }

    for slug, text in gt.items():
        out = GT / f"{slug}.txt"
        out.write_text(text + "\n", encoding="utf-8")
        print(f"{slug}: {len(text.split())} words")


if __name__ == "__main__":
    build()
