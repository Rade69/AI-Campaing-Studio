# → ZA PI — ACS-F1-017: počni implementaciju

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-04

Dodijeljen ti je **ACS-F1-017**, HIGH risk. Ovo je zadatak za implementaciju, odmah — pun kontrakt:
`agent_reports/ACS-F1-017-task-contract.md`.

## Radi ovdje

```text
cd H:\ai-campaign-studio-worktrees\ACS-F1-017-openai-compatible-providers
```

Worktree/branch su već kreirani, kontrakt je već tu.

## Ukratko

DeepSeek, OpenRouter i generički "OpenAI-kompatibilan" provajder svi izlažu OpenAI-kompatibilan
Chat Completions API. NE praviš 3 nova adaptera — ponovo koristiš postojeći `OpenAIAdapter`
(`infrastructure/ai/openai_adapter.py`, merged u ACS-F1-016) sa drugim `base_url`. Jedina izmjena
tom fajlu: on trenutno hardkoduje `provider="openai"`/`provider_code="OPENAI"` u tijelu
`generate()`/`discover_models()` — to treba postati konstruktorski parametar (default ostaje
"openai"/"OPENAI" da se ne pokvari ništa postojeće), inače bi DeepSeek/OpenRouter odgovori lagali
da su od OpenAI-ja.

Novi fajl `infrastructure/ai/openai_compatible_providers.py` — fabrike koje konstruišu
`OpenAIAdapter` sa tačnim base_url/provider_code po provajderu. DeepSeek/OpenRouter imaju FIKSAN
base_url (provjeri protiv zvanične dokumentacije, ne pretpostavljaj) — generički OpenAI-kompatibilan
prima base_url kao parametar (korisnik ga unosi).

## Read-set prije koda (obavezno)

Sve navedeno u kontraktovom "Obavezno pročitati prije koda" bloku — posebno cijeli postojeći
`openai_adapter.py` prije bilo kakve izmjene, i tri relevantna `resources/ai_providers/*.yaml`
fajla (deepseek/openrouter/openai_compatible) da vidiš `base_url_mode` razliku.

## Bitno

- Ne diraj `application/`, `ports/`, `ai_registry/`, `bootstrap.py`, `pyproject.toml` — sve već
  postoji generički iz ACS-F1-016, ne treba nova SDK zavisnost.
- Ako otkriješ da neki provajder NIJE dovoljno OpenAI-kompatibilan za reuse (npr. response shape
  razlike koje traže novi kod van "tanke fabrike") — zaustavi se, javi meni, ne izmišljaj workaround.
- Postojeći `test_openai_adapter.py` testovi MORAJU proći nepromijenjeni (ili minimalno
  prilagođeni uz jasno obrazloženje) — ovo je aditivna izmjena, ne refaktor.

## Kad završiš

Evidence izvještaj kao `agent_reports/2026-09-04-ACS-F1-017-pi.md`, ne commit-uj sam (§29 — HIGH
risk, ide na Codex adversarial review pa tek onda merge).
