# ACS-F1-045 — Claude review (MEDIUM, §29 -- Claude-only)

PR: https://github.com/Rade69/AI-Campaing-Studio/pull/10
Evidence: `agent_reports/2026-09-07-ACS-F1-045-pi.md`
Implementer: Pi. Commit reviewed: `851ea54`.

## Verdict: PASS WITH ONE REQUIRED FIX (not merged yet)

Dio A (fact-grounded planning) je čist PASS -- nezavisno reprodukovan
end-to-end, sve tvrdnje iz evidence-a potvrđene. Dio B (claim_linter
contact-info) ima JEDAN stvaran, uzak, ali potvrđen false-negative gap
koji nije bio testiran -- tražim jednu jednorednu ispravku + jedan
regression test prije merge-a.

## Šta je nezavisno provjereno (van onoga što Pi već tvrdi)

### 1. End-to-end lanac (prompt → ID → matching) -- SVA 3 facta, ne samo 1

Pi-jev integration test dokazuje lanac za `fact-implants` (item[0]).
Napisao sam SOPSTVENI skript koji ide fixture → `LoadBrandFixture` →
`CreateCampaign` → `GenerateCampaignPlan` (fake AI vraća sva tri
`logical_fact_id`-a: `fact-implants`, `fact-team`, `fact-location`) →
`select_allowed_facts` na STVARNOJ `brightsmile.json` fixture. Rezultat:

```text
Cost of implants   | facts_needed=('fact-implants',) -> matched 1
Our team           | facts_needed=('fact-team',)     -> matched 1
Book consultation  | facts_needed=('fact-location',) -> matched 1
```

Sva tri facta se ispravno vežu preko `logical_fact_id`. Ovo je originalni
"web Claude" review-ov Nalaz 1 (0/7 pogodaka na fraze) sada END-TO-END
zatvoren za CIJEL katalog, ne samo jedan fact. **CONFIRMED.**

### 2. Svih 5 van-scope fajlova (6 poziva) + `run_system_b.py` -- STVARNO ažurirani

`grep -rn "GenerateCampaignPlan(" src tests` je vratio 11 poziva u 8
fajlova ukupno. Pročitao sam DIFF za svaki od 8 fajlova (ne samo grep
na finalnom stanju) i potvrdio da je SVAKI poziv minimalna,
jednoredna, aditivna izmjena koja umeće VEĆ POSTOJEĆU lokalnu
`fact_repo` varijablu (koju je taj fajl već imao za
`GenerateSocialPost`/drugu upotrebu) na tačnu poziciju u konstruktoru
-- nema kolateralnih izmjena, nema novih import-ova van onog što je
strogo potrebno. Provjereno fajl-po-fajl:

- `run_system_b.py` -- `fact_repo` je već bio FUNCTION PARAMETER
  (koristi ga `GenerateSocialPost` niže u istoj funkciji) -- čisto
  provlačenje kroz jedan dodatni poziv, nula novog wiring-a.
- `bridge/__init__.py` -- `fact_repo=self._fact_repo`, property već
  postoji (ACS-F1-046-era pattern).
- `test_export_campaign_integration.py` (2 poziva), `test_render_post_integration.py`,
  `test_generate_visual_system_integration.py`,
  `test_plan_post_layout_integration.py` -- svi imaju već-postojeću
  `fact_repo` lokalnu varijablu u istom test-setup bloku.

**CONFIRMED -- svih 5 fajlova + 6 poziva stvarno i ispravno ažurirano,
bez izuzetka, bez kolateralne štete.**

### 3. GitNexus detect-changes / impact -- Pi-jev nalaz REPRODUKOVAN nezavisno

Pi je prijavio da GitNexus indeks NE vidi test pozivaoce (impact je
pokazao samo 2 direktna importer-a umjesto stvarnih 7+ fajlova) i
tretirao to kao worktree-binding artefakt. Pokrenuo sam `impact` sa
`includeTests: true` iz GLAVNOG (pravilno indeksiranog) checkout-a, ne
iz worktree-a:

```text
GenerateCampaignPlan upstream, includeTests=true, maxDepth=2:
  d=1: bridge/__init__.py, run_system_b.py   (2 -- isto kao Pi)
  d=2: presentation_webview/__main__.py
```

I dalje NEMA nijednog test fajla, iako je `test_export_campaign_integration.py`
sam po sebi indeksiran kao `File` node (provjereno cypher upitom). Ovo
NIJE worktree-binding artefakt -- reprodukuje se i iz ispravno
indeksiranog glavnog checkout-a, sa `includeTests: true` eksplicitno
uključenim. **Zaključak: GitNexus upstream `impact`/`detect-changes` ne
može se koristiti kao jedini dokaz potpunosti za promjenu potpisa
konstruktora koja pogađa test fajlove -- ručni `grep` ostaje
autoritet za ovu klasu promjene, kako je Pi i uradio.** Ovo je nalaz o
ALATU, ne o Pi-jevom kodu -- upisujem u CURRENT_STATE kao poznato
ograničenje, ne kao blocker na ovom PR-u.

