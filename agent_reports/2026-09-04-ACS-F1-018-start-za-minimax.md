# → ZA MINIMAX — ACS-F1-018: počni implementaciju

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Dodijeljen ti je **ACS-F1-018**, HIGH risk. Ovo je zadatak za implementaciju, odmah — pun kontrakt:
`agent_reports/ACS-F1-018-task-contract.md`.

## Radi ovdje

```text
cd H:\ai-campaign-studio-worktrees\ACS-F1-018-anthropic-adapter
```

Worktree/branch su već kreirani, kontrakt je već tu.

## Ukratko

Praviš `AnthropicAdapter(TextGenerationPort)` u `infrastructure/ai/anthropic_adapter.py` — prvi
adapter za Anthropic (Claude) API u ovom projektu. Referentan primjer discipline (retry/error-
mapping/DI-seam) je već merged `infrastructure/ai/openai_adapter.py` — pogledaj ga PRIJE nego što
počneš, ali NE kopiraj doslovno: Anthropic Messages API je strukturno drugačiji od OpenAI-jevog
(sistemski prompt je zaseban parametar, ne poruka u listi; response sadržaj je lista blokova ne
string; `stop_reason` umjesto `finish_reason`; drugačija error hijerarhija).

**PRVI KORAK JE ISTRAŽIVANJE, NE KOD**: kontrakt namjerno ne propisuje tačne SDK pozive jer nisam
siguran da moje znanje o trenutnoj Anthropic Python SDK verziji nije zastarjelo. Provjeri stvarnu,
trenutnu dokumentaciju/SDK prije pisanja adaptera — posebno mehanizam strukturisanog (JSON schema)
izlaza i da li `models.list()` postoji i radi.

## Read-set prije koda (obavezno)

Sve navedeno u kontraktovom "Obavezno pročitati/istražiti prije koda" bloku.

## Bitno — lekcija iz ACS-F1-016 (ne ponoviti)

Prošli put je fake test response koristio pojednostavljen shape koji je slučajno maskirao stvaran
bug (`finish_reason` na pogrešnom objektu). Fake response fixture-i u tvojim testovima MORAJU biti
oblikovani kao STVARAN Anthropic SDK shape — provjeri stvarne pydantic/dataclass tipove iz `anthropic`
paketa, ne izmišljaj pojednostavljenu strukturu.

Takođe iz prošlog puta: ako `anthropic` SDK povlači neku tranzitivnu test-zavisnost, deklariši je
ODMAH eksplicitno u `pyproject.toml` dev extras — ne čekaj da to review nađe.

## Ne diraj

`application/`, `ports/`, `ai_registry/`, `bootstrap.py`, `openai_adapter.py`,
`openai_compatible_providers.py` (paralelan task, ACS-F1-017).

## Kad završiš

Evidence izvještaj kao `agent_reports/2026-09-04-ACS-F1-018-minimax.md`, ne commit-uj sam (§29 —
HIGH risk, ide na Codex adversarial review pa tek onda merge).
