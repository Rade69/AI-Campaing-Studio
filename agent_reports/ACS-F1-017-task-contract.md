---
task_id: ACS-F1-017
phase: Faza-1 (A8, dio 3 — OpenAI-compatible provider family)
title: "A8: DeepSeek + OpenRouter + generic OpenAI-compatible adapteri (reuse OpenAIAdapter sa base_url)"
risk: HIGH
coordinator: claude
implementer: pi
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies:
  - ACS-F1-016 (merged, main @ 1b7a71f) — OpenAIAdapter + provider-setup use-case-i (ConfigureProvider/TestProviderConnection/DiscoverModels/SelectDefaultModel), sve već postoji i generičko je (ne OpenAI-specifično u use-case sloju)
allowed_paths:
  - src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
  - src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py
  - tests/unit/infrastructure/ai/test_openai_adapter.py
  - tests/unit/infrastructure/ai/test_openai_compatible_providers.py
  - tests/integration/application/ai_provider/test_ai_provider_flow_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/ai_registry/
  - resources/ai_providers/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/presentation_webview/
  - pyproject.toml
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 99fef92
  index_status: fresh (analyze re-run 2026-09-04 post ACS-F1-016 merge)
  targets:
    - symbol: "src/ai_campaign_studio/infrastructure/ai/openai_adapter.py:OpenAIAdapter"
      upstream_risk: LOW
      upstream_count: "0 production importers (samo vlastiti testovi) — nije žičeno u bootstrap.py. Bezbjedno mijenjati konstruktorski potpis."
      downstream_notes: "Trenutno hardkoduje `provider=\"openai\"` (AIResponse) i `provider_code=\"OPENAI\"` (ModelProfile u discover_models()) u tijelu metoda — OVO SE MORA parametrizovati (vidi Objective) da bi se klasa mogla ponovo koristiti za DeepSeek/OpenRouter/generic bez pogrešnog provenance-a."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "Da li OpenRouter/DeepSeek Chat Completions response shape ima neke razlike od OpenAI-jevog (npr. OpenRouter dodaje polja) koje bi zahtijevale dodatnu toleranciju u response parsing-u — implementer istražuje SDK/API dokumentaciju provajdera i dokumentuje nalaz."
---

# Kontekst

A8 (live AI adapteri) nastavlja provajder-po-provajder, nakon ACS-F1-015 (generička
ProviderConfig/ModelSelection persistencija) i ACS-F1-016 (OpenAI, prvi live adapter, merged).
`resources/ai_providers/*.yaml` već ima SVE definicije (P0 rad): `OPENAI` (merged), `ANTHROPIC`,
`DEEPSEEK`, `GOOGLE`, `OPENROUTER`, `OPENAI_COMPATIBLE` — svaki sa svojim `adapter_type` stringom,
čeka samo Python adapter implementaciju.

**DeepSeek, OpenRouter i generički "OpenAI-kompatibilan" provajder svi izlažu OpenAI-kompatibilan
Chat Completions API** (isti request/response shape kao OpenAI, drugačiji `base_url`). Ovaj task
NE pravi 3 nova adaptera — ponovo koristi `OpenAIAdapter` sa drugim `base_url` po provajderu, uz
JEDNU nužnu izmjenu: `OpenAIAdapter` trenutno hardkoduje `provider="openai"`/
`provider_code="OPENAI"` u tijelu `generate()`/`discover_models()`, što bi za DeepSeek/OpenRouter
proizvelo pogrešan provenance (`AIResponse.provider` bi lagao da je "openai"). Ovaj task
parametrizuje to.

**Obavezno pročitati prije koda**:

```text
agent_reports/ACS-F1-016-task-contract.md                  (originalan OpenAIAdapter dizajn)
agent_reports/2026-09-03-ACS-F1-016-crush.md                (implementer evidence, dizajn odluke)
resources/ai_providers/deepseek.yaml
resources/ai_providers/openrouter.yaml
resources/ai_providers/openai_compatible.yaml
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py  (kompletno, prije izmjene)
tests/unit/infrastructure/ai/test_openai_adapter.py         (postojeći test pattern)
```

