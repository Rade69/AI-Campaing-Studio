# → ZA CODEX — ACS-F1-017 adversarial review (HIGH risk)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

## Status

ACS-F1-017 (DeepSeek + OpenRouter + generički OpenAI-kompatibilan, kroz reuse `OpenAIAdapter`) je
implementiran (Pi), moj arhitektonski review je `PASS_WITH_NOTES`. Na tebi je adversarial review
prije Human Owner odobrenja.

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-017-openai-compatible-providers
Branch:   task/ACS-F1-017-openai-compatible-providers (necommit-ovano, sinhronizovano sa main)
```

## Read-set

```text
agent_reports/ACS-F1-017-task-contract.md
agent_reports/2026-09-04-ACS-F1-017-pi.md                    (implementer evidence)
agent_reports/2026-09-04-ACS-F1-017-review-claude.md         (moj review, u worktree-u)
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py   (diff: provider_code/provider_display parametrizacija)
src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py  (nov fajl)
tests/unit/infrastructure/ai/test_openai_adapter.py           (3 nova testa)
tests/unit/infrastructure/ai/test_openai_compatible_providers.py  (nov fajl)
```

## Šta je posebno relevantno za tvoj adversarial fokus

- **Provenance propagacija**: `AIResponse.provider`/`ModelProfile.provider_code` MORAJU stvarno
  odražavati stvaran provider (ne lažno "openai") kad se koristi kroz DeepSeek/OpenRouter fabrike
  — probaj sa fabrikom + fake client, provjeri da response/models NIKAD ne kažu "openai"/"OPENAI".
- **Base URL tačnost**: DeepSeek `https://api.deepseek.com`, OpenRouter
  `https://openrouter.ai/api/v1` — provjeri protiv trenutne zvanične dokumentacije.
- **`base_url_mode` disciplina**: DeepSeek/OpenRouter FIXED (implementer ne prima base_url kao
  parametar spolja), generic OPENAI_COMPATIBLE USER_CONFIGURABLE (base_url je obavezan parametar)
  — provjeri protiv `resources/ai_providers/*.yaml`.
- **Regresija na postojeći OpenAI default ponašanje** — default `provider_code="OPENAI"`/
  `provider_display="openai"` moraju čuvati TAČNO staro ponašanje, ne samo "blizu".
  `test_generate_uses_default_provider_display` postoji za ovo — provjeri da stvarno testira
  default (bez eksplicitnih argumenata), ne slučajno prosljeđuje "OPENAI" eksplicitno.
- **Nema nove SDK zavisnosti** — `pyproject.toml` netaknut, provjeri da je to stvarno istina (ne
  da neka fabrika tiho uvozi nešto novo).

## Verifikacija koju možeš ponoviti

```bash
cd H:\ai-campaign-studio-worktrees\ACS-F1-017-openai-compatible-providers
pip install -e . --no-deps
pytest -q                                           # 652 passed (nezavisno potvrđeno)
ruff check .
mypy src
pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
```

## Kad završiš

Napiši svoj review izvještaj u `agent_reports/`. Ne commit-uj/merge-uj — Human Owner mora
eksplicitno odobriti nakon tvog i mog review-a.
