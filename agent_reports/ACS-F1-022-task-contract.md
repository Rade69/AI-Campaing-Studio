---
task_id: ACS-F1-022
phase: Faza-1 (post A9, pre G10 analytics-ready)
title: "GenerateCampaignPlan: enforce da svaka generisana uloga pripada CampaignTemplate.role_sequence"
risk: MEDIUM
coordinator: claude
implementer: minimax
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py
  - tests/unit/application/campaigns/test_generate_campaign_plan.py
  - tests/integration/application/campaigns/test_generate_campaign_plan_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/campaigns/create_campaign.py
  - src/ai_campaign_studio/application/campaigns/approve_campaign_plan.py
  - src/ai_campaign_studio/application/campaigns/edit_campaign_plan.py
  - src/ai_campaign_studio/application/schemas/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/ports/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. `_validate_plan_domain` je čista
    funkcija bez I/O, poziva se samo iz `GenerateCampaignPlan.execute` — nema
    drugih pozivalaca (provjereno grep-om prije pisanja kontrakta).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: a62fd5a
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Treći, temeljitiji spoljni code review prolaz je našao (koordinator
nezavisno provjerio prije pisanja kontrakta) da `CampaignTemplate.role_sequence`
— domain koncept eksplicitno opisan u `domain/campaign/templates.py` kao
"semantic role sequence" koja definiše šta jedan template (npr.
`LEAD_GENERATION_V1`, 7 uloga: PROBLEM/EDUCATION/PROOF/OBJECTION/BENEFIT/
OFFER/ACTION) treba da sadrži — **nigdje se stvarno ne provjerava** protiv
generisanog plana. Jedina domain provjera u
`generate_campaign_plan.py::_validate_plan_domain` je:

```python
roles = {item.role for item in output.items}
if len(output.items) >= 2 and len(roles) < 2:
    raise InvariantViolation(...)
```

To je "bar 2 različite uloge od bilo koje od 17 postojećih u `CampaignRole`
enumu" — NE "uloge moraju pripadati template-u". Provjereno: ni
`approve_campaign_plan.py` ni `edit_campaign_plan.py` ne dotiču role uopšte
(samo unique order + neprazan topic/goal). `LEAD_GENERATION_V1.role_sequence`
se šalje modelu SAMO kao tekst u promptu — jedina "zaštita" je da model
poštuje uputstvo.

**Zašto je ovo vrijedno fixa sad**: template/role struktura je dio onoga
što ovaj alat razlikuje od generičkog ChatGPT prompta — CLAUDE.md-ova
filozofija je fact-grounding i strukturisan pristup BAŠ ZATO što se ne
oslanja samo na to da je model dobar (isti princip koji je motivisao claim
linter). Danas, da AI odluči vratiti 7 potpuno drugačijih (ali svih
validnih, svih različitih) uloga koje NISU dio `LEAD_GENERATION_V1`, sistem
bi to prihvatio bez greške. Live testovi (Gemini, DeepSeek) su do sada
vraćali razumne planove — ali to je "vjerovatno će raditi jer je model
dobar", ne "sistem to garantuje".

Ovo NIJE poznat/prihvaćen rizik — propust u domain provjeri, ne namjeran
dizajn (nema komentara koji objašnjava zašto role_sequence članstvo nije
provjereno).

# Objective

`_validate_plan_domain` mora odbaciti plan ako BILO KOJA generisana uloga
NIJE član `template.role_sequence` skupa uloga. **Ovo je subset provjera,
NE provjera tačnog redoslijeda niti tačnog broja/skupa** — `content_piece_count`
(npr. 3) je tipično MANJI od `len(template.role_sequence)` (7 za
`LEAD_GENERATION_V1`), pa AI legitimno bira PODSKUP uloga iz template-a,
ne sve njih niti tačnim redoslijedom. Redoslijed generisanih stavki
(`item.order`) ostaje potpuno nezavisan od redoslijeda u
`template.role_sequence` — ne uvoditi provjeru reda, samo članstva.

