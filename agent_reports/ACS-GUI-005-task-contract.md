---
task_id: ACS-GUI-005
phase: Faza-1 (post A8, post ACS-GUI-004)
title: "Prvi GUI→backend bridge: 'Sačuvaj i napravi plan' zove pravi CreateCampaign + GenerateCampaignPlan (pywebview js_api)"
risk: HIGH
coordinator: claude
implementer: minimax
reviewers: [claude, codex]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies:
  - ACS-GUI-001 (merged) — shell + Početna, presentation_webview/ entrypoint pattern
  - ACS-GUI-002 (merged) — screens fixture pattern
  - ACS-GUI-004 (merged) — tab/panel JS pattern u app.js
  - ACS-F1-016 (merged) — OpenAI adapter
  - ACS-F1-018 (merged) — Anthropic adapter
  - ACS-F1-019 (merged) — Google adapter
  - ACS-F1-017 (u review-u, DeepSeek/OpenRouter) — nije blocker, bridge radi i bez njega
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/
  - src/ai_campaign_studio/presentation_webview/__main__.py
  - src/ai_campaign_studio/presentation_webview/screens/opis_kampanje/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - src/ai_campaign_studio/infrastructure/ai/provider_adapter_factory.py
  - tests/unit/presentation_webview/bridge/
  - tests/unit/presentation_webview/test_opis_kampanje_ssr.py
  - tests/unit/infrastructure/ai/test_provider_adapter_factory.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
  - src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py
  - src/ai_campaign_studio/infrastructure/ai/google_adapter.py
  - src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py
  - src/ai_campaign_studio/infrastructure/database/
  - src/ai_campaign_studio/presentation_webview/shell/
  - src/ai_campaign_studio/presentation_webview/screens/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/_static_pages.py
  - src/ai_campaign_studio/presentation_webview/screens/pocetna/
  - src/ai_campaign_studio/presentation_webview/screens/brend/
  - src/ai_campaign_studio/presentation_webview/screens/kampanje/
  - src/ai_campaign_studio/presentation_webview/screens/kalendar/
  - src/ai_campaign_studio/presentation_webview/screens/podesavanja/
  - src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/
  - src/ai_campaign_studio/presentation_webview/static/app.css
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - docs/gui-v3/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    GitNexus MCP je bio nedostupan (server se rekonektuje) u trenutku pisanja
    ovog kontrakta. Koordinator MORA pokrenuti detect-changes/impact analizu
    prije nego što implementer krene na kod (ili odmah nakon prvog commit-a u
    worktree-u), i zalijepiti stvaran nalaz ovdje prije review-a. Dok se to
    ne uradi, ovaj task se NE SMIJE proglasiti PASS-om.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 73f52b1
  scope_fit: "PENDING — popuniti nakon što GitNexus MCP bude dostupan."
  unknowns:
    - "Ovo je PRVI konkretan pywebview js_api bridge u projektu — nema
      postojećeg impact grafa za presentation_webview/bridge/ jer folder
      ne postoji do ovog taska."
---

# Kontekst

Human Owner je 2026-09-04 eksplicitno odobrio promjenu prioriteta nakon
iskrene procjene stanja aplikacije: arhitektura i fact-grounding rade (live
dokazano protiv DeepSeek i Google Gemini API-ja, vidi
`agent_reports/2026-09-04-ACS-F1-017-pi.md` i
`agent_reports/2026-09-04-ACS-F1-019-*.md`), ali GUI (`docs/gui-v3` port u
`presentation_webview/`) i backend (domain/application/infrastructure) su
**potpuno nepovezani**. Svaki dugme u GUI-ju je ili `data-action="toast"`
stub ili statičan `<a href>` ka sljedećem fixture ekranu. Ovaj task je prvi
stvaran korak da se to promijeni: **jedan** dugme, **jedan** pravi tok
podataka, kraj-do-kraja, kroz pravu SQLite bazu i pravi AI provider poziv.

