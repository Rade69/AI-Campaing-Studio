# ACS-GUI-008 — fix-brief (Claude review, prije GitNexus/Codex/Human Owner ciklusa)

Implementer: MiniMax · Reviewer: Claude (HIGH risk, pun ciklus)
Evidence pregledan: `agent_reports/2026-09-06-ACS-GUI-008-minimax.md`,
diff `0595912..8c98f03` na `task/ACS-GUI-008-studio-sadrzaja-generate`.

## Verdict

Implementacija je kvalitetna — partial-failure handling, idempotentnost
preko DB provjere (`list_campaign_content` pre-check), plan-approval kao
status-check (ne retry), sve dobro testirano (22 nova testa, 986/986 pun
suite, ruff/mypy čisti). **Jedan nalaz mora biti riješen prije nego što
nastavim GitNexus impact + pripremim Codex adversarial rundu** — nema
smisla trošiti taj ciklus na kod koji se mijenja.

## Nalaz: sirov SQL u bridge-u je izbjegediv, ne samo dokumentovan "smell"

Tvoja §8.3/§9 napomena je iskrena i tačna dijagnoza problema, ali postoji
čist izlaz koji GA POTPUNO UKLANJA, ne samo dokumentuje:

`CampaignPlanResultUiModel` (postojeći DTO iz ACS-GUI-005,
`presentation/ui_models.py:44`) **nikad nije vraćao `plan_id`** frontend-u
— samo `campaign_id`/`plan_item_count`/`error_code`/`error_message`. Zato
je `generate_campaign_content` morao SAM da izvede "koji je plan ove
kampanje" preko `database_connection.execute("SELECT id FROM
campaign_plans WHERE campaign_id = ? ORDER BY created_at DESC LIMIT 1")`.

Ali `app.js` VEĆ zna `campaign_id` iz koraka 1 (kreiranje kampanje preko
`create_campaign_and_generate_plan`). Ako taj isti odgovor vrati i
`plan_id` (koji use-case već ima u scope-u — `plan.id` odmah nakon
`GenerateCampaignPlan(...).execute(campaign.id)`), JS ga jednostavno
proslijedi dalje kad kasnije zove `generate_campaign_content` — i sirov
SQL nestaje u potpunosti, bez potrebe za bilo kakvim novim repo-metodom
(dakle `forbidden_paths` na `ports/` ostaje netaknut).

## Tražene izmjene (sve unutar `allowed_paths`)

1. **`presentation/ui_models.py`** — `CampaignPlanResultUiModel` dobija
   novo polje `plan_id: str | None` (aditivno, nakon `campaign_id`).
2. **`presentation_webview/bridge/__init__.py`** —
   `create_campaign_and_generate_plan`-ov success-return sada popunjava
   `plan_id=str(plan.id)` (error granama ostaje `None`, isti obrazac kao
   `campaign_id=None` u tim granama).
3. **`generate_campaign_content`** — payload prima **eksplicitan
   `plan_id`** pored `campaign_id` (boundary validacija: obavezan string,
   isti stil kao `campaign_id`). Zamijeniti CIJELI SQL blok +
   "race condition" re-fetch sa:
   ```python
   plan = self._campaign_repo.get_plan(plan_id)
   if plan is None:
       return self._generate_err(_ERROR_VALIDATION, f"Plan {plan_id} ne postoji.")
   if plan.campaign_id != campaign_id:
       return self._generate_err(
           _ERROR_VALIDATION,
           f"Plan {plan_id} ne pripada kampanji {campaign_id}.",
       )
   ```
   (isti obrazac provjere kao postojeći `ExportCampaign`-ov
   `if plan.campaign_id != campaign_id: raise InvariantViolation`).
4. **`app.js`** — zapamti `plan_id` iz `create_campaign_and_generate_plan`
   odgovora (isto mjesto/state gdje se već pamti `campaign_id` za
   navigaciju ka Studio sadržaja), proslijedi ga u
   `generate_campaign_content` pozivu.
5. **`studio_sadrzaja/__init__.py`** — `StudioSadrzajaFixture` vjerovatno
   treba i `plan_id: str | None = None` uz postojeći `campaign_id`, da
   SSR emit-uje `data-plan-id` pored `data-campaign-id` na dugmetu (JS
   handler čita oba iz DOM-a kad zove bridge).
6. **Testovi** — svi pozivi `generate_campaign_content({"campaign_id": ...})`
   dobijaju i `plan_id`; scenario "kampanja nema plan" postaje "plan_id
   nedostaje iz payload-a" + nov scenario "plan_id ne pripada kampanji"
   (validacija #3 gore). `test_bridge_implements_generate_campaign_content`
   (contracts.py potpis test) ostaje isti (i dalje jedan `raw_payload`
   argument, samo se mijenja OČEKIVANI SADRŽAJ tog dict-a).

Ovo je **manje koda** nego trenutno rješenje (nestaje SQL blok + defensive
re-fetch), i uklanja jedinu stvarnu arhitektonsku povredu u inače vrlo
solidnom radu. `_targets_from_brief`/`_target_for_item` duplikacija (zbog
`application/` u `forbidden_paths`) OSTAJE kako jeste — to je prihvatljivo,
testom upareno sa `run_system_b.py` (`test_generate_content_round_robin_
assignment_matches_run_system_b`), nije dio ovog nalaza.

## Napomena

`create_campaign_and_generate_plan` je već mergovan, već pun-review-ovan
(ACS-GUI-005/006) kod — ova izmjena je ADITIVNA (novo polje, postojeća
polja/testovi netaknuti), pa ne otvara ponovo cijeli taj review, ali
molim eksplicitno potvrdi u novom evidence-u da postojeći
`create_campaign_and_generate_plan` testovi i dalje prolaze nepromijenjeni
(samo prošireni za novo polje, ne izmijenjeni u ponašanju).

Kad ovo sleti, nastavljam pun ciklus: GitNexus impact na
`CampaignBridgeApi.__init__`/`ApproveCampaignPlan`/`GenerateSocialPost`,
pa priprema Codex adversarial runde, pa Human Owner odobrenje (HIGH risk,
nije §29 skraćeni put).
