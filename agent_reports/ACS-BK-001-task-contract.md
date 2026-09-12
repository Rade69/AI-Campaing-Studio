---
task_id: ACS-BK-001
phase: "BK-G1 — Brand Knowledge Domain Foundation"
title: "domain/brand_knowledge/ — KnowledgeCategory/Status/EvidenceType, KnowledgeEntry, BrandKnowledgeSnapshot, controlled field registry"
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-12
dependencies: []
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/domain/brand_knowledge/
  - src/ai_campaign_studio/domain/common/ids.py
  - tests/unit/domain/brand_knowledge/
forbidden_paths:
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/ingestion/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/
graft_required: true
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Prvi gate novog Brand Knowledge inicijative (`docs/AI Campaign Studio —
Brand Knowledge Implementation Plan.md`, §49: *"Prvi task koji treba
otvoriti... isključivo Brand Knowledge Domain Foundation... Bez SQLite,
migration, LLM, GUI, Campaign Engine... prvo treba zaključati domain
contract."*).

**Pipeline koji ovaj domen modelira** (plan §0, ne implementira se
ovdje, samo se low-level tipovi definišu):

```text
ApprovedFact (već postoji, S2-G1/G7a)
    ↓
Brand Knowledge Builder (BK-G3/G4, budući)
    ↓
KnowledgeEntry PROPOSALS
    ↓ HUMAN REVIEW (BK-G6, budući)
Approved Knowledge Entries
    ↓
BrandKnowledgeSnapshot (BK-G7, budući)
    ↓
Campaign Engine (BK-G8, budući)
```

**Nepregovorljiv princip** (plan §0/§31, isto kao postojeći fact-first
princip za `ApprovedFact`): `ApprovedFact` = dokaz koji je čovjek
odobrio; `KnowledgeEntry` = strukturisana interpretacija te činjenice;
`BrandKnowledgeSnapshot` = uređena slika znanja. **LLM ne odlučuje šta
je istina** — ovaj task ne dodaje LLM ništa (nema LLM koda u BK-G1),
ali MORA postaviti tipove tako da svaki `KnowledgeEntry` bude
NEIZBJEŽNO vezan za `source_fact_ids` (invarijanta ispod) — to je
temelj na kojem BK-G4-ov anti-hallucination validator kasnije stoji.

**Nezavisno verifikovano prije pisanja kontrakta** (ne pretpostavljeno
iz plana): `domain/common/ids.py` već ima `FactId`/`BrandSnapshotId`
(`NewType`); `domain/common/errors.py` već ima `InvariantViolation`
(`DomainError` podklasa, `default_code=ErrorCode.INVARIANT_VIOLATION`).
Oba se koriste direktno, ne izmišljati nove.

**Graft je primarni alat od 2026-09-12** (`.agent/GRAFT_PROTOCOL.md`)
— koristiti `graft callers`/`graft grep`/`graft blast` za pre/post-change
provjeru. GitNexus ostaje sekundarna probaciona provjera tokom
prelaznog perioda — uraditi obje ako je moguće, Graft je obavezan
minimum.

# Objective

## 1. `domain/brand_knowledge/` (nov paket, isti stil kao `domain/ingestion/`)

```text
domain/brand_knowledge/
    __init__.py    (re-export svih javnih simbola, isti obrazac kao
                    domain/ingestion/__init__.py)
    enums.py
    entities.py
    policies.py
```

## 2. `enums.py`

```python
class KnowledgeCategory(StrEnum):
    COMPANY = "COMPANY"
    OFFERING = "OFFERING"
    AUDIENCE = "AUDIENCE"
    DIFFERENTIATOR = "DIFFERENTIATOR"
    PRICING = "PRICING"
    CONTACT = "CONTACT"
    BRAND_VOICE = "BRAND_VOICE"
    TRUST = "TRUST"

class KnowledgeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONFLICT = "CONFLICT"

class EvidenceType(StrEnum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
```

Dokumentovati u docstring-u (plan §3.3): `EXPLICIT` = informacija
direktno postoji u ≥1 `ApprovedFact`; `INFERRED` = izvedena iz obrasca
kroz više činjenica (npr. BRAND_VOICE iz stila više tekstova).

## 3. Kontrolisani field registry po kategoriji (plan §5, DOSLOVNO)

U `policies.py` (ne u `enums.py` — ovo je validaciona politika, ne
čista vokabular-definicija):

```python
ALLOWED_FIELDS_BY_CATEGORY: Mapping[KnowledgeCategory, frozenset[str]] = {
    KnowledgeCategory.COMPANY: frozenset({
        "name", "description", "industry", "company_type", "location",
        "founded", "mission",
    }),
    KnowledgeCategory.OFFERING: frozenset({
        "service", "product", "package", "feature", "benefit",
    }),
    KnowledgeCategory.AUDIENCE: frozenset({
        "target_segment", "industry", "geography", "need", "pain_point",
        "objection", "motivation",
    }),
    KnowledgeCategory.DIFFERENTIATOR: frozenset({
        "advantage", "unique_selling_point", "expertise", "guarantee",
        "capability",
    }),
    KnowledgeCategory.PRICING: frozenset({
        "price", "starting_price", "price_range", "discount",
        "payment_terms", "pricing_model",
    }),
    KnowledgeCategory.CONTACT: frozenset({
        "email", "phone", "address", "website", "social_profile",
    }),
    KnowledgeCategory.BRAND_VOICE: frozenset({
        "tone", "formality", "vocabulary", "preferred_phrase",
        "forbidden_phrase", "sentence_style", "cta_style",
        "technical_language",
    }),
    KnowledgeCategory.TRUST: frozenset({
        "testimonial", "customer", "certification", "award",
        "statistic", "case_study", "years_experience", "project_count",
    }),
}

def is_field_allowed(category: KnowledgeCategory, field: str) -> bool: ...
def assert_field_allowed(category: KnowledgeCategory, field: str) -> None:
    """Raise InvariantViolation if ``field`` is not in the controlled
    registry for ``category``. Unknown fields are NEVER silently
    accepted (plan §5) — this is the single source of truth every
    later gate (BK-G3 deterministic extractor, BK-G4 LLM validator)
    must reuse, not re-implement."""
```

## 4. `entities.py` — `KnowledgeEntry`

```python
@dataclass(frozen=True)
class KnowledgeEntry:
    id: KnowledgeEntryId
    brand_snapshot_id: BrandSnapshotId
    category: KnowledgeCategory
    field: str
    value: str
    evidence_type: EvidenceType
    status: KnowledgeStatus
    source_fact_ids: tuple[FactId, ...]
    confidence: float | None
    conflict_group_id: str | None
    created_at: datetime
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_fact_ids", tuple(self.source_fact_ids))
        if not self.source_fact_ids:
            raise InvariantViolation(
                "KnowledgeEntry.source_fact_ids must not be empty "
                "(plan §4 -- HUMAN_MANUAL exception is a future feature, "
                "not v1)"
            )
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise InvariantViolation(
                f"KnowledgeEntry.confidence must be in [0.0, 1.0] or None, "
                f"got {self.confidence!r}"
            )
        if not self.value.strip():
            raise InvariantViolation("KnowledgeEntry.value must not be empty")
        assert_field_allowed(self.category, self.field)
```

Dokumentovati u docstring-u (plan §4, doslovno prenijeti semantiku):
`confidence` NIJE vjerovatnoća da je činjenica istinita (istinitost je
već utvrđena preko `ApprovedFact`) — znači koliko je klasifikator
siguran da činjenica pripada TOJ kategoriji/field-u. Deterministički
extractor (budući BK-G3) → uvijek `1.0`. LLM klasifikacija (budući
BK-G4) → `0.0`-`1.0`. Ljudski ručno odobrena vrijednost → može biti
`None`.

## 5. `entities.py` — `BrandKnowledgeSnapshot`

```python
@dataclass(frozen=True)
class BrandKnowledgeSnapshot:
    id: BrandKnowledgeSnapshotId
    brand_snapshot_id: BrandSnapshotId
    version: int
    approved_entry_ids: tuple[KnowledgeEntryId, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "approved_entry_ids", tuple(self.approved_entry_ids)
        )
```

Dokumentovati arhitektonsku odluku (plan §9, DOSLOVNO): ovo NE
zamjenjuje postojeći `BrandSnapshot` (voice/audiences/services/
visual_identity/restrictions/approved_fact_ids) — derived extension,
`brand_snapshot_id` pokazuje na TAČNU verziju iz koje je znanje
izvedeno. Dva različita `BrandSnapshot`-a MOGU dati dva različita
Brand Knowledge snapshot-a; miješanje činjenica iz više
`BrandSnapshot` verzija u JEDAN Knowledge Snapshot je NAMJERNO
neподržano u v1 (budući use-case dizajn, ne ovaj task). NE dirati
postojeći `domain/brand/entities.py::BrandSnapshot` — `forbidden_paths`
svakako to sprječava, ali dokumentovati ZAŠTO (da implementer ne
pokuša "popraviti" postojeći VO da referencira novi Knowledge sloj).

Snapshot sadrži SAMO `APPROVED` entry-je (ne `PROPOSED`/`REJECTED`/
`CONFLICT`) — ovo je INVARIJANTA koju ČUVA use-case koji ga gradi
(budući BK-G7), NE ovaj domain entitet sam (entitet je čista struktura,
ne zna odakle su mu `approved_entry_ids` došli — isti princip kao
`IngestionRun`/`CrawlTarget` koji ne validiraju svoj vlastiti "sadržaj",
samo strukturu). NE dodavati provjeru u `__post_init__` da su svi
entry-ji stvarno `APPROVED` — to zahtijeva pristup bazi (koja ovdje ne
postoji), pogrešan sloj za tu provjeru.

## 6. Novi ID tipovi (`domain/common/ids.py`, aditivno, isti obrazac)

```python
# Brand Knowledge (BK-G1).
KnowledgeEntryId = NewType("KnowledgeEntryId", str)
BrandKnowledgeSnapshotId = NewType("BrandKnowledgeSnapshotId", str)
```

**NE dodavati `KnowledgeConflictGroupId`** (plan §6 eksplicitno: "samo
ako se pokaže da je potreban pravi domain identitet... Ne dodavati
apstrakciju unaprijed") — `conflict_group_id: str | None` ostaje plain
string na `KnowledgeEntry` dok BK-G5 (conflict detection) ne pokaže
da treba tipizovan identitet.

## 7. `__init__.py` exports

Isti obrazac kao `domain/ingestion/__init__.py` — re-export svih
javnih simbola (3 enum-a, 2 entiteta, `ALLOWED_FIELDS_BY_CATEGORY`,
`is_field_allowed`, `assert_field_allowed`), `__all__` lista.

# Šta NE raditi (eksplicitno, plan §49/§45)

- NEMA SQLite/migracije (nema `resources/migrations/`, nema
  repository porta) — to je BK-G2.
- NEMA LLM koda, NEMA AI provider importa — BK-G4.
- NEMA GUI-ja — BK-G6.
- NEMA Campaign Engine integracije — BK-G8.
- NEMA `KnowledgeConflictGroupId` (§6 iznad).
- NE dirati postojeći `domain/facts/` ili `domain/brand/` — samo
  IMPORTOVATI `FactId`/`BrandSnapshotId` iz `domain/common/ids.py`
  (već postoje), ne uvoditi novu zavisnost na `domain/facts/entities.py`
  direktno (ovaj task ne treba `ApprovedFact`/`FactCandidate` klase
  same, samo njihov ID tip).
- NE uvoditi `vector database`/`embeddings`/`knowledge graph` tipove
  (plan §45) — čista dataclass/enum struktura.

# Acceptance

- [ ] `KnowledgeCategory` (8 vrijednosti), `KnowledgeStatus` (4),
      `EvidenceType` (2) tačno kako je specificirano.
- [ ] `ALLOWED_FIELDS_BY_CATEGORY` pokriva svih 8 kategorija sa TAČNO
      navedenim field-ovima iz plana §5 (ne manje, ne više, ne
      izmišljeni dodatni field-ovi).
- [ ] `KnowledgeEntry` frozen; `source_fact_ids` coerced u tuple;
      prazan `source_fact_ids` → `InvariantViolation`; `confidence`
      van `[0,1]` → `InvariantViolation`; `confidence=None` DOZVOLJENO
      (ne baca); prazan `value` → `InvariantViolation`; nepoznat
      `field` za dati `category` → `InvariantViolation` (test za SVAKU
      od 8 kategorija sa bar jednim validnim i jednim nevalidnim
      field-om).
- [ ] `BrandKnowledgeSnapshot` frozen; `approved_entry_ids` coerced u
      tuple.
- [ ] `KnowledgeEntryId`/`BrandKnowledgeSnapshotId` dodani na kraj
      `domain/common/ids.py`, postojeće linije netaknute.
- [ ] Unit testovi (plan §32, doslovno): KnowledgeEntry frozen,
      source_fact_ids coerced, empty source_fact_ids rejected, invalid
      confidence rejected (probati `-0.1`, `1.1`, prihvatiti `0.0`,
      `1.0`, `None`), valid/invalid field po svakoj kategoriji, valid
      statuses/evidence types (kompletnost enum vrijednosti),
      BrandKnowledgeSnapshot frozen, approved_entry_ids tuple.
- [ ] `python -m pytest tests/unit/domain/brand_knowledge/ -v` prolazi.
- [ ] `python -m pytest -q` (pun suite, DeepSeek unset) prolazi, 0
      regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths` — POSEBNO nula u
      `domain/facts/`, `domain/brand/`, `application/`, `ports/`,
      `infrastructure/`, `presentation_webview/`, `resources/migrations/`.
- [ ] Graft `callers`/`grep` pre-change evidence (novi simboli, pa je
      "no callers" očekivano za sve NOVE simbole — ipak provjeriti da
      `FactId`/`BrandSnapshotId`/`InvariantViolation` importi ne kvare
      ništa postojeće preko `graft blast`).
- [ ] **CI provjeren preko PR-a.**

# Implementation steps

1. Pročitati `domain/ingestion/entities.py`/`enums.py`/`__init__.py`
   (S2-G1) kao stil-referencu — identičan obrazac (frozen dataclass,
   tuple coercion u `__post_init__`, StrEnum, re-export `__init__.py`).
2. Pročitati `domain/facts/entities.py`/`policies.py` za
   `InvariantViolation` korišćenje kao referencu (kako se poziva, koji
   error message stil).
3. Pročitati `domain/common/ids.py`/`domain/common/errors.py` u
   cjelini (kratki fajlovi).
4. Napisati `enums.py`.
5. Napisati `policies.py` (registry + validacione funkcije) PRIJE
   `entities.py` (entiteti pozivaju `assert_field_allowed`).
6. Napisati `entities.py`.
7. Dodati ID tipove.
8. `__init__.py` exports.
9. Testovi (plan §32 checklist doslovno).
10. Graft `callers`/`grep`/`blast` prije commit-a (`.agent/GRAFT_PROTOCOL.md`).

# Review focus — Claude (MEDIUM, §29)

- Field registry TAČNO prepisan iz plana §5 (uporediti liniju-po-liniju,
  ne oslanjati se na pamćenje).
- `source_fact_ids`-empty i `confidence`-range invarijante stvarno
  bacaju `InvariantViolation`, ne generički `ValueError`/`AssertionError`.
- `BrandKnowledgeSnapshot` NE pokušava validirati da su entry-ji
  stvarno `APPROVED` (pogrešan sloj, §5 objašnjenje iznad) — ako
  implementer to doda, to je scope creep za ovaj task, tražiti uklanjanje.
- Scope čist (Graft/GitNexus diff potvrda).
- Mutation test na bar jednu invarijantu (npr. privremeno ukloniti
  empty-check, potvrditi da test padne, vratiti).

# Rollback

MEDIUM risk (čist domain kod, nema I/O, nema migracije, nema GUI,
identična klasa kao ACS-S2-001). Claude-only review → odmah merge po
§29 ako PASS.

# Coordination

Nema zavisnosti (prvi Brand Knowledge task). Blokira BK-G2 (persistence
— zavisi od ovih tipova). Nema poznatih paralelnih kandidata trenutno
otvorenih na ovom projektu — ako se pojavi nezavisan task (npr.
nastavak S2-018 ili GUI polish), provjeriti `allowed_paths` presjek
prije paralelnog rada (workflow §10) — ovaj task ne dira ništa izvan
novog `domain/brand_knowledge/` paketa pa je nizak rizik za konflikt.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-BK-001-domain-foundation
Branch:   task/ACS-BK-001-domain-foundation
Base:     main @ befcba5
```
