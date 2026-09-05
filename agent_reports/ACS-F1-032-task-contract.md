---
task_id: ACS-F1-032
phase: Faza-1 (post A13) — A14 dio 1, RENDERER SPIKE (plan sekcija 42)
title: "Renderer spike: R-A (HTML/CSS + Playwright) vs R-B (SVG-based) — poređenje i odluka"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - spikes/renderer/
  - artifacts/renderer_spike_result.json
  - pyproject.toml
forbidden_paths:
  - src/
  - tests/
  - resources/migrations/
  - application/
  - domain/
  - ports/
  - infrastructure/
notes_on_paths: >
  `pyproject.toml` je dozvoljen SAMO za dvije stvari: (1) dodavanje
  `[tool.ruff] extend-exclude = ["spikes"]` (ili ekvivalentna sekcijska
  varijanta) da throwaway spike kod ne zagađuje `ruff check .` na
  postojećem kodu; (2) SPIKE-ONLY zavisnosti (`playwright`, i šta god R-B
  zahtijeva — npr. `pillow`/`cairosvg`/drugo) idu u NOVU opcionu grupu
  `[project.optional-dependencies] renderer-spike = [...]`, NIKAD u
  glavni `dependencies` niz — pobjednički kandidat dobija pravu,
  trajnu zavisnost tek u BUDUĆEM A14 dio 2 tasku (produkcijski renderer),
  nakon što je odluka stvarno donesena. Gubitnički kandidat se NE dodaje
  u `pyproject.toml` uopšte ako implementer unaprijed zna njegovu
  zavisnost neće pobijediti — ali odluka dolazi TEK na kraju, pa je
  privremeno prisustvo obje zavisnosti u `renderer-spike` grupi tokom
  rada očekivano i u redu.
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Čisto izolovan, throwaway spike kod van `src/` — ne dira postojeći
    application/domain/ports/infrastructure kod niti ijedan postojeći
    potpis. GitNexus impact provjera nepotrebna.
---

# Kontekst