# Implementation steps

1. Proširi `_validate_plan_domain(output: CampaignPlanOutput)` da prima i
   `template: CampaignTemplate` kao dodatni parametar (isti tip koji
   `_build_user_text` već prima — vidi poziv u `execute()`, gdje se već
   koristi `LEAD_GENERATION_V1` konstanta).
2. Dodaj provjeru (nakon postojeće duplicate-topics i distinct-roles
   provjere, ista funkcija):
   ```python
   allowed_roles = set(template.role_sequence)
   invalid_roles = roles - allowed_roles
   if invalid_roles:
       raise InvariantViolation(
           f"campaign plan uses roles outside template "
           f"{template.id!r}: {sorted(r.value for r in invalid_roles)}"
       )
   ```
3. Ažuriraj poziv u `execute()`: `_validate_plan_domain(output, LEAD_GENERATION_V1)`
   (isti template koji se već koristi za `_build_user_text`).
4. Testovi:
   - Unit: plan sa validnim ulogama (podskup `LEAD_GENERATION_V1.role_sequence`)
     i dalje prolazi bez greške.
   - Unit: plan sa BAR JEDNOM ulogom van template-a (npr. `FAQ` ili `STORY`,
     koje NISU u `LEAD_GENERATION_V1.role_sequence`) baca `InvariantViolation`
     sa jasnom porukom koja navodi tačno koje uloge su nevažeće.
   - Unit: plan gdje su SVE uloge van template-a (potpun mismatch) — isti
     rezultat.
   - Integration: potvrdi da postojeći fixture-driven test i dalje prolazi
     bez izmjene (ako fixture koristi uloge van `LEAD_GENERATION_V1`, to je
     samo po sebi nalaz — javi koordinatoru PRIJE nego što promijeniš
     fixture podatke da "prođu" test, umjesto da izmijeniš provjeru).

# Acceptance

- [ ] `_validate_plan_domain` prima `template` parametar.
- [ ] Plan sa svim ulogama unutar `template.role_sequence` (podskup, bilo
      koji redoslijed) prolazi.
- [ ] Plan sa bar jednom ulogom van `template.role_sequence` baca
      `InvariantViolation` sa porukom koja imenuje nevažeće uloge.
- [ ] Postojeća "bar 2 različite uloge" i "nema duplikat tema" provjera
      OSTAJU nepromijenjene (ovaj task ih ne dira, samo dodaje treću
      provjeru).
- [ ] Nema provjere REDOSLIJEDA uloga — samo članstva.
- [ ] `domain/`, `create_campaign.py`, `approve_campaign_plan.py`,
      `edit_campaign_plan.py`, `application/schemas/` NISU DIRANI (git diff
      dokaz).
- [ ] `python -m pytest tests/unit/application/campaigns/ tests/integration/application/campaigns/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/campaigns/test_generate_campaign_plan.py tests/integration/application/campaigns/test_generate_campaign_plan_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- subset provjera je ispravna (ne exact-match, ne order-sensitive);
- error poruka je korisna (navodi tačno koje uloge su problem, ne generička
  poruka);
- postojeće dvije domain provjere nepromijenjene;
- integration test fixture ne koristi uloge van template-a (ili je, ako
  koristi, to bilo eksplicitno prijavljeno koordinatoru, ne tiho
  prilagođeno da "prođe").

# Rollback

MEDIUM risk — application-layer dodatna validacija, ne dira domain/šemu.
Fix na istoj branch bez proširenja scope-a. §29: Claude-only review, PASS
-> odmah merge.

# Coordination

Nezavisno od ACS-F1-020 (Pi, claim_linter fix runda u toku) i ACS-F1-023
(planiran, UNIQUE constraint migracija) — sva tri disjoint fajlovi, mogu
ići paralelno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-022-role-sequence-enforcement
Branch:   task/ACS-F1-022-role-sequence-enforcement
Base:     main @ a62fd5a
```
