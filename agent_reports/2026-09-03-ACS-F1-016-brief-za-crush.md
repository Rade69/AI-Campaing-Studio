# → ZA CRUSH — ACS-F1-016 brief

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-03

## Status — UNBLOCKED, ali HIGH risk, pažljivo pročitaj prije koda

ACS-F1-015 (persistence sloj) je mergovan — možeš krenuti. Ali ovo je **prvi task u projektu koji
dodiruje SecretStore i pravi pravi vanjski API poziv** → puni Codex+Claude+Human Owner ciklus, ne
streamlined MEDIUM put kao dosadašnji taskovi koje si radio.

## Gdje je pun kontrakt

`agent_reports/ACS-F1-016-task-contract.md` — OBAVEZNO pročitaj cijeli prije koda, ovo je gušći i
rizičniji kontrakt od prosjeka.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-016-openai-adapter
Branch:   task/ACS-F1-016-openai-adapter
```

**Prvi korak**: `git merge main` u worktree PRIJE bilo kakvog koda — worktree je granat prije
ACS-F1-015 merge-a, treba ti `ports/provider_config.py`.

## Ukratko šta radiš

1. **`OpenAIAdapter`** (`infrastructure/ai/openai_adapter.py`) — implementira `TextGenerationPort`
   (`generate()`) + VLASTITE `test_connection()`/`discover_models()` metode (NE generički
   `AIProviderConnectionPort` — kontrakt objašnjava zašto).
2. **Četiri use-case-a** u novom `application/ai_provider/` paketu: `ConfigureProvider`,
   `TestProviderConnection`, `DiscoverModels`, `SelectDefaultModel`.
3. **`pyproject.toml`** — dodaj `openai` (ili izabran HTTP klijent) kao zavisnost, dokumentuj
   izbor.

## Najvažnije — dva pravila koja se NE pregovaraju

1. **Cijeli automatski test suite MORA proći BEZ pravog API ključa** — HTTP/SDK transport se
   MOCK-UJE u potpunosti, nijedan test ne smije praviti stvaran mrežni poziv. Ovo je eksplicitna
   Human Owner odluka (2026-09-03), ne prijedlog.
2. **`bootstrap.py` se NE DIRA** — čuva postojeću "fully offline by design" invarijantu.
   Use-case-i/adapter se ne žice u composition root u ovom tasku.

## Retry policy (plan sekcija 20, doslovno)

Schema-repair retry (2 pokušaja sa eksplicitnom repair instrukcijom) je APPLICATION-layer
odgovornost — NE gradiš je u ovom tasku. Network/rate-limit retry SMIJE biti u adapteru, ali
OGRANIČEN (npr. 2 pokušaja, ti biraš i dokumentuješ) — ne beskonačna petlja. Svaki retry MORA biti
logovan (standardni `logging` modul).

## Adversarijalna provjera (obavezna, `adversarial_required: true`)

Barem jedan test koji dokazuje da retry STVARNO staje: mock transport koji UVIJEK failuje mora
dati jasnu grešku u razumnom broju poziva, ne visjeti/petljati beskonačno.

## Van scope-a

`AIProviderConnectionPort` implementacija (generički multi-provider dispatch — prerano dok postoji
samo OpenAI), `ports/ai_registry.py`/`ports/secrets.py`/`ai_registry/`/`infrastructure/secrets/`
(koristiš, ne mijenjaš), ostalih 5 provajdera (Anthropic/Google/DeepSeek/OpenRouter/OpenAI-
compatible — budući odvojeni taskovi).

## Review

Codex ide prvi (adversarial/retry/error-mapping fokus), ja poslije (arhitektura — SecretStore
korišten ispravno, `bootstrap.py` netaknut). Bez Human Owner "odobravam" nema merge-a, bez obzira
na Codex/Claude PASS.
