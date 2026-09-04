---
verdict: REJECT
scope: PASS_WITH_NOTES
acceptance: REJECT
architecture: PASS
security: PASS_WITH_NOTES
tests: PASS_WITH_NOTES
gitnexus_impact: NOT_AVAILABLE
blocking_findings: [BF-1, BF-2]
---

CILJ: ACS-F1-016 treba dodati prvi live OpenAI adapter + provider setup use-case-e, uz bounded retry, safe error mapping, SecretStore referencu umjesto raw ključa, i potpuno offline test suite.
URAĐENO: REJECT — implementacija je blizu, ali dvije stvarne rupe ostaju: `finish_reason` se čita sa pogrešnog OpenAI objekta, a `ConfigureProvider` ignoriše kontraktni `requires_api_key` guard.
NE DIRATI: Ne dirati `bootstrap.py`, registry/secrets/provider-config portove, SQLite/migrations, mock adapter, Campaign Engine use-case-e, niti postojeći DI seam obrazac.
SLJEDEĆE: Implementer neka uradi usku fix rundu za BF-1/BF-2 + doda regresione testove; zatim vratiti Codex-u na re-review prije Human Owner odobrenja.

# ACS-F1-016 — Codex adversarial review

Pregledano prema:

- `agent_reports/2026-09-03-ACS-F1-016-brief-za-codex.md`
- `agent_reports/ACS-F1-016-task-contract.md`
- `agent_reports/2026-09-03-ACS-F1-016-crush.md`
- `agent_reports/2026-09-03-ACS-F1-016-review-claude.md`
- stvarni kod u `src/ai_campaign_studio/infrastructure/ai/openai_adapter.py`
- stvarni kod u `src/ai_campaign_studio/application/ai_provider/*.py`
- adapter/use-case/integration testovi u `tests/unit/...` i `tests/integration/application/ai_provider/`
- `pyproject.toml` i `tests/architecture/test_import_boundaries.py` diff

## Verdict

REJECT.

Nisam našao secret leak u error mapping-u, beskonačan retry, slučajni mrežni poziv u testovima, niti `application -> infrastructure` boundary proboj. F1 iz Claude review-a (`httpx` dev dependency) je stvarno zatvoren u `pyproject.toml`.

Ali našao sam dvije konkretne, reprodukovane rupe koje treba popraviti prije Human Owner approval-a.

## Blocking findings

### BF-1 — [medium] `OpenAIAdapter.generate()` gubi `finish_reason` sa real-shaped OpenAI response-a

Evidence:

- `src/ai_campaign_studio/infrastructure/ai/openai_adapter.py:115`
- `tests/unit/infrastructure/ai/test_openai_adapter.py:37`
- moja adversarial proba:

```text
openai_version=2.38.0
finish_reason=None
```

Failure path:

OpenAI Chat Completions response drži `finish_reason` na choice objektu (`completion.choices[0].finish_reason`), dok `message` nosi sadržaj (`completion.choices[0].message.content`). Implementacija radi:

```python
message = completion.choices[0].message
...
finish_reason=getattr(message, "finish_reason", None)
```

Test fixture slučajno maskira bug jer pravi fake response sa `finish_reason` na `message`:

```python
message = SimpleNamespace(content=content, finish_reason="stop")
choice = SimpleNamespace(message=message)
```

Sa realnijim fake objektom:

```python
message = SimpleNamespace(content='{"result":"ok"}')
choice = SimpleNamespace(message=message, finish_reason="stop")
```

adapter vraća `AIResponse.finish_reason is None`.

Impact:

Live OpenAI responses će gubiti finish reason telemetry/status. To je ograničen defekt, ali realan: downstream kod neće moći razlikovati normalan stop od length/content-filter/tool cutoff signala kada počne koristiti `AIResponse.finish_reason`.

Recommended correction:

U `_generate_once()` zadržati `choice = completion.choices[0]`, čitati `message = choice.message`, a `finish_reason=getattr(choice, "finish_reason", None)`. Dodati regression test koji fake response oblikuje kao stvarni OpenAI shape: `finish_reason` na `choice`, ne na `message`.

### BF-2 — [medium] `ConfigureProvider` ne provjerava `requires_api_key` prije upisa secreta

Evidence:

- kontrakt: `agent_reports/ACS-F1-016-task-contract.md:213` izričito traži potvrdu da provider postoji i `requires_api_key`
- `src/ai_campaign_studio/application/ai_provider/configure_provider.py` nema nijednu `requires_api_key` provjeru
- testovi pokrivaju samo provider sa `requires_api_key=True`: `tests/unit/application/ai_provider/test_configure_provider.py:61`
- moja adversarial proba:

```text
noauth_configured=True secret_names=['provider/NOAUTH/api_key']
```

Failure path:

`ConfigureProvider.execute()` učita provider preko registry-ja i odmah konstruiše:

```python
credential_ref = f"provider/{provider.provider_code}/api_key"
self._secret_store.set_secret(credential_ref, api_key)
```

Ako registry vrati validan provider sa `requires_api_key=False`, use-case ga ipak označi kao configured i upiše secret. To je direktno suprotno task contract-u.

Impact:

Trenutno je OpenAI happy path pogođen manje jer bundled OpenAI provider zaista ima `requires_api_key=True`. Ipak, use-case je generički `ConfigureProvider`, a A8 roadmap eksplicitno uvodi druge provider-e kasnije. Ova rupa bi za no-key/provider-with-other-auth scenario kreirala lažnu credential referencu i pogrešno stanje konfiguracije.

