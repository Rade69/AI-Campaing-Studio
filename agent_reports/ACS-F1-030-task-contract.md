---
task_id: ACS-F1-030
phase: Faza-1 (post A16) — A13 dio 2, foundation (plan sekcija 24, prerequisit za sekcije 40-41)
title: "layout_specs perzistencija: LayoutSpec identitet + migracija + VisualRepositoryPort proširenje"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - resources/migrations/0005_layout_specs.sql
  - src/ai_campaign_studio/domain/common/ids.py
  - src/ai_campaign_studio/domain/visual/layout.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - tests/unit/domain/visual/test_layout.py
  - tests/integration/database/repositories/test_sqlite_visual_repository.py
  - tests/integration/database/test_migrations.py
forbidden_paths:
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/domain/visual/entities.py
  - src/ai_campaign_studio/domain/visual/enums.py
  - src/ai_campaign_studio/domain/visual/slots.py
  - src/ai_campaign_studio/application/schemas/
  - resources/prompts/
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0001_brand_facts.sql
  - resources/migrations/0002_campaign_content_visual.sql
  - resources/migrations/0003_content_payload.sql
  - resources/migrations/0004_uniqueness_constraints.sql
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Proširuje POSTOJEĆI port (`VisualRepositoryPort`) sa dvije nove metode
    (aditivno, ne mijenja postojeći `save_visual_system`/`get_visual_system`
    potpis) i dodaje NOVU migraciju (aditivna tabela, ne dira postojeće
    tabele/kolone). Koordinator pokreće detect-changes/impact prije merge-a
    (GitNexus MCP dostupan, indeks stale — re-index prije provjere) da
    potvrdi da nijedan postojeći pozivalac `VisualRepositoryPort` (trenutno
    samo `ACS-F1-029`) nije pogođen proširenjem.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: ea0820f
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

A13 dio 1 (`GenerateVisualSystem`, ACS-F1-029) je mergovan — perzistuje
`CampaignVisualSystem` po kampanji, ali `LayoutSpec` (raster layout za
KONKRETAN post) vraća SAMO in-memory, jer `layout_specs` tabela (plan
sekcija 24, `0002_visual.sql` u planu) nikad nije kreirana — postoji SAMO
`campaign_visual_systems`.

**Ovaj task NE piše `plan_post_layout.py`/`validate_layout.py` (plan
sekcije 40-41, per-post AI-generisan layout + deterministička provjera da
li headline tekst staje u odabrani layout).** To je sljedeći task
(A13 dio 2b), namjerno ODVOJEN od ovog. Razlog za razdvajanje: ISTI obrazac
je već primijenjen za `campaign_visual_systems`/`VisualRepositoryPort`/
`SqliteVisualRepository` — ta cijela fundacija je izgrađena RANIJE (rana
P0/A3-A5 faza), potpuno odvojeno od use-case-a koji je konačno stigao da je
koristi (ACS-F1-029, mnogo kasnije). Ovaj task ponavlja TAČNO taj obrazac
za `layout_specs`: prvo fundacija (migracija + identitet + port + adapter),
zasebno testirana i mergovana, PRIJE nego što bilo koji use-case pokuša da
je koristi. Ovo drži svaki task malim i nezavisno provjerljivim (isti
princip primijenjen svuda ovog session-a: A16 scope reduction, A12 podjela
na tri kontrakta, itd.).

# Objective

1. Novi ID tip `LayoutSpecId` (`domain/common/ids.py`), isti obrazac kao
   `VisualSystemId = NewType("VisualSystemId", str)`.
2. `domain/visual/layout.py::LayoutSpec` dobija TRI NOVA OPCIONA polja sa
   `None` default-om — **ne smije pokvariti nijedno postojeće mjesto koje
   već konstruiše `LayoutSpec` bez njih** (ACS-F1-029
   `generate_visual_system.py`, `tests/unit/domain/visual/test_layout.py`):
   - `id: LayoutSpecId | None = None`
   - `content_piece_id: PostId | None = None`
   - `validation_status: str | None = None` (namjerno plain `str`, ne nov
     enum — Slice 1 minimalno; vrijednosti `"VALID"`/`"INVALID"` su
     konvencija dokumentovana u docstring-u, ne zaključan tip; buduci
     `plan_post_layout.py` odlučuje stvarne vrijednosti)