**Zašto HIGH, ne MEDIUM kao ACS-GUI-00x**: prethodni GUI taskovi su bili
izolovana prezentaciona površina (SSR fixture markup, nula backend
dodira). Ovaj task:
1. uvodi PRVI `js_api` bridge u projektu (nova, bezbjednosno-osjetljiva
   površina, `docs/PYWEBVIEW_SECURITY.md` §3 direktno primjenjiva);
2. prvi put piše u pravu SQLite bazu iz GUI klika (ne iz testa/skripte);
3. prvi put zove pravi eksterni AI provider iz GUI klika (mrežni poziv,
   trošak, latencija, greške van naše kontrole);
4. uvodi novi infrastructure fajl (`provider_adapter_factory.py`) koji
   bira i instancira jedan od 4 postojeća adaptera runtime-no.

Full ciklus po CLAUDE.md: Claude review pa Codex adversarial review pa
eksplicitno "odobravam" od Human Owner-a prije merge-a. §29 skraćeni put
NE VAŽI za ovaj task.

**Obavezno pročitati prije koda**:

```text
docs/PYWEBVIEW_SECURITY.md (cijeli — §3 js_api pravila su direktno
  normativna za ovaj task: uska bridge klasa, boundary validacija, nikad
  ne vraćati secret/token u JS, nikad proizvoljna putanja/komanda iz JS)
docs/gui-v3/INTEGRATION.md (bridge/ folder konvencija, "Campaign/Brand
  metode... dodavati tek kroz F1 task contracte")
src/ai_campaign_studio/presentation/contracts.py (postojeći P0.21
  PresentationFacade Protocol — VIDI "Šta NIJE u scope-u" ispod prije
  nego što pokušaš implementirati cijeli Protocol)
src/ai_campaign_studio/presentation/state.py, ui_models.py
src/ai_campaign_studio/bootstrap.py (SAMO pročitati/importovati,
  NE MIJENJATI — vidi ACS-GUI-001 kontrakt §"Zašto ne bootstrap.py/main.py":
  import create_bootstrap je dozvoljen, izmjena fajla nije)
src/ai_campaign_studio/presentation_webview/__main__.py (trenutni
  composition root — nema DB/UoW/repo wiring uopšte, samo render+window)
src/ai_campaign_studio/presentation_webview/screens/opis_kampanje/__init__.py
  (trenutni fixture render — "Sačuvaj i napravi plan →" je statičan <a href>)
src/ai_campaign_studio/presentation_webview/static/app.js (postojeći
  data-action dispatch pattern — toast, tab, ?campaign= handler)
src/ai_campaign_studio/application/campaigns/create_campaign.py
src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py
src/ai_campaign_studio/application/schemas/campaign_brief.py
  (CampaignBriefInput — boundary Pydantic validacija, VEĆ POSTOJI)
src/ai_campaign_studio/application/brands/load_brand_fixture.py
src/ai_campaign_studio/ports/repositories.py (BrandRepositoryPort NEMA
  get_brand/list_brands — vidi "Brand seeding" ispod, NE DODAVATI metode
  ovdje, taj fajl je forbidden)
src/ai_campaign_studio/ports/provider_config.py (ProviderConfigRepositoryPort,
  list_provider_configs — KAKO SE ZAISTA nalazi koji provider je podešen)
src/ai_campaign_studio/ports/ai.py (AIRequest/AIResponse/TextGenerationPort)
resources/fixtures/brightsmile.json (demo brend, isti kao svuda drugo u GUI-ju)
tests/integration/application/campaigns/test_generate_campaign_plan_integration.py
  (TAČAN pattern za real-repo wiring — repliciraj ga u bridge composition-u,
  ne izmišljaj novi)
resources/platforms/instagram.yaml, facebook.yaml, linkedin.yaml
  (channel/platform_code/format_code mapping — vidi tabelu ispod)
```

