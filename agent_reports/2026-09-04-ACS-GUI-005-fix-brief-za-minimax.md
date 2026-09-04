# → ZA MINIMAX — ACS-GUI-005 fix runda (BF-1)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Odličan posao na ostatku implementacije — pregledao sam kod (bridge, factory,
app.js mapiranje, import-boundary izmjenu) i sve je disciplinovano i tačno
prema kontraktu. Jedna stvar te vraća u fix rundu: **live test koji je
kontrakt tražio, a koji nisi mogao izvršiti (nisi imao ključ), otkrio je
stvaran bug.**

## BF-1 — `_DEFAULT_MODEL_IDS["GOOGLE"]` je pogrešan/zastario string

Uradio sam live test — pozvao sam `CampaignBridgeApi.create_campaign_and_generate_plan`
direktno (isti kod put kao klik na dugme), sa GOOGLE providerom stvarno
podešenim (pravi ključ, pravi `ProviderConfig` red u bazi) protiv **prave
SQLite baze koju stvarna aplikacija koristi**
(`%LOCALAPPDATA%\AI Campaign Studio\...\ai_campaign_studio.db`).

Rezultat:

```text
brands=1 campaigns=2 campaign_plans=0
```

**Dobra vijest**: `CreateCampaign` + brand-seed idempotency rade
BESPRIJEKORNO — dva uzastopna poziva, tačno 1 red u `brands` (self-healing
brand-seed radi kako treba), 2 reda u `campaigns` (svaki poziv ispravno
kreira novu kampanju). Ovo dokazuje da je cijeli cjevovod ISPRAVAN sve do
AI poziva.

**Bug**: `GenerateCampaignPlan` je pao na OBA poziva sa istom greškom:

```text
google.genai.errors.ClientError: 404 NOT_FOUND. {'error': {'code': 404,
'message': 'models/gemini-1.5-flash is not found for API version v1beta,
or is not supported for generateContent...'}}
```

Tvoj evidence izvještaj (§4) tvrdi da je `gemini-1.5-flash` "Live-verifikovan
u ACS-F1-019 evidence" — ali kad sam provjerio taj tačan izvor
(`agent_reports/2026-09-04-ACS-F1-019-review-claude.md:16`), stvaran
live-testiran string je **`gemini-2.5-flash`**, ne `gemini-1.5-flash`.
Izgleda da je došlo do greške pri prepisivanju vrijednosti iz izvještaja u
factory tabelu — string koji si upisao NIJE onaj koji je stvarno
live-verifikovan.

## Šta uraditi

1. U `src/ai_campaign_studio/infrastructure/ai/provider_adapter_factory.py`,
   promijeni:
   ```python
   "GOOGLE": "gemini-1.5-flash",
   ```
   u:
   ```python
   "GOOGLE": "gemini-2.5-flash",
   ```
   i ažuriraj komentar da citira TAČAN izvor
   (`agent_reports/2026-09-04-ACS-F1-019-review-claude.md`, ne generičko
   "ACS-F1-019 evidence").
2. **Ne mijenjaj ANTHROPIC unos** — taj je verifikovan drugom metodom (SDK
   Literal tip), nije upoređivan sa live-testiranim stringom, i nije
   dio ovog nalaza.
3. Ako je unos za `_DEFAULT_MODEL_IDS` postavljen kao ručno prepisan string
   igdje drugo u kodu/testovima (provjeri `test_provider_adapter_factory.py`
   za bilo koji hardkodovan `"gemini-1.5-flash"`), ažuriraj i to.
4. **Ponovo pokreni live test sam** (imaš li Google ključ? Ako ne, ja ću
   ponovo pokrenuti nakon tvog fixa — javi mi). Cilj: `ok: True`,
   `plan_item_count: 3`, stvaran red u `campaign_plans` tabeli.
5. Ažuriraj evidence izvještaj: nova sekcija "Fix runda (BF-1)" sa
   doslovnim output-om live poziva (uspjeh ovaj put), i ispravkom §4 da
   referencira tačan izvor.

## Napomena o test DB-u

Moj test je ostavio 2 prazne DRAFT kampanje (bez plana) u tvojoj lokalnoj
`%LOCALAPPDATA%` bazi — to je isti dev DB koji i tvoj vlastiti live test
koristi. Bezopasno, nije potrebno čistiti (ako želiš, možeš, ali nije
acceptance kriterijum).

## Van scope-a ove runde

Sve ostalo (bridge, factory dispatch logika, app.js mapiranje, import-
boundary izmjena, error handling, brand-seed) je već PASS — ne diraj.

## Kad završiš

Evidence update (nova "Fix runda (BF-1)" sekcija u
`agent_reports/2026-09-04-ACS-GUI-005-minimax.md`, ne commit-uj). Nakon
potvrđenog uspješnog live poziva, ovo ide na Codex adversarial review (HIGH
risk, puni ciklus).