**Risk**: HIGH — isti razred kao ACS-F1-016 (SecretStore dodir preko postojećih use-case-a, stvaran
vanjski API surface čak i ako je mock-ovan u testovima). Puna Codex + Claude + Human Owner procedura,
bez izuzetka.

# Objective

1. **Parametrizovati `OpenAIAdapter`** da prima `provider_code: str = "OPENAI"` i
   `provider_display: str = "openai"` (ili slično imenovanje — implementer bira, dokumentuje) u
   konstruktoru, i koristiti te vrijednosti umjesto hardkodovanih literala u `AIResponse.provider`
   i `ModelProfile.provider_code` (unutar `discover_models()`). Default vrijednosti MORAJU čuvati
   postojeće OpenAI ponašanje — ovo je aditivna izmjena, postojeći `test_openai_adapter.py` testovi
   moraju i dalje proći BEZ izmjene (osim ako implementer eksplicitno dokumentuje zašto je neki
   test morao da se prilagodi).
2. **Novi fajl `infrastructure/ai/openai_compatible_providers.py`** — tanak modul koji:
   - Definiše konstante za fiksne base URL-ove: DeepSeek (`https://api.deepseek.com`), OpenRouter
     (`https://openrouter.ai/api/v1`). Implementer PROVJERAVA ove vrijednosti protiv zvanične
     dokumentacije prije upotrebe (ne uzimati zdravo za gotovo) i dokumentuje izvor u komentaru.
   - Izlaže fabrike/helper funkcije (npr. `build_deepseek_adapter(api_key, model) -> OpenAIAdapter`,
     `build_openrouter_adapter(...)`, `build_openai_compatible_adapter(api_key, model, base_url)`
     za USER_CONFIGURABLE slučaj) koje konstruišu `OpenAIAdapter` sa odgovarajućim
     `base_url`/`provider_code`/`provider_display`. Generički "OpenAI-kompatibilan" provajder prima
     `base_url` kao parametar (iz `ProviderConfig`, korisnik ga unosi — `base_url_mode:
     USER_CONFIGURABLE` u registry-ju), DeepSeek/OpenRouter imaju FIKSAN base_url (ne uzimaju ga od
     korisnika — `base_url_mode: FIXED`).
   - NE uvoditi novu SDK zavisnost — sve ide kroz postojeći `openai` paket klijent.
3. **Ne dirati use-case sloj** (`ConfigureProvider`/`TestProviderConnection`/`DiscoverModels`/
   `SelectDefaultModel`) — svi su već generički (rade sa bilo kojim `TextGenerationPort`-
   kompatibilnim adapterom kroz DI seam iz ACS-F1-016), ne trebaju izmjenu za novi provider_code.
   Ako implementer otkrije da NEŠTO u use-case sloju ipak treba dirati, to je split-contract signal
   — zaustaviti i javiti koordinatoru, ne tiho proširivati scope.
4. **Ne dirati `bootstrap.py`** — kompozicija (koji adapter se instancira za koji provider_code) je
   budući bridge task, isto kao i za OpenAI u ACS-F1-016.

# Implementation steps

1. Pročitati `openai_adapter.py` u cjelosti, identifikovati SVA mjesta gdje se `"openai"`/
   `"OPENAI"` hardkoduje.
2. Dodati `provider_code`/`provider_display` (ili slično imenovane) konstruktorske parametre sa
   default vrijednostima koje čuvaju postojeće ponašanje. Zamijeniti hardkodovane literale.
3. Kreirati `openai_compatible_providers.py` sa konstantama base URL-ova (provjerenim protiv
   dokumentacije) i fabrikama za DeepSeek/OpenRouter/generic OpenAI-compatible.
