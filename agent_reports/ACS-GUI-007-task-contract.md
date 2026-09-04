---
task_id: ACS-GUI-007
phase: Faza-1 (post ACS-GUI-006)
title: "Podešavanja → AI provajderi: stvarno povezivanje (real KeyringSecretStore + ConfigureProvider preko bridge-a)"
risk: HIGH
coordinator: claude
implementer: minimax
reviewers: [claude, codex]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies:
  - ACS-GUI-005/006 (merged) — bridge composition pattern (CampaignBridgeApi, _build_bridge seam)
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_podesavanja_ssr.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - src/ai_campaign_studio/presentation_webview/screens/opis_kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/
  - src/ai_campaign_studio/presentation_webview/shell/
  - src/ai_campaign_studio/presentation_webview/static/app.css
  - docs/gui-v3/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije review-a. Novi bridge metod + nova
    `AppSettings(environment="production")` konstrukcija u
    `CampaignBridgeApi.__init__` je jedina izmjena van
    `presentation_webview/`/`presentation/` sloja — provjerena unaprijed
    da `settings.environment` ima TAČNO JEDNO mjesto upotrebe u cijelom
    kodu (`bootstrap.py:144`, bira secret store adapter), nema drugog
    ponašanja vezanog za tu vrijednost.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: b489a93
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Otkriveno tokom ACS-GUI-005 review-a (N2 napomena, koordinator): stvarna
GUI aplikacija UVIJEK konstruiše `AppSettings(environment="development")`
(nigdje u kodu se ne poziva sa `environment="production"`), što znači da
`create_bootstrap()` uvijek bira `EnvironmentSecretStore` — adapter koji
čita SAMO iz OS environment varijabli i eksplicitno je **read-only**
(`set_secret`/`delete_secret` bacaju `SecretStoreError`, po dizajnu —
"dev/test adapter"). Posljedica: `ConfigureProvider` use-case (već
postoji, već testiran, već korišten u ranijim live validacijama preko
ručnih skripti) **ne može stvarno persistovati API ključ kroz pravu
aplikaciju danas**. Podešavanja ekran (`screens/podesavanja/`) je i dalje
potpuno fixture-driven — svih 6 "Podesi" dugmadi su `data-action="toast"`
stub-ovi, nijedan ne zove stvaran kod.

**Ovo je praktičan blocker za bilo koju stvarnu upotrebu aplikacije** —
bez ovoga, jedini način da neko podesi provider je da ja ručno pokrenem
skriptu (kako sam radio za sve live validacije u A8/ACS-GUI-005). Human
Owner je eksplicitno odobrio ovo kao sljedeći prioritet, prije G10
evaluation harness-a.

**Obavezno pročitati prije koda**:

```text
docs/PYWEBVIEW_SECURITY.md (§3 direktno normativan — OVAJ put bridge
  PRIMA sirov API ključ string OD JS-a, prvi put da secret ide u tom
  smjeru kroz bridge, ne samo iz njega — pažljivo pročitati "Nijedna
  js_api metoda ne vraća API ključ... nazad u JS kontekst" i primijeniti
  isti duh na ULAZ, ne samo izlaz)
src/ai_campaign_studio/application/ai_provider/configure_provider.py
  (VEĆ POSTOJI, VEĆ TESTIRAN — samo ga pozvati iz bridge-a, ne mijenjati)
src/ai_campaign_studio/infrastructure/secrets/keyring_secret_store.py
  (VEĆ POSTOJI — nikad ne loguje `value`, samo `name`/exception class)
src/ai_campaign_studio/infrastructure/secrets/environment_secret_store.py
  (dev/test adapter, read-only po dizajnu — NE mijenjati, samo razumjeti
  zašto trenutno blokira)
src/ai_campaign_studio/config/settings.py (AppSettings.environment)
src/ai_campaign_studio/bootstrap.py (SAMO čitati, NE MIJENJATI —
  `_build_secret_store` na liniji ~144 je JEDINO mjesto gdje se
  `settings.environment` provjerava u cijelom kodu, potvrđeno grep-om)
src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  (postojeći `CampaignBridgeApi` — dodaješ NOVU metodu, ne novu klasu;
  isti "usko, svrsi-namijenjeno" pravilo per PYWEBVIEW_SECURITY §3 i
  dalje važi za SVAKU metodu pojedinačno, ne za klasu kao cjelinu)
src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py
  (trenutni fixture render — Provider.code je lowercase "openai" stil,
  STVARAN provider_code konvencija svugdje drugo je UPPERCASE "OPENAI" —
  vidi mapiranje ispod)
```

# Objective

1. Real `CampaignBridgeApi` može stvarno persistovati API ključ kroz OS
   keyring (ne kroz read-only dev adapter).
