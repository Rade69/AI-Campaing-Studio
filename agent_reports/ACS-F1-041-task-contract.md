---
task_id: ACS-F1-041
phase: CI fix follow-up (F5+F6 iz nezavisne ChatGPT provjere 2026-09-06)
title: "PillowRenderer: nedostajući bundle font mora dati RENDER_ERROR, ne tihi SUCCESS; dodati font u resource validation"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies: [ACS-F1-040]
allowed_paths:
  - src/ai_campaign_studio/infrastructure/rendering/selected_renderer.py
  - scripts/validate_resources.py
  - tests/unit/infrastructure/rendering/test_selected_renderer.py
  - tests/unit/scripts/test_validate_resources.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/application/
  - resources/fonts/
  - .github/workflows/ci.yml
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Izolovana izmjena unutar `PillowRenderer` (privatni `_load_font`
    helper + `render()` early-return grana) i jednog validacionog
    skripta. Javni potpis `PillowRenderer.render()` (`RenderRequest ->
    RenderResult`) se NE mijenja -- samo koji `RenderStatus` vraća u
    jednom NOVOM edge-case-u koji do sad nije mogao nastati (bundle
    font uvijek postoji nakon ACS-F1-040).
---

# Kontekst

Nezavisna ChatGPT provjera (2026-09-06) je potvrdila ACS-F1-040 fix
(bundle-ovan Noto Sans, CI zeleno), ali ispravno primijetila da je
ostatak namjere iz tog kontrakta ("fallback ostaje odbrambena mjera,
sad glasan preko `warnings.warn`") i dalje arhitektonski slab:

`PillowRenderer.render()` trenutno, čak i nakon ACS-F1-040, u slučaju
da bundle-ovani font fizički nedostaje ili je oštećen -- i dalje
vraća `RenderStatus.SUCCESS` (uz `warnings.warn`, koji se lako
izgubi -- pytest filter, log level, production `warnings` config).
Renderer tvrdi da je deterministički ("isti input -> isti PNG"), ali
ako font nedostaje, isti input daje DRUGAČIJI font -> drugačiji
wrapping -> drugačiji PNG, pod istim "SUCCESS" statusom kao normalan
render. To je ista klasa problema koju je UX istraživanje označilo
kao D10 ("nema fake success state-a") -- samo sad na nivou
render-status-a, ne GUI-ja.

Postojeći `render()` VEĆ ima obrazac za ovo (bad-format grana,
`selected_renderer.py` oko linije 412-424): upiše sentinel PNG,
vrati `RenderStatus.RENDER_ERROR` sa jasnom porukom. Font-missing
slučaj treba PRATITI ISTI obrazac, ne izmišljati nov.

Drugi nalaz iste provjere: `scripts/validate_resources.py` (provjerava
i18n/regional/platforms/providers/migracije) NEMA sekciju za fontove.
Nedostajući/oštećen bundle font bi se OTKRIO tek kad neko pokrene
renderer test -- treba biti otkriven ranije, eksplicitno, istim
mehanizmom kao ostali bundle-ovani resursi.

# Objective

## 1. `selected_renderer.py` -- font-missing postaje `RENDER_ERROR`

- `_load_font(weight)` NE smije više interno gutati `OSError` i tiho
  vraćati `ImageFont.load_default()`. Umjesto toga, neka i dalje
  postoji kao helper koji MOŽE raise-ovati (ili vraća
  `Font | None` / eksplicitan rezultat-tip -- implementer bira
  najčistiji oblik unutar postojećeg stila fajla), ali `PillowRenderer`
  taj neuspjeh mora PRESRESTI i pretvoriti u kontrolisan
  `RenderResult`.
- U `PillowRenderer.__init__`, font loading GREŠKA se ne smije
  progutati -- sačuvati je (npr. `self._font_load_error:
  str | None`).
- Na POČETKU `render()` (prije bilo kakvog crtanja, ISTI stil kao
  postojeća bad-format provjera): ako `self._font_load_error` nije
  `None`, upisati sentinel PNG (isti obrazac kao bad-format grana) i
  vratiti:
  ```python
  RenderResult(
      status=RenderStatus.RENDER_ERROR,
      output_path=str(out),
      warnings=(f"FONT_RESOURCE_MISSING: {self._font_load_error}",),
      render_ms=...,
  )
  ```
- `ImageFont.load_default()` fallback se POTPUNO UKLANJA iz
  produkcijske putanje -- render sa nedostajućim fontom se NIKAD ne
  smije "uspjeti" sa pogrešnim metrikama.
- Normalan slučaj (bundle font postoji, što je GARANTOVANO nakon
  ACS-F1-040 u svakom checkout-u) se ponaša IDENTIČNO kao danas --
  ovo je NOVA grana za NOV, do sad nemoguć edge-case, ne promjena
  postojećeg ponašanja.

## 2. `scripts/validate_resources.py` -- font resource validation

Dodati provjeru (isti stil kao postojeće i18n/regional/platform
provjere u istom fajlu):

- `resources/fonts/NotoSans-Regular.ttf` i
  `resources/fonts/NotoSans-Bold.ttf` STVARNO postoje na disku.
- Oba fajla se STVARNO mogu učitati preko
  `PIL.ImageFont.truetype(path, size=24)` bez izuzetka.
- Font STVARNO pokriva BHS Latin dijakritike -- provjeriti da
  `font.getlength(ch)` za `č ć š đ ž Č Ć Š Đ Ž` daje isti rezultat kao
  vizuelna provjera iz ACS-F1-040 evidence-a (implementer treba
  smisliti provjerljiviji test od samog `getlength` -- npr. renderovati
  svaki karakter u malu masku i provjeriti da maska nije prazna
  (`getmask(ch).getbbox() is not None`), što razlikuje stvaran glyph
  od `.notdef` praznog okvira pouzdanije nego sama širina).

# Implementation steps

1. `selected_renderer.py`: font-load greška postaje `RENDER_ERROR`
   (Objective #1).
2. Test: privremeno pokvariti/preimenovati putanju do fonta (monkeypatch
   `_FONT_PATH_BOLD`/`_FONT_PATH_REG` ili ekvivalent) i potvrditi da
   `render()` vraća `RenderStatus.RENDER_ERROR` sa
   `FONT_RESOURCE_MISSING` u `warnings`, PNG sentinel i dalje napisan
   (isti standard kao postojeći bad-format test).
3. Test: normalan slučaj (bundle font postoji) i dalje daje IDENTIČAN
   PNG kao prije ove izmjene -- regresija zabranjena (uporediti sa
   postojećim `test_render_is_deterministic_same_input_same_png`
   fixture-om ili sličnim).
4. `validate_resources.py`: dodati font sekciju (Objective #2).
5. Test za validator: privremeno ukloniti/pokvariti font fajl (u
   izolovanom tmp resource dir-u, NE u pravom `resources/fonts/`) i
   potvrditi da validator vrati exit code 1 sa jasnom porukom.

# Acceptance

- [ ] Font-missing/oštećen scenario u `PillowRenderer.render()` daje
      `RenderStatus.RENDER_ERROR` sa `FONT_RESOURCE_MISSING` porukom,
      NE `SUCCESS`.
- [ ] `ImageFont.load_default()` se više NE koristi u produkcijskoj
      render putanji.
- [ ] Normalan render (bundle font postoji) ostaje BAJT-IDENTIČAN
      prijašnjem ponašanju (regresija zabranjena).
- [ ] `validate_resources.py` provjerava postojanje + učitljivost +
      BHS glyph coverage za oba bundle-ovana font fajla.
- [ ] `python -m pytest tests/unit/infrastructure/rendering/
      tests/unit/scripts/test_validate_resources.py -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `python scripts/validate_resources.py` i dalje prolazi na
      trenutnom (ispravnom) stanju repoa.
- [ ] Nema izmjena van `allowed_paths` (POSEBNO: `resources/fonts/`
      SAMI fajlovi se ne diraju, samo se PROVJERAVAJU).
- [ ] **CI provjeren preko PR-a** (vidi Verification) -- ne samo
      lokalno (nauk iz ACS-F1-040 review-a: obična `git push` na task
      branch NE pokreće CI, `ci.yml` sluša samo
      `push:[main]`/`pull_request:[main]`).

# Verification

```bash
python -m pytest tests/unit/infrastructure/rendering/ tests/unit/scripts/test_validate_resources.py -v
python -m pytest -q
python -m ruff check .
python -m mypy src
python scripts/validate_resources.py

# CI provjera MORA ići preko PR-a, ne samog push-a:
git push -u origin task/ACS-F1-041-font-render-error
gh pr create --base main --title "ACS-F1-041: font RENDER_ERROR + validation" --body "..."
gh pr checks   # ili: gh run watch (nakon što se pull_request run pojavi)
```

# Review focus -- Claude

- Font-missing test STVARNO simulira nedostajući fajl (monkeypatch
  putanje ili privremeno preimenovanje u testu), ne samo mockuje
  povratnu vrijednost -- mora proći kroz STVARAN `ImageFont.truetype`
  `OSError` put.
- Normalan render slučaj STVARNO ostaje bajt-identičan (uporediti PNG
  bytes prije/poslije ove izmjene za isti fixture, ne samo "status je
  SUCCESS").
- `validate_resources.py`-ov font test STVARNO detektuje oštećen/
  nedostajući font (mutation-test: privremeno pokvariti font u
  izolovanom tmp dir-u tokom review-a, potvrditi crveni exit code, pa
  vratiti).
- CI na PR-u STVARNO zeleno (provjeriti preko `gh pr checks`/`gh run
  list`, ne vjerovati implementerovoj tvrdnji).

# Rollback

MEDIUM risk -- mijenja ponašanje POSTOJEĆEG, mergovanog renderer-a u
JEDNOM novom edge-case-u (font-missing), plus proširuje jedan
validacioni skript. Izolovano, lako se revertuje na istoj grani ako
review nađe regresiju u normalnom (font-postoji) slučaju.

# Coordination

Zavisi od ACS-F1-040 (mergovano) -- UNBLOCKED. Ne blokira ništa hitno
(font VEĆ postoji u svakom checkout-u nakon ACS-F1-040, ovo je
odbrambeno pojačanje, ne aktivan bug). Može čekati iza P1.5-G3 ako
korisnik da prioritet CSV Import-u.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-041-font-render-error
Branch:   task/ACS-F1-041-font-render-error
Base:     main @ 912e234
```
