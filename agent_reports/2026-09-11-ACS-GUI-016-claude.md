# ACS-GUI-016 — malformirani /sitemap.xml ubijao je cijelu diskaveriju

**Datum:** 2026-09-11
**Agent:** Claude
**Povod:** korisnik prijavio da `https://kingdomdoo.com/en/` ništa ne učita.

## Uzrok (reprodukovan direktno na prijavljenom URL-u)

```
WARNING ... discovery_failed url=https://kingdomdoo.com/en/
  error=malformed sitemap XML at 'https://kingdomdoo.com/sitemap.xml':
  syntax error: line 1, column 0
WARNING ... zero_targets_discovered run=... source_scope=('https://kingdomdoo.com/en/',)
```

`kingdomdoo.com/sitemap.xml` ne postoji, pa server vraća SVOJU početnu HTML
stranicu sa status kodom 200 (uobičajen fallback/SPA-routing obrazac) umjesto
404. `SitemapReader.list_entries()` ispravno baca `SitemapParseError` kad
sadržaj nije validan XML (po dizajnu — malformiran sitemap ≠ odsutan
sitemap). Problem: `DomainDiscovery.discover()` NIJE hvatao tu grešku ni na
jednom od dva mjesta gdje poziva `list_entries()` — greška je izlazila iz
CIJELE `discover()` funkcije neuhvaćena, i `IngestBrandSources._discover()`
je to tretirao kao potpuni neuspjeh za taj URL — GUBEĆI čak i seed URL
(`https://kingdomdoo.com/en/`) koji je već bio dodat u listu kandidata
NEKOLIKO LINIJA RANIJE, prije nego što je sitemap parsing pukao.

## Fix

`DomainDiscovery._safe_sitemap_entries()` — novi wrapper oko oba poziva
`self._sitemaps.list_entries(...)` (robots.txt-deklarisani sitemap-ovi I
konvencionalni `/sitemap.xml`). Hvata `SitemapParseError` specifično
(ne generic `Exception` — poštuje postojeći namjerni dizajn gdje
`SitemapReader` razlikuje "odsutan" od "malformiran"), loguje upozorenje,
vraća `()` — isto ponašanje kao za odsutan sitemap. Diskaverija nastavlja sa
seed URL-om i on-page linkovima.

## Mutation test

Test `test_discover_survives_sitemap_xml_that_is_actually_html` privremeno
pokvaren (uklonjen try/except) → PAO sa `SitemapParseError` (potvrđuje da
test stvarno hvata regresiju) → vraćen fix → PROLAZI.

## Verifikacija

```
Live re-provjera na TAČNOM prijavljenom URL-u:
  https://kingdomdoo.com/en/ → fetched=3 extracted=210 candidates=210 failed=0
  (prije fix-a: fetched=0 extracted=0 candidates=0)

python -m ruff check . : All checks passed
python -m mypy src     : Success, 218 fajlova
pytest (web_ingestion + ingestion): 182/182 PASS
pytest (puna regresija): 1547 passed, 1 failed (nepovezan, flaky DeepSeek
  test — treći različit nasumičan uzrok danas, potvrđuje nedeterminizam
  a ne regresiju)
```

## Kako testirati

Zatvori stari prozor i pokreni ponovo:
```
cd "H:\AI Campaing Studio"
$env:PYTHONPATH = "H:\AI Campaing Studio\src"
.venv\Scripts\python.exe -m ai_campaign_studio.presentation_webview
```
Probaj `https://kingdomdoo.com/en/` ponovo — trebalo bi da vrati ~210
kandidata.
