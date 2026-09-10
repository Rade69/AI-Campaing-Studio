---
task_id: ACS-S2-015
phase: "S2-G7a — Approve/Reject FactCandidate use-case"
title: "application/ingestion/approve_fact_candidates.py — ApproveFactCandidate + RejectFactCandidate"
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-10
dependencies: [ACS-S2-001, ACS-S2-002]
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/application/ingestion/approve_fact_candidates.py
  - src/ai_campaign_studio/domain/facts/enums.py
  - src/ai_campaign_studio/domain/facts/policies.py
  - tests/unit/application/ingestion/test_approve_fact_candidates.py
  - tests/unit/domain/facts/test_policies.py
  - tests/integration/application/ingestion/test_approve_fact_candidates_flow.py
forbidden_paths:
  - src/ai_campaign_studio/domain/facts/entities.py
  - src/ai_campaign_studio/domain/ingestion/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/application/ingestion/ingest_brand_sources.py
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Sedmi Slice 2 gate (a-dio). Kanonski plan §10 "S2-G7a": *"Scope:
`application/ingestion/approve_fact_candidates.py`. Approval pravi NOV
`ApprovedFact`, nikad ne mutira candidate; reject označava candidate.
Recrawl NIKAD tiho ne prepisuje postojeći `ApprovedFact` — promijenjen
izvor pravi NOVI `CONFLICTED`/`CHANGE_DETECTED` candidate za ljudski
re-review."* Risk MEDIUM (provenance invariant).

**Ovaj task NAMJERNO NE zavisi kodno od S2-G6** (Pipeline
Orchestration, trenutno u implementaciji, worktree
`ACS-S2-014-ingestion-pipeline`) — G7a operiše nad VEĆ PERSISTOVANIM
`FactCandidate` redovima preko `IngestionRepositoryPort`
(`get_fact_candidate`/`save_fact_candidate`, S2-G1/S2-G2, MERGED),
isto kao što je S2-G2 svoje testove pisao sa ručno seed-ovanim
podacima bez čekanja na G3/G4/G5/G9. **Ovaj task se MOŽE raditi
PARALELNO sa G6-ovom implementacijom** — vidi §Coordination ispod za
punu analizu i provjeru.

Reference dokumenti (`.agent/TASK_ROUTING.md` "Website Ingestion task"):
kanonski plan §2 (fact-first princip, provenance nikad implicitan),
§11 (G-WI-EVIDENCE, G-WI-FACT-FIRST hard gate-ovi), `domain/facts/entities.py`
(`FactCandidate`/`ApprovedFact`/`SourceReference`), `domain/facts/policies.py`
(`is_candidate_proposed`/`assert_candidate_proposed`, S2-G1).

# §1 — Gap ispunjen unutar ovog kontrakta: `FactStatus.REJECTED`

`FactStatus` enum (S2-G1) ima `APPROVED`/`SUPERSEDED`/`SOFT_DELETED`/
`PROPOSED` — NEMA `REJECTED`. G1-ova `is_candidate_proposed` docstring
ovo eksplicitno predviđa: *"e.g. a future REJECTED status"*. Isti
obrazac gap-a kao S2-002 (`CrawlTarget`) i S2-014 (`UrlClassifierPort`)
— mali, dobro-definisan dodatak unutar gate-a koji ga prvi put stvarno
treba.

`domain/facts/enums.py`: dodati `REJECTED = "REJECTED"` na kraj enum-a
(postojeće 4 vrijednosti netaknute).

# §2 — Odluka (koordinator, 2026-09-10): odobreni fakt je "free-floating" u v1

Kanonski plan §10 S2-G7b (SLJEDEĆI gate, GUI) eksplicitno navodi
`assemble_brand_snapshot` kao ZASEBAN bridge metod, odvojen od
`approve_fact_candidate`/`reject_fact_candidate`. Nezavisno
verifikovano: linkovanje `ApprovedFact` → `BrandSnapshot` ide preko
`brand_snapshot_facts` join tabele, koju POPUNJAVA
`save_brand_snapshot` preko `BrandSnapshot.approved_fact_ids: list[FactId]`
polja (`sqlite_brand_repository.py:91-96`) — kreiranje NOVE
`BrandSnapshot` verzije je vlastita, veća operacija (Brand domen, ne
Facts/Ingestion domen).

