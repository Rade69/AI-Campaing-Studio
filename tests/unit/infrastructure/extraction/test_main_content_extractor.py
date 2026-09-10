"""Unit tests for MainContentExtractor (S2-G4)."""

from __future__ import annotations

import pytest

from ai_campaign_studio.infrastructure.extraction import MainContentExtractor

# A realistic BHS news article with nav/footer boilerplate that Trafilatura
# should strip.
ARTICLE_HTML = """<html>
<head><title>Naslov vijesti</title></head>
<body>
<nav>Naslovna Novosti Sport Kontakt</nav>
<article>
  <h1>Iran napao bazu SAD-a u Jordanu</h1>
  <p>Prema tim informacijama, američki jurišni avion A-10 Thunderbolt pogođen je
  i ostao je bez jednog krila.</p>
  <p>Napad je izveden na zračnu bazu Muwaffaq Salti u Jordanu.</p>
</article>
<footer>© 2026 Sva prava zadržana</footer>
</body>
</html>"""


def test_extract_returns_trafilatura_result_when_available(monkeypatch) -> None:
    extractor = MainContentExtractor()
    monkeypatch.setattr(
        extractor, "_extract_with_trafilatura", lambda html, url: "CLEAN TEXT"
    )
    assert extractor.extract("<html>x</html>") == "CLEAN TEXT"


def test_extract_falls_back_to_raw_text_when_trafilatura_returns_empty(
    monkeypatch,
) -> None:
    extractor = MainContentExtractor()
    monkeypatch.setattr(extractor, "_extract_with_trafilatura", lambda html, url: "")
    result = extractor.extract(
        "<html><body><p>Hello world</p><script>bad()</script></body></html>"
    )
    assert "Hello world" in result
    assert "bad()" not in result


def test_extract_falls_back_when_trafilatura_raises(monkeypatch) -> None:
    trafilatura = pytest.importorskip("trafilatura")

    def boom(*args, **kwargs) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(trafilatura, "bare_extraction", boom)
    result = MainContentExtractor().extract(
        "<html><body><p>Preživio sam</p></body></html>"
    )
    assert "Preživio" in result


def test_extract_empty_input_returns_empty() -> None:
    assert MainContentExtractor().extract("") == ""


def test_extract_never_raises_on_malformed_html() -> None:
    # Graceful fallback guarantee: any garbage must produce a str, not raise.
    result = MainContentExtractor().extract("<<<garbage")
    assert isinstance(result, str)


def test_extract_strips_boilerplate_with_real_trafilatura() -> None:
    pytest.importorskip("trafilatura")
    text = MainContentExtractor().extract(ARTICLE_HTML)
    assert "Muwaffaq Salti" in text
    assert "Kontakt" not in text
    assert "Sva prava zadržana" not in text
