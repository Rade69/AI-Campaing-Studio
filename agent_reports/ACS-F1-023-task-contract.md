---
task_id: ACS-F1-023
phase: Faza-1 (post A5, pre G10 analytics-ready)
title: "Nova migracija: UNIQUE indeksi za revisions(entity_type,entity_id,version) i campaign_items(plan_id,order)"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - resources/migrations/0004_uniqueness_constraints.sql
  - tests/unit/infrastructure/database/test_migrations.py
  - tests/integration/infrastructure/database/
forbidden_paths:
  - resources/migrations/0000_foundation.sql
  - resources/migrations/0001_brand_facts.sql
  - resources/migrations/0002_campaign_content_visual.sql
  - resources/migrations/0003_content_payload.sql
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/database/repositories/
  - src/ai_campaign_studio/infrastructure/database/migrations.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. Nova migracija je append-only (isti
    pattern kao 0000-0003) -- ne dira postojeće migracije/šemu, samo dodaje
    2 nova UNIQUE indeksa preko CREATE UNIQUE INDEX (SQLite nema ALTER TABLE
    ADD CONSTRAINT).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: a62fd5a
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Treći, temeljitiji spoljni code review prolaz je našao (koordinator
nezavisno potvrdio prije pisanja kontrakta, `grep -rn "UNIQUE"
resources/migrations/*.sql` → nula pogodaka u sve 4 postojeće migracije)
da cijela SQL šema NEMA nijedan UNIQUE constraint. Dvije konkretne
posljedice:

1. **`revisions` tabela** — `ReviseContentPiece.execute()` računa sljedeću
   verziju u Python-u:
   ```python
   existing = self._revision_repo.list_entity_revisions(...)
   next_version = len(existing) + 1
   ```
   Ovo NIJE atomsko na nivou baze — ništa ne sprječava da dva reda dobiju
   isti `(entity_type, entity_id, version)` par ako se ikad desi race
   (npr. dva paralelna poziva na istom desktop procesu, ili budući
   multi-window/multi-process scenario).
2. **`campaign_items` tabela** — `item.order` unutar jednog `plan_id`
   provjerava se JEDINO u use-case sloju (`edit_campaign_plan.py`
   `_validate_items`), ne u šemi. Baza dozvoljava duplikat `order` unutar
   istog plana.

**Zašto sad, ne kasnije**: ovo je jeftino popraviti dok nema pravih
korisnika/produkcijskih podataka — dodavanje UNIQUE indeksa kasnije, kad
baza već ima redove sa (teorijskim) duplikatima, zahtijeva prvo
deduplikaciju podataka, mnogo skuplje.

Ovo NIJE poznat/prihvaćen rizik — propust u šemi, ne namjeran dizajn.

**Provjereno prije kontrakta da fix neće pokvariti postojeće upsert
putanje**:
- `SqliteRevisionRepository.save_revision` koristi
  `ON CONFLICT(id) DO UPDATE` — conflict target je `id` (PK), NE
  `(entity_type, entity_id, version)`. Novi UNIQUE indeks je nezavisan
  dodatan safety net, ne mijenja postojeće ponašanje upsert-a po `id`-u.
- `SqliteCampaignRepository.save_plan` radi `DELETE FROM campaign_items
  WHERE plan_id = ?` pa reinsert svih stavki — atomično unutar iste
  transakcije, pa `UNIQUE(plan_id, "order")` neće sudariti stari i novi
  red pri re-save-u istog plana.

# Objective

Nova migracija `resources/migrations/0004_uniqueness_constraints.sql`
(append-only, isti pattern kao 0000-0003) dodaje TAČNO dva
`CREATE UNIQUE INDEX` iskaza (SQLite nema `ALTER TABLE ... ADD CONSTRAINT`):

```sql
CREATE UNIQUE INDEX idx_revisions_entity_version
    ON revisions(entity_type, entity_id, version);

CREATE UNIQUE INDEX idx_campaign_items_plan_order
    ON campaign_items(plan_id, "order");
```

