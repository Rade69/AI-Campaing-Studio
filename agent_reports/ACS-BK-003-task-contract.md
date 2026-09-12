---
task_id: ACS-BK-003
phase: "BK-G3 — Deterministička ekstrakcija"
title: "application/brand_knowledge/deterministic_classifier.py -- regex-based KnowledgeEntry proposals iz ApprovedFact sadržaja"
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-12
dependencies: [ACS-BK-001, ACS-BK-002]
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/application/brand_knowledge/
  - tests/unit/application/brand_knowledge/
  - tests/integration/application/brand_knowledge/
forbidden_paths:
  - src/ai_campaign_studio/domain/brand_knowledge/
  - src/ai_campaign_studio/domain/facts/
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_brand_knowledge_repository.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/presentation_webview/
  - resources/migrations/
graft_required: true
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Treći gate Brand Knowledge inicijative (`docs/AI Campaign Studio —
Brand Knowledge Implementation Plan.md`, §10/§11). BK-G1 (domain,
`ACS-BK-001`, merge `88df6da`) i BK-G2 (persistence,
`ACS-BK-002`, merge `0a1a5bc`) su zaključani — **ni jedno ni drugo se
ovdje ne dira** (`forbidden_paths`). Ovaj task je PRVI pravi "punilac"
`KnowledgeEntry` tabele: deterministički (regex/parsing) classifier
koji iz `ApprovedFact.content` izvlači ono što se pouzdano prepoznaje
BEZ LLM-a, prije BK-G4 (LLM structured classification, budući task).

**Pipeline (plan §46, non-negotiable, ne zaobilaziti)**:

```text
website → extraction → FactCandidate → HUMAN APPROVAL → ApprovedFact
    → Knowledge classification (OVAJ TASK) → HUMAN REVIEW (budući BK-G6)
    → BrandKnowledgeSnapshot (budući BK-G7)
```

Ovaj task NE radi human review niti snapshot — samo kreira
`KnowledgeEntry` redove sa `status=PROPOSED`. Odobravanje/odbijanje je
BK-G6-ov posao (GUI).

**Nezavisno verifikovano prije pisanja kontrakta** (ne pretpostavljeno
iz plana):

- `FactRepositoryPort.list_snapshot_facts(snapshot_id: BrandSnapshotId)
  -> tuple[ApprovedFact, ...]` već postoji — ovaj task ga koristi da
  pročita sve odobrene činjenice za dati `BrandSnapshot` (ne treba nova
  port metoda).
- `BrandKnowledgeRepositoryPort.save_entry(entry: KnowledgeEntry) ->
  None` (BK-G2) je upsert-po-`id` — ovo je iskorišćeno za idempotenciju
  ispod (nema potrebe za novom `build_key`/`classifier_version`
  tabelom, plan §43 hedge: "ako je potrebno" — nije potrebno za v1,
  vidi ispod).
- Stil-predložak za application use-case klasu:
  `application/ingestion/approve_fact_candidates.py`
  (`ApproveFactCandidate`/`RejectFactCandidate`) — konstruktor prima
  portove + lokalni `_UnitOfWork` Protocol (svaki modul definiše svoj,
  ne dijeli se globalni), `.execute(...)` metoda, `EntityNotFound`/
  `InvariantViolation` iz `domain.common.errors`. Ovaj task prati isti
  obrazac.
- `domain/common/ids.py` ima `new_id()` helper — koristi se za
  NE-determinističke ID-jeve na drugim mjestima u projektu, ali OVDJE
  se namjerno NE koristi (vidi Idempotency niže — treba nam
  deterministički, ne random, ID).
- `tests/architecture/test_import_boundaries.py` potvrđuje:
  `application/` NE SMIJE importovati `infrastructure`/
  `presentation_webview`/GUI — ovaj task koristi ISKLJUČIVO
  `domain.brand_knowledge`, `domain.facts`, `domain.common`, i
  `ports.repositories` (Protocol tipovi, ne konkretni adapteri).
- Test stil-predložak: `tests/unit/application/ingestion/
  test_approve_fact_candidates.py` (ručno pisani fake repo/UoW
  objekti, ne prava SQLite) + `tests/integration/application/ingestion/
  test_approve_fact_candidates_flow.py` (pravi SQLite repo-i). Ovaj
  task prati isti dvoslojni obrazac.
