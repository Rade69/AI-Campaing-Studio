# ACS-F1-029 — Claude review (round 1) + fix brief za Pi

**Task:** ACS-F1-029 (A13 — `GenerateVisualSystem`)
**Implementer:** Pi
**Reviewer:** Claude (MEDIUM, §29 Claude-only)
**Verdict:** PASS_WITH_NOTES — jedan fix zatražen prije merge-a (F1, LOW severity, ali stvaran acceptance gap)

## Šta je nezavisno provjereno

Pročitao sam `generate_visual_system.py` u cjelosti (ne samo evidence report) i
oba test fajla. Pokrenuo sam testove i statičke provjere nezavisno u worktree-u:

```text
$ pytest tests/unit/application/visual/ tests/integration/application/visual/ -v
11 passed
$ pytest -q
832 passed
$ ruff check .
All checks passed!
$ mypy src
Success: no issues found in 149 source files
```

Kod je čist i tačno prati kontrakt: `plan.status != APPROVED` odbija PRIJE AI
poziva, enum→str konverzija je eksplicitna (`.value`), `_validate_visual_domain`
stvarno hvata nedozvoljen `style`, `LayoutSpec` je dosljedno in-memory (nema
pokušaja perzistencije), `domain/`/`ports/`/`infrastructure/`/`resources/`
nedirnuti (potvrđeno `git status --short` u worktree-u — samo 3 nova
direktorijuma). HERO i SPLIT su STVARNO odvojena dva testa (ne jedan
parametrizovan), tačno kako je kontrakt tražio.

## F1 — `test_missing_entities_raise_entity_not_found("brief")` ne testira brief

Kontrakt (Implementation steps, tačka 5) je tražio: "Plan/campaign/brief/snapshot
ne postoji → `EntityNotFound` (4 odvojena testa ili parametrizovano)".

U `test_generate_visual_system.py` (linije 301-326), parametrizacija ima 4
labele (`"plan"`, `"campaign"`, `"brief"`, `"snapshot"`), ali kod grana je:

```python
if missing == "plan":
    ...
elif missing == "snapshot":
    ...
else:
    # campaign/brief absence is exercised by pointing the plan at a
    # campaign id that the fake repo does not hold.
    plan = CampaignPlan(..., campaign_id=CampaignId("missing-campaign"), ...)
    use_case, _ = _make_use_case(plan, ai_port)
    plan_id = CampaignPlanId("plan-1")
```

`"campaign"` i `"brief"` padaju u ISTI `else` granu — identičan test se
izvršava dva puta pod dva različita imena. Kad je `plan.campaign_id =
"missing-campaign"`, `get_campaign("missing-campaign")` vraća `None` i
`EntityNotFound` se baca NA CAMPAIGN koraku — kod nikad ne stigne do `get_brief`
poziva (`generate_visual_system.py:113-115`). Rezultat: taj kod-put
(`brief is None → EntityNotFound`) nema NIJEDAN test u cijelom paketu.

Ovo NIJE funkcionalni bug — sama produkcijska linija je ispravna i identičnog
oblika kao tri druga već-testirana `is None` provjere u istoj funkciji (isti
rizik, već pokriven precedentom). Ali test-suite nominalno tvrdi 4 odvojena
scenarija kad zapravo testira 3 (jedan dupliran pod dva imena), što je stvaran
acceptance-kriterijum gap, ne stilski nit-pick.

### Traženi fix

Napraviti "brief missing" GENUINE zaseban scenario: campaign se PRONAĐE (isti
`campaign-1`), ali `campaign.brief_id` pokazuje na brief koji `_FakeCampaignRepository`
nema. Npr.:

```python
elif missing == "campaign":
    plan = CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("missing-campaign"),
        version=1,
        status=CampaignPlanStatus.APPROVED,
        created_at=_CREATED_AT,
        items=(),
    )
    use_case, _ = _make_use_case(plan, ai_port)
    plan_id = CampaignPlanId("plan-1")
elif missing == "brief":
    campaign_without_brief = Campaign(
        id=CampaignId("campaign-1"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="missing-brief",
        status=CampaignStatus.PLAN_APPROVED,
        created_at=_CREATED_AT,
    )
    visual_repo = _FakeVisualRepository()
    use_case = GenerateVisualSystem(
        _FakeCampaignRepository(campaign_without_brief, _brief(), _plan()),
        _FakeBrandRepository(_snapshot()),  # type: ignore[arg-type]
        visual_repo,
        _FakePromptRepository(),
        ai_port,
        _FakeUnitOfWork(),
    )
    plan_id = CampaignPlanId("plan-1")
```

(implementer bira tačan oblik — bitno je da `get_campaign` uspije i `get_brief`
stvarno vrati `None`, ne da se ponovo padne na campaign koraku). Nakon fixa,
sva 4 parametrizovana slučaja moraju gađati 4 STVARNO različita `if X is None`
mjesta u `generate_visual_system.py` (plan/campaign/brief/snapshot), ne 3.

## Ostalo — bez primjedbi

Nema drugih nalaza. `_build_user_text` sam provjerio red-po-red protiv
`domain/visual/enums.py` (11 enum tipova) — sve nabrojano, ništa promašeno.
`_ALLOWED_STYLES` case-sensitivity odluka je dokumentovana i razumna
(dokumentovana u docstring-u, konzistentna sa planovim primjerom). Integration
test je stvaran round-trip kroz `SqliteVisualRepository`, ne fake.

## Sljedeći korak

Pi: dodati genuine "brief missing" scenario (gore), potvrditi da sva 4
`missing_entities` parametrizacije gađaju 4 različita koda-puta, ponovo
pokrenuti `pytest tests/unit/application/visual/ tests/integration/application/visual/ -v`
+ `pytest -q` (cijeli suite) + `ruff check .` + `mypy src`, ažurirati evidence
report sa novim rezultatom. Ovo je mala izmjena (jedan test slučaj), ne
zahtijeva novu Codex rundu (LOW severity, MEDIUM risk task ostaje na
Claude-only §29) — kad se potvrdi, koordinator merguje.