4. Testovi:
   - Regresija: SVI postojeći `test_openai_adapter.py` testovi i dalje prolaze nepromijenjeni (ili
     minimalno prilagođeni uz jasno obrazloženje).
   - Novi testovi za parametrizovani `provider_code`/`provider_display` (default ostaje "openai"/
     "OPENAI", eksplicitna vrijednost se ispravno propagira u `AIResponse`/`ModelProfile`).
   - `test_openai_compatible_providers.py`: svaka fabrika konstruiše `OpenAIAdapter` sa tačnim
     `base_url`/`provider_code` (mock-ovan `OpenAI` klijent — provjeriti KOJIM argumentima je
     konstruisan, ne pozivati stvaran mrežni klijent).
   - Cijeli test suite i dalje BEZ pravog API ključa/mrežnog poziva (ista disciplina kao
     ACS-F1-016).

# Acceptance

- [ ] `OpenAIAdapter` default ponašanje (bez novih parametara) identično prije/poslije —
      postojeći testovi prolaze.
- [ ] `AIResponse.provider`/`ModelProfile.provider_code` ispravno odražavaju stvaran provider kad
      se koristi za DeepSeek/OpenRouter/generic (ne "openai" lažno).
- [ ] DeepSeek/OpenRouter base URL-ovi provjereni protiv zvanične dokumentacije, ne pretpostavljeni.
- [ ] Generički OpenAI-compatible provider prima `base_url` kao parametar (USER_CONFIGURABLE),
      DeepSeek/OpenRouter imaju fiksan base_url (FIXED) — potvrđeno protiv `resources/ai_providers/
      *.yaml` `base_url_mode` polja.
- [ ] Nema nove SDK zavisnosti u `pyproject.toml` (forbidden path — ako implementer misli da je
      potrebna, to je signal da je pretpostavka o OpenAI-kompatibilnosti pogrešna, zaustaviti i
      javiti koordinatoru).
- [ ] `application/`, `ports/`, `ai_registry/`, `bootstrap.py` netaknuti.
- [ ] `python -m pytest -q` prolazi kompletno, bez pravog API ključa.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `python -m pytest tests/architecture/test_import_boundaries.py -v` prolazi.
- [ ] `python scripts/check_no_secrets.py` čist.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/unit/infrastructure/ai/ -v
python -m ruff check .
python -m mypy src
python -m pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
```

# Review focus — Codex (adversarial) + Claude (arhitektura)

- Provjeriti da je `provider_code`/`provider_display` STVARNO propagiran u SVE relevantne izlazne
  strukture (`AIResponse`, `ModelProfile`), ne samo u dio koda — probati sa DeepSeek-om i potvrditi
  da `AIResponse.provider != "openai"`.
- Base URL vrijednosti — provjeriti protiv stvarne dokumentacije, ne samo protiv onoga što
  implementer tvrdi.
- `base_url_mode` FIXED vs USER_CONFIGURABLE poštovan tačno kao u YAML registry-ju.
- Nema regresije na postojeće OpenAI testove/ponašanje (default parametri).
- Error mapping/retry logika (naslijeđena iz `OpenAIAdapter`) i dalje ispravna za sve provajdere.
- Test ključevi EXAMPLE-markirani, nema pravog mrežnog poziva.

# Rollback

Fix na istoj branch bez proširenja scope-a. Ako se ispostavi da neki provajder (npr. OpenRouter)
NIJE dovoljno OpenAI-kompatibilan za reuse (vidi `unknowns` u gitnexus bloku), to je split-contract
signal — zaustaviti implementaciju za taj provajder, javiti koordinatoru, ne izmišljati workaround.

# Coordination

Nezavisno od budućih ACS-F1-018 (Anthropic) i ACS-F1-019 (Google) — ne dijeli fajlove sa njima
(oni trebaju svoje nove adaptere/SDK). Može ići paralelno ako se implementeri razlikuju.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-017-openai-compatible-providers
Branch:   task/ACS-F1-017-openai-compatible-providers
Base:     main @ 99fef92
```
