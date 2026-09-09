---
task_id: ACS-S2-001
phase: "S2-G1 — Brand Ingestion Domain + Ports (contracts only) — prvi Slice 2 gate"
title: "domain/ingestion, domain/facts.FactCandidate, ports/web_ingestion.py, ports/repositories.py.IngestionRepositoryPort"
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-09
dependencies: []
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/domain/ingestion/
  - src/ai_campaign_studio/domain/facts/entities.py
  - src/ai_campaign_studio/domain/facts/enums.py
  - src/ai_campaign_studio/domain/facts/policies.py
  - src/ai_campaign_studio/domain/common/ids.py
  - src/ai_campaign_studio/ports/web_ingestion.py
  - src/ai_campaign_studio/ports/repositories.py
  - tests/unit/domain/ingestion/
  - tests/unit/domain/facts/
  - tests/unit/ports/
forbidden_paths:
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/jobs/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Ovo je PRVI Task Contract Slice 2 (Website/Brand Ingestion). Kanonski
plan: [docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md](../docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md)
(§10, sekcija "S2-G1"). Human Owner je 2026-09-08 potvrdio da Slice 2
može krenuti nakon P1.5-G7/G8 PASS-a (oba zatvorena — vidi
`.agent/CURRENT_STATE.md`).

**Nula runtime/infrastructure koda u ovom tasku.** Čisto domain
entities/enums/ID-jevi + Protocol port definicije. Ništa se ne poziva,
ništa se ne perzistira — sljedeći gate (S2-G2, migracija 0009) prvi put
daje ovim tipovima stvarnu SQLite tabelu.

**Postojeći seam koji ovaj task ispunjava** (nezavisno verifikovano
prije pisanja ovog kontrakta):

- `domain/facts/enums.py` `FactStatus` docstring VEĆ kaže: *"Slice 1
  has no PROPOSED status — that arrives with the Slice 2 FactCandidate
  workflow."* Namjerno ostavljen seam iz Faze 1.
- `domain/facts/entities.py` `SourceReference` VEĆ ima
  `snapshot_id: str | None` i `chunk_id: str | None` polja —
  namijenjena upravo za `SourceSnapshot`/`SourceChunk` ID-jeve koje ovaj
  task uvodi. NE mijenjati `SourceReference` shape (samo dodati novi
  `FactCandidate` entitet pored postojećeg `ApprovedFact`); provjeriti
  da li ta polja treba tipizirati na nove ID tipove (`SourceSnapshotId`/
  `SourceChunkId`) umjesto `str | None` — ako da, to je aditivna
  tightening izmjena, ne breaking change (currently `str`, NewType je i
  dalje `str` runtime-wise).
- `ports/repositories.py` je JEDAN fajl sa više `Protocol` klasa
  (`BrandRepositoryPort`, `FactRepositoryPort`, `PerformanceRepositoryPort`,
  itd.) — `IngestionRepositoryPort` ide ovdje kao NOVA klasa, ISTI
  obrazac. NE dirati nijednu postojeću Protocol metodu (GitNexus
  `detect_changes` mora pokazati nula izmjena na postojećim
  `ports/repositories.py` simbolima, samo dodavanje).

# Objective

## 1. `domain/ingestion/` (nov paket)

Immutable value objects/entiteti (isti stil kao `domain/performance/entities.py`
— `@dataclass(frozen=True)`, `datetime` polja, `NewType` ID-jevi):

- `SourceSnapshot` — immutable snimak jedne fetch-ovane stranice/dokumenta
  u jednom trenutku (URL, fetched_at, content_hash, raw content ref —
  odlučiti da li raw sadržaj ide inline ili kao fajl-referenca; S2-G2 će
  odlučiti stvarnu perzistenciju, ovaj task samo definiše shape).
- `SourceChunk` — locator-precizna referenca unutar jednog `SourceSnapshot`-a
  (npr. koji CSS selector/heading/paragraf index) — ovo je ono na šta
  `FactCandidate`/`ApprovedFact.source_ref.chunk_id` pokazuje.
- `IngestionRun` — jedan pokušaj ingestovanja jednog brenda (status,
  started_at, finished_at, run-level statistika).
- `IngestionCheckpoint` — progres unutar jednog `IngestionRun`-a
  (koja faza je zadnja završena — vidi S2-G6 DISCOVER→CLASSIFY→FETCH→
  RENDER→EXTRACT→BUILD_FACTS→DONE state mašinu iz kanonskog plana §10,
  ovaj task samo definiše enum/shape, ne orkestraciju).

