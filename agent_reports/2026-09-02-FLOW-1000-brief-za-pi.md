# → ZA PI — FLOW-1000 brief

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-02

## Status — spreman, ništa ne blokira

**Prvi task pod novom `FLOW-NNNN` šemom** (naslov ide UZ broj svaki put kad se pominje — "FLOW-1000
— Plan-approved guard u GenerateSocialPost", nikad golo "FLOW-1000"). Ništa ga ne blokira, sve od
čega zavisi (`CampaignPlanStatus`, `ApproveCampaignPlan` stil primjer) već postoji na `main`.

## Gdje je pun kontrakt

`agent_reports/FLOW-1000-task-contract.md` — pročitaj ga cijelog.

```text
Worktree: ../ai-campaign-studio-worktrees/FLOW-1000-plan-approved-guard
Branch:   task/FLOW-1000-plan-approved-guard
Base:     main @ 52e2638
```

## Ukratko šta radiš

Malen task — zatvara poznat gap iz ACS-F1-014 (koji si ti radio... ne, to je bio Crush — svejedno,
gap je tvoj `generate_social_post.py` iz ACS-F1-011/012). Plan sekcija 32: "Post generation ne
smije krenuti sa DRAFT planom" — `GenerateSocialPost.execute()` trenutno UOPŠTE ne provjerava
`plan.status`.

**Jedna izmjena**: odmah nakon što se plan učita (`plan = self._campaign_repo.get_plan(plan_id)`,
poslije `None`-provjere, PRIJE pretrage `campaign_item`-a i PRIJE bilo kakvog AI poziva):

```python
if plan.status is not CampaignPlanStatus.APPROVED:
    raise InvariantViolation(
        f"campaign plan {plan_id} is {plan.status.value}; only an APPROVED "
        "plan can be used to generate posts"
    )
```

Dodaj `CampaignPlanStatus` import iz `domain.campaign.enums`.

## Pažnja — najlakše mjesto da se nešto zeza

**Svi POSTOJEĆI happy-path testovi u oba test fajla trenutno koriste `_plan()` sa
`status=CampaignPlanStatus.DRAFT`** — nakon tvoje izmjene će svi pasti dok ih ne ažuriraš na
`CampaignPlanStatus.APPROVED`. Ovo NIJE oslabljivanje testa — happy path sad ispravno zahtijeva
odobren plan (isto kao što si u ACS-F1-012 morao ažurirati `GENERATING`→`DRAFT`).

Dodaj i NOVE negativne testove: DRAFT plan → `InvariantViolation` **prije AI poziva** (dokaži da
je fake AI port `call_count`/`requests` ostao 0, ne samo da postoji exception negdje), isto za
SUPERSEDED plan.

## Van scope-a

- `select_allowed_facts.py`/`claim_validator.py`/`claim_linter.py`/`derive_content_status.py`/
  `application/campaigns/` — ne diraj, samo jedna guard klauzula u `generate_social_post.py`.