**Odluka: G7a v1 SAMO kreira `ApprovedFact` (ne-linkovan ni na jedan
`BrandSnapshot`).** Linkovanje (`assemble_brand_snapshot`) je
EKSPLICITNO van scope-a OVOG taska — dolazi sa G7b. Ovo drži G7a
tijesno uz kanonski plan §10 tekst (samo `approve_fact_candidates.py`)
i izbjegava da ova MEDIUM task nenamjerno preraste u Brand-domain
izmjenu (koja bi bila HIGH — postojeći `BrandSnapshot`/`approved_fact_ids`
kod je van `allowed_paths`, netaknut).

# Objective

## 1. `domain/facts/policies.py` — nova čista funkcija (aditivno)

```python
def build_approved_fact_from_candidate(
    candidate: FactCandidate,
    snapshot: SourceSnapshot,
) -> ApprovedFact:
    """Build the FIRST version of a brand-new ApprovedFact from a
    PROPOSED FactCandidate. Caller MUST call assert_candidate_proposed
    first. Always version=1, fresh logical_fact_id (this is a NEW
    logical fact, not a next version of an existing one — merging into
    an existing logical fact is an explicit future feature, not v1)."""
```

`source_ref = SourceReference(source_type="web_ingestion", uri=snapshot.url,
snapshot_id=str(candidate.snapshot_id), chunk_id=str(candidate.chunk_id)
if candidate.chunk_id else None)` — G-WI-EVIDENCE dokaz (traceable do
`SourceSnapshot`).

Unit test: dokazuje `version == 1`, `status == APPROVED`, `logical_fact_id`
je fresh (nije prazan, nije `candidate.id`), `source_ref.uri == snapshot.url`.

## 2. `application/ingestion/approve_fact_candidates.py` (nov fajl)

```python
class ApproveFactCandidate:
    def __init__(self, ingestion_repo: IngestionRepositoryPort,
                 fact_repo: FactRepositoryPort) -> None: ...
    def execute(self, candidate_id: FactCandidateId) -> ApprovedFact:
        """1. get_fact_candidate -- ako None, raise (implementer bira
        tačan error tip, isti stil kao ostatak application layer-a).
        2. assert_candidate_proposed(candidate) -- InvariantViolation
        ako već APPROVED/REJECTED (idempotency-safe: dvostruki approve
        MORA pasti, ne tiho no-op-ovati -- provenance invarijanta).
        3. get_source_snapshot(candidate.snapshot_id) -- za source_ref.uri.
        4. build_approved_fact_from_candidate(candidate, snapshot).
        5. fact_repo.save_fact(approved_fact).
        6. candidate SE NE MUTIRA (frozen) -- konstruisati NOVU kopiju
           preko dataclasses.replace(candidate, status=FactStatus.APPROVED)
           i save_fact_candidate() -- candidate.content/snapshot_id/
           chunk_id/created_at OSTAJU IDENTIČNI, samo status polje se
           mijenja (isti princip kao ApprovedFact immutable-replace).
        7. Return approved_fact.
        ATOMICITY: ako je save_fact uspio ALI save_fact_candidate
        padne (ili obrnuto), stanje je nekonzistentno (fact postoji,
        candidate i dalje PROPOSED, ili obrnuto). Implementer MORA
        koristiti postojeći UnitOfWork obrazac (isti kao ostali
        multi-write use-case-i u projektu -- pogledati CreateCampaign
        ili sličan za referencu PRIJE pisanja) da oba write-a budu
        atomska."""

class RejectFactCandidate:
    def __init__(self, ingestion_repo: IngestionRepositoryPort) -> None: ...
    def execute(self, candidate_id: FactCandidateId, reason: str | None = None) -> None:
        """1. get_fact_candidate -- raise ako None.
        2. assert_candidate_proposed -- isto kao approve, dvostruki
           reject/reject-nakon-approve MORA pasti.
        3. dataclasses.replace(candidate, status=FactStatus.REJECTED)
           -- reason NIJE polje na FactCandidate (S2-G1 entitet nema
           to polje) -- ako implementer smatra da je reason bitan za
           audit, DOKUMENTOVATI kao OUT_OF_SCOPE_FINDING (dodavanje
           polja je domain/facts/entities.py izmjena, VAN
           allowed_paths ovog taska), NE tiho odbaciti parametar bez
           napomene.
        4. save_fact_candidate()."""
```

