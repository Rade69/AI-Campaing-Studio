# → ZA CRUSH — ACS-F1-014 brief

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-02

## Status — spreman, ništa ne blokira

Sve od čega ovaj task zavisi (`CampaignRepositoryPort.get_plan`/`save_plan`/`get_campaign`/
`save_campaign`, `CampaignPlanStatus`, `CampaignStatus`) već postoji na `main`. Možeš krenuti
odmah.

## Gdje je pun kontrakt

`agent_reports/ACS-F1-014-task-contract.md` — pročitaj ga cijelog, ovaj brief je samo skraćeni
pregled.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-014-campaign-plan-editing
Branch:   task/ACS-F1-014-campaign-plan-editing
Base:     main @ d11aaec
```

**Napomena o task-ID-u**: ovaj task se zove "ACS-F1-014", NE "A10" kao broj — "A10" je samo
referenca na sekciju u planu (plan-numeracija), različita od task-ID sistema. Takođe: ne miješati
sa ACS-F1-010 (već DONE, potpuno druga stvar — SocialPostPayload persistence). Od sljedećeg
NOVOG taska pa nadalje projekat prelazi na drugačiju šemu (`FLOW-NNNN`), ali ovaj kontrakt je
napisan prije te odluke i zadržava staro ime.

## Ukratko šta radiš

Plan sekcije 31 ("Campaign plan manual edit") i 32 ("Approve Campaign Plan"). Nastavlja
`application/campaigns/` paket iz ACS-F1-009 (create_campaign.py/generate_campaign_plan.py, već
mergovano — NE diraj ih, samo su ti stil-primjer).

Tri nova use-case-a:

1. **`edit_campaign_plan.py`** — `EditCampaignPlan.execute(plan_id, updated_items)`. Namjerno
   jednostavan API: pozivalac šalje CIJELU novu listu itema kakvu plan treba da ima (dodaš/
   izbrišeš/zamijeniš/izmijeniš item prosto slanjem različite liste) — use-case sam ne pravi
   command-tip API za svaki slučaj izmjene. Stari plan mora biti `DRAFT` (inače
   `InvariantViolation`), postaje `SUPERSEDED`; novi plan je `DRAFT`, `version = old.version + 1`.
   Oba se perzistuju atomično.
2. **`reorder_campaign_item.py`** — `ReorderCampaignItem.execute(plan_id, ordered_item_ids)`.
   NE duplira versioning logiku — validira da je `ordered_item_ids` permutacija postojećih
   item-ova, gradi novu listu sa `order` popravljenim na `1..N`, pa **delegira na
   `EditCampaignPlan.execute()`**.
3. **`approve_campaign_plan.py`** — `ApproveCampaignPlan.execute(plan_id)`. Plan mora biti `DRAFT`
   (inače `InvariantViolation`), provjerava broj itema > 0 + nema duplicate `order` + svaki item
   ima non-empty topic/goal, pa `CampaignPlan.status → APPROVED` I `Campaign.status →
   PLAN_APPROVED` (oba atomično).

## Najvažnije pravilo — šta NE diraš

**`generate_social_post.py` je STROGO van scope-a ovog taska**, iako postoji poznat, dokumentovan
gap (post generation trenutno ne provjerava da je plan `APPROVED`). Taj fajl je bio predmet
paralelnog ACS-F1-012 taska koji je upravo mergovan — namjerno je ostavljeno da se izbjegne
konflikt. Ne "popravljaj to usput" ovim taskom.

## Pažnja — najlakše mjesto da se nešto zeza

- Editovanje NE-DRAFT plana (i APPROVED i SUPERSEDED) mora biti nemoguće — test za OBA statusa,
  ne samo jedan.
- Atomicity: stari plan SUPERSEDED + novi plan DRAFT moraju se perzistovati zajedno ili nijedan —
  testiraj mid-failure na pravoj SQLite bazi (isti obrazac kao ACS-F1-007/009/011).
- `ReorderCampaignItem` mora STVARNO delegirati na `EditCampaignPlan` (ne duplirati
  persist/validation kod) — ovo je nešto što ću posebno provjeriti diff-om.

## Van scope-a

- `create_campaign.py`/`generate_campaign_plan.py` — ne diraj.
- `generate_social_post.py` — ne diraj (vidi gore).
- `domain/`/`ports/` — sve što ti treba već postoji, nema potrebe za novim repository metodama.
