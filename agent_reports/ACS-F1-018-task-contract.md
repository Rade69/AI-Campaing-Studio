---
task_id: ACS-F1-018
phase: Faza-1 (A8, dio 4 — Anthropic adapter)
title: "A8: Anthropic (Claude) live adapter — TextGenerationPort implementacija"
risk: HIGH
coordinator: claude
implementer: minimax
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies:
  - ACS-F1-016 (merged, main @ 1b7a71f) — OpenAIAdapter kao referentan pattern (retry/error-mapping/DI-seam disciplina), provider-setup use-case-i (već generički, ne treba izmjena)
allowed_paths:
  - src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py
  - tests/unit/infrastructure/ai/test_anthropic_adapter.py
  - tests/integration/application/ai_provider/test_ai_provider_flow_integration.py
  - pyproject.toml
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
  - src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
  - src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py
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
    - symbol: "src/ai_campaign_studio/ports/ai.py:TextGenerationPort"
      upstream_risk: LOW
      upstream_count: "Protocol implementiran od OpenAIAdapter (i mock_adapter.py). Novi implementer (AnthropicAdapter) je dodatna implementacija istog Protocol-a, ne mijenja postojeće importere."
      downstream_notes: "Use-case sloj (application/ai_provider/*) prima adapter kroz DI (lokalni Protocol u samom use-case fajlu, ne konkretnu klasu) — potvrđeno u ACS-F1-016 review-u. Nema potrebe za izmjenom use-case sloja."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "TAČAN mehanizam strukturisanog (JSON schema) izlaza kod Anthropic Messages API-ja — implementer MORA provjeriti trenutno stanje Anthropic dokumentacije prije pisanja koda (moguće: forced tool_use sa JSON schema kao tool input schema, ILI native structured output ako ga Anthropic sad nudi, ILI prompt-based JSON sa post-hoc parsing/repair). Ovaj kontrakt namjerno NE propisuje tačan mehanizam jer je autor kontrakta nesiguran da li se API promijenio od poslednjeg poznatog stanja — implementer istražuje i dokumentuje izbor sa obrazloženjem u evidence izvještaju."
    - "Da li `client.models.list()` postoji i stabilan je u trenutnoj `anthropic` Python SDK verziji (registry: `supports_model_discovery: true` za ANTHROPIC) — implementer provjerava, i ako NE postoji/nije pouzdan, vraća se koordinatoru sa nalazom prije nego što izmisli workaround (npr. hardkodovana lista modela bi kršila D-AI-2 \"no hardcoded model lists\")."
---

# Kontekst

A8 nastavlja provajder-po-provajder nakon ACS-F1-016 (OpenAI, merged) i ACS-F1-017 (OpenAI-
kompatibilna porodica, u toku). Anthropic (`resources/ai_providers/anthropic.yaml`:
`adapter_type: anthropic`, `requires_api_key: true`, `supports_model_discovery: true`,
`base_url_mode: FIXED`) je STRUKTURNO RAZLIČIT API od OpenAI-ja — ovo NIJE reuse task kao
ACS-F1-017, treba pravi nov adapter sa `anthropic` Python SDK-om.

**Ključne poznate razlike od OpenAI Chat Completions (implementer provjerava svaku protiv trenutne
zvanične Anthropic dokumentacije prije oslanjanja na njih — API-ji se mijenjaju):**

- Anthropic Messages API nema "system" poruku unutar `messages` liste — sistemski prompt ide kao
  zaseban top-level `system` parametar u `client.messages.create(...)`.
  `AIRequest.system_text`/`AIRequest.user_text` (postojeći port, provjeriti tačna imena polja u
  `ports/ai.py`) se mapiraju na to.
- Response sadržaj je LISTA content blokova (`message.content`), ne jedan string kao kod OpenAI-ja
  — tipično `message.content[0].text` za čist tekstualni odgovor, ali implementer provjerava
  stvaran shape (može biti tool_use blok ako se strukturisani izlaz radi preko tool-calling-a).