3. Nova migracija `resources/migrations/0005_layout_specs.sql` — tabela
   `layout_specs` TAČNO po plan sekciji 24:
   ```sql
   CREATE TABLE layout_specs (
       id TEXT PRIMARY KEY,
       content_piece_id TEXT NOT NULL REFERENCES content_pieces(id),
       format TEXT NOT NULL,
       payload_json TEXT NOT NULL,
       validation_status TEXT NOT NULL,
       created_at TEXT NOT NULL
   );
   ```
   `payload_json` nosi SVA enum-tipizovana polja (`primitive`,
   `image_position`, `headline_position`, `headline_scale`, `overlay`,
   `logo_position`, `cta_style`, `alignment`) kao JSON, isti stil kao
   `style_json` u `campaign_visual_systems`.
4. `ports/repositories.py::VisualRepositoryPort` dobija DVIJE NOVE metode
   (aditivno, postojeće dvije NETAKNUTE):
   ```python
   def save_layout_spec(self, layout_spec: LayoutSpec) -> None: ...
   def get_layout_spec(self, layout_spec_id: LayoutSpecId) -> LayoutSpec | None: ...
   ```
   Zahtijeva da `layout_spec.id`/`layout_spec.content_piece_id`/
   `layout_spec.validation_status` NISU `None` u trenutku poziva
   `save_layout_spec` (implementer bira: `ValueError` na `None` id, ili
   oslanjanje na tip-checker — dokumentovati odluku u docstring-u metode,
   isti stil kao `CampaignRepositoryPort.delete_campaign`-ov opsežan
   docstring).
5. `SqliteVisualRepository` implementira obje nove metode — isti stil kao
   `save_visual_system`/`get_visual_system` (enum → `.value` pri snimanju,
   `EnumType(row[...])` pri čitanju, `json.dumps`/`json.loads` za
   `payload_json`).

# Implementation steps

1. `domain/common/ids.py`: dodati `LayoutSpecId = NewType("LayoutSpecId", str)`
   odmah nakon `VisualSystemId` (isti stil, isti fajl, jedna linija).

2. `domain/visual/layout.py`: proširiti `LayoutSpec` dataclass sa tri nova
   opciona polja (redoslijed: postojeća polja PRVA, nova polja NA KRAJU —
   frozen dataclass sa default vrijednostima mora imati sva default-polja
   nakon non-default polja, `format: str` je zadnje POSTOJEĆE polje bez
   default-a pa novi opcioni dolaze poslije njega). Ažurirati docstring da
   objasni da su ova tri polja `None` za in-memory (neperzistovan) layout
   (ACS-F1-029 stil), a popunjena za perzistovan layout (budući A13 dio 2b).