- `channels/definitions.py` NE sadrži listu social-media domena (to je
  channel/platform/format registry, ne URL-domain matching) — lista
  poznatih social domena za ovaj task piše se lokalno, novo, u
  `deterministic_classifier.py` (mala, eksplicitna, closed lista, vidi
  §2 niže).

**Graft je primarni alat od 2026-09-12** — `graft callers`/`graft
grep`/`graft blast` prije i poslije izmjene, obavezno za novi
application paket koji konzumira portove iz BK-G1/BK-G2.

# Objective

## 1. Idempotency politika (plan §43 — MORA biti fiksirano prije koda)

**Deterministički (ne random) `KnowledgeEntryId`**, tako da ponovni
build nad ISTOM činjenicom/field-om prirodno upsert-uje umjesto da
duplicira red (`save_entry` je već upsert-po-`id`, BK-G2):

```python
import hashlib

def _deterministic_entry_id(
    brand_snapshot_id: BrandSnapshotId, fact_id: FactId, field: str
) -> KnowledgeEntryId:
    raw = f"detkn:{brand_snapshot_id}:{fact_id}:{field}"
    return KnowledgeEntryId(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32])
```

`"detkn:"` prefiks namjerno razlikuje deterministički-porijeklo entry
od budućeg LLM-porijeklo entry-ja (BK-G4) — dvije klasifikacione
metode nikad ne mogu kolidirati na istom ID-ju čak i bez formalnog
`classifier_version` polja (koje bi zahtijevalo migraciju/domain
izmjenu, oboje van `allowed_paths`, plan §44 eksplicitno hedge-uje
"ako je potrebno" — NIJE potrebno za v1, jer prefiks + (snapshot, fact,
field) trojka već daju kolizijsku sigurnost dovoljnu za ovaj gate).

**Prihvaćeno v1 ograničenje (dokumentovati u docstring-u, NE
rješavati)**: ako JEDNA činjenica sadrži VIŠE različitih vrijednosti za
ISTI field (npr. dvije različite cijene u istom tekstu), zadržava se
SAMO PRVI pronađeni match (po poziciji u tekstu) — ostali se
ignorišu/preskaču. Ovo je namjerna v1 pojednostavljenost (izbjegava
lažne "koji je prvi/koji je stariji" liste), ne bug. Ako se docentnije
pokaže da BK-G3-ov klasifikator treba obraditi ponovni build koji
proizvede MANJE match-eva nego prethodni (stare vrijednosti ostaju kao
"stale" redovi u bazi) — poznato v1 ograničenje, rješava budući gate
ako se pokaže potrebnim (isti princip kao BK-G1-ovo izbjegavanje
`KnowledgeConflictGroupId` dok se ne pokaže potreba).

## 2. `application/brand_knowledge/deterministic_classifier.py`

Dva sloja u istom fajlu (ili razdvojiti u `_extractors.py` ako čitljivost
zahtijeva — implementer odlučuje, ali javni API ostaje isti):

### 2a. Čiste extract funkcije (bez I/O), jedna po tipu:

```python
def extract_email(content: str) -> str | None: ...
def extract_phone(content: str) -> str | None: ...
def extract_website_url(content: str) -> str | None: ...       # non-social
def extract_social_profile_url(content: str) -> str | None: ...
def extract_starting_price(content: str) -> str | None: ...
def extract_generic_price(content: str) -> str | None: ...
def extract_discount_percent(content: str) -> str | None: ...
def extract_founded_year(content: str) -> str | None: ...
```

Svaka vraća `None` ako nema pouzdanog, nedvosmislenog match-a — NIKAD
ne nagađati (plan §11, non-negotiable).

**Tačna pravila** (implementer MORA ovo poštovati, ne izmišljati
alternativna):

- **email**: standardan email regex
  (`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`).
- **phone**: samo ako string sadrži OR (a) vodeći `+` pa 7-15 cifara
  (razmaci/crtice/zagrade dozvoljeni), OR (b) obližnji keyword
  (`tel`, `telefon`, `phone`, `mob`) unutar ~15 karaktera prije broja.
  Cilj: NE pogoditi "299 EUR" ili godinu kao telefon.