- "Finish reason" ekvivalent je `message.stop_reason` (drugačije ime polja od OpenAI-jevog
  `finish_reason`), sa drugačijim mogućim vrijednostima (`end_turn`, `max_tokens`,
  `stop_sequence`, `tool_use`, itd. — implementer provjerava tačan skup).
- Token usage: `message.usage.input_tokens`/`message.usage.output_tokens` (provjeriti tačna imena
  protiv SDK-a).
- Error hijerarhija: `anthropic.APIError`/`RateLimitError`/`APIConnectionError`/
  `AuthenticationError` i slično — implementer provjerava tačnu hijerarhiju u instaliranoj SDK
  verziji prije pisanja `_map_error()`, ne pretpostavlja da je identična OpenAI-jevoj samo zato što
  zvuči slično.

**Obavezno pročitati prije koda**:

```text
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py   (referentan pattern — retry/error-
                                                                mapping/DI-seam/test_connection/
                                                                discover_models disciplina, NE
                                                                doslovna kopija zbog API razlika)
tests/unit/infrastructure/ai/test_openai_adapter.py           (referentan test pattern)
src/ai_campaign_studio/ports/ai.py                             (TextGenerationPort, AIRequest,
                                                                AIResponse, AITelemetry — tačna
                                                                polja koja MORAJU biti popunjena)
src/ai_campaign_studio/domain/common/errors.py                 (ErrorCode/InfrastructureError —
                                                                postojeća taksonomija, reuse-ovati
                                                                ne izmišljati novu)
resources/ai_providers/anthropic.yaml
agent_reports/ACS-F1-016-task-contract.md                     (originalan OpenAI kontrakt, isti
                                                                nivo disciplina se očekuje ovdje)
```

**Risk**: HIGH — isti razred kao ACS-F1-016 (prvi put ovaj SDK dodiruje SecretStore preko
postojećih use-case-a, stvaran vanjski API surface). Puna Codex + Claude + Human Owner procedura.

# Objective

`AnthropicAdapter(TextGenerationPort)` u `infrastructure/ai/anthropic_adapter.py`, sa istom
DISCIPLINOM kao `OpenAIAdapter` (ali NE istim kodom — API je strukturno drugačiji):

- Implementira `TextGenerationPort.generate()`.
- Vlastite `test_connection()`/`discover_models()` metode (NE implementira
  `AIProviderConnectionPort` — isti razlog kao OpenAI: multi-provider-dispatch potpis je
  preuranjen dok se provajderi dodaju jedan-po-jedan).
- Bounded retry (implementer bira tačan broj/uslove, dokumentuje — ne mora biti identično `_MAX_ATTEMPTS
  = 2` iz OpenAI-ja ako Anthropic ima drugačije retry-worthy greške, ali MORA biti ograničen, ne
  beskonačan).
- Svaka SDK greška mapirana u domain `InfrastructureError` (postojeći `ErrorCode` enum —
  `RATE_LIMIT`/`NETWORK_ERROR`/`INVALID_API_KEY`/`PROVIDER_ERROR`), nikad sirov SDK exception ili
  API ključ u poruci.
- DI seam: `client` opcioni konstruktorski parametar (production gradi pravi `Anthropic(...)`
  klijent, testovi injektuju fake) — isti obrazac kao `OpenAIAdapter`.
- Strukturisan izlaz: implementer istražuje i bira mehanizam (vidi `unknowns` u gitnexus bloku),
  dokumentuje izbor i ZAŠTO u evidence izvještaju.
- `pyproject.toml`: dodati `anthropic` SDK kao zavisnost (verzija po izboru implementera,
  dokumentovan razlog kao kod `openai>=1.30` u ACS-F1-016). Provjeriti odmah da li ta verzija
  povlači neku tranzitivnu test-zavisnost (kao `httpx` kod OpenAI-ja, F1 iz ACS-F1-016) i ako da,
  deklarisati je eksplicitno u `dev` extras SMJESTA, ne čekati review da to nađe.

# Implementation steps

1. Istražiti trenutnu `anthropic` Python SDK dokumentaciju: Messages API shape, error hijerarhiju,
   structured-output mehanizam, models list API. Dokumentovati nalaze u evidence izvještaju PRIJE
   pisanja koda (kratko, sa linkovima/verzijom SDK-a ako je moguće).