# Acceptance

- [ ] `FactStatus.REJECTED` dodano, postojeće 4 vrijednosti netaknute.
- [ ] `build_approved_fact_from_candidate` — pure function, testirana
      izolovano (bez repo-a).
- [ ] `ApproveFactCandidate.execute`: PROPOSED candidate → nov
      `ApprovedFact` (version=1, status=APPROVED) PERZISTOVAN preko
      `fact_repo.save_fact` + candidate PERZISTOVAN sa
      `status=APPROVED` preko `ingestion_repo.save_fact_candidate` —
      OBOJE atomski (UnitOfWork).
- [ ] `ApproveFactCandidate` na NE-PROPOSED candidate (već APPROVED
      ili REJECTED) → `InvariantViolation`, NIŠTA se ne piše (test
      dokazuje da se `save_fact`/`save_fact_candidate` NE pozivaju --
      npr. preko spy/mock repo-a ili provjerom da baza ostaje
      nepromijenjena).
- [ ] `RejectFactCandidate.execute`: PROPOSED → REJECTED, `ApprovedFact`
      se NIKAD ne kreira za reject putanju.
- [ ] `RejectFactCandidate` na NE-PROPOSED candidate → `InvariantViolation`.
- [ ] **G-WI-EVIDENCE dokazano integration testom**: kreiran stvaran
      `SourceSnapshot` + `FactCandidate` preko `IngestionRepositoryPort`,
      approve, pa provjereno da `approved_fact.source_ref.uri ==
      snapshot.url` i `source_ref.snapshot_id == str(candidate.snapshot_id)`
      -- traceable unazad, ne samo tip-nivo (S2-G1 je to dokazao na
      tip-nivou, ovaj integration test dokazuje na PODATAK-nivou).
- [ ] `ApprovedFact` NIJE linkovan ni na jedan `BrandSnapshot` (§2 --
      potvrditi da `brand_snapshot_facts` tabela NIJE dirana, van
      `allowed_paths` svakako, ali test treba EKSPLICITNO dokumentovati
      da je ovo namjerna v1 granica, ne propust).
- [ ] Atomicity test (mid-failure): `save_fact` uspije, `save_fact_candidate`
      simulirano padne (ili obrnuto) → UnitOfWork rollback, NIŠTA
      persistovano (isti stil test kao ACS-F1-009's `test_end_to_end_fixture_to_plan`
      atomicity dokaz — pogledati kao referencu).