- **website URL**: `https?://[^\s]+`, PA provjeriti da domain NIJE u
  poznatoj social listi (ispod) — ako jeste, to je
  `social_profile`, ne `website`.
- **social profile URL**: isti URL regex, domain JESTE u closed listi:
  `facebook.com`, `instagram.com`, `linkedin.com`, `x.com`,
  `twitter.com`, `tiktok.com`, `youtube.com`, `pinterest.com`,
  `threads.net`, `snapchat.com` (tačno platforme iz CLAUDE.md
  zaključanih platformi + `twitter.com` kao alias za X).
- **starting_price**: keyword (`od`, `starting from`, `from`,
  case-insensitive) NEPOSREDNO prije broja + valuta (`EUR`, `USD`,
  `KM`, `BAM`, `$`, `€`). Normalizovana vrijednost: `"<broj>
  <VALUTA>"` (npr. `"299 EUR"`) — DODATI `"/month"` SAMO ako je u
  istoj rečenici eksplicitan keyword (`mjesečno`, `monthly`, `/mo`,
  `per month`) — ne izmišljati periodicitet koji tekst ne kaže.
- **generic price**: broj + valuta BEZ "starting/od" keyword-a →
  `PRICING.price` (ista normalizacija, bez perioda ako nije eksplicitan).
- **discount_percent**: broj + `%` u istoj rečenici sa keyword-om
  (`popust`, `discount`, `off`, `sniženje`) u bilo kom redoslijedu →
  `PRICING.discount`, vrijednost `"<N>%"`.
- **founded_year**: keyword (`osnovan`, `osnovana`, `established`,
  `founded`) + 4-cifreni broj u opsegu 1800-2026 unutar iste rečenice →
  `COMPANY.founded`, vrijednost je sama godina kao string. GOLI
  4-cifreni broj BEZ ovog keyword-a se NIKAD ne tretira kao godina
  osnivanja (previše nedvosmisleno bez konteksta).

Bilo koji tekst koji ne zadovoljava gornje tačno navedene uslove →
`None` (preskočiti, ne pokušavati "najbolje nagađanje").

### 2b. Orkestracija (čista funkcija, i dalje bez I/O):

```python
@dataclass(frozen=True)
class _DeterministicMatch:
    category: KnowledgeCategory
    field: str
    value: str

def classify_fact_content(content: str) -> tuple[_DeterministicMatch, ...]:
    """Run every extractor once; return only the matches found (order:
    email, phone, website, social, starting_price, generic price,
    discount, founded_year). A fact commonly yields 0-2 matches."""
```

Napomena: `starting_price` i `generic price` se MEĐUSOBNO ISKLJUČUJU
za isti tekst (ako `extract_starting_price` pogodi, `extract_generic_price`
se NE poziva na istom price-mention-u — implementer treba paziti da ne
proizvede DUPLI PRICING entry iz istog broja).

### 2c. Use-case klasa (I/O, isti stil kao `ApproveFactCandidate`):

```python
class ExtractDeterministicKnowledge:
    def __init__(
        self,
        fact_repo: FactRepositoryPort,
        brand_knowledge_repo: BrandKnowledgeRepositoryPort,
    ) -> None: ...

    def execute(
        self, brand_snapshot_id: BrandSnapshotId
    ) -> tuple[KnowledgeEntry, ...]:
        """Read every ApprovedFact for brand_snapshot_id, run the
        deterministic classifier on each, save (upsert) one
        KnowledgeEntry per match, return everything saved (may be
        empty tuple -- not every fact yields a match, that's normal).
        """
```

Nema `UnitOfWork` parametar ovdje (za razliku od
`ApproveFactCandidate`) — svaki `save_entry` poziv je već sam-atomičan
(BK-G2 F1 fix, `_own_transaction`); nema potrebe za višestrukom
transakcijom preko više entry-ja (svaki entry je nezavisna jedinica
rada, djelimičan neuspjeh na jednom factu ne smije blokirati ostale —
VIDI Review focus niže za tačnu odluku o exception-handling-u po
factu).

