# → ZA CODEX — ACS-F1-019 adversarial review (HIGH risk)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

## Status

ACS-F1-019 (Google/Gemini live adapter, `google-genai` SDK) je implementiran (Crush), moj
arhitektonski review je `PASS_WITH_NOTES`. Na tebi je adversarial review prije Human Owner
odobrenja.

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-019-google-adapter
Branch:   task/ACS-F1-019-google-adapter (necommit-ovano, sinhronizovano sa main)
```

## Read-set

```text
agent_reports/ACS-F1-019-task-contract.md
agent_reports/2026-09-04-ACS-F1-019-crush.md              (implementer evidence — SDK istraživanje)
agent_reports/2026-09-04-ACS-F1-019-review-claude.md      (moj review, u worktree-u)
src/ai_campaign_studio/infrastructure/ai/google_adapter.py
tests/unit/infrastructure/ai/test_google_adapter.py
pyproject.toml diff (google-genai>=1.0)
```

## Šta je posebno relevantno za tvoj adversarial fokus

- **SDK shape tačnost**: Ja sam nezavisno instalirao `google-genai` u worktree-u i provjerio SVAKI
  korišten tip (`GenerateContentConfig`, `Content`, `Part`, `Candidate`,
  `GenerateContentResponse`, `GenerateContentResponseUsageMetadata`, `ClientError`) — sve se
  poklapa. Slobodno ponovi tu provjeru sam, posebno ako sumnjaš na nešto specifično.
- **Retry bound**: `_MAX_ATTEMPTS=2`, retry samo na `ServerError`/`ClientError(429)`, NE na
  `ClientError(401/403)` (autentikacija ne smije retry-ovati). Provjeri da nema puta ka
  beskonačnoj petlji.
- **Error mapping**: nikad sirov API ključ ili SDK exception tekst u poruci grešku.
- **`test_connection()`**: `ClientError` 401/403 → `False` (legitiman rezultat), SVE ostalo →
  `InfrastructureError` (uključujući `ClientError(429)` — provjeri da se rate limit na
  test_connection ne tretira kao "nevalidan ključ", test to pokriva ali provjeri semantiku).
- **Test ključevi**: `"AIza-EXAMPLE-key"` format — provjeri da nigdje ne curi nešto što liči na
  stvaran Google API key.
- **`response_json_schema` vs `response_schema`**: SDK ima OBA polja na `GenerateContentConfig` —
  provjeri da je adapter dosljedno koristio `response_json_schema` (raw JSON schema dict, ne
  Pydantic model) svuda gdje treba.

## Verifikacija koju možeš ponoviti

```bash
cd H:\ai-campaign-studio-worktrees\ACS-F1-019-google-adapter
pip uninstall google-genai -y && pip install -e ".[dev]" && pytest -q   # 655 passed (nezavisno potvrđeno)
ruff check .
mypy src
pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
```

## Kad završiš

Napiši svoj review izvještaj u `agent_reports/`. Ne commit-uj/merge-uj — Human Owner mora
eksplicitno odobriti nakon tvog i mog review-a.