### 4. Puna nezavisna reprodukcija (u worktree-u, ne samo CI)

```text
PYTHONPATH=src python -m pytest -q        -> 1060 passed, 1 warning in 173.20s
PYTHONPATH=src python -m ruff check .     -> All checks passed!
PYTHONPATH=src python -m mypy src         -> Success: no issues found in 175 source files
```

Poklapa se sa Pi-jevim evidence-om i sa CI (PR #10, SUCCESS).

## Nalaz -- REQUIRED FIX prije merge-a

### F1 (MEDIUM, potvrđeno reprodukcijom) -- contact-info regex ima false-negative na goli neseparirani broj od 8-10 cifara

Lokacija: `resources/claim_rules/default_v1.yaml`, prvi
`contact_info_patterns` unos (telefon-pattern); primjenjuje se preko
`claim_linter._numeric_reason_code`.

Pattern `(?:\+\d{1,3}[\s\-\.]?)?\d{2,3}[\s\-\./]?\d{3}[\s\-\.]?\d{3,4}`
ima SVA tri separatora opcionalna, što znači da BILO KOJI kontinuirani
niz od 8 do 10 cifara -- bez razmaka, crtice, tačke ili kose crte --
zadovoljava minimalnu dužinu i biva pogrešno klasifikovan kao
"kontakt info", pa IZBJEGAVA `unsupported-number` iako nije telefon.
Reprodukovano uživo:

```text
'Imamo preko 12345678 zadovoljnih klijenata.' -> None (treba biti 'unsupported-number')
```

Ovo je NOVA rupa koju ovaj fix uvodi -- prije ACS-F1-045, SVAKI goli
broj (bez obzira na dužinu) je padao na generic `unsupported-number`
fallback. Sada AI-generisan tekst sa velikim brojem bez separatora
(broj klijenata, pregleda, pratilaca -- upravo onaj tip fabrikovane
tvrdnje koju cijeli fact-first sistem postoji da uhvati) može proći
nezapaženo. Nije testirano u dodatim testovima (jedini "goli broj"
regresioni test koristi "500", 3 cifre, ispod praga).

**Predložena ispravka (minimalna, verifikovana)**: ukloniti `?` poslije
PRVOG separator character-class-a (između prve i druge grupe cifara),
čineći BAR JEDAN separator obaveznim:

```text
staro: \d{2,3}[\s\-\./]?\d{3}[\s\-\.]?\d{3,4}
novo:  \d{2,3}[\s\-\./]\d{3}[\s\-\.]?\d{3,4}
```

Testirano protiv sva tri postojeća legitimna formata (i dalje prolaze)
i protiv 8/9/10-cifrenih golih nizova (sad ispravno NE prolaze):

```text
'065 123 456'        old=True  new=True   (i dalje radi)
'033/123-456'        old=True  new=True   (i dalje radi)
'+387 61 123 456'    old=True  new=True   (i dalje radi)
'12345678'           old=True  new=False  (ispravljeno)
'123456789'          old=True  new=False  (ispravljeno)
'1234567890'         old=True  new=False  (ispravljeno)
```

**Traženo od Pi**: primijeniti ovu jednu izmjenu u
`resources/claim_rules/default_v1.yaml` (ukloniti taj jedan `?`) +
dodati JEDAN regression test u `test_claim_linter.py` (goli 8-10-cifreni
niz bez separatora i dalje mora dati `unsupported-number`). Ništa
drugo van ovoga -- ostatak PR-a je PASS.

## Ostalo -- manje, ne-blokirajuće napomene

- `is_fact_usable` filtriranje u `GenerateCampaignPlan.execute()` nema
  namjenski test koji dokazuje da NE-APPROVED fact biva isključen iz
  prompt-a (svi testni fact-ovi su APPROVED). `is_fact_usable` je već
  zasebno testirana, postojeća policy funkcija (ACS-F1-001) i
  kompozicija je trivijalna (`tuple(f for f in facts if
  is_fact_usable(f))`) -- ne tražim dodatni test, samo bilježim.

## Sljedeći korak

Vraćam PR #10 Pi-ju za jednu ciljanu izmjenu (F1). Poslije fix-a:
ponoviti `pytest -q`/`ruff`/`mypy`, potvrditi CI zeleno, i ja
ponavljam SAMO regex-relevantni dio provjere (ne cijeli review) prije
merge-a. MEDIUM risk, Claude-only ostaje dovoljno -- nije potreban
Codex ni Human Owner approval za ovaj task.