## 3. `__init__.py` exports

`ExtractDeterministicKnowledge`, `classify_fact_content` (za testove),
svaka `extract_*` funkcija (za granularne unit testove).

# Šta NE raditi (eksplicitno, plan §10/§11/§45/§46)

- NE pokušavati regexom određivati `target audience`/`USP`/
  `brand voice`/`service semantics` — to je BK-G4 (LLM).
- NE izmišljati vrijednost koju tekst doslovno ne kaže (plan §11) —
  dozvoljena je SAMO normalizacija formata (npr. "€299" → "299 EUR"),
  nikad interpretacija/parafraza.
- NE dodavati `classifier_version` kolonu/polje — vidi Idempotency
  sekciju iznad (prefiks + trojka je dovoljno za v1).
- NE mapirati goli procenat/godinu bez keyword konteksta (vidi tačna
  pravila iznad) — bolje preskočiti nego pogrešno klasifikovati.
- NE raditi HUMAN REVIEW ni `BrandKnowledgeSnapshot` sastavljanje — to
  su budući BK-G6/BK-G7 taskovi. Ovaj task samo kreira `PROPOSED`
  entry-je.
- NE importovati `infrastructure`/`presentation_webview` u
  `application/brand_knowledge/` (arhitektonska granica, provjerava
  `tests/architecture/test_import_boundaries.py`).
- NE dirati `domain/brand_knowledge/`, `domain/facts/`,
  `sqlite_brand_knowledge_repository.py`, `ports/repositories.py`,
  `resources/migrations/` (`forbidden_paths`).

# Acceptance

- [ ] Svaka `extract_*` funkcija: unit testovi sa POZITIVNIM
      primjerima (tačno navedeni patterns) I NEGATIVNIM/near-miss
      primjerima (npr. "299 EUR" ne smije pogoditi kao telefon; goli
      "2019" bez "osnovan" ne smije pogoditi kao founded_year; URL na
      nepoznatom domenu je website, ne social).
- [ ] `classify_fact_content`: fact sa 0 match-eva → prazan tuple; fact
      sa dva različita tipa (npr. email + cijena) → oba pronađena;
      starting_price i generic price se međusobno isključuju na istom
      broju (test za ovo eksplicitno).
- [ ] Plan §10 primjer doslovno kao test: `"Paketi počinju od 299 EUR
      mjesečno."` → `category=PRICING, field=starting_price,
      value="299 EUR/month"` (ili ekvivalentan tačan normalizovan
      format, dokumentovati tačno koji).
- [ ] `ExtractDeterministicKnowledge.execute`: round-trip sa fake
      repo-ima (unit) I sa pravim SQLite repo-ima (integration) —
      isto kao `test_approve_fact_candidates.py` +
      `test_approve_fact_candidates_flow.py` dvoslojni obrazac.
- [ ] Idempotency test: pozvati `execute` DVA PUTA nad ISTIM
      `brand_snapshot_id`/istim factovima → drugi poziv upsert-uje
      (isti broj redova u bazi, ne duplirano), potvrđeno direktnim
      SQL brojanjem redova.
- [ ] Svaki kreiran `KnowledgeEntry` ima `status=PROPOSED`,
      `evidence_type=EXPLICIT`, `confidence=1.0`,
      `source_fact_ids=(fact.id,)` (tačno jedan, ne prazan/više).
- [ ] `python -m pytest tests/unit/application/brand_knowledge/
      tests/integration/application/brand_knowledge/ -v` prolazi.
- [ ] `python -m pytest -q` (pun suite, DeepSeek key unset) — 0
      regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] `tests/architecture/test_import_boundaries.py` i dalje prolazi
      (novi paket ne krši granice).
- [ ] Nema izmjena van `allowed_paths`.
- [ ] Graft `callers`/`grep`/`blast` pre/post-change evidence.
- [ ] Mutation test na bar jednu extract funkciju (npr. privremeno
      olabaviti phone regex, potvrditi da negative-test test padne,
      vratiti) I na idempotency (privremeno vratiti `new_id()` umjesto
      determinističkog ID-ja, potvrditi da idempotency test padne,
      vratiti).