A13 je potpuno gotov u kodu (plan sekcije 39-41, ACS-F1-029/030/031).
Sljedeći komad prije `G10 Vertical Slice PASS` je A14 (renderer) —
plan sekcija 42 EKSPLICITNO zabranjuje pisanje produkcijskog renderera
prije ovog spike-a ("Ne implementirati production renderer prije
spike-a"). Ovo NIJE običan application-layer task — nema ports/domain
izmjene, izlaz nije "testovi prolaze" nego STRUKTURISANA ODLUKA
(`artifacts/renderer_spike_result.json`) potkrijepljena stvarno
izgrađenim i uporeñenim kodom za oba kandidata.

Human Owner je eksplicitno odabrao **pun spike, oba kandidata** (nasuprot
skraćivanju kao kod G9/UI framework gate-a, gdje je pywebview odabran bez
punog PySide6 poređenja) — ovaj task MORA stvarno izgraditi i uporediti
R-A i R-B, ne samo argumentovati za jedan.

**Namjerno van scope-a ovog taska** (postaje A14 dio 2, poslije odluke):
`ports/rendering.py` (`RenderRequest`/`RenderResult`/`RendererPort`, plan
sekcija 43), `infrastructure/rendering/selected_renderer.py`,
`application/rendering/render_post.py`. Plan sekcija 42 eksplicitno kaže:
"Tek nakon odluke kreirati infrastructure/rendering/selected_renderer.py."

# Objective

Izgraditi i uporediti dva throwaway kandidata pod `spikes/renderer/`,
svaki protiv ISTOG test seta (isti headline tekst, isti format), i
proizvesti `artifacts/renderer_spike_result.json` sa poljima tačno po
planu: `candidate`, `render_success`, `overflow_detection`,
`bhs_glyphs_ok`, `avg_render_ms`, `memory_notes`, `packaging_notes`,
`implementation_notes`, `decision`.

## Test set (isti za oba kandidata)

- **Format**: `1080x1350` (plan sekcija 45, obavezan Slice-1 format).
- **BHS glyph test**: headline/caption tekst koji sadrži STVARNE č/ć/š/đ/ž
  karaktere — reuse tekst iz `resources/fixtures/brightsmile.json`
  (već sadrži BHS dijakritike, potvrđeno) umjesto izmišljanja novog teksta.
- **Overflow test**: NAMJERNO predugačak headline (npr. 150+ karaktera) da
  se provjeri kako svaki kandidat detektuje/prijavljuje da tekst ne staje
  — ovo je preteča `LAYOUT_VALIDATION_ERROR` koncepta iz plan sekcije 44
  (taj mehanizam SAM po sebi nije u scope-u ovog taska, samo dokaz da
  kandidat MOŽE detektovati overflow deterministički).
- **Logo/slika placeholder**: jednostavan test asset (može biti generisan
  programski, npr. jednobojan PNG) da se dokaže da kandidat može
  kompozicionisati sliku + tekst, ne samo čist tekst.

## Kandidat R-A — HTML/CSS + Playwright

`spikes/renderer/candidate_a_playwright/` — HTML/CSS template renderovan
preko Playwright headless browsera u PNG screenshot. Testirati SVIH 10
stavki iz plan sekcije 42: font loading, deterministic viewport, text
measurement, PNG screenshot, 1080x1350, BHS glyphs, overflow, startup
time, persistent browser (da li se browser instance može ponovo
koristiti za više renderovanja bez restart troška), crash/cancel
(šta se desi ako render "zaglavi" ili baci grešku — da li ostaje
zombie proces).

## Kandidat R-B — SVG-based

`spikes/renderer/candidate_b_svg/` — generisan SVG (tekst + oblici),
rasterizovan u PNG preko BILO KOJE najjednostavnije dostupne biblioteke
(implementer bira — browser headless render SVG-a, Pillow sa
ImageDraw+font metrikom, cairosvg, resvg, itd. — "Cilj nije savršena
biblioteka", plan doslovno). Isti test set kao R-A.

## Poređenje (6 kriterijuma iz plana)

Za SVAKI kandidat, konkretna bilješka (ne apstraktna ocjena) za:
`determinism`, `layout control`, `text measurement`, `packaging`,
`performance`, `implementation complexity`. Ovo ide u
`spikes/renderer/COMPARISON.md` (slobodan format, tabela ili prozu),
NE u finalni JSON (JSON nosi samo pobjednikove izmjerene vrijednosti +
`decision` polje sa kratkim obrazloženjem zašto je taj kandidat pobijedio
i šta je konkretno izgubio gubitnik).

# Implementation steps

1. `spikes/renderer/candidate_a_playwright/` — HTML/CSS template (statičan
   fajl ili string), skripta koja: pokreće Playwright (chromium headless),
   učitava template sa stvarnim BHS tekstom, snima PNG na `1080x1350`,
   mjeri render vrijeme (nekoliko uzastopnih poziva, prosjek), pokušava
   detektovati overflow (npr. mjerenjem stvarne visine renderovanog
   teksta preko `getBoundingClientRect()`/JS evaluacije protiv dostupnog
   slot prostora).
2. `spikes/renderer/candidate_b_svg/` — ekvivalentna skripta za SVG put.
3. `spikes/renderer/COMPARISON.md` — 6-kriterijumsko poređenje, konkretno,
   sa referencama na stvarne brojke/opažanja iz koraka 1-2 (ne
   generičko "oboje rade dobro").
4. `artifacts/renderer_spike_result.json` — finalan odluka-artifact.
5. `pyproject.toml` — `[tool.ruff] extend-exclude` za `spikes` (ili
   ekvivalent) + `renderer-spike` opciona zavisnost grupa (vidi
   `notes_on_paths` iznad).
6. Instalacija: `playwright install chromium` (ili odgovarajući browser)
   dokumentovano u evidence-u kao komanda koju je implementer pokrenuo
   (ovo skida stvaran browser binary — očekivano i odobreno za OVAJ
   task, ne generalna praksa).

# Acceptance

- [ ] Oba kandidata stvarno izgrađena i pokrenuta (ne samo jedan sa
      argumentacijom za drugi) — evidence sadrži stvaran output oba
      (screenshot putanje ili base64/opis, izmjerena vremena).
- [ ] BHS glyphs test: screenshot/output pokazuje č/ć/š/đ/ž ispravno
      renderovane (ne prazne kutije/mojibake) za OBA kandidata, ili
      eksplicitno dokumentovano da jedan kandidat NE prikazuje ih
      ispravno (to je legitiman nalaz, ne blocker).
- [ ] Overflow test: oba kandidata daju NEKI deterministički signal da
      predug tekst ne staje (ne tiho odsijecanje bez signala).
- [ ] `avg_render_ms` izmjeren za oba (nekoliko uzastopnih render poziva,
      ne jedan hladan start).
- [ ] `spikes/renderer/COMPARISON.md` postoji, pokriva svih 6 kriterijuma
      za oba kandidata konkretno.
- [ ] `artifacts/renderer_spike_result.json` postoji, sadrži TAČNO polja
      iz plan sekcije 42 (`candidate`, `render_success`,
      `overflow_detection`, `bhs_glyphs_ok`, `avg_render_ms`,
      `memory_notes`, `packaging_notes`, `implementation_notes`,
      `decision`), validan JSON.
- [ ] `infrastructure/rendering/selected_renderer.py`,
      `ports/rendering.py`, `application/rendering/` NISU KREIRANI (git
      diff dokaz — to je sljedeći task, poslije ove odluke).
- [ ] `src/`, `tests/`, `application/`, `domain/`, `ports/`,
      `infrastructure/`, `resources/migrations/` NISU DIRANI.
- [ ] `pyproject.toml` izmjena SAMO ruff-exclude + `renderer-spike`
      opciona grupa — glavni `dependencies` niz NEDIRAN.
- [ ] `python -m pytest tests -q` (POSTOJEĆI suite) prolazi nepromijenjen
      — spike ne smije slomiti ništa postojeće.
- [ ] `python -m ruff check .` prolazi (uz novi exclude za `spikes/`).
- [ ] `python -m mypy src` prolazi (spike kod je van `src/`, mypy ga i
      ne vidi — ovo samo potvrđuje da ništa u `src/` nije slučajno
      dirano).
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -m pytest tests -q
python -m ruff check .
python -m mypy src
python -c "import json; json.load(open('artifacts/renderer_spike_result.json'))"
```

Napomena implementeru: nema poznate/postojeće `test_renderer_spike.py`
provjere niti očekivanja da spike kod prolazi kroz `pytest` — ovo je
namjerno, spike živi van `src/`/`tests/` stabla po dizajnu (throwaway,
plan sekcija 42 folder konvencija).

# Review focus — Claude

- Oba kandidata STVARNO rade (pokrenuti evidence komande sam, ne
  vjerovati na riječ da je "renderovano" bez stvarnog fajla/dokaza);
- BHS glyph tvrdnja provjerena na stvarnom PNG-u (otvoriti sliku, ne
  samo čitati "radi" u tekstu);
- overflow detekcija je STVARNO deterministička (isti predug tekst
  daje isti signal pri ponovljenom pozivu), ne slučajna;
- `renderer_spike_result.json` polja tačno odgovaraju plan sekciji 42
  (imena polja, ne parafraze);
- `pyproject.toml` izmjena je STVARNO ograničena na ono što je
  dozvoljeno (ruff exclude + spike-only opciona grupa) — glavni
  `dependencies` niz i CI-relevantne sekcije netaknute;
- `infrastructure/rendering/`, `ports/rendering.py`,
  `application/rendering/` NISU pipnuti — ovo je STOP gate, ne
  sugestija.

# Rollback

MEDIUM risk (nova eksterna zavisnost — Playwright browser binary —
i netrivijalan obim), ali IZOLOVANO od produkcijskog koda (throwaway
spike, van `src/`). Brisanje `spikes/renderer/` i revert
`pyproject.toml` izmjene je potpun, bezopasan rollback ako se nešto
pokvari. §29: Claude-only review, PASS → odmah merge.

# Coordination

Nezavisan od svega trenutno otvorenog (ne dira `src/`/`tests/`).
Blokira budući task **A14 dio 2** (produkcijski renderer —
`ports/rendering.py` + `infrastructure/rendering/selected_renderer.py`
+ `application/rendering/render_post.py`) koji se piše TEK nakon što
Human Owner potvrdi odluku iz `artifacts/renderer_spike_result.json`.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-032-renderer-spike
Branch:   task/ACS-F1-032-renderer-spike
Base:     main @ 0db79a7
```