2. Nova bridge metoda `configure_provider(raw_payload: dict) -> dict`
   validira ulaz, zove postojeći `ConfigureProvider` use-case, vraća
   JSON-safe rezultat (NIKAD ne vraća sam ključ nazad u JS).
3. Podešavanja ekran: za 5 "jednostavnih" provajdera (OpenAI, Anthropic,
   Google, DeepSeek, OpenRouter — svi trebaju SAMO api_key, ne base_url),
   "Podesi" dugme otkriva input polje + "Sačuvaj" dugme koje stvarno zove
   bridge. **"OpenAI kompatibilan" (generic, treba i base_url + model)
   OSTAJE toast stub u ovom tasku** — eksplicitno van scope-a, ne
   improvizovati poseban formu za njega sada.

# Implementation steps

## 1. `AppSettings(environment="production")` — SAMO u bridge-u

U `CampaignBridgeApi.__init__`, dodaj **novi keyword-only test seam**,
simetričan postojećem `paths`:

```python
def __init__(
    self,
    *,
    paths: AppPaths | None = None,
    settings: AppSettings | None = None,
) -> None:
    if settings is None:
        settings = AppSettings(environment="production")
    self._bootstrap = create_bootstrap(settings=settings, paths=paths)
    ...
```

**NE MIJENJATI** `bootstrap.py`-ov `create_bootstrap()` default (i dalje
`AppSettings()` = "development" za SVE OSTALE pozivaoce — testovi,
skripte, budući `main.py`). Ovo je namjerna, uska izmjena SAMO za pravu
GUI app instancu — potvrđeno (vidi Kontekst) da `environment` nema drugo
ponašanje osim biranja secret store adaptera, pa je ovo bezbjedno.

Testovi koji instanciraju `CampaignBridgeApi` direktno (postojeći bridge
testovi) MORAJU sada eksplicitno proslijediti
`settings=AppSettings(environment="development")` (ili ekvivalentan fake)
da NE diraju pravi OS keyring tokom test run-a — provjeri SVE postojeće
pozive u `test_campaign_bridge_api.py` i ažuriraj ih; ako neki test
oslanja na default bez override-a, MORA eksplicitno proslijediti test
settings.

## 2. Nov DTO: `ProviderConfigResultUiModel`

U `presentation/ui_models.py`, isti stil kao `CampaignPlanResultUiModel`:

```python
@dataclass(frozen=True)
class ProviderConfigResultUiModel:
    ok: bool
    provider_code: str | None
    error_code: str | None
    error_message: str | None
```

**NEMA polja za API ključ** — ni u kom obliku, ni maskiranog/djelimičnog.

## 3. `PresentationFacade` Protocol — nova metoda

U `presentation/contracts.py`, dodaj TAČNO jednu novu metodu (isti
pattern kao `create_campaign_and_generate_plan` iz ACS-GUI-005):

```python
def configure_provider(
    self, raw_payload: dict[str, Any]
) -> ProviderConfigResultUiModel: ...
```

## 4. Bridge: `configure_provider` metoda

U `CampaignBridgeApi`:

```python
def configure_provider(self, raw_payload: dict) -> dict:
    """Persist a provider API key via ConfigureProvider (ACS-GUI-007).

    Boundary validation only -- JS payload is untrusted. NEVER returns
    the api_key (input OR echoed) in the result dict, and NEVER logs it.
    """
```

- Validacija: `raw_payload` mora biti `dict` sa `provider_code: str`
  (ne-prazan nakon `.strip()`) i `api_key: str` (ne-prazan nakon
  `.strip()`) — ako bilo šta fali/pogrešnog tipa/prazno, vrati
  `_ERROR_VALIDATION` PRIJE nego što dotakneš `ConfigureProvider`.
- Pozovi `ConfigureProvider(self._bootstrap.provider_registry,
  self._provider_config_repo, self._bootstrap.secret_store).execute(
  provider_code.strip().upper(), api_key.strip())` — SVI potrebni
  objekti VEĆ POSTOJE kao atributi na `self` (provjereno, nema nove
  composition wiring potrebne).
- Uhvati:
  - `RegistryError` (nepoznat provider_code) i `InvariantViolation`
    (provider ne zahtijeva ključ) → `_ERROR_VALIDATION`, poruka
    smije sadržati `provider_code` (nije tajna) ali NIKAD `api_key`.
  - Sve ostalo (npr. `SecretStoreError` iz keyring backend-a) →
    `_ERROR_INTERNAL` (postojeći kod), poruka SAMO
    `type(exc).__name__`, ne `str(exc)` (za razliku od validation
    grana — ovdje `str(exc)` MOŽE teoretski sadržati backend detalje
    koje ne želimo izlagati; provjeri da `SecretStoreError` poruke iz
    `keyring_secret_store.py` zaista nikad ne sadrže `value`, ali budi
    konzervativan ovdje i dalje).
