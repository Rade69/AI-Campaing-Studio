---
task_id: ACS-F1-019
phase: Faza-1 (A8, dio 5 — Google (Gemini) adapter)
title: "A8: Google (Gemini) live adapter — TextGenerationPort implementacija"
risk: HIGH
coordinator: claude
implementer: crush
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies:
  - ACS-F1-016 (merged, main @ 1b7a71f) — OpenAIAdapter kao referentan disciplina-pattern (retry/error-mapping/DI-seam), provider-setup use-case-i (već generički, ne treba izmjena)
allowed_paths:
  - src/ai_campaign_studio/infrastructure/ai/google_adapter.py
  - tests/unit/infrastructure/ai/test_google_adapter.py
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
  - src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py
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
      upstream_count: "Protocol implementiran od OpenAIAdapter (i mock_adapter.py). Novi implementer (GoogleAdapter) je dodatna implementacija istog Protocol-a, ne mijenja postojeće importere."
      downstream_notes: "Use-case sloj prima adapter kroz DI (lokalni Protocol), ne treba izmjenu."
      affected_processes: []
  scope_fit: PASS
  unknowns:
    - "KOJI Google Python SDK koristiti — postoje DVA: stariji `google-generativeai` (genai.configure() + GenerativeModel) i noviji unificirani `google-genai` (genai.Client()). Implementer MORA provjeriti koji je trenutno zvanično preporučen za novi kod i dokumentovati izbor sa obrazloženjem — autor kontrakta nije siguran koji je trenutno kanonski zbog poznate SDK migracije u toku u ovom ekosistemu."
    - "Tačan mehanizam strukturisanog (JSON schema) izlaza kod izabranog SDK-a (npr. `generation_config`/`response_schema` parametri) — implementer provjerava protiv trenutne dokumentacije, ne pretpostavlja."
    - "Da li models-list API postoji i stabilan je za izabrani SDK (registry: `supports_model_discovery: true` za GOOGLE) — implementer provjerava, vraća se koordinatoru ako nije pouzdan prije izmišljanja hardkodovane liste (D-AI-2)."
---

# Kontekst

A8 nastavlja provajder-po-provajder. Google (`resources/ai_providers/google.yaml`:
`adapter_type: google`, `requires_api_key: true`, `supports_model_discovery: true`,
`base_url_mode: FIXED`) treba pravi nov adapter — Gemini API je strukturno drugačiji i od OpenAI-ja
i od Anthropic-a.

**Ovaj kontrakt namjerno NE propisuje tačne SDK pozive** (za razliku od ACS-F1-016 gdje je OpenAI
API bio poznat i stabilan) — Google-ov Python AI SDK ekosistem je bio u tranziciji (stariji
`google-generativeai` → noviji unificirani `google-genai`), i tačno trenutno stanje treba
provjeriti u trenutku implementacije, ne pretpostaviti iz eventualno zastarjelog znanja. Implementer
prvi korak je istraživanje, ne kod.

**Obavezno pročitati/istražiti prije koda**:

```text
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py   (referentan DISCIPLINA-pattern — ne
                                                                doslovna kopija, API je drugačiji)
src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py (ako je ACS-F1-018 već merged do
                                                                trenutka rada na ovom tasku —
                                                                drugi primjer "nov SDK, ista
                                                                disciplina")
tests/unit/infrastructure/ai/test_openai_adapter.py           (referentan test pattern)
src/ai_campaign_studio/ports/ai.py                             (TextGenerationPort, AIRequest,
                                                                AIResponse, AITelemetry)
src/ai_campaign_studio/domain/common/errors.py                 (ErrorCode/InfrastructureError —
                                                                postojeća taksonomija)
resources/ai_providers/google.yaml
agent_reports/ACS-F1-016-task-contract.md
```

**Risk**: HIGH — isti razred kao ACS-F1-016/018. Puna Codex + Claude + Human Owner procedura.

# Objective

`GoogleAdapter(TextGenerationPort)` u `infrastructure/ai/google_adapter.py`, ista DISCIPLINA kao
`OpenAIAdapter`/`AnthropicAdapter`:

