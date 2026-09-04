# → ZA CODEX — ACS-F1-018 adversarial review (HIGH risk)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

## Status

ACS-F1-018 (Anthropic/Claude live adapter) je implementiran (MiniMax), prošao kroz jednu fix rundu
(BF-1: prompt-based JSON zamijenjen native `output_config` mehanizmom), moj arhitektonski review
je `PASS_WITH_NOTES`. Na tebi je adversarial review prije Human Owner odobrenja.

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-018-anthropic-adapter
Branch:   task/ACS-F1-018-anthropic-adapter (necommit-ovano, sinhronizovano sa main)
```

## Read-set

```text
agent_reports/ACS-F1-018-task-contract.md
agent_reports/2026-09-04-ACS-F1-018-minimax.md          (implementer evidence, uključuje BF-1 fix rundu)
agent_reports/2026-09-04-ACS-F1-018-review-claude.md    (moj review, u worktree-u)
src/ai_campaign_studio/infrastructure/ai/anthropic_adapter.py
tests/unit/infrastructure/ai/test_anthropic_adapter.py
pyproject.toml diff (anthropic>=0.30 -> anthropic>=1.0)
```

## Kontekst iz paralelnih taskova (relevantno za tvoj adversarial fokus)

Ovo je TREĆI provider adapter u seriji. Iz prethodna dva naučeno:
- **ACS-F1-016 (OpenAI)**: fake test fixture je maskirao `finish_reason` bug jer nije oblikovan
  kao stvaran SDK shape — provjeri da svi fake response-i u ovom test suite-u koriste STVARNE
  `anthropic.types.*` klase, ne pojednostavljene `SimpleNamespace`.
- **ACS-F1-017 (DeepSeek)**: bez server-side schema enforcement-a, model je vraćao pogrešan broj
  stavki u nizu. MiniMax je zato birao native `output_config` umjesto prompt-based pristupa —
  provjeri da je taj izbor stvarno ispravno implementiran (šema se ŠALJE serveru, ne samo
  spominje u promptu).
- **ACS-F1-017 re-review**: regex koji detektuje "exact count" iz teksta je imao false-positive
  bug (`discount`→"count"). Ovaj adapter NEMA takav regex (koristi native enforcement umjesto
  text-parsing-a) — provjeri da je to stvarno tako, da nije ostao neki trag stare prompt-based
  logike.

## Šta je posebno relevantno za tvoj adversarial fokus

- **`output_config` payload tačnost**: provjeri da `{"format": {"type": "json_schema", "schema":
  request.json_schema}}` stvarno stiže do `messages.create()` poziva, sa spy testom na argumente.
- **`system_text` MORA proći nemodifikovan** — provjeri test
  `test_generate_does_not_inject_schema_directive_into_system` stvarno to dokazuje (ne samo da
  test postoji, nego da asertuje tačno to).
- **Retry bound**: `_MAX_ATTEMPTS=2`, retry na `RateLimitError`/`APIConnectionError`/
  `APITimeoutError`, NE na `AuthenticationError`/`BadRequestError`.
- **Error mapping**: nikad sirov API ključ ili SDK exception tekst.
- **`pyproject.toml` lower bound**: `anthropic>=1.0` — provjeri da je ovo stvarno dovoljno
  (output_config garantovano dostupan od 1.0, ne od neke kasnije podverzije).
- **Test ključevi**: EXAMPLE-markirani format (`sk-ant-EXAMPLE-...`).

## Verifikacija koju možeš ponoviti

```bash
cd H:\ai-campaign-studio-worktrees\ACS-F1-018-anthropic-adapter
pip install -e ".[dev]"
pytest -q                                           # 673 passed (nezavisno potvrđeno)
ruff check .
mypy src
pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
```

**Nema live API poziva u ovoj rundi** — ni implementer ni koordinator nemaju Anthropic ključ. Ako
ti imaš pristup, live test bi bio vrijedan (isti obrazac kao DeepSeek/Google probe).

## Kad završiš

Napiši svoj review izvještaj u `agent_reports/`. Ne commit-uj/merge-uj — Human Owner mora
eksplicitno odobriti nakon tvog i mog review-a.