3. `resources/migrations/0005_layout_specs.sql` — tačan DDL iz sekcije
   Objective #3 iznad. Provjeriti da `content_piece_id REFERENCES
   content_pieces(id)` prati isti FK stil kao ostale tabele u
   `0002_campaign_content_visual.sql` (bez `ON DELETE CASCADE` — projekat
   je append-only/audit-trail orijentisan, nema presedana za cascade
   delete nigdje u postojećim migracijama).

4. `ports/repositories.py`: dodati dvije metode na `VisualRepositoryPort`
   (Protocol) sa docstring-om koji objašnjava pretpostavku (identitet mora
   biti popunjen prije snimanja).

5. `infrastructure/database/repositories/sqlite_visual_repository.py`:
   implementirati `save_layout_spec`/`get_layout_spec`. `save_layout_spec`
   koristi `INSERT ... ON CONFLICT(id) DO UPDATE` isti stil kao
   `save_visual_system` (upsert). `get_layout_spec` vraća `None` ako red ne
   postoji, inače rekonstruiše `LayoutSpec` sa svim enum poljima kao pravim
   domain enumima (ne stringovima) — isti stil kao `get_visual_system`.

6. Testovi:
   - `tests/unit/domain/visual/test_layout.py`: NOVI test — `LayoutSpec`
     konstruisan SA `id`/`content_piece_id`/`validation_status` popunjenim
     ispravno drži te vrijednosti; POSTOJEĆI test
     (`test_layout_spec_fields_are_typed_enums`) MORA I DALJE PROĆI
     NEPROMIJENJEN (dokaz da su nova polja stvarno opciona, ne lome
     postojeću konstrukciju bez njih).
   - `tests/integration/database/repositories/test_sqlite_visual_repository.py`:
     novi testovi — round-trip `save_layout_spec`/`get_layout_spec` (pravi
     SQLite, seed-ovan `content_piece` red preko postojećeg
     `SqliteContentRepository` fixture obrasca, isti stil kao `_seed_campaign`
     helper koji već postoji u ovom fajlu), `get_layout_spec` na nepostojeći
     id vraća `None`. POSTOJEĆA tri testa (`test_repository_is_a_visual_repository_port`,
     `test_round_trip_visual_system`, `test_get_unknown_returns_none`) MORAJU
     I DALJE PROĆI NEPROMIJENJENA.
   - `tests/integration/database/test_migrations.py` (POSTOJI već, pokriva
     migration runner P0.17): dodati/potvrditi da `0005_layout_specs.sql`
     bude otkrivena i primijenjena bez grešaka na svježoj bazi (postojeći
     `test_fresh_db_migration_applies_foundation`-stil test, provjeriti da
     `applied` uključuje verziju 5 i da `schema_migrations` ima red za nju).

# Acceptance

- [ ] `LayoutSpecId` postoji u `domain/common/ids.py`.
- [ ] `LayoutSpec` ima tri nova OPCIONA polja (`id`, `content_piece_id`,
      `validation_status`), svi default `None`.
- [ ] Postojeća konstrukcija `LayoutSpec(...)` BEZ ovih polja (ACS-F1-029,
      `test_layout.py`) i dalje radi identično — 0 regresija (test dokaz).
- [ ] `resources/migrations/0005_layout_specs.sql` postoji, tabela tačno
      prati plan sekciju 24 (5 kolona + `id` PK).
- [ ] `run_migrations` na svježoj bazi primjenjuje `0005` bez greške,
      redoslijed poslije `0004`.
- [ ] `VisualRepositoryPort` ima `save_layout_spec`/`get_layout_spec`;
      postojeće `save_visual_system`/`get_visual_system` NETAKNUTE
      (git diff dokaz).
- [ ] `SqliteVisualRepository` implementira obje nove metode; round-trip
      test dokazuje save→get vraća identičan objekat (uključujući sve
      enum-tipizovana polja kao prave domain enume, ne stringove).
- [ ] `get_layout_spec` na nepostojeći id vraća `None`, ne baca izuzetak.
- [ ] `application/`, `domain/visual/entities.py`, `domain/visual/enums.py`,
      `domain/visual/slots.py`, `application/schemas/`, `resources/prompts/`,
      i postojeće migracije (`0000`-`0004`) NISU DIRANE.
- [ ] `python -m pytest tests/unit/domain/visual/ tests/integration/database/repositories/test_sqlite_visual_repository.py -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/domain/visual/ -v
python -m pytest tests/integration/database/repositories/test_sqlite_visual_repository.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `LayoutSpec` polja su STVARNO opciona (default `None`), postojeći
  ACS-F1-029 kod (`generate_visual_system.py`) i njegovi testovi i dalje
  prolaze bez izmjene poziva;
- migracija je čisto aditivna — pokrenuti `run_migrations` na bazi koja
  već ima `0000`-`0004` primijenjene i potvrditi da `0005` prolazi bez FK
  grešaka (test protiv prave baze sa postojećim `content_pieces` redom);
- `save_layout_spec`/`get_layout_spec` round-trip stvarno čuva enum tipove
  (ne string-ove) na povratku, isti nivo provjere kao postojeći
  `test_round_trip_visual_system`;
- nema promjene u `save_visual_system`/`get_visual_system` ponašanju (git
  diff, plus postojeća tri testa i dalje zelena nepromijenjena);
- `validation_status` kao plain `str` (ne enum) je namjerna Slice-1
  odluka — provjeriti da docstring to objašnjava, ne izgleda kao propust.

# Rollback

MEDIUM risk — aditivna migracija + domain polja + port proširenje, nema
brisanja/izmjene postojećeg ponašanja. Fix na istoj branch bez proširenja
scope-a. §29: Claude-only review, PASS → odmah merge.

# Coordination

Nezavisan od svega trenutno otvorenog. Blokira budući task (A13 dio 2b —
`plan_post_layout.py`/`validate_layout.py`, plan sekcije 40-41: AI-generisan
per-post `LayoutSpec` + deterministička provjera da headline tekst staje u
odabrani layout prema Slice-1 `ContentSlotContract` defaultima iz sekcije
41) — TAJ task se NE piše dok se ovaj ne mergira, jer zavisi od
`save_layout_spec`/`get_layout_spec`/`LayoutSpecId` koji ovaj task uvodi.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-030-layout-specs-foundation
Branch:   task/ACS-F1-030-layout-specs-foundation
Base:     main @ ea0820f
```