2. Implementirati `AnthropicAdapter` prateći disciplinu iz `openai_adapter.py` (struktura fajla,
   docstring stil, error mapping pattern) ali sa tačnim Anthropic API pozivima.
3. Test suite: potpuno mock-ovan `Anthropic` klijent (fake response objekti oblikovani kao STVARAN
   SDK shape — ACS-F1-016 je imao bug (BF-1) baš zato što je test fixture koristio pojednostavljen,
   ne-realan shape; ne ponoviti tu grešku).
4. `pyproject.toml`: `anthropic` zavisnost + bilo koja nužna test-zavisnost eksplicitno u dev
   extras (vidi F1 lekciju iz ACS-F1-016 — verifikovati iz GENUINELY svježeg environment-a, ne
   environment-a koji već ima nešto instalirano "slučajno").

# Acceptance

- [ ] `AnthropicAdapter` implementira `TextGenerationPort.generate()`, vraća popunjen `AIResponse`
      (svako polje iz porta, uključujući telemetry).
- [ ] `test_connection()`: nevalidni ključ → `False` (ne exception), ostale greške →
      `InfrastructureError`.
- [ ] `discover_models()`: mapira Anthropic modele u `ModelProfile` sa `source=DISCOVERED` — ILI,
      ako models-list API nije pouzdano dostupan, implementer se vraća koordinatoru sa nalazom
      prije nego što izmisli hardkodovanu listu (kršilo bi D-AI-2).
- [ ] Retry ograničen (ne beskonačan), dokumentovani uslovi.
- [ ] Error mapping nikad ne curi sirov API ključ ili SDK exception tekst.
- [ ] Strukturisan izlaz mehanizam dokumentovan i testiran sa realno-oblikovanim fake response-om.
- [ ] Test ključevi EXAMPLE-markirani (`"sk-ant-EXAMPLE-..."` ili slično).
- [ ] Nema pravog mrežnog poziva u automatskom test suite-u.
- [ ] `pyproject.toml` nova zavisnost + sve tranzitivne test-zavisnosti eksplicitno deklarisane,
      verifikovano iz svježeg environment-a.
- [ ] `application/`, `ports/`, `ai_registry/`, `bootstrap.py`, `openai_adapter.py`,
      `openai_compatible_providers.py` netaknuti.
- [ ] `python -m pytest -q` prolazi kompletno.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `python -m pytest tests/architecture/test_import_boundaries.py -v` prolazi.
- [ ] `python scripts/check_no_secrets.py` čist.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/unit/infrastructure/ai/test_anthropic_adapter.py -v
python -m ruff check .
python -m mypy src
python -m pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
# F1-lekcija: verifikovati iz svježeg environment-a
pip uninstall anthropic -y && pip install -e ".[dev]" && pytest -q
```

# Review focus — Codex (adversarial) + Claude (arhitektura)

- Fake response fixture-i u testovima MORAJU biti oblikovani kao STVARAN Anthropic SDK shape
  (provjeriti protiv `anthropic` paketovih tipova, isto kao što je urađeno za BF-1 fix u
  ACS-F1-016) — ne kao pojednostavljen `SimpleNamespace` koji slučajno maskira bug.
  "Finish reason"/stop_reason posebno provjeriti (isti razred greške kao BF-1).
- Structured output mehanizam — provjeriti da stvarno radi, ne samo da test prolazi (adversarial
  proba sa response-om koji krši schema, response-om koji nije JSON, itd.).
- Retry/error mapping — nema beskonačne petlje, nema curenja ključa.
- Scope — ništa van `allowed_paths`.

# Rollback

Fix na istoj branch bez proširenja scope-a.

# Coordination

Nezavisno od ACS-F1-017 (OpenAI-kompatibilna porodica) i budućeg ACS-F1-019 (Google) — nema
dijeljenih fajlova sa njima. Može ići paralelno ako implementeri nisu isti.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-018-anthropic-adapter
Branch:   task/ACS-F1-018-anthropic-adapter
Base:     main @ 99fef92
```
