---
task_id: ACS-GUI-010
phase: UX polish (UX_Evolution_Buffer_Later.md §4.2, P0/P1 tier)
title: "Kampanje lista: dodati kolonu 'Sljedeći korak'"
risk: LOW
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/__init__.py
  - tests/unit/presentation_webview/test_kampanje_ssr.py
forbidden_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Čisto fixture-driven SSR ekran, nula bridge poziva, nula
    postojećih pozivalaca van sopstvenog test fajla. Izolovano od
    ACS-GUI-008/009/HOTFIX-002 (drugi fajlovi u potpunosti).
---

# Kontekst

Iz nezavisnog UX pregleda (`AI_Campaign_Studio_UX_Evolution_Buffer_Later.md`,
2026-09-06, §4.2) -- jedina konkretna, odmah-izvodljiva dopuna za
Kampanje listu: kolona koja govori "šta korisnik sada treba uraditi",
ne samo "gdje se kampanja nalazi" (status).

`presentation_webview/screens/kampanje/__init__.py` je DANAS potpuno
fixture-driven (nema bridge poziva uopšte -- `Campaign` dataclass +
`DEFAULT_FIXTURE` sa 3 statična reda). Ovaj task ostaje na ISTOM nivou
(fixture-only) -- NE povezuje ekran sa stvarnim podacima (to je zaseban,
veći task, van scope-a ovdje).

Primjer iz UX dokumenta:

```text
KAMPANJA              STATUS       SLJEDEĆI KORAK        PLANIRANO
Proljetna kolekcija   U pripremi   Dovrši opis           6 objava
Lansiranje seruma     Planirano    Pregledaj sadržaj     8 objava
Novi web-sajt         Odobreno     Spremno za izvoz      5 objava
```

# Objective

1. `Campaign` dataclass (`kampanje/__init__.py`) dobija novo polje
   `next_step: str` (OBAVEZNO, ne opciono -- svaki red MORA imati
   sljedeći korak, nema "legacy" fallback slučaja za ovaj čisto-fixture
   ekran).
2. `DEFAULT_FIXTURE`-ova 3 postojeća reda dobijaju `next_step`
   vrijednosti koje odgovaraju njihovom `status_label`-u (razuman
   izbor, npr. "U pripremi" -> "Dovrši opis", "Planirano" -> "Pregledaj
   sadržaj", "Odobreno" -> "Spremno za izvoz" -- prati UX dokument
   ako se poklapa, implementer prilagođava ako ne).
3. `_campaign_row()` renderuje novu `<td>{next_step}</td>` kolonu,
   POZICIONIRANU između `Status` i `Planirano` (prati UX dokumentov
   predloženi redoslijed kolona).
4. `render_body()`-ov `<thead>` dobija novi `<th>Sljedeći korak</th>`
   na odgovarajućem mjestu.
5. HTML escaping (`html.escape`) za `next_step`, isti standard kao
   ostala polja.

# Implementation steps

1. Izmjene po Objective #1-5.
2. Test: SSR output sa `DEFAULT_FIXTURE` sadrži sve tri `next_step`
   vrijednosti, tačan redoslijed kolona u `<thead>`.
3. Test: XSS escape dokaz za `next_step` (isti obrazac kao postojeći
   escape testovi za druga polja u ovom fajlu, ako postoje -- ako ne
   postoje, napraviti jedan po analogiji sa
   `test_render_body_generate_content_button_escapes_campaign_id` iz
   `studio_sadrzaja` test fajla).

# Acceptance

- [ ] `Campaign.next_step: str` postoji, obavezno polje.
- [ ] Tabela prikazuje kolonu "Sljedeći korak" između Status i
      Planirano.
- [ ] `DEFAULT_FIXTURE` ima razumne `next_step` vrijednosti za sva 3
      reda.
- [ ] XSS escape dokazan testom.
- [ ] `python -m pytest tests/unit/presentation_webview/test_kampanje_ssr.py -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` (POSEBNO: `bridge/`,
      `static/app.js`, `studio_sadrzaja/`, `pregled_izvoz/` netaknuti).
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/presentation_webview/test_kampanje_ssr.py -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-GUI-010-kampanje-next-step
gh pr create --base main --title "ACS-GUI-010: Kampanje lista -- kolona Sljedeći korak"
gh pr checks
```

# Review focus -- Claude

- Nema slučajnog dodira `bridge/__init__.py`/`app.js`/`contracts.py`/
  `ui_models.py` (ta 4 fajla su trenutno pod aktivnim, konfliktnim
  radom ACS-GUI-008/009 -- ovaj task ih NE SMIJE dirati uopšte).
- `html.escape` STVARNO primijenjen na `next_step` (test dokaz sa
  `<script>` payload-om, ne samo tvrdnja).

# Rollback

LOW risk, potpuno izolovan fixture-only ekran. Trivijalno revertovati.

# Coordination

Nula zavisnosti, nula preklapanja sa ACS-GUI-008/009/HOTFIX-002 (drugi
fajlovi). Ovo je NAMJERNO malen, siguran task za paralelno zauzimanje
agenta dok se veći GUI-008/009 fix rundovi rješavaju -- NIJE dio
šireg UX redizajna (Studio sadržaja 3-kolonski layout iz istog UX
dokumenta EKSPLICITNO čeka dok se GUI-008/009/HOTFIX ne slegnu -- vidi
memoriju `reference_ux_evolution_buffer_later_2026-09-06`).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-010-kampanje-next-step
Branch:   task/ACS-GUI-010-kampanje-next-step
Base:     main @ 4f4be8d
```