Ne uvoditi `CrawlTarget`/lease-queue polja ovdje (§7 kanonskog plana) —
to je S2-G2 persistence-schema odgovornost, ne domain-model odgovornost;
ako se pokaže da `CrawlTarget` treba biti domain entitet (ne samo SQL
red), dodati ga OVDJE ali dokumentovati zašto u evidence izvještaju.

## 2. `domain/facts/` — `FactCandidate` + `FactStatus.PROPOSED`

- Dodati `FactStatus.PROPOSED` u postojeći enum (`domain/facts/enums.py`)
  — ISPUNJAVA dokumentovani seam, ne mijenja postojeće vrijednosti
  (`APPROVED`/`SUPERSEDED`/`SOFT_DELETED` ostaju netaknute).
- Dodati NOV `FactCandidate` entitet u `domain/facts/entities.py`, pored
  postojećeg `ApprovedFact` (ne mijenjati `ApprovedFact` shape).
  `FactCandidate` MORA nositi provenance koji je traceable do
  `SourceSnapshot`/`SourceChunk` (§ "G-WI-EVIDENCE" hard gate, kanonski
  plan §11) — svaki `FactCandidate` mora biti moguće pratiti unazad do
  immutable snimka izvora.
- `domain/facts/policies.py` — provjeriti da li postojeće politike
  (npr. `select_allowed_facts` stil provjera) trebaju NOVU čisto-domain
  politiku za `FactCandidate` (npr. "candidate ne postaje approved fact
  direktno" invarijanta na tipskom nivou) — ako da, dodati OVDJE kao
  čistu funkciju bez I/O. Approve/Reject USE-CASE (application layer)
  je S2-G7a, van scope-a ovog taska — ovaj task samo osigurava da tip-nivo
  invarijanta postoji (npr. nema konstruktora koji pravi `ApprovedFact`
  direktno iz `FactCandidate` bez prolaska kroz explicit approve korak).

## 3. `ports/web_ingestion.py` (nov fajl)

`Protocol` definicije (isti stil kao `ports/ai.py`/`ports/export.py` —
metod signature, bez implementacije):

- `HttpFetcherPort` — `fetch(url: str) -> FetchResult` (ili slično; MORA
  odražavati §4 sync/async odluku ispod — potpisi su SINHRONI).
- `SitemapReaderPort` — čita/parsira sitemap.xml, vraća listu URL-ova.
- `UrlClassifierPort` — §8 kanonskog plana page classification
  (HOME/ABOUT/PRODUCT/... enum — definisati taj enum ovdje ili u
  `domain/ingestion/` ako je domain koncept, ne infrastructure detalj).
- `MainContentExtractorPort` — HTML → očišćen tekst + `SourceChunk`-ovi.
- `VisualIdentityExtractorPort` — HTML/assets → signali za postojeći
  `VisualIdentity` VO (ne mijenjati `VisualIdentity` u ovom tasku).
- `DocumentExtractorPort` — PDF/DOCX/XLSX → isti `SourceChunk` model
  (S2-G9 dependency, definisati port ovdje da G9 može startovati
  paralelno kad dođe red).

Svi potpisi SINHRONI (`def`, ne `async def`) — vidi §4 odluka ispod.

## 4. `ports/repositories.py` — `IngestionRepositoryPort` (aditivno)

Nova `Protocol` klasa, isti stil kao postojeće (`save_*`/`get_*`/`list_*`
metode za `SourceSnapshot`/`SourceChunk`/`IngestionRun`/
`IngestionCheckpoint`/`FactCandidate`). NE dirati nijednu postojeću
klasu u fajlu.

## 5. Novi ID tipovi (`domain/common/ids.py`, aditivno)

`SourceSnapshotId`, `SourceChunkId`, `IngestionRunId`,
`IngestionCheckpointId`, `FactCandidateId` — isti `NewType("X", str)`
obrazac, dodati na kraj fajla, ne mijenjati postojeće linije.

# §4 — Sync vs async runtime odluka (MORA biti odlučeno ovdje, prije bilo kog fetch koda)

Kanonski plan §5 eksplicitno kaže da ovo pitanje NIJEDAN izvorni
dokument nije riješio i da MORA biti odlučeno u S2-G1, prije S2-G3 koda.

**Odluka (koordinator, 2026-09-09): OSTATI SINHRON.** Svi portovi u
ovom kontraktu (`HttpFetcherPort` itd.) su definisani sa `def`, ne
`async def`.

Razlozi:

1. **Cijela postojeća arhitektura je 100% sinhrona** — `JobManager`
   (`ThreadPoolExecutor`), svaka repository implementacija, cijeli
   bridge, svaki SQLite poziv u aplikaciji. `asyncio.run()` unutar
   JEDNOG `JobManager.submit()` callable-a bi uveo ugniježden
   event-loop model usred inače potpuno sinhronog procesa — dva
   concurrency paradigme u istom procesu je stvaran maintenance trošak
   (debugging, cancellation semantika, testing) bez jasne koristi na
   ovom obimu (jedan brand ingestion run, desetak-do-stotinjak stranica
   preko `ThreadPoolExecutor`-a, ne hiljade konkurentnih konekcija gdje
   asyncio stvarno pobjeđuje).
2. **§7 kanonskog plana (SQLite lease queue) je već dizajniran sinhrono**
   (`BEGIN → SELECT → UPDATE → COMMIT` worker claim obrazac) — savršeno
   se uklapa u postojeći `ThreadPoolExecutor` worker-pool stil, nula
   trenja.
3. **SSRF odbrana se PREMJEŠTA sa aiohttp resolver-hook-a na `requests`
   + custom `HTTPAdapter`** koji validira SVAKI resolvovani IP PRIJE
   konekcije (ekvivalent aiohttp `AbstractResolver` principu, samo na
   urllib3 sloju — npr. custom `HTTPAdapter.init_poolmanager` sa
   `urllib3.util.connection.create_connection` override-om koji radi
   `socket.getaddrinfo` pa `ipaddress.ip_address(...).is_global` PRIJE
   `socket.connect`). Ovo je S2-G3 implementacioni detalj (van scope-a
   OVOG taska), ali port signatura (`HttpFetcherPort.fetch`) mora biti
   sinhrona da se ovaj mehanizam uopšte može ovako implementirati bez
   uvođenja `asyncio` samo za jedan adapter.
4. **§6.2 literal-IP-u-URL-u bypass** (aiohttp `TCPConnector.is_ip_address()`
   gap) je URL-policy-sloj provjera koja se dešava PRIJE bilo kakve
   konekcije/rezolucije — identična obaveza bez obzira na sync/async
   izbor, ne utiče na ovu odluku, ali MORA biti u S2-G3 acceptance kad
   se taj gate kontraktuje (već zabilježeno u kanonskom planu §10).

**Ova odluka je PROMPT za implementera, ne pitanje** — ako implementer
smatra da async ipak treba, MORA stati i eskalirati koordinatoru prije
pisanja koda koji krši ovu odluku (ista disciplina kao Pi-jev D1/D2
eskalacija na ACS-F1-057).

# Implementation steps

1. Pročitati `domain/facts/entities.py`, `domain/facts/enums.py`,
   `domain/facts/policies.py`, `domain/performance/entities.py` (stil
   referenca), `domain/common/ids.py`, `ports/repositories.py`,
   `ports/ai.py` (Protocol stil referenca) PRIJE pisanja koda.
2. Dodati nove ID tipove.
3. Napisati `domain/ingestion/` paket (entities + enums ako treba
   state-mašina enum za `IngestionCheckpoint` faze).
4. Dodati `FactStatus.PROPOSED` + `FactCandidate` u `domain/facts/`.
5. Napisati `ports/web_ingestion.py`.
6. Dodati `IngestionRepositoryPort` u `ports/repositories.py`.
7. Unit testovi za sve nove entitete (immutability, frozen dataclass
   ponašanje) i za bilo koju domain policy iz Objective #2 (ako se
   doda) — čisti domain testovi, bez SQLite/I-O (ništa se ne perzistira
   u ovom tasku).
