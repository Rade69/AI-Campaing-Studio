# → ZA MINIMAX — ACS-GUI-007 (Podešavanja: real provider config)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Human Owner je ovo odobrio kao sljedeći prioritet, prije G10 rada —
praktičan blocker koji sam našao u N2 napomeni ACS-GUI-005 review-a:
prava aplikacija danas ne može stvarno sačuvati API ključ kroz GUI, samo
kroz ručnu skriptu. Ti si napisao originalni bridge, pa je logično da
nastaviš na istom kodu.

## Prvi korak

Pročitaj kontrakt u cijelosti:
[agent_reports/ACS-GUI-007-task-contract.md](agent_reports/ACS-GUI-007-task-contract.md)
(`main @ b1a7789`).

## Ključna stvar koju kontrakt zaključava (ne improvizuj)

`AppSettings(environment="production")` ide SAMO u `CampaignBridgeApi.__init__`
kao default za novi `settings` test seam (simetričan postojećem `paths`
seam-u) — `bootstrap.py`-ov `create_bootstrap()` default OSTAJE
"development" za sve ostale pozivaoce. Provjerio sam unaprijed
(`grep settings.environment`) da to polje ima TAČNO JEDNO mjesto upotrebe
u cijelom kodu (`bootstrap.py:144`, bira secret store) — ali Codex će to
nezavisno provjeriti u review-u, pa i ti provjeri sam prije nego predaš.

## Bitno: postojeći bridge testovi

Nakon što default postane "production", SVI postojeći testovi koji
instanciraju `CampaignBridgeApi()` bez override-a bi počeli dirati PRAVI
OS keyring tokom test run-a. Moraš ih SVE ažurirati da eksplicitno
proslijede `settings=AppSettings(environment="development")` (ili
ekvivalentan test fake). Ovo je najlakše mjesto da nešto proklizi — budi
temeljit.

## Gdje raditi

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config
Branch:   task/ACS-GUI-007-provider-config
Base:     main @ b1a7789
```

Worktree je već kreiran.

```bash
python -m pip install -e . --no-deps -q
```

## Risk i review put

HIGH — prvi put da secret string ULAZI u bridge OD JS-a (do sad je samo
izlazio iz njega server-side). Pun ciklus: tvoj rad → Claude review →
Codex adversarial review → moje odobrenje. Kontrakt ima obavezan "Live
funkcionalna provjera" korak — moraš stvarno provjeriti da se ključ
upisao u keyring, ne samo da test prolazi.

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-GUI-007-minimax.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju).
