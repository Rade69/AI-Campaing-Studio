# → ZA CRUSH — ACS-F1-019: počni implementaciju

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-04

Dodijeljen ti je **ACS-F1-019**, HIGH risk. Ovo je zadatak za implementaciju, odmah — pun kontrakt:
`agent_reports/ACS-F1-019-task-contract.md`.

## Radi ovdje

```text
cd H:\ai-campaign-studio-worktrees\ACS-F1-019-google-adapter
```

Worktree/branch su već kreirani, kontrakt je već tu.

## Ukratko

Praviš `GoogleAdapter(TextGenerationPort)` u `infrastructure/ai/google_adapter.py` — prvi adapter
za Google (Gemini) API u ovom projektu. Referentan primjer discipline (retry/error-mapping/DI-seam)
je već merged `infrastructure/ai/openai_adapter.py` (ti si ga i pisao u ACS-F1-016) — pogledaj ga
kao PRIMJER DISCIPLINE, ne kao kod za kopiranje. Gemini API je strukturno drugačiji.

**PRVI KORAK JE ISTRAŽIVANJE, NE KOD**: kontrakt namjerno ne propisuje tačan SDK jer je Google-ov
Python AI SDK ekosistem bio u tranziciji (stariji `google-generativeai` vs noviji unificirani
`google-genai`) i nisam siguran koji je trenutno kanonski za nov kod. Provjeri stvarno, trenutno
stanje prije pisanja adaptera — koji paket, tačan shape poziva, mehanizam strukturisanog izlaza, da
li models-list radi.

## Read-set prije koda (obavezno)

Sve navedeno u kontraktovom "Obavezno pročitati/istražiti prije koda" bloku.

## Bitno — lekcija iz ACS-F1-016 (svoju grešku ne ponavljaj)

Sjećaš se F1 (nedeklarisan `httpx`) i BF-1 (fake test response koji je maskirao `finish_reason`
bug jer nije bio oblikovan kao stvaran SDK shape). Za ovaj task: (1) ako novi SDK povlači neku
tranzitivnu test-zavisnost, deklariši je ODMAH eksplicitno u `pyproject.toml` dev extras; (2) fake
response fixture-i MORAJU biti oblikovani kao STVARAN Google SDK shape, ne pojednostavljena
struktura koja slučajno prikriva bug.

## Ne diraj

`application/`, `ports/`, `ai_registry/`, `bootstrap.py`, `openai_adapter.py`,
`openai_compatible_providers.py` (paralelan task, ACS-F1-017), `anthropic_adapter.py` (paralelan
task, ACS-F1-018).

## Kad završiš

Evidence izvještaj kao `agent_reports/2026-09-04-ACS-F1-019-crush.md`, ne commit-uj sam (§29 —
HIGH risk, ide na Codex adversarial review pa tek onda merge).