- Uspjeh: `{"ok": True, "provider_code": <upper>, "error_code": None,
  "error_message": None}`.
- Nikad ne raise-uje u JS (isti catch-all pattern kao
  `create_campaign_and_generate_plan`).

## 5. Podešavanja ekran — real input forma za 5 provajdera

U `screens/podesavanja/__init__.py`:

- Dodaj mapiranje fixture `Provider.code` (lowercase) → stvaran
  UPPERCASE `provider_code`: `"openai"→"OPENAI"`, `"anthropic"→"ANTHROPIC"`,
  `"google"→"GOOGLE"`, `"deepseek"→"DEEPSEEK"`, `"openrouter"→"OPENROUTER"`.
  `"openai_compatible"` NEMA mapiranje — ostaje toast stub (provjeri
  `_provider_row` da grana na osnovu `p.code == "openai_compatible"`).
- Za 5 mapiranih provajdera, `_provider_row` sada renderuje:
  ```html
  <button data-action="provider-toggle" data-provider-code="OPENAI">Podesi</button>
  <div class="provider-input-row" id="provider-input-OPENAI" hidden>
    <input type="password" class="input" id="provider-key-OPENAI" placeholder="API ključ">
    <button data-action="provider-save" data-provider-code="OPENAI">Sačuvaj</button>
  </div>
  ```
  (tačan HTML/CSS klase po tvom nahođenju unutar postojećeg stila —
  NE dirati `app.css`, koristi postojeće `.input`/`.btn` klase.)
- `"openai_compatible"` red ostaje NEPROMIJENJEN (i dalje
  `data-action="toast"`).

## 6. `app.js` — novi handleri

- `data-action="provider-toggle"` — toggle `hidden` na odgovarajućem
  `provider-input-<CODE>` div-u (čist DOM toggle, bez mrežnog poziva,
  isti stil kao postojeći tab handler).
- `data-action="provider-save"` — pročitaj vrijednost iz
  `provider-key-<CODE>` input-a, pozovi
  `window.pywebview.api.configure_provider({provider_code, api_key})`,
  na uspjeh: prikaži toast, ISPRAZNI input polje (`value = ''`) i
  sakrij red nazad (`hidden = true`) — NIKAD ne ostavljaj upisan ključ
  vidljiv u DOM-u duže nego što mora. Na grešku: prikaži toast sa
  `error_message`, OSTAVI input vidljiv da korisnik pokuša ponovo (ali
  I DALJE isprazni polje — ne ostavljati pogrešan/djelimičan ključ u
  input-u nakon neuspjelog pokušaja).
- Dugme za "Sačuvaj" se disable-uje za vrijeme poziva (isti
  double-click zaštita pattern kao `save-and-plan` iz ACS-GUI-005).

# Šta NIJE u scope-u (eksplicitno)

- **"OpenAI kompatibilan" real wiring** — treba i `base_url` i `model_id`
  polja, drugačiji oblik forme, ostaje toast stub.
