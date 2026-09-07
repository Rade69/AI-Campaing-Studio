# ACS-F1-046 — addendum: odobreno proširenje scope-a (2026-09-07)

Odgovor na Crush-ov OUT_OF_SCOPE_FINDING (AGENTS.md protokol ispoštovan
ispravno — worktree napravljen, kod NIJE dirn dok se scope ne potvrdi).
Koordinator je nezavisno pročitao `ports/repositories.py` +
`infrastructure/database/repositories/sqlite_campaign_repository.py` +
`sqlite_brand_repository.py` + `domain/campaign/entities.py` +
`domain/brand/entities.py` da potvrdi TAČAN nedostatak prije davanja
odluke.

## Potvrđeno stanje (prije odluke)

- `CampaignRepositoryPort` NEMA nijedan "vrati SVE kampanje" metod —
  jedini read metodi su `get_campaign(campaign_id)` (single) i
  `get_plan(plan_id)` (single, po plan_id-u, ne po campaign_id-u).
  `list_campaigns()` iz kontrakta je fundamentalno neizvodljiv bez
  novog port metoda.
- Nema metoda da se dobije plan ZA campaign_id (samo obrnuto — plan_id
  → plan). `plan_item_count` iz kontrakta zahtijeva takav lookup.
- `BrandRepositoryPort` NEMA `get_brand(brand_id)` — samo
  `save_brand`/`save_snapshot`/`get_snapshot`. `BrandSnapshot` NE nosi
  `Brand.name` (provjereno u `domain/brand/entities.py`) — nema
  zaobilaznice preko snapshot-a. "brand" polje iz kontrakta je
  neizvodljivo bez novog port metoda.
- `Campaign` domain entitet ima SAMO `created_at`, NEMA `updated_at`
  polje nigdje (ni domain, ni SQL šema koliko je provjereno). Ovo NIJE
  propust u repo sloju — polje doslovno ne postoji u sistemu.

Crush-ova procjena je tačna: 3 nova repo metoda + jedna odluka.

## ODLUKA 1 — 3 nova ADITIVNA repo metoda, odobreno

`allowed_paths` za ACS-F1-046 se proširuje sa:

```text
src/ai_campaign_studio/ports/repositories.py
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py
tests/unit/ports/test_repositories.py
tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py
tests/unit/infrastructure/database/repositories/test_sqlite_brand_repository.py
```

`forbidden_paths` stavka `src/ai_campaign_studio/ports/` i
`.../infrastructure/` se OGRANIČAVA na "nema izmjena van ova tri
navedena fajla" — `domain/`, migracije, i svi ostali `ports/`/
`infrastructure/` fajlovi OSTAJU potpuno forbidden, bez izuzetka.

Tačne nove metode (implementer prati POSTOJEĆI stil u istim fajlovima
— `tuple[...]` povrat, `Row → domain` mapping helperi kao
`_campaign_from_row`, isti upit-stil kao `get_plan`):

1. **`CampaignRepositoryPort.list_campaigns() -> tuple[Campaign, ...]`**
   — SQLite: `SELECT * FROM campaigns ORDER BY created_at DESC`. Prazna
   tabela → `()`, ne greška. ISTI ordering koji je kontrakt već
   nagovijestio (`created_at DESC`).
2. **`CampaignRepositoryPort.get_latest_plan_for_campaign(campaign_id: CampaignId) -> CampaignPlan | None`**
   — SQLite: `SELECT * FROM campaign_plans WHERE campaign_id = ? ORDER BY version DESC LIMIT 1`,
   pa isti item-loading kod kao postojeći `get_plan` (JOIN/ORDER BY
   `"order"` na `campaign_items`). Ako kampanja nema nijedan plan →
   `None` → bridge računa `plan_item_count=0`. Implementer NIJE
   dužan generalizovati zajednički helper sa `get_plan` ako to
   dodatno komplikuje diff — mala duplikacija dvije SQL metode je
   prihvatljiva (YAGNI, ne praviti apstrakciju za dvije metode).
3. **`BrandRepositoryPort.get_brand(brand_id: BrandId) -> Brand | None`**
   — SQLite: `SELECT * FROM brands WHERE id = ?`. Nepostojeći
   `brand_id` → `None` (bridge tretira kao "N/A" ili slično u prikazu,
   implementer bira i dokumentuje — ovo ne bi trebalo da se desi u
   praksi jer je `campaign.brand_id` FK-referenciran, ali metod mora
   biti null-safe kao i svi ostali `get_*` metodi u repo sloju).

Sve tri su ČISTO ADITIVNE — nijedna postojeća metoda/potpis se ne
mijenja. Isti standard kao ACS-F1-009 (`get_brief()`) i ACS-F1-015 —
review će line-by-line diff-ovati `repositories.py` da potvrdi da
nijedna postojeća linija nije dirana.

## ODLUKA 2 — `updated_at` se ISKLJUČUJE iz ovog taska

`updated_at` se NE dodaje. Razlog: polje ne postoji NIGDJE u sistemu
(ni `Campaign` dataclass, ni `campaigns` SQL šema) — dodavanje bi
zahtijevalo: (a) novo polje na `domain/campaign/entities.py`
(forbidden path, i van scope-a čisto-read-path taska), (b) novu
`ALTER TABLE` migraciju, (c) izmjenu SVAKOG write-patha koji mijenja
stanje kampanje (plan approve, buduće statusne tranzicije) da postavi
`updated_at`. To je materijalno veća, cross-cutting promjena od "dodaj
3 aditivna read metoda" i ne pripada HIGH-risk GUI-read-path tasku.

**`list_campaigns` prikazuje SAMO `created_at`** (ISO 8601 string, isti
format kao ostala mjesta u kodu — `datetime.isoformat()`).
`CampaignSummaryUiModel`/ekvivalent NE dobija `updated_at` polje u ovoj
verziji. Ovo je BUDUĆA stavka (npr. kad se radi statusna
istorija/audit trail) — implementer NE pravi placeholder/null polje
"za svaki slučaj", prosto ga izostavlja.

## Šta ostaje isto

Sve ostalo iz `agent_reports/ACS-F1-046-task-contract.md` važi bez
izmjene — ekran ostaje SAMO Kampanje lista, `render_body()` ostaje
fixture-driven SSR fallback, XSS-escape zahtjev nepromijenjen, review
ciklus ostaje Claude + Codex (HIGH), PR pa CI provjera obavezna.

## Sljedeći korak za Crush

Nastaviti u ISTOM worktree-u (`ACS-F1-046-kampanje-read-path`) —
worktree i branch ostaju, samo se `allowed_paths` proširuje kako je
gore navedeno. Implementirati tri nova repo metoda + testove PRVO
(izolovano, `tests/unit/ports/`+`tests/unit/infrastructure/...`), pa
tek onda `list_campaigns` bridge metod koji ih koristi, pa
`app.js`/`kampanje/__init__.py` hydration, prateći redoslijed iz
originalnog kontrakta ("Implementation steps").