Pogledati (ne dirati, samo referenca za konstruktor signature):

```text
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py (__init__)
src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py (__init__)
src/ai_campaign_studio/infrastructure/ai/google_adapter.py (__init__)
src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py
  (build_deepseek_adapter, build_openrouter_adapter)
```

# Objective

Klik na "Sačuvaj i napravi plan →" na Opis kampanje ekranu:
1. čita stvarne vrijednosti iz forme (DOM, ne fixture);
2. zove novi `js_api` bridge metod koji stvarno izvršava
   `CreateCampaign.execute(...)` pa `GenerateCampaignPlan.execute(...)`
   protiv prave SQLite baze i pravog konfigurisanog AI providera;
3. prikazuje rezultat (uspjeh/greška) kroz postojeći toast mehanizam;
4. na uspjehu navigira na `../plan_kampanje/index.html?campaign=<id>`
   (taj ekran OSTAJE fixture-driven u ovom tasku — dinamičko renderovanje
   pravog plana je budući task, vidi "Šta NIJE u scope-u").

# Šta NIJE u scope-u (eksplicitno, da se ne improvizuje)

- **Plan kampanje ekran ne prikazuje pravi generisani plan.** Ostaje
  fixture kao danas. Real render je budući task (npr. ACS-GUI-006).
- **Ne implementirati cijeli `PresentationFacade` Protocol.** Bridge klasa
  koju izlažeš kroz `js_api=` NE MORA (i ne treba) da nasljeđuje/implementira
  svih 6 postojećih metoda (`set_app_locale`, `get_app_state`, itd.) — to je
  strukturalni `Protocol`, Python ga ne provjerava nominalno. Ti dodaješ
  TAČNO JEDNU novu metodu na sam `PresentationFacade` Protocol
  (`contracts.py`) kao dokumentacioni/budući ugovor, ali tvoja konkretna
  bridge klasa je samostalna, uska klasa (per PYWEBVIEW_SECURITY.md §3),
  ne pokušaj graditi punu konkretnu implementaciju Protocol-a "za svaki
  slučaj".
- **Ne dirati `ports/repositories.py`.** Nema `get_brand`/`list_brands`
  metode na `BrandRepositoryPort` — ne dodavati je. Brand seeding (ispod)
  rješava se lokalnim state fajlom, ne novim port metodom.
- **Ne graditi puni "Podešavanja → AI provajderi" GUI flow.** Provider
  mora već biti podešen preko postojeće `ConfigureProvider` skripte
  (ručno, van GUI-ja, isto kao što je koordinator radio za live
  validaciju) — ako nijedan nije podešen, bridge vraća jasnu grešku,
  ne pokušava sam da traži API ključ od korisnika.
- **Ne graditi model discovery/registration flow.** `AIProviderRegistry`
  nema unaprijed registrovane modele (provideri u `resources/ai_providers/`
  su metadata, ne model liste) — ovaj task koristi HARDKODOVANU
  provider→model_id tabelu (ispod), ne `resolve_default_text_model`.
- **Ne mijenjati `app.css`.** Dugme koristi postojeće `.btn`/`.btn.primary`
  klase; loading/disabled stanje (ako ga implementiraš) ide preko
  postojećeg `disabled` HTML atributa, ne nove CSS klase.

# Brand seeding (rješava nedostatak Brand-creation GUI-ja)

`CreateCampaign` traži `brand_id` + `brand_snapshot_id` koji već postoje u
bazi — GUI još nema ekran za kreiranje brenda. `BrandRepositoryPort` nema
metodu da se pita "da li brend već postoji" (samo `save_brand`/
`save_snapshot`/`get_snapshot`), i `map_brand_fixture` generiše NOV
`brand.id`/`snapshot.id` (`new_id()`) svaki put kad se pozove — pozivanje
`LoadBrandFixture` na svaki app start bi dupliciralo brend beskonačno.