- `generate()` implementira `TextGenerationPort`.
- Vlastite `test_connection()`/`discover_models()` (NE `AIProviderConnectionPort`).
- Bounded retry, dokumentovani uslovi.
- Svaka SDK greška mapirana u domain `InfrastructureError` (postojeći `ErrorCode` enum), nikad
  sirov SDK exception ili API ključ u poruci.
- DI seam: `client` opcioni konstruktorski parametar za testove.
- Strukturisan izlaz mehanizam istražen, izabran, dokumentovan.
- `pyproject.toml`: nova zavisnost (SDK po izboru, dokumentovan izbor) + sve tranzitivne
  test-zavisnosti ODMAH eksplicitno deklarisane (F1 lekcija iz ACS-F1-016 — ne čekati review).

# Implementation steps

1. Istražiti trenutno stanje Google Gemini Python SDK-a (koji paket je kanonski za nov kod,
   Messages/generate shape, error hijerarhija, structured-output mehanizam, models-list API).
   Dokumentovati nalaze u evidence izvještaju PRIJE pisanja koda.
2. Implementirati `GoogleAdapter` prateći disciplinu iz `openai_adapter.py`.
3. Test suite: potpuno mock-ovan klijent, fake response objekti oblikovani kao STVARAN SDK shape
   (ne pojednostavljen — vidi BF-1 lekciju iz ACS-F1-016 review-a).
4. `pyproject.toml`: nova zavisnost + eksplicitne test-zavisnosti, verifikovano iz svježeg
   environment-a.

# Acceptance

- [ ] `GoogleAdapter` implementira `TextGenerationPort.generate()`, popunjen `AIResponse`.
- [ ] `test_connection()`: nevalidni ključ → `False`, ostale greške → `InfrastructureError`.
- [ ] `discover_models()`: mapira Google modele u `ModelProfile` (`source=DISCOVERED`) — ILI
      implementer se vraća koordinatoru ako models-list nije pouzdano dostupan.
- [ ] Retry ograničen, dokumentovan.
- [ ] Error mapping nikad ne curi ključ/SDK exception tekst.
- [ ] Strukturisan izlaz dokumentovan i testiran realno-oblikovanim fake response-om.
- [ ] Test ključevi EXAMPLE-markirani.
- [ ] Nema pravog mrežnog poziva u automatskom test suite-u.
- [ ] `pyproject.toml` nova zavisnost + tranzitivne test-zavisnosti eksplicitne, verifikovano iz
      svježeg environment-a.
- [ ] `application/`, `ports/`, `ai_registry/`, `bootstrap.py`, ostali provider adapteri netaknuti.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src`, `test_import_boundaries.py`,
      `check_no_secrets.py` — svi prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m pytest tests/unit/infrastructure/ai/test_google_adapter.py -v
python -m ruff check .
python -m mypy src
python -m pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
# F1-lekcija: verifikovati iz svježeg environment-a
pip uninstall <nova-test-zavisnost-ako-postoji> -y && pip install -e ".[dev]" && pytest -q
```

# Review focus — Codex (adversarial) + Claude (arhitektura)

- Fake response fixture-i MORAJU biti oblikovani kao stvaran SDK shape (isti razred provjere kao
  BF-1 u ACS-F1-016).
- Structured output mehanizam — adversarial proba sa response-om koji krši schema.
- SDK izbor (stariji vs noviji Google paket) — obrazložen, ne slučajan.
- Retry/error mapping — nema beskonačne petlje, nema curenja ključa.
- Scope — ništa van `allowed_paths`.

# Rollback

Fix na istoj branch bez proširenja scope-a.

# Coordination

Nezavisno od ACS-F1-017 (OpenAI-kompatibilna porodica) i ACS-F1-018 (Anthropic) — nema dijeljenih
fajlova. Može ići paralelno ako implementeri nisu isti.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-019-google-adapter
Branch:   task/ACS-F1-019-google-adapter
Base:     main @ 99fef92
```
