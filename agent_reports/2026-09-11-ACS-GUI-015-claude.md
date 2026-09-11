# ACS-GUI-015 — dijagnostika "gotovo za par sekundi, ništa učitano"

**Datum:** 2026-09-11
**Agent:** Claude

## Uzrok (reprodukovan direktno)

Napravio sam skriptu koja testira nekoliko realnih ulaza kroz pravi bridge:

```
'example.com' (bez šeme)        → SUCCEEDED za 0.51s, fetched=0 candidates=0
'http://127.0.0.1:9/' (privatna)→ SUCCEEDED za 0.51s, fetched=0 candidates=0
'https://example.com/robots.txt'→ SUCCEEDED, 6 candidates (radi normalno)
'https://example.com/'          → SUCCEEDED, 6 candidates (radi normalno)
```

`DomainDiscovery.discover()` vraća PRAZAN tuple bez ijedne greške kad URL
nema šemu (`http://`/`https://`) ili je privatna/loopback adresa —
`IngestBrandSources` to izvještava kao **SUCCEEDED** (tehnički tačno — ništa
nije puklo), ali sa 0 rezultata i BEZ IKAKVE poruke. GUI je to prikazivao
kao potpuno prazan, tih završetak — otud utisak "ništa se ne dešava".

## Popravke

### 1. Backend dijagnostika (`ingest_brand_sources.py`) — bilo potpuno tiho

- `_discover()`: nova `_LOGGER.warning("zero_targets_discovered run=%s
  source_scope=%s", ...)` kad se registruje 0 target-a.
- `_fetch()`: nova `_LOGGER.warning("fetch_skipped_unsafe run=%s url=%s
  reason=%s", ...)` kad SSRF politika blokira DISKOVAN (ne seed) link —
  ranije se samo tiho mijenjalo stanje u bazi, ništa u logu.

### 2. Frontend — glavni fix (`app.js`, `startIngestion`)

- **Auto-dodavanje `https://`** kad korisnik unese URL bez šeme (npr.
  "example.com" → "https://example.com") — najvjerovatniji stvaran scenario
  (tipkanje adrese kao u browseru, bez razmišljanja o `https://` prefiksu).
- **Jasna poruka umjesto tihog "gotovo"**: kad job završi SUCCEEDED sa
  `progress_total==0` → "Nijedna stranica nije pronađena za taj URL —
  provjeri da li je adresa ispravna i dostupna (ne lokalna/privatna mreža)."
  Kad ima target-a ali 0 fetched-a → drugačija poruka o blokiranim/
  nedostupnim stranicama.
- **Odbrambeni try/catch oko CIJELE poll-callback funkcije** — ACS-GUI-014
  je otkrio da je JEDNA neuhvaćena greška u ovoj funkciji dovoljna da
  zamrzne dugme zauvijek bez ijedne vidljive poruke; sad SVAKA buduća
  slična greška završava kao toast, ne kao tiho zamrzavanje.

## Verifikacija

```
Backend log (ponovljen repro): "zero_targets_discovered run=... source_scope=('example.com',)"
                                "zero_targets_discovered run=... source_scope=('http://127.0.0.1:9/',)"
  → potvrđeno da se sada VIDI u logu, ranije ništa.

Frontend fix uživo (JS-stil poziv, "https://example.com" bez trailing /):
  fetched=2 extracted=6 candidates=6 → potvrđeno da auto-scheme rješava
  bare-domain slučaj kompletno (od GUI unosa do rezultata).

Novi Node-VM test (test_ingestion_scheme_autofix_and_zero_result_toast):
  input "example.com" → submitted urls=["https://example.com"]
  SUCCEEDED sa total=0 → toast sadrži "Nijedna stranica nije pronađena"

ruff/mypy: čisto
pytest (presentation_webview + ingestion): 376/376 PASS
pytest (puna regresija): 1547 passed, 0 failed, 438.05s
```

## Šta korisnik treba da zna

Ako opet vidiš "gotovo brzo, ništa učitano" NAKON ove izmjene — sad ćeš
dobiti konkretnu poruku zašto (nema stranica pronađenih / blokirane su),
umjesto tišine. Ako se to desi, provjeri i pošalji mi tačan URL koji si
unio — a sad postoji i log trag (`zero_targets_discovered` /
`fetch_skipped_unsafe`) koji mogu pregledati direktno.

## Kako testirati

```
cd "H:\AI Campaing Studio"
$env:PYTHONPATH = "H:\AI Campaing Studio\src"
.venv\Scripts\python.exe -m ai_campaign_studio.presentation_webview
```
Probaj i sa i bez `https://` prefiksa — oba bi trebala raditi isto.