- **Real-time status refresh na Podešavanja ekranu** (npr. "Nije
  povezano" → "Povezano" odmah nakon uspješnog Sačuvaj-a bez reload-a) —
  ekran je i dalje statički pre-renderovan (`write_all_pages()` na
  startup), dinamičko osvježavanje jednog reda je veći UI inženjering
  problem. Za ovaj task, uspjeh se vidi kroz toast + činjenicu da
  sljedeći "Sačuvaj i napravi plan →" poziv STVARNO pronalazi ključ
  (provjerivo end-to-end testom, ne vizuelnim statusom na ovom ekranu).
- **`list_ai_providers()`/`get_provider_status()` real implementacija**
  (postoje na `PresentationFacade` Protocol iz P0, ali nemaju konkretnu
  implementaciju još) — van scope-a, GUI i dalje prikazuje fixture
  status labele.
- **Testiraj vezu / Učitaj modele / Izaberi model tok** iz callout teksta
  — potpuno budući task (model discovery/registration).

# Acceptance

- [ ] `CampaignBridgeApi.__init__` prima `settings` test seam,
      default u produkciji je `AppSettings(environment="production")`.
- [ ] `bootstrap.py` NIJE DIRAN — `create_bootstrap()` default ostaje
      "development" za sve ostale pozivaoce.
- [ ] Svi postojeći bridge testovi eksplicitno proslijede test
      `settings` (development) — ne diraju pravi OS keyring tokom
      test run-a.
- [ ] `configure_provider` validira payload PRIJE poziva
      `ConfigureProvider` — nepotpun/pogrešan tip → `VALIDATION_ERROR`.
- [ ] `configure_provider` NIKAD ne vraća `api_key` (ni sirov ni
      djelimičan/maskiran) u povratnom dict-u — test sa sentinel
      vrijednošću dokazuje (isti pattern kao
      `test_returned_dict_is_json_serializable_and_contains_no_secrets`
      iz ACS-GUI-005).
- [ ] `configure_provider` NIKAD ne loguje `api_key` — provjeri SVE
      `logger.exception`/`logger.*` pozive u novoj metodi.
- [ ] Uspješan poziv stvarno upisuje u OS keyring (LIVE test, ne samo
      mock) — vidi Verification.
- [ ] Nepoznat `provider_code` → `VALIDATION_ERROR`, ne pucanje.
- [ ] Podešavanja: 5 provajdera (ne "openai_compatible") imaju real
      input+Sačuvaj tok; "openai_compatible" ostaje toast stub.
- [ ] `app.js` novi handleri ne diraju postojeće (`tab`, `toast`,
      `save-and-plan`, `lang-pick`) — regresija provjerena.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`,
      `bootstrap.py`, `main.py`, `opis_kampanje/`, `plan_kampanje/`,
      `shell/`, `app.css` NISU DIRANI (git diff dokaz).
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `python -m pytest tests/architecture/test_import_boundaries.py -v`
      prolazi.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/presentation_webview/bridge/ tests/unit/presentation_webview/test_podesavanja_ssr.py tests/unit/presentation/ -v
python -m pytest tests -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m ruff check .
python -m mypy src
```

# Live funkcionalna provjera (obavezna, HIGH risk)

Implementer MORA:
1. Pokrenuti pravu aplikaciju, otvoriti Podešavanja, kliknuti "Podesi" na
   NEKI provider (npr. DeepSeek — ključ već poznat iz A8 live validacija,
   pitaj koordinatora da ga postavi u keyring pod TEST kredencijalima ako
   treba stvaran test bez trošenja pravog produkcijskog ključa — ili
   koristi bilo koji string za "uspješno upisano u keyring" provjeru,
   pravi API poziv nije potreban za OVAJ test, samo da se persistuje).
2. Nakon "Sačuvaj", direktno provjeriti OS keyring (`keyring.get_password`)
   da je vrijednost stvarno tamo.
3. Kliknuti "Sačuvaj i napravi plan →" na Opis kampanje i potvrditi da
   bridge sada pronalazi taj provider (ranije bi vratio
   `NO_PROVIDER_CONFIGURED`/`PROVIDER_KEY_MISSING`).

Bez ovoga se task ne smije proglasiti PASS-om.

# Review focus — Claude

- `settings` seam ne curi u `bootstrap.py` default;
- svi postojeći testovi ažurirani da NE diraju pravi keyring;
- `api_key` nikad ne prelazi nazad u JS niti u log;
- boundary validacija prije `ConfigureProvider` poziva;
- "openai_compatible" ostaje netaknut stub, nema improvizovane forme.

# Review focus — Codex (adversarial, HIGH risk pun ciklus)

- Da li BILO KOJI error path (uključujući neočekivane exception tipove)
  može procuriti `api_key` u povratnu vrijednost ili log?
- Da li JS input polje (`type="password"`) stvarno sprječava da se ključ
  vidi u DOM-u nakon uspješnog/neuspješnog Sačuvaj-a (provjeri da li se
  input STVARNO prazni u oba slučaja, ne samo na uspjeh)?
- Da li je moguće dvoklikom na "Sačuvaj" izazvati dva paralelna
  `ConfigureProvider` poziva za isti provider (race na
  `set_secret`/`save_provider_config`)?
- Da li `AppSettings(environment="production")` promjena ima BILO KAKAV
  drugi efekat osim secret store izbora (nezavisno provjeriti grep
  tvrdnju iz kontrakta, ne samo prihvatiti je)?

# Rollback

HIGH risk — prvi put da secret string ulazi u bridge OD JS-a (ne samo
izlazi iz njega), i prva stvarna keyring write putanja kroz GUI. Fix na
istoj branch bez proširenja scope-a. Pun review ciklus prije merge-a.

# Coordination

Nezavisno od bilo kojeg budućeg G10 rada (sljedeći task nakon ovog, po
Human Owner odluci 2026-09-04) — G10 ne zavisi od ovoga, ali logično
dolazi poslije jer bez podešenog providera G10 evaluation harness ne bi
imao šta da testira kroz pravu aplikaciju (može i dalje raditi direktno
protiv use-case-a/skripti, ali GUI-kroz-Podešavanja tok je prirodniji
redoslijed).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-007-provider-config
Branch:   task/ACS-GUI-007-provider-config
Base:     main @ b489a93
```
