# → ZA PI — ACS-F1-020 (claim_linter word-boundary bug)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-04

Ovo je ista klasa greške koju si već popravio u R2-BF-1
(`_COUNT_LINE_RE`, ACS-F1-017) — substring match bez granice riječi,
samo ovaj put u `claim_linter.py`, koji nikad nisi ti pisao (A12 dio 1,
ranije), ali si već dokazano dobar u ovom tačnom obrascu fixa.

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-F1-020-task-contract.md](agent_reports/ACS-F1-020-task-contract.md)
(`main @ 0aa264e`).

## Kratko, u čemu je bug

`src/ai_campaign_studio/application/posts/claim_linter.py` — i
`lint_claim` (prohibited terms) i `_numeric_reason_code` (duration units,
currency symbols) koriste `term in text_folded` umjesto word-boundary
regexa. Nezavisno sam reprodukovao:

- `"Ordinacija ima tri jedinice..."` (VERIFIED_BY_FACT tvrdnja) →
  pogrešno postaje `PROHIBITED` jer `"jedinice"` sadrži `"jedini"`.
- `"Posjetite nas danas..."` (obična CTA) → pogrešno dobija
  `unsupported-duration` jer `"danas"` sadrži `"dan"`.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-020-claim-linter-word-boundary
Branch:   task/ACS-F1-020-claim-linter-word-boundary
Base:     main @ 0aa264e
```

Worktree je već kreiran. Prije testova:

```bash
python -m pip install -e . --no-deps -q
```

## Šta uraditi

Kontrakt ima tačan opis (Implementation steps 1-5), plus jedna stvar koju
spoljni review NIJE testirao ali koja ima identičnu manu — currency
symbol provjera (`symbol.casefold() in text_folded`). Popravi i to, isti
obrazac, sa bar jednim regresionim testom.

**Pazi na multi-word termine** ("bez rizika", "potpuno sigurno") —
word-boundary na cijeloj frazi (`\bbez rizika\b`) i dalje treba raditi
ispravno, ne razbijaj to. Dodaj eksplicitan test da dokažeš da fix ne
kvari taj slučaj.

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-F1-020-pi.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju). MEDIUM risk — nakon
mog review-a, ako PASS, ide direktno na merge (§29, bez Codex runde).