# Implementation steps

1. Kreiraj `resources/migrations/0004_uniqueness_constraints.sql` sa gornja
   dva `CREATE UNIQUE INDEX` iskaza. Pogledaj `0003_content_payload.sql`
   kao referencu za format/stil komentara na vrhu fajla (NE DIRATI taj
   fajl, samo čitaj kao primjer).
2. Testovi:
   - Migracija se primjenjuje čisto na praznu bazu (postojeći
     `test_migrations.py` pattern već to provjerava za sve migracije —
     potvrdi da i 0004 prolazi isti test bez izmjene tog testa, samo
     dodavanjem novog fajla).
   - Novi test: pokušaj insertovati DVA `revisions` reda sa istim
     `(entity_type, entity_id, version)` (različit `id`) → mora baciti
     `sqlite3.IntegrityError`.
   - Novi test: pokušaj insertovati DVA `campaign_items` reda sa istim
     `(plan_id, "order")` (različit `id`) → mora baciti
     `sqlite3.IntegrityError`.
   - Potvrdi da postojeći `ReviseContentPiece`/`GenerateSocialPost`
     integration testovi (iz ACS-F1-021, već merged) i dalje prolaze
     nepromijenjeni — ovo je regresioni dokaz da normalan tok (jedinstvene
     verzije/order) nije pogođen.

# Acceptance

- [ ] `resources/migrations/0004_uniqueness_constraints.sql` postoji, sadrži
      tačno ta dva `CREATE UNIQUE INDEX` iskaza.
- [ ] Migracija se čisto primjenjuje na praznu bazu.
- [ ] Duplikat `(entity_type, entity_id, version)` u `revisions` baca
      `IntegrityError` (novi test dokazuje).
- [ ] Duplikat `(plan_id, order)` u `campaign_items` baca `IntegrityError`
      (novi test dokazuje).
- [ ] Postojeći `0000`-`0003` migracije NISU DIRANE (git diff dokaz).
- [ ] `domain/`, `application/`, `ports/`, repository fajlovi NISU DIRANI.
- [ ] `python -m pytest tests/unit/infrastructure/database/ tests/integration/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija —
      OVO JE POSEBNO VAŽNO ovdje jer novi indeksi mogu otkriti postojeći
      test fixture koji (ne)namjerno pravi duplikate; ako neki test PADNE
      zbog novog indeksa, NE MIJENJATI indeks da test prođe — javi
      koordinatoru, to je nalaz (test fixture pravi podatke koje šema sad
      ispravno odbija).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/infrastructure/database/ -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- indeks nazivi i kolone tačno odgovaraju kontraktu;
- migracija je čisto append-only, ne dira 0000-0003;
- postojeći upsert putanje (`save_revision` ON CONFLICT(id),
  `save_plan` delete-and-reinsert) i dalje rade nepromijenjeno;
- **koordinator će nezavisno primijeniti migraciju protiv svoje POSTOJEĆE
  lokalne dev baze** (korišćene za ACS-GUI-005 live test) prije merge-a,
  da potvrdi da ne postoje već-postojeći duplikati koji bi blokirali
  migraciju na stvarnim (ne samo praznim test) podacima.

# Rollback

MEDIUM risk — čisto aditivna šema izmjena (novi indeksi, ne mijenja
postojeće kolone/tabele). Fix na istoj branch bez proširenja scope-a.
§29: Claude-only review, PASS -> odmah merge.

# Coordination

Nezavisno od ACS-F1-020 (Pi, claim_linter fix runda) i ACS-F1-022
(MiniMax, role_sequence enforcement) — sva tri disjoint fajlovi, mogu ići
paralelno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-023-unique-constraints
Branch:   task/ACS-F1-023-unique-constraints
Base:     main @ a62fd5a
```