**Rješenje** (isti idiom kao `_load_window_state`/`_save_window_state` u
`__main__.py`): u istom `_user_data_dir()`, novi fajl `brand-seed.json`
sa `{"brand_id": "...", "brand_snapshot_id": "..."}`.

- Na svaki bridge poziv (ili lijeno, prvi put kad zatreba): ako
  `brand-seed.json` postoji, pročitaj ga i probaj
  `brand_repo.get_snapshot(snapshot_id)`. Ako vrati snapshot — koristi ta
  dva ID-a, gotovo.
- Ako fajl ne postoji ILI `get_snapshot` vrati `None` (baza obrisana/
  premještena) — pozovi `LoadBrandFixture.execute(brightsmile.json path)`,
  dobij novi `(brand_id, snapshot_id)`, sačuvaj ih u `brand-seed.json`
  (isti "swallow OSError" defanzivni stil kao `_save_window_state`).
- Ovo NE dira `ports/repositories.py` niti dodaje novu perzistencionu
  apstrakciju — čist lokalni cache fajl, isti pattern kao window-state.

# Provider/model rezolucija (hardkodovana, eksplicitno)

1. `SqliteProviderConfigRepository.list_provider_configs()` → filtriraj
   `configured is True`.
2. Ako je prazno → bridge vraća `error_code="NO_PROVIDER_CONFIGURED"`,
   `error_message` (BHS, korisno) — npr. "Nijedan AI provajder nije
   podešen. Podesi API ključ ručno (skripta) dok Podešavanja ekran ne
   bude spojen na pravi backend."
3. Ako ima jedan ili više — izaberi PRVI po ovom fiksnom prioritetu:
   `OPENAI, ANTHROPIC, GOOGLE, DEEPSEEK, OPENROUTER` (redoslijed kojim su
   adapteri mergovani u A8; ako nijedan iz liste nije podešen a nešto
   drugo jeste, uzmi taj — ne smije pući samo zato što redoslijed ne
   pokriva slučaj).