8. GitNexus: `detect_changes` PRIJE commit-a mora pokazati SAMO nove
   simbole + aditivne izmjene na `ports/repositories.py`/
   `domain/facts/enums.py`/`domain/facts/entities.py`/
   `domain/common/ids.py` — nula izmjena postojećih potpisa.

# Acceptance

- [ ] `domain/ingestion/` paket postoji: `SourceSnapshot`, `SourceChunk`,
      `IngestionRun`, `IngestionCheckpoint`, sve `frozen=True`.
- [ ] `FactStatus.PROPOSED` dodano, postojeće 3 vrijednosti netaknute.
- [ ] `FactCandidate` entitet postoji, traceable do
      `SourceSnapshot`/`SourceChunk` (G-WI-EVIDENCE princip na tip-nivou).
- [ ] `ApprovedFact`/`SourceReference` shape NIJE promijenjen (osim
      eventualnog tightening-a `snapshot_id`/`chunk_id` tipova, ako
      implementer to uradi — mora biti eksplicitno dokumentovano).
- [ ] `ports/web_ingestion.py` postoji sa svih 6 portova, SVI potpisi
      sinhroni (`def`, ne `async def`).
- [ ] `IngestionRepositoryPort` dodan u `ports/repositories.py`, nijedna
      postojeća Protocol klasa/metoda nije dirana (GitNexus
      `detect_changes` potvrđuje).