- [ ] `python -m pytest -q` (DeepSeek unset) pun suite prolazi, 0
      regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` -- POSEBNO nula izmjena u
      `domain/facts/entities.py` (nema novog polja na `FactCandidate`
      za `reason`, čak i ako implementer misli da bi bilo korisno --
      eskalirati kao OUT_OF_SCOPE_FINDING umjesto samoinicijativno
      dodavati).
- [ ] GitNexus pre-change context + `detect_changes` evidence.
- [ ] **CI provjeren preko PR-a.**

# Implementation steps

1. Pročitati `domain/facts/entities.py`, `domain/facts/policies.py`,
   `domain/facts/enums.py` (S2-G1 stanje) u cjelini.
2. Pročitati `ports/repositories.py` — `FactRepositoryPort` i
   `IngestionRepositoryPort` tačne metode (ne pretpostaviti imena).
3. Pronaći postojeći UnitOfWork-korišćen use-case kao stil-referencu
   (npr. `application/campaigns/create_campaign.py` ili slično) PRIJE
   pisanja `ApproveFactCandidate`.
4. Dodati `FactStatus.REJECTED`.
5. Napisati `build_approved_fact_from_candidate` + unit test.
6. Napisati `ApproveFactCandidate`/`RejectFactCandidate` + unit +
   integration testovi.
7. GitNexus `detect_changes` prije commit-a.

# Review focus — Claude (MEDIUM, §29)

- Provenance invarijanta bukvalno ispoštovana: candidate se NIKAD ne
  mutira in-place (frozen dataclass + `dataclasses.replace`, ne
  `object.__setattr__` hack).
- Dvostruki approve/reject MORA pasti (ne tiho no-op) — ovo je SRŽ
  provenance garancije.
- Atomicity (UnitOfWork) stvarno korišten, ne dva odvojena
  nezaštićena write-a.
- `ApprovedFact` NIJE linkovan na `BrandSnapshot` (§2 granica
  ispoštovana).
- `FactStatus.REJECTED` dodavanje čisto aditivno (GitNexus
  `detect_changes` potvrda).

# Rollback

MEDIUM risk (application-layer logika nad već-pregledanim S2-G1/S2-G2
tipovima, nema I/O concurrency, nema migracije, nema GUI). Claude-only
review → odmah merge po §29 ako PASS.

# Coordination — PARALELNI RAD (provjereno, workflow §10)

**Ovaj task MOŽE ići PARALELNO sa S2-G6 implementacijom** (worktree
`ACS-S2-014-ingestion-pipeline`, trenutno aktivan):

1. **`allowed_paths` presjek**: G6 dira `application/ingestion/
   ingest_brand_sources.py` (jedan fajl) + `infrastructure/web_ingestion/
   url_classifier.py`. G7a dira `application/ingestion/
   approve_fact_candidates.py` (drugi fajl) + `domain/facts/enums.py`/
   `policies.py`. NULA presjeka na file-nivou. Oba taska kreiraju NOVE
   fajlove u ISTOM `application/ingestion/` direktorijumu koji trenutno
   ne postoji na `main` (G6 worktree ga je tek napravio, necommit-ovano)
   — git ovo rješava bez konflikta (dva različita nova fajla u istom
   direktorijumu se ne sudaraju), JEDINO potencijalno dijeljeno mjesto
   je `application/ingestion/__init__.py` AKO oba taska pokušaju
   kreirati/mijenjati export listu — implementer G7a treba PROVJERITI
   da li G6 worktree već ima taj fajl PRIJE nego ga kreira (`git log`/
   `ls` na G6 worktree), i ako da, dodati SVOJ export bez brisanja
   G6-ovog (mali, lako rješiv detalj, ne blokira paralelan start).
2. **Semantička zavisnost**: G7a NE poziva niti uvozi ništa iz
   `ingest_brand_sources.py` — testira se nad ručno seed-ovanim
   `FactCandidate`/`SourceSnapshot` podacima preko
   `IngestionRepositoryPort` direktno (isti obrazac kao S2-002's
   testovi, koji nisu čekali G3/G4/G5/G9 da postoje). Nema skrivene
   zavisnosti na G6-ovo ponašanje.
3. **GitNexus**: `IngestionRepositoryPort`/`FactRepositoryPort` su
   shared-contract portovi koje OBA taska čitaju (ne mijenjaju) — bez
   shared-caller rizika.

**Zaključak: siguran za odmah paralelan start** sa DRUGIM implementerom
(dok G6 implementer nastavlja svoj rad).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-015-approve-reject-fact-candidates
Branch:   task/ACS-S2-015-approve-reject-fact-candidates
Base:     main @ 9645fd7
```
