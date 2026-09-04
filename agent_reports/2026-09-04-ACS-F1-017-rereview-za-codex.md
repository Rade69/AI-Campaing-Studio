# → ZA CODEX — ACS-F1-017 re-review (BF-1 fix, live-verifikovan)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

## Status

Pi je popravio BF-1 (DeepSeek je odbijao `response_format: json_schema` — nalaz iz ručne live
validacije Human Owner-a). Ja sam nezavisno provjerio kod I live-testirao fix protiv pravog
DeepSeek API-ja (ne samo mock). Moj review: `PASS`.

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-017-openai-compatible-providers
Branch:   task/ACS-F1-017-openai-compatible-providers (necommit-ovano, sinhronizovano sa main)
```

## Read-set

```text
agent_reports/ACS-F1-017-task-contract.md
agent_reports/2026-09-04-ACS-F1-017-pi.md              (implementer evidence, "Fix runda (BF-1)" sekcija na dnu)
agent_reports/2026-09-04-ACS-F1-017-review-claude.md   (moj review, u worktree-u — sadrži moju live proba)
src/ai_campaign_studio/infrastructure/ai/openai_adapter.py      (nov: structured_output_mode parametar)
src/ai_campaign_studio/infrastructure/ai/openai_compatible_providers.py
tests/unit/infrastructure/ai/test_openai_adapter.py
tests/unit/infrastructure/ai/test_openai_compatible_providers.py
```

## Šta je posebno relevantno za tvoj adversarial fokus

- **`json_schema` (OpenAI default) put mora ostati BAJT-ZA-BAJT isti** kao prije BF-1 fix-a —
  provjeri da `structured_output_mode` default ne mijenja postojeće OpenAI ponašanje na bilo koji
  način (ovo sam ja provjerio čitanjem, ali probaj i sam).
- **Exact-count mehanizam** — dvije nezavisne putanje detekcije (`minItems==maxItems` u schema-i,
  `*_count: N` regex u user_text-u). Probaj adversarial slučajeve: schema BEZ `minItems`/`maxItems`
  ali SA `content_piece_count` u tekstu (mora i dalje raditi — ovo je stvaran slučaj,
  `CampaignPlanOutput` schema nema array bounds); regex lažni pozitiv (npr. neko drugo polje koje
  sadrži "count" u imenu, ali nije broj stavki); prazan `array_constraints`+`count_constraints`
  (mora graciozno preskočiti "Exact count requirements" sekciju, ne dodati prazan blok).
- **Provjeri da `json_object` mod STVARNO nikad ne šalje `json_schema` response_format** — testiraj
  sa mock klijentom koji bi pukao na neočekivan `response_format` ključ.
- **DeepSeek/OpenRouter/generic default izbori** — DeepSeek `json_object` (live-verifikovano),
  OpenRouter `json_object` (KONZERVATIVNO, ne live-verifikovano — provjeri da je to jasno
  dokumentovano kao pretpostavka, ne tvrdnja), generic default `json_object` sa mogućnošću
  eksplicitnog `json_schema`.
- **Nema nove SDK zavisnosti**, `pyproject.toml` netaknut — provjeri.

## Verifikacija koju možeš ponoviti

```bash
cd H:\ai-campaign-studio-worktrees\ACS-F1-017-openai-compatible-providers
pip install -e . --no-deps
pytest -q                                           # 655 passed (nezavisno potvrđeno)
ruff check .
mypy src
pytest tests/architecture/test_import_boundaries.py -v
python scripts/check_no_secrets.py
```

Ako imaš pristup DeepSeek ključu, slobodno ponovi i live poziv preko `build_deepseek_adapter` —
ja sam to već uradio i potvrdio (tačno 3 stavke, stvaran sadržaj, nema 400 greške), ali nezavisna
druga potvrda je uvijek vrijedna.

## Kad završiš

Napiši svoj review izvještaj u `agent_reports/`. Ne commit-uj/merge-uj — Human Owner mora
eksplicitno odobriti nakon tvog i mog review-a.
