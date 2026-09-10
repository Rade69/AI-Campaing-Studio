---
task_id: ACS-S2-016
phase: "S2-G7b — Brand Intelligence Review UI (bridge + ekran)"
title: "presentation_webview bridge + Brend ekran — get_ingestion_review, approve_fact_candidate, reject_fact_candidate, assemble_brand_snapshot"
coordinator: minimax (privremeni, Claude na pauzi zbog limita tokena)
implementer: pi
reviewers: [claude, codex, human_owner]
status: "OPEN -- contract written before code, zadnji blokirajući task prije 'unesi URL → vidi rezultat' demo"
created_at: 2026-09-10
dependencies: [ACS-S2-001, ACS-S2-002, ACS-S2-014, ACS-S2-015]  # svi MERGED
risk: HIGH
gitnexus_required: true
adversarial_required: true
---

# Kontekst

Osmi i **zadnji blokirajući** Slice 2 gate (a-dio G7 je G7a,
MERGED u PR #31 kao `37af25b`). Kanonski plan §10 S2-G7b
specificira:

> "**Scope:** proširenje Brend ekrana + bridge read/write metode
> (`get_ingestion_review`, `approve_fact_candidate`,
> `reject_fact_candidate`, `assemble_brand_snapshot`)."

**Risk: HIGH (GUI lifecycle + human-in-loop, ista klasa kao
P1.5-G7a/b sa `pywebviewready` timing rizikom).** Pun ciklus:
Claude re-review → Codex adversarial re-review → Human Owner
eksplicitno odobrenje (NE §29, NE koordinator-override). Ako
Claude ostane na pauzi, vidjeti §Workflow odstupanja ispod.

**Zašto je ZADNjI BLOKIRAJUĆI**: kad G7b bude merged, čitava
"unesi URL brenda, vidi izvučene fact-ove, odobri/odbij ih" petlja
je ZATVORENA u aplikaciji — G6 cijevi, G7a use-case-i, G7b
GUI/bridge za interakciju. To je bio cilj koji je Human Owner
tražio prije par poruka.

# Ključna arhitektonska odluka (VEĆ VERIFIKOVANA)

**`BrandSnapshot.approved_fact_ids: tuple[FactId, ...]` VEĆ
POSTOJI** u `domain/brand/entities.py:52` (Faza 1).
`sqlite_brand_repository.py:save_brand_snapshot` već prihvata
`BrandSnapshot` sa `approved_fact_ids` (linija 91-96) i čita ih
nazad (linija 130). Faza 1 već radi join preko
`brand_snapshot_facts` tabele.

**`assemble_brand_snapshot` NE TREBA** uvoditi novi domain entitet
niti novi repository contract. Bridge metoda samo:

1. Prikupi `ApprovedFact` ID-ove za brend (preko
   `FactRepositoryPort.list_approved_facts_by_brand(brand_id) -> tuple[ApprovedFact, ...]`
   — **ova metoda NE POSTOJI**, treba je dodati, vidi §3)
2. Učita zadnji `BrandSnapshot` za brend (preko novog
   `BrandRepositoryPort.get_latest_snapshot(brand_id) -> BrandSnapshot | None`,
   vidi §3), ili `None` ako nema prethodnih
3. Inkrementira `version` (zadnji.version + 1, ili 1 za prvi)
4. Konstruiše novi `BrandSnapshot` sa svim
   `BrandSnapshot` poljima (voice, audiences, services, visual,
   restrictions — kopira iz zadnjeg ako postoji) + `approved_fact_ids`
5. `brand_repo.save_brand_snapshot(snapshot)`
6. Vrati `{"snapshot_id": str, "version": int, "approved_fact_count": int}`

# §1 — Scope (allowed_paths, sve su ADITIVNE izmjene)

```yaml
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py  # 4 nove metode
  - src/ai_campaign_studio/presentation_webview/screens/brend/__init__.py  # proširenje
  - src/ai_campaign_studio/presentation_webview/static/app.js  # handler-i
  - src/ai_campaign_studio/presentation_webview/screens/_static_pages.py  # ako treba helper
  - src/ai_campaign_studio/ports/repositories.py  # proširenje BrandRepositoryPort + FactRepositoryPort
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_repository.py  # save/get_latest + implementacija list_approved_facts
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_fact_repository.py  # implementacija list_approved_facts_by_brand
  - src/ai_campaign_studio/application/ingestion/dependencies.py  # ako treba expose novi repo
  - tests/unit/presentation_webview/bridge/test_ingestion_review_bridge.py  # NOVI
  - tests/unit/presentation_webview/screens/test_brend_review_ui.py  # NOVI
  - tests/unit/ports/test_repositories_g7b.py  # NOVI (port method smoke)
  - tests/integration/presentation_webview/test_ingestion_review_flow.py  # NOVI (end-to-end)
  - agent_reports/2026-09-10-ACS-S2-016-pi.md
  - agent_reports/2026-09-10-ACS-S2-016-fix-round*-brief.md  # ako treba
forbidden_paths:
  - src/ai_campaign_studio/domain/brand/entities.py  # NE DIRATI — BrandSnapshot već ima approved_fact_ids
  - src/ai_campaign_studio/domain/brand/value_objects.py  # NE DIRATI
  - src/ai_campaign_studio/domain/facts/entities.py  # NE DIRATI
  - src/ai_campaign_studio/domain/facts/policies.py  # NE DIRATI
  - src/ai_campaign_studio/domain/ingestion/  # NE DIRATI
  - src/ai_campaign_studio/application/ingestion/approve_fact_candidates.py  # NE DIRATI (G7a MERGED)
  - src/ai_campaign_studio/application/ingestion/reject_fact_candidates.py  # NE DIRATI (G7a MERGED)
  - src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py  # NE DIRATI (G6 MERGED)
  - src/ai_campaign_studio/infrastructure/web_ingestion/  # NE DIRATI
  - src/ai_campaign_studio/infrastructure/extraction/  # NE DIRATI
  - src/ai_campaign_studio/infrastructure/visual_extraction/  # NE DIRATI
  - src/ai_campaign_studio/infrastructure/document_ingestion/  # NE DIRATI
  - resources/migrations/  # NE DIREKTORIJSKE IZMJENE (nema nove migracije u G7b)
```

# §2 — Bridge metode (4 nove, na `CampaignBridgeApi`)

## 2.1 `get_ingestion_review(self, raw_payload: dict) -> dict`

**Input** (raw_payload, standardni Faza 1 dict format):
```python
{"brand_id": "<str>"}
```

**Output** (success):
```python
{
  "ok": True,
  "brand_id": "<str>",
  "candidates": [
    {
      "candidate_id": "<str>",
      "snapshot_id": "<str>",
      "snapshot_url": "<str>",  # iz SourceSnapshot
      "content": "<str>",  # FactCandidate.content (plain text)
      "chunk_id": "<str | None>",
      "status": "PROPOSED",  # ili APPROVED/REJECTED
      "created_at": "<iso8601>"
    },
    ...  # SVI FactCandidate za brend (po FactRepositoryPort.list_fact_candidates_by_brand)
  ],
  "approved_count": 3,  # broj APPROVED (NE u "candidates" listi, zaseban brojač)
  "rejected_count": 0
}
```

**Greške**: `_brand_err("brand_not_found", ...)`, `_ingestion_err("repo_error", ...)`.

## 2.2 `approve_fact_candidate(self, raw_payload: dict) -> dict`

**Input**:
```python
{"candidate_id": "<str>"}
```

**Output** (success):
```python
{
  "ok": True,
  "approved_fact_id": "<str>",  # novi ApprovedFact.id (UUID ili hash-based, vidjeti G7a)
  "candidate_id": "<str>",
  "snapshot_url": "<str>",  # iz source_ref.uri
  "version": 1
}
```

**Implementacija**: delegirati na G7a `ApproveFactCandidate.execute(candidate_id)`
(preko dependency injection — bridge NE smije importovati application
layer direktno, koristiti DI container). G7a već garantuje:
- Idempotency: dvostruki approve na ISTI candidate → `InvariantViolation`
- Atomicity: save_fact + save_fact_candidate u UnitOfWork

**Greške**: `_brand_err("invariant_violation", ...)` ako već
APPROVED/REJECTED, `_brand_err("candidate_not_found", ...)` ako
nema.

## 2.3 `reject_fact_candidate(self, raw_payload: dict) -> dict`

**Input**:
```python
{"candidate_id": "<str>", "reason": "<str | None>"}
```

**Output** (success):
```python
{"ok": True, "candidate_id": "<str>", "status": "REJECTED"}
```

**Implementacija**: delegirati na G7a `RejectFactCandidate.execute(candidate_id, reason)`.
`reason` je dokumentovan u G7a contract kao `OUT_OF_SCOPE_FINDING`
(nije polje na FactCandidate, persistira se samo kao log; ako
korisnik misli da je reason bitan za audit, eskalirati).

**Greške**: iste kao 2.2.

## 2.4 `assemble_brand_snapshot(self, raw_payload: dict) -> dict`

**Input**:
```python
{"brand_id": "<str>"}
```

**Output** (success):
```python
{
  "ok": True,
  "snapshot_id": "<str>",
  "brand_id": "<str>",
  "version": 2,  # inkrement
  "approved_fact_count": 5,
  "created_at": "<iso8601>"
}
```

**Implementacija** (vidi "Ključna arhitektonska odluka"):
1. `fact_repo.list_approved_facts_by_brand(brand_id)` → lista ApprovedFact
2. `brand_repo.get_latest_snapshot(brand_id)` → None ili zadnji BrandSnapshot
3. Ako prazan `approved_fact_ids` (nema APPROVED) → `_brand_err("no_approved_facts", "...")`
4. Konstruiše `BrandSnapshot(brand_id=..., version=last.version+1 or 1, ...)` sa:
   - `voice`, `audiences`, `services`, `visual_identity`, `restrictions`
     KOPIRANA iz zadnjeg (ili default prazni value objects za prvi)
   - `language`, `locale`, `script` kopirana iz zadnjeg (default
     "en" / "en_US" / "Latin" za prvi)
   - `approved_fact_ids = tuple(f.id for f in approved_facts)`
5. `brand_repo.save_brand_snapshot(snapshot)` — već postoji,
   prima `BrandSnapshot` sa `approved_fact_ids`
6. Vrati dict

**Greške**: `_brand_err("brand_not_found", ...)`, `_brand_err("no_approved_facts", ...)`,
`_brand_err("repo_error", ...)`.

# §3 — Port proširenja (ADITIVNO, ne mijenja potpise postojećih metoda)

## 3.1 `FactRepositoryPort` (`ports/repositories.py`)

Dodati:
```python
def list_approved_facts_by_brand(self, brand_id: BrandId) -> tuple[ApprovedFact, ...]:
    """Return all APPROVED facts for a brand, ordered by created_at DESC.

    Used by assemble_brand_snapshot to compute approved_fact_ids
    for a new BrandSnapshot. Empty tuple if no approved facts.
    """
```

`sqlite_fact_repository.py`: implementacija preko JOIN
`approved_facts` + `fact_candidates` + `source_snapshots` (isti
obrazac kao i ostali read modeli).

## 3.2 `FactRepositoryPort` (dodatno)

Dodati:
```python
def list_fact_candidates_by_brand(
    self, brand_id: BrandId, statuses: tuple[FactStatus, ...] | None = None
) -> tuple[FactCandidate, ...]:
    """Return FactCandidate rows for a brand, optionally filtered by
    statuses. Default returns all (PROPOSED, APPROVED, REJECTED).
    Used by get_ingestion_review.
    """
```

`sqlite_fact_repository.py`: implementacija.

## 3.3 `BrandRepositoryPort` (`ports/repositories.py`)

Dodati:
```python
def get_latest_snapshot(self, brand_id: BrandId) -> BrandSnapshot | None:
    """Return the highest-version BrandSnapshot for a brand, or None
    if no snapshot has been assembled yet. Used by
    assemble_brand_snapshot to compute the next version.
    """
```

`sqlite_brand_repository.py`: implementacija `ORDER BY version DESC LIMIT 1`.

**NE DIRAJ** `save_brand_snapshot` (već radi), `save_brand`,
`get_brand`, ostale postojeće metode.

# §4 — GUI ekran (Brend ekran proširenje)

## 4.1 `screens/brend/__init__.py`

Dodati novi route `brend.fact_review` (slug/handler). Pattern
pratiti Faza 1 konvenciju (vidjeti `screens/kampanje/__init__.py`
i slične za referencu PRIJE pisanja).

**Prikaz**: lista FactCandidate redova (iz `get_ingestion_review`),
sa dva dugmeta po redu: "Approve" (poziva 2.2) i "Reject" (poziva
2.3, sa opcionalnim reason text input-om). Na vrhu ekrana: broj
PROPOSED, APPROVED, REJECTED, + dugme "Assemble Brand Snapshot"
(poziva 2.4, vidljivo samo ako APPROVED > 0).

## 4.2 `static/app.js`

Dodati handler-e za:
- `get_ingestion_review` (load na mount)
- `approve_fact_candidate` (dugme)
- `reject_fact_candidate` (dugme + reason)
- `assemble_brand_snapshot` (dugme)

Svi error-response-ovi MORAJU biti vidljivi korisniku (toast /
inline error). NE tiho swallow-ati greške.

**Node/VM izvršni test OD PRVE VERZIJE** (kanonski plan §10
ključna odluka, isti obrazac kao F1-046/049/051/053 — 4 puta
dokazano). Ako se pojavi query-param parsing obrazac, reuse-ovati
postojeći (vidjeti Codex F1-053 napomena u planu), ne ponoviti
treći put.

# §5 — Acceptance

- [ ] `get_ingestion_review` vraća PROPOSED/APPROVED/REJECTED
      candidate za brend, sa `snapshot_url` iz SourceSnapshot
- [ ] `approve_fact_candidate` delegira na G7a `ApproveFactCandidate`,
      NEMA bypass logike, NEMA vlastite FactCandidate mutacije
- [ ] `reject_fact_candidate` isto, delegira na G7a `RejectFactCandidate`
- [ ] `assemble_brand_snapshot` NE kreira ApprovedFact (G7a posao),
      SAMO kreira BrandSnapshot sa `approved_fact_ids` (već
      postojećim ApprovedFact ID-evima)
- [ ] `assemble_brand_snapshot` inkrementira version (zadnji + 1,
      ili 1 za prvi); dva uzastopna poziva daju version=1, version=2
- [ ] `assemble_brand_snapshot` sa praznim approved_facts → greška
      `no_approved_facts`, NE pravi prazan BrandSnapshot
- [ ] GUI ekran prikazuje listu, approve/reject/assemble dugmad
      rade, greške su vidljive korisniku
- [ ] **G-WI-EVIDENCE nastavlja vrijediti**: nakon assemble, svaki
      ApprovedFact u `approved_fact_ids` ima `source_ref.uri` koji
      je TRAGABLE do SourceSnapshot URL-a (nije tip-nivo, nego
      podatak-nivo, integration test)
- [ ] **Idempotency (G7a)**: dvostruki approve istog candidate_id
      preko bridge → `invariant_violation` (G7a garantuje, bridge
      samo prosljeđuje)
- [ ] **Atomicity (G7a)**: ako save_fact padne, NI save_fact_candidate
      ne perzistira (G7a UnitOfWork, bridge ne dira)
- [ ] `BrandSnapshot.approved_fact_ids: tuple[FactId, ...]` se
      NE dira u `domain/brand/entities.py` (vec postoji)
- [ ] Nema nove migracije (G7b koristi postojeću
      `brand_snapshot_facts` join tabelu)
- [ ] **Izvršni Node/VM test** za `static/app.js` (NE
      string-assertion) — demonstrira DOM rendering + button
      click → bridge call → DOM update flow
- [ ] `python -m pytest -q` (DeepSeek unset) pun suite prolazi, 0
      regresija
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze
- [ ] GitNexus pre-change context + `detect_changes` evidence
- [ ] **CI provjeren preko PR-a** (test + lint + mypy job)

# §6 — Implementation steps

1. Pročitati `ports/repositories.py`, `domain/brand/entities.py`,
   `domain/facts/entities.py`, `domain/facts/enums.py`,
   `infrastructure/database/repositories/sqlite_brand_repository.py`,
   `infrastructure/database/repositories/sqlite_fact_repository.py`
   u cjelini (NE pretpostaviti potpise).
2. Pročitati `presentation_webview/bridge/__init__.py` Faza 1
   pattern (Faza 1 reference: `get_brand_overview`, `list_campaigns`,
   `_resource_scope`, `_brand_err`).
3. Pročitati `screens/brend/__init__.py` i jedan drugi Faza 1
   ekran (npr. `screens/kampanje/__init__.py`) za route pattern.
4. Pročitati `static/app.js` za DOM handler pattern.
5. Pročitati G7a evidence
   (`agent_reports/2026-09-10-ACS-S2-015-opencode.md`) za stil
   G7a use-case-ova.
6. Proširiti `FactRepositoryPort` sa
   `list_approved_facts_by_brand` + `list_fact_candidates_by_brand`.
7. Proširiti `BrandRepositoryPort` sa `get_latest_snapshot`.
8. Implementirati SQL upite u `sqlite_fact_repository.py` i
   `sqlite_brand_repository.py`.
9. Dodati 4 bridge metode u `CampaignBridgeApi`.
10. Dodati `brend.fact_review` route + handler u
    `screens/brend/__init__.py`.
11. Dodati DOM handler-e u `static/app.js` (Node/VM test).
12. Unit + integration testovi:
    - `tests/unit/presentation_webview/bridge/test_ingestion_review_bridge.py`
    - `tests/unit/presentation_webview/screens/test_brend_review_ui.py`
    - `tests/unit/ports/test_repositories_g7b.py` (port method smoke)
    - `tests/integration/presentation_webview/test_ingestion_review_flow.py`
13. GitNexus `detect_changes` PRIJE commit-a.
14. Lokalni commit, push, otvori PR.

# §7 — Review focus — Claude + Codex (HIGH, pun ciklus)

- **GUI lifecycle (pywebviewready timing)** — `screens/brend/`
  route se MORA registrovati PRIJE `app.js` mount-a; vidjeti F1-047
  obrazac za referencu.
- **human-in-loop idempotency** — bridge approve/reject MORA
  delegirati na G7a bez vlastite logike (NE duplicirati
  `assert_candidate_proposed` u bridge).
- **`assemble_brand_snapshot` validacija** — prazan
  `approved_fact_ids` MORA biti error, NE prazan BrandSnapshot.
  Ovo je "snimak bez sadržaja" anti-pattern.
- **Snapshot version race** — dva uzastopna assemble poziva u
  istom `run_id` MORAJU dati version=1, version=2 (NE oba
  version=2). Ako korisnik klikne "Assemble" dva puta brzo,
  drugi klik MORA dobiti novi version.
- **Port method smoke** — svaki novi port method MORA imati unit
  test koji dokazuje da SQL upit radi sa praznom bazom (ne
  crashuje, vraća prazan tuple).
- **Bridge error contract** — `_brand_err`, `_ingestion_err`
  pattern iz Faza 1; NE izmišljati nove error code-ove bez
  coordinate sa Claude-om.
- **Scope-cleanliness** — NULA izmjena u `forbidden_paths`.
  Posebno: NE dirati `domain/brand/entities.py` (`BrandSnapshot`
  već ima `approved_fact_ids`).

# §8 — Workflow (HIGH, pun ciklus)

1. **Pi implementer** piše kod po ovom contract-u, pokreće
   `python -m pytest -q`, `python -m ruff check .`,
   `python -m mypy src`. Otvara PR.
2. **Claude re-review** (kad se vrati sa pauze) — provjeri scope,
   contract-compliance, integration testove.
3. **Codex adversarial re-review** — fresh repro za svaku
   acceptance tačku, posebno:
   - assemble_brand_snapshot sa praznim approved_facts → error
   - approve preko bridge idempotency (dvostruki approve istog
     candidate → invariant_violation)
   - GUI lifecycle (pywebviewready timing)
4. **Coordinator** (MiniMax) — nezavisna verifikacija, mutation-
   test na ključnim invariantama:
   - Reverziraj `assert_candidate_proposed` provjeru u
     bridge delegaciji → test pada
   - Reverziraj `no_approved_facts` provjeru u
     `assemble_brand_snapshot` → test pada
5. **Human Owner** — eksplicitno odobrenje za squash-merge
   PR-a (NE §29, NE koordinator-override).
6. **Coordinator** — squash-merge, post-merge ciklus
   (git pull, npx gitnexus analyze, CURRENT_STATE.md prepend,
   CI verification).
7. **Demo** — "unesi URL, vidi rezultat" petlja ZATVORENA u
   aplikaciji, end-to-end demo spreman.

# §9 — Workflow odstupanja (ako Claude ostane na pauzi)

G6 je merged sa Human Owner + Codex PASS + Claude PASS override
(dokumentovano u `agent_reports/2026-09-10-ACS-S2-014-claude-pass-override.md`).
**G7b NE SMIJE koristiti isti override** bez eksplicitnog
dopuštenja Human Owner-a u ovom tasku — Claude review je
obavezan za GUI lifecycle klase.

Ako Claude ostane na pauzi, koordinator MORA:
1. Sačekati Claude povratak
2. ILI: tražiti novi Human Owner override (jednokratni, ne
   praviti presedan za buduće HIGH taskove)

# §10 — Out of scope (ne raditi)

- Nema izmjene `BrandSnapshot` VO (već ima `approved_fact_ids`)
- Nema izmjene `FactCandidate` VO (G7a već dodao `REJECTED`)
- Nema nove migracije
- Nema izmjene `application/ingestion/approve_fact_candidates.py`
  (G7a MERGED)
- Nema izmjene G3/G4/G5/G6/G9 koda
- Nema proširenja scope-a na druge ekrane (kalendar, kampanje,
  itd. — samo Brend)
- Nema S2-G8 (Playwright fallback) izmjene (opcioni, kasnije)
- Nema UI redesign-a Brend ekrana (samo proširenje sa novim
  sub-route-om)
- Nema novog WebView entry point-a (koristiti postojeći)
- Nema mockovanje `_brand_repo` u bridge testovima (koristiti
  pravu SQLite, isti pattern kao G7a integration testovi)
