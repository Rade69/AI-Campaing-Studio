# → ZA PI — ACS-F1-015 brief

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-03

## Status — spreman, ništa ne blokira

Prvi od dva taska za A8 (live AI adapters). Ništa ga ne blokira — `provider_configs`/
`model_selections` tabele postoje od P0, samo ih niko još nije koristio.

## Gdje je pun kontrakt

`agent_reports/ACS-F1-015-task-contract.md` — pročitaj ga cijelog.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-015-provider-config-persistence
Branch:   task/ACS-F1-015-provider-config-persistence
```

**Napomena o imenovanju**: ovaj task se ranije zvao "FLOW-1002" — vratili smo se na `ACS-F1-`
šemu, ignoriši svako "FLOW" ako ga negdje vidiš u starim referencama.

## Ukratko šta radiš

Čist persistence sloj, BEZ SecretStore-a, BEZ mrežnih poziva — priprema teren za drugi task
(ACS-F1-016, OpenAI adapter, HIGH, blokiran na ovom).

1. **`ports/provider_config.py`** — `ProviderConfig`/`ModelSelection` dataclass-e (kontrakt ima
   tačna polja) + `ProviderConfigRepositoryPort`/`ModelSelectionRepositoryPort` Protocol-i
   (`@runtime_checkable`, isti stil kao `ports/repositories.py`).
2. **`infrastructure/database/repositories/sqlite_provider_config_repository.py`** — SQLite
   adapter nad VEĆ POSTOJEĆIM `provider_configs`/`model_selections` tabelama (nema nove
   migracije — DDL je već u `resources/migrations/0000_foundation.sql`, kontrakt ima tačne
   kolone). Isti upsert obrazac kao `sqlite_campaign_repository.py`.

## Pažnja — najlakše mjesto da se nešto zeza

- `credential_ref` je STRING REFERENCA (npr. `"provider/OPENAI/api_key"`), NIKAD stvaran API
  ključ — ovaj task ne uvozi `ports/secrets.py`/`infrastructure/secrets/` nigdje.
- `bool` kolone (`configured`/`validated`) moraju STVARNO round-trip-ovati kao `bool`, ne
  procuriti kao `0`/`1` int.
- Idempotentnost (`ON CONFLICT DO UPDATE`) — test sa `COUNT(*)` provjerom, ne samo da test
  prolazi.

## Van scope-a

`ports/ai_registry.py`/`ai_registry/` — drugi koncept (definicija provajdera, ne korisnikovo
stanje konfiguracije), ne diraj. `infrastructure/database/repositories/__init__.py` — ja dodajem
re-export nakon merge-a (isti obrazac kao ACS-F1-006).