- [ ] Novi ID tipovi dodani na kraj `domain/common/ids.py`, postojeće
      linije netaknute.
- [ ] Unit testovi za sve nove domain entitete + policy (ako dodana).
- [ ] `python -m pytest -q` cijeli suite prolazi, 0 regresija (isti
      poznati flaky `test_gate_report_against_current_repo_passes`
      MOŽE se pojaviti nezavisno od ovog taska — ako se pojavi,
      izolovano ponoviti da se potvrdi flaky, ne blokirati review na
      osnovu njega; vidi `.agent/CURRENT_STATE.md` napomenu).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`, posebno NULA u `infrastructure/`,
      `application/`, `presentation_webview/`, `jobs/`, `resources/migrations/`.
- [ ] GitNexus pre-change context + `detect_changes` evidence u
      izvještaju.
- [ ] **CI provjeren preko PR-a.**

# Review focus — Claude (MEDIUM, §29)

- Potpisi u `ports/web_ingestion.py` su SVI sinhroni (§4 odluka
  ispoštovana bukvalno).
- `ports/repositories.py`/`domain/facts/enums.py`/`domain/facts/entities.py`/
  `domain/common/ids.py` diff je ČISTO aditivan (GitNexus
  `detect_changes` + ručni diff read).
- `FactCandidate` provenance polje stvarno pokazuje na
  `SourceSnapshot`/`SourceChunk` ID (ne string bez tipa, ne opciono
  izostavljeno).
- Nema slučajnog uvoda `application`/`infrastructure`/`presentation_webview`
  importa u domain/ports slojeve (arhitektonska granica — postojeći
  `tests/architecture/test_import_boundaries.py` mora ostati zelen bez
  izmjena, jer ovaj task ne dodaje nove module tipove van
  domain/ports).

# Rollback

MEDIUM risk — čisti domain/ports kod, nema migracije, nema
infrastructure/GUI/lifecycle rizika. Claude-only review → odmah merge
po §29 ako PASS.

# Coordination — PARALELNI RAD

**Provjereno prema workflow §10 (allowed_paths presjek + GitNexus
shared-caller):**

- Unutar Slice 2: NIJEDAN drugi S2-G* gate ne može ići paralelno sa
  ovim taskom. DAG (kanonski plan §3) je strogo sekvencijalan na ovoj
  tački — S2-G2 (persistence) zavisi od portova/entiteta koje TEK ovaj
  task definiše; S2-G3/G4/G5/G9 zavise od S2-G2 sheme; S2-G6+ zavise
  od svega prije. Otvaranje bilo kog drugog S2-G* branch-a sada bi
  značilo nagađanje potpisa koje ovaj task tek fiksira — NE raditi to.
- **Van Slice 2, IDENTIFIKOVAN je jedan bezbjedan paralelni kandidat:**
  [ACS-MAINT-001](ACS-MAINT-001-task-contract.md) (dijagnostika za
  ponavljajući flaky gate-report test) — `allowed_paths` potpuno
  disjunktan (`scripts/generate_phase0_gate_report.py` +
  `tests/unit/scripts/`), nema GitNexus shared-caller sa
  `domain/`/`ports/` (gate-report skripta ne uvozi ni domain ni ports
  module). Sigurno za drugog implementera (Crush/MiniMax) da radi
  ISTOVREMENO dok Pi (ili drugi implementer) radi na ovom tasku.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-001-brand-ingestion-domain-ports
Branch:   task/ACS-S2-001-brand-ingestion-domain-ports
Base:     main @ c2bc637
```