Recommended correction:

Nakon `provider_registry.get_provider(provider_code)`, dodati eksplicitan guard za `not provider.requires_api_key` koji vraća/podiže projektno odgovarajuću domensku grešku (npr. `InvariantViolation` sa jasnom porukom da ovaj use-case konfiguriše samo API-key provider-e). Regression test: fake provider sa `requires_api_key=False`; dokazati da `secret_store.set_secret` i `save_provider_config` nisu pozvani.

## Coverage reviewed

Pregledao sam:

- kompletan `OpenAIAdapter`
- sva 4 provider setup use-case-a
- adapter unit testove
- provider use-case unit testove
- provider setup SQLite integration test
- `pyproject.toml` dependency diff
- `tests/architecture/test_import_boundaries.py` carve-out diff
- literal key scan oko `sk-` test vrijednosti
- stvarni status/diff scope

Scope:

`git status --short --branch` pokazuje očekivane F1-016 promjene:

```text
## task/ACS-F1-016-openai-adapter
 M pyproject.toml
 M tests/architecture/test_import_boundaries.py
?? agent_reports/2026-09-03-ACS-F1-016-crush.md
?? agent_reports/2026-09-03-ACS-F1-016-review-claude.md
?? src/ai_campaign_studio/application/ai_provider/
?? src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
?? tests/integration/application/ai_provider/
?? tests/unit/application/ai_provider/
?? tests/unit/infrastructure/ai/test_openai_adapter.py
```

Napomena: branch `task/ACS-F1-016-openai-adapter` je jedan koordinator-state commit iza `main` (`main` ima noviji `.agent/CURRENT_STATE.md`). To ne mijenja reviewed implementation scope, ali prije finalnog merge-a treba uskladiti branch/main state da se ne unese koordinacioni drift.

## Verification evidence

Targeted provider/adapter suite:

```text
python -m pytest tests\unit\infrastructure\ai\test_openai_adapter.py tests\unit\application\ai_provider tests\integration\application\ai_provider -q -p no:cacheprovider
23 passed in 2.36s
```

Architecture boundaries:

```text
python -m pytest tests\architecture\test_import_boundaries.py -q -p no:cacheprovider
18 passed in 0.24s
```

Mypy, with explicit local cache because default mypy cache path hit a Windows permission/SQLite cache issue:

```text
python -m mypy src --cache-dir .tmp_codex_review\mypy_cache
Success: no issues found in 134 source files
```

Ruff:

```text
python -m ruff check .
warning: Encountered error: Access is denied. (os error 5)
warning: Encountered error: Access is denied. (os error 5)
All checks passed!
```

Secret scan:

```text
python scripts\check_no_secrets.py
NO CONFIRMED SECRET IN TRACKED FILES
```

Full pytest:

```text
python -m pytest -q -p no:cacheprovider
1 failed, 642 passed in 46.34s
```

The single failure is `tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes`. The generated gate report says every inner check passes except `ruff:false`, while direct `python -m ruff check .` passes. In this review environment, pytest/temp/cache operations also hit Windows permission issues unless forced to a local temp/cache directory. I am therefore not treating the full-pytest gate-report failure as an ACS-F1-016 code finding; it is a test-environment/gate interaction to re-run cleanly after the fix round.

GitNexus:

```text
npx gitnexus detect-changes --repo AI-Campaing-Studio
```

Result: NOT_AVAILABLE for this worktree. GitNexus warns that the index was built at `H:\AI Campaing Studio`, while cwd is sibling worktree `H:\ai-campaign-studio-worktrees\ACS-F1-016-openai-adapter`; then its internal `git diff -U0` fails with "Not a git repository". This matches the known worktree-binding limitation in `.agent/CURRENT_STATE.md`. I compensated with manual `git status`, `git diff`, source/test read, and targeted live probes.

## Adversarial checks

1. Retry bound: existing test uses repeated `RateLimitError` side effect and asserts `call_count == OpenAIAdapter._MAX_ATTEMPTS`; code confirms only `RateLimitError`/`APIConnectionError` retry, not `AuthenticationError` or generic `OpenAIError`.
2. No raw key in mapped errors: `_map_error()` returns generic `InfrastructureError` messages (`OpenAI rate limit exceeded`, `OpenAI connection error`, `OpenAI API key invalid`, `OpenAI provider error`) without including SDK exception text.
3. Test keys: new test literals are `sk-EXAMPLE-*`; `rg -n sk- src tests agent_reports pyproject.toml` found no new non-placeholder key-shaped test value in the F1-016 implementation scope.
4. Real-shaped completion probe found BF-1.
5. `requires_api_key=False` provider probe found BF-2.

## Not verified

- I did not make a live OpenAI network call with a real API key; the Human Owner decision says automated tests must be offline and live key is not required for review.
- I did not get a clean full `pytest -q` PASS in this sandbox because the phase0 gate-report e2e reports `ruff:false` while direct ruff passes, and several default temp/cache paths hit Windows permission issues. Targeted F1-016 tests, architecture tests, direct ruff, direct mypy, and direct secret scan were run as listed above.

## Fix-round scope

Keep the fix tight:

1. BF-1: read `finish_reason` from `choice`, and add a regression test with real-shaped fake response.
2. BF-2: enforce `requires_api_key` in `ConfigureProvider`, and add a regression test proving no secret/config write happens for non-API-key providers.
3. Re-run targeted suite + architecture + ruff + mypy + secret scan; then re-run full pytest in a clean local environment if possible.

