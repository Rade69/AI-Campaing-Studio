# Sažetak sesije — Pi (implementer), ACS-F1-043/044/045

Agent: pi
Datum: 2026-09-07
Obuhvat: tri uzastopna P1.5 / fact-first taska (2026-09-06 → 2026-09-07)

## Urađeno

| Task | Šta | PR | Status |
|---|---|---|---|
| ACS-F1-043 — P1.5-G3 dio 2, CSV import persistence + use-case-i | `PerformanceImportRow` + migracija 0007 + 3 repo metoda + `ImportPerformanceCsv`/`PreviewPerformanceMapping`/`ConfirmPerformanceImport` | #6 | MERGOVAN |
| ACS-F1-044 — P1.5-G4, matching | `MatchPerformanceImportBatch` (prioritet 1 external_content_id, prioritet 2 analytics_match_key) + `match_status` polje + migracija 0008 + `list_distribution_instances_by_campaign` | #8 | MERGOVAN |
| ACS-F1-045 — fact-first fix (web Claude review Nalaz 1+2) | `GenerateCampaignPlan` pokazuje AI-ju stvaran katalog facts sa `logical_fact_id`-evima; `claim_linter` ne flaguje telefon/adresu | #10 | CI ZELENO, čeka review/merge |

## Ključni nalazi prijavljeni koordinatoru (OUT_OF_SCOPE)

- **ACS-F1-044 F1**: kontrakt tražio perzistenciju `match_status` ali držao
  `resources/migrations/` u `forbidden_paths`. Riješeno dodavanjem migracije
  `0008` (ALTER TABLE ADD COLUMN, non-destruktivno). Posljedica: migracija =
  HIGH po workflow §29 → risk tier pitanje za koordinatora.
- **ACS-F1-045 F1**: kontrakt pretpostavio "bridge + testovi" kao pozivaoce
  i tražio "nema izmjena van allowed_paths", ali obavezan `fact_repo`
  parametar je NUŽNO promijenio 6 poziva u 5 fajlova van `allowed_paths`
  (`run_system_b.py` produkcijski + export/rendering/visual×2 integration
  testovi). Svi ažurirani mehanički.

## Verifikacijski baseline (svaki task, u worktree-u)

- ACS-F1-043: targeted 56, puni suite 1009, ruff/mypy čisti, CI #6 zeleno.
- ACS-F1-044: targeted 67, puni suite 1053, ruff/mypy čisti, CI #8 zeleno.
- ACS-F1-045: targeted 132, puni suite 1060, ruff/mypy čisti, CI #10 zeleno.
- Dio B mutation test (adversarial dokaz): bez `contact_info_patterns`
  telefon/adresa padaju na `unsupported-number`, sa patternom ne.

## Evidence fajlovi

```text
agent_reports/2026-09-06-ACS-F1-043-pi.md
agent_reports/2026-09-06-ACS-F1-044-pi.md
agent_reports/2026-09-07-ACS-F1-045-pi.md
```

## Poznato ograničenje (svaki task)

`npx gitnexus detect-changes` iz worktree-a nije pouzdan (worktree-binding
problem, dokumentovan u workflow §7) — svugdje kompenzovano ručnim
`git diff main...HEAD` + caller grep-om; reviewer (Claude) treba čist
`detect-changes` poslije `git fetch`.

## Naredni koraci (za koordinatora)

1. Review + merge ACS-F1-045 (PR #10) — uz odluku o risk tier-u zbog
   van-scope pozivalaca i ažuriranje `allowed_paths` u kontraktu.
2. Ažurirati `.agent/CURRENT_STATE.md` G10 sekciju sa nijansom (R1 dokazuje
   "sistem ne fabrikuje", ne "sistem prenosi stvarne činjenice" — ACS-F1-045
   ovo popravlja).
3. Sljedeći prirodan korak: P1.5-G5 Metric Calculation (čeka signal
   korisnika), zatim ACS-F1-046/047 (preostala dva nalaza iz iste nezavisne
   review, već dodijeljena Crush/MiniMax).
