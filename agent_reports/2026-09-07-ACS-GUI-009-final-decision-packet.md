# ACS-GUI-009 (v2) — final decision packet (HIGH risk)

**Task**: Pregled i izvoz — stvaran vizuelni sistem + layout + render +
ZIP export. Prvi GUI→backend put koji pokreće stvaran
`GenerateVisualSystem` → `PlanPostLayout` → `ExportCampaign` lanac.

**PR**: https://github.com/Rade69/AI-Campaing-Studio/pull/9
**HEAD**: `1dcaf1f` (rebase-ovan na main kroz ACS-F1-045/046/047)
**Implementer**: Crush
**Reviewers**: Claude (koordinator, 2 runde), Codex (adversarial, 2 runde)

## READY FOR HUMAN OWNER APPROVAL

## Tok review-a (kratko)

1. **Implementacija (v1 pa v2)** — v1 je izgubio korak sa main-om
   (HOTFIX-002/GUI-008 strukturne izmjene), koordinator napisao
   addendum, implementer napravio čist v2 na svježem main-u.
2. **Codex round 1** — REJECT: BF-1 (secret-in-log u
   `_resolve_ai_adapter`), BF-2 (concurrent ZIP korupcija — 9/50 u
   kontrolisanom testu), BF-3 (test gaps + `_seed_brand_and_campaign`
   ID-reuse bug).
3. **Fix runda 1** — `logger.error` (type-only) za BF-1; cijela export
   sekvenca pod `_lock_for(campaign_id, plan_id)` za BF-2; helper
   proširen + 2 nova testa za BF-3. Koordinator NEZAVISNO
   mutation-testirao OBA (BF-1 i BF-2) — vraćen stari kod, novi
   testovi padaju kako treba, fix vraćen.
4. **Veliki rebase** — branch je bio baziran OD PRIJE ACS-F1-045/046/047;
   rebase je proizveo 3-way konflikt u `bridge/__init__.py` i test
   fajlu (F1-047-ove nove metode vs. GUI-009-ov novi
   `export_campaign_package`, plus DVIJE nezavisno evoluirane verzije
   `_seed_brand_and_campaign` helper-a). Koordinator ručno riješio,
   provjerio brojem test funkcija prije/poslije (56+7=63, tačno) i
   punim gate-om.
5. **Codex round 2** — **PASS_WITH_NOTES, bez blocking nalaza.**
   Dodatno pokrenuo concurrent-export regresiju JOŠ 10 puta (ukupno
   uz implementer-ovih 50 + koordinatorovih 30 = preko 90 pokušaja
   kroz cio ciklus, 0 korupcija sa fix-om), potvrdio da rebase nije
   unio regresiju u dijeljenom F1-047 kodu.

## Šta je konačno stanje koda

- `export_campaign_package` — nova `@_with_call_resources` bridge
  metoda: boundary validacija → plan/campaign lookup + APPROVED +
  ownership provjera → idempotentan `CampaignVisualSystem` (in-process
  mapa) → per-post `LayoutSpec` petlja (partial-failure tolerantna) →
  `ExportCampaign` (7-parametarski konstruktor) → ZIP na
  `data_dir/exports/<campaign_id>.zip`.
- **BF-2 fix**: cijela sekvenca (idempotentni visual-system check →
  layout petlja → ExportCampaign) je unutar JEDNOG
  `_lock_for(campaign_id, plan_id)` — isti lock kao
  `generate_campaign_content`. Sprečava concurrent-write korupciju
  fiksne ZIP putanje i čini visual-system idempotentnost atomičnom
  (bez TOCTOU-a).
- **BF-1 fix**: `_resolve_ai_adapter`-ov adapter-factory except grana
  loguje SAMO `type(exc).__name__` + siguran provider code, bez
  traceback-a/`str(exc)` — isti obrazac kao `configure_provider`
  (ACS-GUI-007 BF-3).
- **BF-3 fix**: cross-campaign ownership test (dva genuinely nezavisna
  campaign/plan para) + export lifecycle-failure DTO test (tačan
  7-key set).
- `_LIFECYCLE_ERROR_MAPPERS`/`_LIFECYCLE_ERROR_MESSAGES` proširen za
  `export_campaign_package` -> `_export_err`.
- `approve-gate` ostaje UI-only (potvrđeno od Codex-a oba puta).

## Gate (zadnji poznat, potvrđen od koordinatora i Codex-a nezavisno)

```text
pytest -q                    -> 1087 passed
ruff check .                 -> All checks passed
mypy src                     -> Success, 175 files
CI (PR #9, gh pr checks)     -> zeleno
```

## Poznati, prihvaćeni rezidualni rizik (ne blokira)

**Secret-in-log obrazac i dalje postoji na DVA DRUGA mjesta** —
`create_campaign_and_generate_plan()` i `generate_campaign_content()`
i dalje koriste `logger.exception(...)` za adapter-factory failure
(isti tip rizika kao BF-1, ali NIJE uveden niti mijenjan ovim PR-om —
postojeći kod iz ACS-GUI-005/008). Codex je ovo eksplicitno potvrdio
kao neblokirajuće za OVAJ task i preporučio zaseban mali
security-hardening task koji bi primijenio isti type-only obrazac na
sva preostala adapter-factory mjesta. Crush je ovo prvi prijavio kao
OUT_OF_SCOPE_FINDING, i ja i Codex smo nezavisno potvrdili.

**Preporuka**: otvoriti kratak, samostalan hardening task poslije ovog
merge-a (LOW/MEDIUM risk, mehanička izmjena na 2 mjesta + 2 sentinel
testa, isti obrazac kao BF-1).

## Traženo odobrenje

HIGH risk task, pun ciklus proveden (implementer → Claude ×2 →
Codex ×2, plus koordinator-vođen veliki rebase). Rezidualni rizik je
eksplicitno pregledan i ne blokira. Molim odobrenje za merge PR #9 u
main.