- [ ] **CI provjeren preko PR-a.**

# Implementation steps

1. Pročitati `domain/brand_knowledge/entities.py`/`enums.py`/
   `policies.py` (BK-G1, READ-ONLY) — tačna imena polja,
   `assert_field_allowed`.
2. Pročitati `application/ingestion/approve_fact_candidates.py` u
   cjelini kao stil-predložak.
3. Pročitati `domain/facts/entities.py` (`ApprovedFact.content`,
   `.id`) i `ports/repositories.py`
   (`FactRepositoryPort.list_snapshot_facts`,
   `BrandKnowledgeRepositoryPort.save_entry`) — READ-ONLY, ne dirati.
4. Napisati extract funkcije + testove PRVO (TDD prirodno ovdje radi
   dobro — svaka funkcija je čista, lako testirati izolovano).
5. Napisati `classify_fact_content` orkestraciju + testove.
6. Napisati `ExtractDeterministicKnowledge` use-case + unit testove
   (fake repo-i) + integration testove (pravi SQLite).
7. Idempotency test (poziv dva puta).
8. Pun suite + ruff + mypy + architecture boundary test.
9. Graft `callers`/`grep`/`blast` prije commit-a.

# Review focus — Claude (MEDIUM, §29)

- Svako `extract_*` pravilo TAČNO kako je specificirano (uporediti
  regex logiku liniju-po-liniju sa §2a iznad, ne oslanjati se na
  "izgleda razumno").
- Nema izmišljanja vrijednosti van teksta (plan §11 provjera na svaki
  extractor).
- Deterministički ID (§1) stvarno determinističan (isti ulaz → isti
  ID svaki put, provjeriti eksplicitnim testom poziva funkcije dva
  puta sa istim argumentima).
- `ExtractDeterministicKnowledge.execute` NE pravi human-review niti
  snapshot logiku (scope creep provjera).
- Odluka o exception-handling-u po factu: ako JEDAN fact-ov
  `save_entry` baci (npr. `InvariantViolation` iz BK-G2-ovog F4/F5
  guard-a na nekom rubnom slučaju), da li `execute` treba (a) odmah
  propagirati i prekinuti cijeli batch, ili (b) logovati i nastaviti
  sa ostalim factovima? Implementer MORA eksplicitno odlučiti i
  dokumentovati u docstring-u — ne ostavljati implicitno. Preporuka
  koordinatora: propagirati (opcija a) za v1 — "silent skip on error"
  bi sakrio prave bugove; ako se pokaže da je jedan loš fact previše
  ometajući u praksi, to je budući task, ne ovaj.
- Graft/GitNexus diff potvrda (čist scope).
- Mutation test na bar jedan extractor + na idempotency.

# Rollback

MEDIUM risk (čista application logika, nema I/O sheme, nema migracije,
nema GUI-ja, identična klasa rizika kao ACS-S2-015/ACS-BK-001).
Claude-only review → odmah merge po §29 ako PASS.

# Coordination

Zavisi od `ACS-BK-001` (merge `88df6da`) i `ACS-BK-002` (merge
`0a1a5bc`) — oba merge-ovana, BK-G3 može startovati odmah. Blokira
BK-G4 (LLM klasifikacija) samo mekano (plan §10: "prije LLM-a izdvojiti
stvari koje pouzdano možemo parsirati" — BK-G4 treba znati šta je BK-G3
već pokrio da ne duplira/koliduje na istim poljima; tačan mehanizam
za to je BK-G4-ov task contract problem, ne ovaj).

**Paralelni rad**: Trenutno nema drugih otvorenih worktree-ova
(provjereno `git worktree list` 2026-09-12). Ovaj task ne dira ništa
izvan novog `application/brand_knowledge/` paketa, pa je nizak rizik
za konflikt sa bilo kojim budućim paralelnim taskom osim samog BK-G4
(koji bi trebalo da čeka da se BK-G3 završi, ne pravi kandidat za
paralelizaciju — vidi Kontekst).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-BK-003-deterministic-extraction
Branch:   task/ACS-BK-003-deterministic-extraction
Base:     main @ efb86d1
```
