# Codex review request — ACS-P0-005

Za: Codex (adversarial/test reviewer)
Od: Claude (koordinator)
Datum: 2026-09-01

## Kontekst

Paralelni task uz ACS-P0-006 (SQLite foundation, review se vodi odvojeno).
`allowed_paths` disjoint. Pi je predao vlastiti detaljan report (uključujući
oba adversarial dokaza) — koordinator je nezavisno ponovio oba i potvrdio.
Ovo je **security-osjetljiv** task (SecretStore) — Codex fokus treba biti
posebno agresivan na secret-leak scenarije.

## Read protocol

1. `AGENTS.md`, `CLAUDE.md`
2. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §14/§15
3. `.agent/CURRENT_STATE.md`
4. `agent_reports/ACS-P0-005-task-contract.md`
5. `agent_reports/2026-09-01-ACS-P0-005-pi-confirmed.md` (coordinator evidence)
6. Sam diff (vidi ispod)

## Šta pregledati

```text
Repo:     H:\AI Campaing Studio  (main branch)
Worktree: H:\ai-campaign-studio-worktrees\ACS-P0-005-ai-registry-secrets
Branch:   task/ACS-P0-005-ai-registry-secrets
Commit:   5517c8b (base: main@820bbf9)
```

```bash
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-005-ai-registry-secrets --stat
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-005-ai-registry-secrets
```

Koristi merge-base diff ako je main odmakao:
`git diff $(git merge-base main task/ACS-P0-005-ai-registry-secrets) task/ACS-P0-005-ai-registry-secrets`.
Svi fajlovi su NOVI. GitNexus `detect-changes` iz worktree-a neće raditi
(poznato ograničenje) — tretiraj kao `UNKNOWN`.

## Napomena o environment-u

Ako naiđeš na oštećen `pydantic_core`/mypy `librt` wheel u fresh `.venv`
(viđeno na ACS-P0-004/006 ovog ciklusa), fix je
`pip install --force-reinstall --no-cache-dir pydantic pydantic-core mypy`.

## Fokus review-a (security-critical)

1. **Secret leak kroz druge putanje koje test ne pokriva** — postojeći
   testovi provjeravaju `str(exc)`/`repr(exc)` i `caplog.text`. Probaj:
   `KeyringSecretStore.__repr__`/`__str__` default (dataclass-style ili
   Python default object repr) — da li ijedan atribut objekta ikad drži
   secret value nakon poziva (npr. da li se value cachira u
   `self`-nešto)? Trenutni kod ne cachira ništa u `self`, ali potvrdi
   pregledom.
2. **`secret_to_env_var` edge cases** — probaj `name` bez `"provider/"`
   prefiksa (npr. samo `"api_key"`), prazan string, `name` sa duplim
   slash-om (`"provider//api_key"`), `name` sa specijalnim karakterima.
   Provjeri da mapiranje ne producira collision (dva različita `name`
   mapiraju na isti env var) ili da barem ne puca na neočekivan način.
3. **`EnvironmentSecretStore.get_secret` sa praznim env var value** — ako
   je `AI_CAMPAIGN_STUDIO_OPENAI_API_KEY=""` (postavljen ali prazan), da li
   `get_secret` vraća `""` ili bi trebalo `None`? Kontrakt kaže "missing
   secret → None", provjeri da li prazan string računa kao "missing" ili
   je to legitimna (makar besmislena) vrijednost — nije nužno bug, ali
   provjeri da ponašanje ima smisla.
4. **Duplicate detection u registry-ju** (već izvršen dokaz od
   koordinatora, FAIL→PASS potvrđeno) — ponovi nezavisno da potvrdiš.
5. **`register_discovered_models` provider_code mismatch validacija** —
   test da li stvarno odbija model sa pogrešnim `provider_code` (kod ima
   provjeru u `registry.py`, potvrdi test postoji i stvarno pokriva to).
6. **Regresija** — 111 testova:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-005-ai-registry-secrets"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   ```
7. **Scope-clean diff + nema provider SDK/network** (grep za
   openai/anthropic/google.generativeai/requests importe u novim fajlovima).

## Traženi output

`agent_reports/2026-09-01-ACS-P0-005-review-codex.md`, isti format kao
`agent_reports/2026-09-01-ACS-P0-005-review-claude.md`.

Ako `PASS`/`PASS_WITH_NOTES` bez blocking findings, tražim Human Owner
odobrenje za merge (nezavisno od ACS-P0-006 statusa).
