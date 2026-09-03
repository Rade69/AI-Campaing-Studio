# → ZA CODEX — ACS-F1-016 adversarial review (HIGH risk)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-03

## Status

ACS-F1-016 (OpenAI live adapter + provider-setup use-case-i, A8 dio 2) je implementiran
(Crush), arhitektonski review odrađen (Claude) — `PASS_WITH_NOTES`, jedini blocking nalaz
(F1, nedeklarisana `httpx` test-zavisnost) je pronađen, popravljen i nezavisno reverifikovan.
**Sad je na tebi** — HIGH risk politika (SecretStore dodir + prvi stvaran vanjski API poziv u
projektu) zahtijeva tvoj adversarial review PRIJE Human Owner odobrenja, bez izuzetka.

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-016-openai-adapter
Branch:   task/ACS-F1-016-openai-adapter (necommit-ovano, sinhronizovano sa main)
```

## Read-set

```text
agent_reports/ACS-F1-016-task-contract.md
agent_reports/2026-09-03-ACS-F1-016-crush.md            (implementer evidence + F1 fix runda)
agent_reports/2026-09-03-ACS-F1-016-review-claude.md    (moj arhitektonski review, u worktree-u)
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py
src/ai_campaign_studio/application/ai_provider/*.py
tests/unit/infrastructure/ai/test_openai_adapter.py
tests/unit/application/ai_provider/
tests/integration/application/ai_provider/
```

## Šta je posebno relevantno za tvoj adversarial fokus

- **Retry bound**: `_MAX_ATTEMPTS = 2`, samo na `RateLimitError`/`APIConnectionError`. Provjeri
  da nema puta ka beskonačnoj petlji, da se retry ne dešava na `AuthenticationError`
  (autentikacija treba odmah da failuje, ne da retry-uje).
- **Error mapping** (`_map_error`): nikad sirov SDK exception ili API ključ ne curi u poruku
  greške — provjeri sve grane, ne samo happy path.
- **`credential_ref`**: striktno string referenca kroz cijeli tok
  (`ConfigureProvider`→`SecretStorePort`→`ProviderConfig`) — provjeri da nigdje ne prolazi
  sirov ključ kroz log/serijalizaciju/exception message.
- **Test fixture ključevi**: svi moraju biti `EXAMPLE`-markirani (ACS-P0-008 lekcija o GitHub
  push protection false positives) — provjeri da nijedan izgleda kao stvaran ključ.
- **DI seam odluka**: `TestProviderConnection`/`DiscoverModels` primaju adapter kroz lokalni
  `Protocol`, ne konstruišu `OpenAIAdapter` interno — provjeri da ovo stvarno drži
  `application → infrastructure` granicu (ne samo da test prolazi slučajno).
- **Mock/transport izolacija**: cijeli test suite mora proći BEZ pravog API ključa i BEZ
  stvarnog mrežnog poziva (Human Owner eksplicitna odluka) — provjeri da nijedan test
  slučajno ne pravi pravi HTTP zahtjev (npr. fixture koji zaboravi mock-ovati transport).

## Verifikacija koju možeš ponoviti

```bash
cd H:\ai-campaign-studio-worktrees\ACS-F1-016-openai-adapter
pip uninstall httpx -y && pip install -e ".[dev]" && pytest -q   # 643 passed (nezavisno potvrđeno)
ruff check .
mypy src
pytest tests/architecture/test_import_boundaries.py -v            # 18 passed
python scripts/check_no_secrets.py
```

## Kad završiš

Napiši svoj review izvještaj u `agent_reports/` (format po projektnoj konvenciji — vidi moj
`2026-09-03-ACS-F1-016-review-claude.md` kao primjer strukture). Ne commit-uj/merge-uj —
Human Owner mora eksplicitno odobriti nakon tvog i mog review-a, čak i ako je tvoj verdict PASS.