4. `provider_code → model_id` (hardkodovana tabela u
   `provider_adapter_factory.py`, komentar uz svaki: "verifikovano
   live YYYY-MM-DD" ili "NIJE live-testirano, provjeriti prije merge-a"):
   - `OPENAI` → model koji je već live-testiran u ACS-F1-016 evidence
     izvještaju (pogledaj taj izvještaj za tačan string, ne izmišljaj).
   - `DEEPSEEK` → `"deepseek-chat"` (POTVRĐENO live, vidi
     `agent_reports/2026-09-04-ACS-F1-017-pi.md`).
   - `GOOGLE` → model koji je live-testiran u ACS-F1-019 evidence
     izvještaju (pogledaj taj izvještaj za tačan string).
   - `ANTHROPIC` → NIJE live-testiran nigdje u projektu. Implementer MORA
     provjeriti da model_id string stvarno postoji (npr. Anthropic
     zvanična docs stranica modela, ista disciplina kao ACS-F1-018 SDK
     research) prije nego što ga hardkodira — ako je implementer nesiguran,
     napisati to eksplicitno u evidence izvještaju kao otvoreno pitanje,
     NE nagađati string.
   - `OPENROUTER` → ACS-F1-017 još nije mergovan; ako se ovaj task
     implementira prije njega, izostaviti OPENROUTER iz tabele (samo 4
     unosa) i baciti jasnu internu grešku ako se ipak izabere — koordinator
     će ovo popuniti u fix rundi nakon što ACS-F1-017 merguje, ako zatreba.
5. `provider_adapter_factory.build_text_generation_adapter(provider_code,
   model_id, api_key) -> TextGenerationPort` — čita `api_key` preko
   `secret_store.get_secret(config.credential_ref)` (bridge poziva
   secret_store, factory samo prima gotov string — factory NIKAD ne dira
   SecretStorePort direktno, čist dispatch na 4 postojeća konstruktora).

# Forma → CampaignBriefInput mapiranje (zaključano, ne improvizovati)

Opis kampanje forma nema polje za `content_piece_count` niti prava
`channel`/`platform_code`/`format_code` registry vrijednosti (prikazuje
ljudski čitljive labele). Za OVAJ task:

- `content_piece_count` = **hardkodovano `3`** (isti broj kao live
  validacija u A8; dodavanje pravog polja na formu je budući task).
- `offer` = polje "Ponuda / proizvod" (`ponuda`).
- `goal` = polje "Cilj kampanje" (`cilj`, trenutno single-option select).
- `audience_text` = polje "Ciljna publika" (`publika`).
- `content_language_context` = sirova vrijednost iz "Jezik sadržaja"
  selecta (`SR`/`HR`/`BS`/`EN`) — prosljeđuje se doslovno, domain sloj
  ovo tretira kao slobodan string (nema enum ograničenja u
  `CampaignBriefInput`, provjereno).
- `special_instructions` = `["Posebne instrukcije"]` ako polje nije
  prazno, inače `[]`.
- `targets` = tačno JEDAN `CampaignTargetInput`, `channel` uvijek
  `"SOCIAL"` (jedina trenutna opcija), `platform_code`/`format_code` po
  ovoj tabeli (verifikovano protiv `resources/platforms/*.yaml`):

  | Platforma (GUI) | `platform_code` | Format (GUI)   | `format_code`      |
  |---|---|---|---|
  | Instagram | `INSTAGRAM` | Feed 4:5 / Kvadrat 1:1 | `FEED_POST` |
  | Instagram | `INSTAGRAM` | Priča 9:16 | `STORY` |
  | Facebook  | `FACEBOOK`  | Feed 4:5 / Kvadrat 1:1 | `FEED_POST` |
  | Facebook  | `FACEBOOK`  | Priča 9:16 | `STORY` |
  | LinkedIn  | `LINKEDIN`  | (bilo koji) | `PROFESSIONAL_POST` |

  LinkedIn nema STORY/FEED_POST format u registryju (samo
  `PROFESSIONAL_POST`/`ARTICLE_LINK_POST`) — GUI-jev format select ne
  mapira semantički na LinkedIn. Ovo je POZNAT, namjeran nesklad za ovaj
  task (ne popravljati GUI select opcije ovdje) — LinkedIn uvijek dobija
  `PROFESSIONAL_POST` bez obzira na izabrani format.
- `naziv`/`campaign_name`/`badge_*` polja se NE koriste u brief-u (nema
  im mapiranja u `CampaignBriefInput`) — ignorisati.

`brand_id`/`brand_snapshot_id` dolaze iz brand seeding koraka (iznad), ne
iz forme.

# Implementation steps

1. **`provider_adapter_factory.py`** (novi fajl,
   `infrastructure/ai/provider_adapter_factory.py`): dispatch funkcija
   opisana iznad. Unit test: za svaki od 4 (ili 5) provider_code-a,
   provjeri da vraća instancu očekivane klase sa `api_key`/`model`
   proslijeđenim (mock/inspect atribute, ne stvaran API poziv).

2. **`presentation/ui_models.py`**: novi frozen dataclass
   `CampaignPlanResultUiModel` — polja `ok: bool`, `campaign_id: str | None`,
   `plan_item_count: int | None`, `error_code: str | None`,
   `error_message: str | None`. Isti stil kao `ProviderStatusUiModel`.

3. **`presentation/contracts.py`**: dodaj TAČNO jednu metodu na
   `PresentationFacade` Protocol:
   `def create_campaign_and_generate_plan(self, raw_brief: dict[str, Any]) -> CampaignPlanResultUiModel: ...`
   Ažuriraj docstring klase (trenutno kaže "Campaign UI actions are
   intentionally absent in P0" — ovo više nije tačno za ovu jednu
   metodu, formuliši precizno).

4. **`presentation_webview/bridge/__init__.py`** (novi folder+fajl):
   - Funkcija/klasa koja gradi composition (poziva
     `ai_campaign_studio.bootstrap.create_bootstrap()` — SAMO import,
     ne mijenjaj `bootstrap.py`) i vrati sve što treba: `secret_store`,
     `database_connection`, `paths`.
   - Na vrhu te iste konekcije, izgradi `SqliteUnitOfWork`,
     `SqliteBrandRepository`, `SqliteFactRepository`,
     `SqliteCampaignRepository`, `SqliteProviderConfigRepository`,
     `YamlPromptRepository.from_bundled_resources()` — TAČAN pattern iz
     `tests/integration/application/campaigns/test_generate_campaign_plan_integration.py`,
     ne izmišljati novi.
   - Klasa `CampaignBridgeApi` (ime po tvom nahođenju, ali usko i
     svrsi-namijenjeno per PYWEBVIEW_SECURITY.md §3) sa TAČNO jednom
     javnom metodom za JS: `create_campaign_and_generate_plan(self,
     payload: dict) -> dict`.
     - Validira/tipizira `payload` na granici (ručna provjera tipova
       polja iz payload dict-a prije nego što uđe u
       `CampaignBriefInput.model_validate` — JS strana šalje proizvoljan
       JSON, ne vjerovati mu).
     - Radi brand seeding (iznad).
     - Radi provider/model rezoluciju (iznad).
     - Poziva `CreateCampaign.execute(...)` pa
       `GenerateCampaignPlan.execute(...)`.
     - Hvata očekivane greške (`InvariantViolation`, `EntityNotFound`,
       `pydantic.ValidationError`, provider/mrežne greške iz adaptera)
       i mapira ih u `error_code="GENERATION_FAILED"` /
       `"VALIDATION_ERROR"` sa BHS `error_message` — NIKAD ne pušta sirov
       Python traceback/exception string nazad u JS (security §3 duh:
       ne curiti internals, npr. API ključ ne može biti u exception
       message-u nijednog adaptera, ali budi siguran).
     - Vraća `dict` (ne dataclass direktno — `js_api` mora vratiti
       JSON-serijalizabilnu vrijednost), npr.
       `dataclasses.asdict(result_model)`.

5. **`presentation_webview/__main__.py`**: u `_open_window`, konstruiši
   `CampaignBridgeApi` instancu (composition iz koraka 4) i proslijedi
   je `webview.create_window(..., js_api=bridge_api)`. Health-check
   grešku (npr. bootstrap ne uspije) tretiraj isto strogo kao postojeći
   `WebView2MissingError` put — ne smije tiho pasti u polovično stanje.

6. **`screens/opis_kampanje/__init__.py`**:
   - Dodaj stabilne `id` atribute na sva relevantna polja (naziv, cilj,
     ponuda, publika, kanal, platforma, format, jezik, instrukcije) —
     prefiks `id="f-..."` (npr. `id="f-ponuda"`).
   - Zamijeni `<a class="btn primary" href="../plan_kampanje/index.html">`
     sa `<button class="btn primary" data-action="save-and-plan">` (isti
     tekst "Sačuvaj i napravi plan →").
   - `sacuvaj_nacrt_toast`/"Sačuvaj nacrt" dugme OSTAJE nepromijenjeno
     (i dalje toast stub — nije dio ovog taska).

7. **`static/app.js`**: novi `data-action==='save-and-plan'` handler —
   pokupi vrijednosti iz DOM-a preko `id`-jeva iz koraka 6, pozovi
   `window.pywebview.api.create_campaign_and_generate_plan(payload)`
   (vraća Promise), na `result.ok` prikaži toast sa brojem stavki i
   navigiraj na `../plan_kampanje/index.html?campaign=' + result.campaign_id`,
   na grešku prikaži toast sa `result.error_message`. Dugme se disable-uje
   (`disabled` atribut) za vrijeme poziva i re-enable-uje u `finally`
   (ili na grešku) da spriječi dupli klik dok traje mrežni poziv.
   Postojeći toast/tab/`?campaign=` handleri ostaju netaknuti.

# Acceptance

- [ ] Klik na "Sačuvaj i napravi plan →" (sa konfigurisanim providerom u
      keyring-u i pravim API ključem) stvarno kreira red u `campaigns`
      tabeli i red u `campaign_plans` tabeli u pravoj SQLite bazi
      (provjeriti direktnim SQL upitom nad `%LOCALAPPDATA%\ai-campaign-studio\...`
      bazom nakon klika, NE samo test assertion).
- [ ] Bez podešenog providera, klik daje jasnu BHS grešku kroz toast
      (`NO_PROVIDER_CONFIGURED`), aplikacija se ne ruši, GUI ostaje
      upotrebljiv.
- [ ] Drugi klik (isti brend, već seed-ovan) NE pravi duplikat brenda —
      `brand-seed.json` se čita i ponovo koristi.
- [ ] Nijedna `js_api` metoda ne vraća API ključ/token/SecretStore sadržaj
      nazad u JS (provjeri `dict` koji `create_campaign_and_generate_plan`
      vraća — samo `ok`/`campaign_id`/`plan_item_count`/`error_code`/
      `error_message`).
- [ ] Bridge klasa izložena kroz `js_api=` NIJE sirovi `PresentationFacade`
      niti domain servis — provjeri da je to namjenska uska klasa
      (PYWEBVIEW_SECURITY.md §3).
- [ ] `provider_adapter_factory.py` ne dira `SecretStorePort` direktno
      (prima gotov `api_key` string).
- [ ] `PresentationFacade` Protocol ima TAČNO jednu novu metodu, ostatak
      Protocol-a nepromijenjen; nema pokušaja pune konkretne
      implementacije svih 6 metoda.
- [ ] `ports/repositories.py` NIJE DIRAN (git diff dokaz) — nema novih
      metoda na `BrandRepositoryPort`.
- [ ] `plan_kampanje/`, `podesavanja/`, `brend/`, `kampanje/`,
      `kalendar/`, `pocetna/`, `shell/`, `app.css` NISU DIRANI.
- [ ] `bootstrap.py`/`main.py` NISU MIJENJANI (import iz `bootstrap.py`
      je OK, izmjena fajla nije).
- [ ] Forma→brief mapiranje prati TAČNO tabelu iz "Forma → CampaignBriefInput
      mapiranje" sekcije (posebno LinkedIn→`PROFESSIONAL_POST` uvijek).
- [ ] Anthropic model_id (ako je uključen) je STVARNO provjeren da postoji
      (ne nagađan) — navesti u evidence izvještaju KAKO je provjeren.
- [ ] `python -m pytest -q` prolazi (uključujući nove testove za bridge i
      adapter factory).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `python -m pytest tests/architecture/test_import_boundaries.py -v`
      prolazi (bridge/composition smije importovati infrastructure —
      provjeri da import-boundary test to već dozvoljava za
      `presentation_webview/`; ako ne dozvoljava, javi koordinatoru PRIJE
      nego što probaš zaobići test, ne mijenjaj taj test fajl sam jer je
      van tvog allowed_paths).
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/ -q
python -m pytest tests/architecture/test_import_boundaries.py -v
python -m pytest tests/unit/presentation_webview/bridge/ -v
python -m pytest tests/unit/infrastructure/ai/test_provider_adapter_factory.py -v
python -m ruff check .
python -m mypy src
```

# Vizuelna + funkcionalna provjera (obavezna, NE samo testovi)

Implementer MORA pokrenuti pravu aplikaciju
(`PYTHONPATH=src python -m ai_campaign_studio.presentation_webview`),
sa VEĆ podešenim providerom (koordinator će prije dodjele taska
potvrditi koji provider ima ključ u keyring-u za ovaj test — ili
implementer traži od koordinatora da to uradi), i:

1. Otvoriti Opis kampanje, kliknuti "Sačuvaj i napravi plan →".
2. Sačekati toast sa rezultatom (uspjeh sa brojem stavki, ili jasna
   greška).
3. Na uspjeh, potvrditi navigaciju na Plan kampanje ekran sa
   `?campaign=<id>` u URL-u.
4. Direktnim upitom nad SQLite bazom (`sqlite3` CLI ili python skripta,
   NE mijenjati bazu ručno) potvrditi da `campaigns` i `campaign_plans`
   redovi stvarno postoje sa očekivanim sadržajem.
5. Screenshot toast poruke (uspjeh) priložiti evidence izvještaju.
6. Ponoviti klik da se potvrdi da brand seeding ne duplira brend (provjeri
   brojem redova u `brands` tabeli prije/poslije drugog klika).

Bez ove provjere task se NE SMIJE proglasiti PASS-om.

# Review focus — Claude

- Bridge klasa je stvarno uska (jedna javna metoda), ne curi
  facade/domain servis;
- boundary validacija payload dict-a prije `CampaignBriefInput.model_validate`;
- error handling ne curi sirove exception stringove/traceback u JS;
- brand-seed self-healing logika (fajl postoji ali `get_snapshot` vrati
  `None` → re-seed, ne pukne);
- provider priority + hardkodovana model tabela tačno prati kontrakt;
- forma→brief mapiranje (posebno LinkedIn format edge case) tačno;
- `ports/repositories.py`/`bootstrap.py`/`main.py` netaknuti (git diff);
- svi ostali ekrani/CSS netaknuti (git diff scope provjera);
- import-boundary test i dalje prolazi (bridge ne krši Clean/Hexagonal
  granice — bridge SMIJE importovati infrastructure jer je i sâm dio
  composition-root sloja, ali provjeri da `screens/opis_kampanje/__init__.py`
  i dalje NE importuje infrastructure/application direktno — samo JS
  poziva bridge, Python SSR modul ostaje čist).

# Review focus — Codex (adversarial, HIGH risk pun ciklus)

- Da li payload iz JS-a (proizvoljan, nepovjerljiv) može izazvati bilo
  šta van `CampaignBriefInput` validacije prije nego što dotakne
  repozitorije (npr. injection kroz `content_language_context` slobodan
  string, prekomjerno dugačak string, non-string tip koji prođe kroz
  Python bez greške do SQLite write-a)?
- Da li bilo koji error path curi API ključ, DB putanju, ili interni
  stack trace nazad u `dict` koji ide u JS?
- Da li je moguće dvoklikom (prije nego što se dugme disable-uje) izazvati
  dvije paralelne kampanje/duplikat brenda (race condition u
  brand-seed.json read-modify-write)?
- Da li `provider_adapter_factory` ikad instancira adapter sa praznim/
  `None` `api_key` bez greške (tiho slanje prazne vrijednosti provideru)?

# Rollback

HIGH risk, ali izolovano na nov kod (nov folder + jedan postojeći dugme).
Rollback = revert commit-a, nema migracija baze koje treba unazad
(brand-seed.json i eventualni test brend redovi u bazi ostaju bezopasni
leftover, ne blokiraju rollback).

# Coordination

Nezavisno od preostalog ACS-F1-017 review-a (DeepSeek/OpenRouter) — ako
ACS-F1-017 još nije mergovan kad ovaj task krene, implementer izostavlja
DEEPSEEK/OPENROUTER iz provider factory-ja dok se ne pojave na main-u
(vidi provider/model rezolucija, korak 4), koordinator dopunjava u fix
rundi.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-005-campaign-bridge
Branch:   task/ACS-GUI-005-campaign-bridge
Base:     main @ 73f52b1
```
