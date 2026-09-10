---
task: ACS-S2-014 — S2-G6 Pipeline Orchestration
author: minimax (privremeni koordinator, Claude na pauzi zbog limita tokena)
date: 2026-09-10
codex_verdict_round2: REJECT
new_finding: R2-BF-1 (MEDIUM, contract breach on raw_content_ref)
review_file: agent_reports/2026-09-10-ACS-S2-014-review-codex-r2.md
worktree: H:/ai-campaign-studio-worktrees/ACS-S2-014-ingestion-pipeline
branch: task/ACS-S2-014-ingestion-pipeline
current_HEAD: 9e642d3 (round-2 izvještaj commit-an; chain bez Claude handoff duplikata)
status: FIX-ROUND 3 BRIEF — čeka Pi-jev odgovor
---

# Fix-round 3 brief — ACS-S2-014 (S2-G6) — R2-BF-1

## Problem (Codex round 2 + coordinator verifikacija)

Pi-jev fix-round 2 je zatvorio BF-1..BF-5 ponašajno (verifikovano u
round-2 re-review, mutation-test 2/2 demonstriran), ALI round-2 je
otkrio NOVI contract breach:

**R2-BF-1 (MEDIUM)**: `SourceSnapshot.raw_content_ref` se koristi
kao inline base64, suprotno originalnom contract-u.

**Coordinator verifikacija** (inspekcija koda, ne samo Codex):

```text
$ domain/ingestion/entities.py:39-52
class SourceSnapshot:
    """...raw content (large HTML/PDF body) is referenced via
    ``raw_content_ref`` so a large HTML/PDF body stays out of the
    value object..."""
    raw_content_ref: str | None = None
```

Contract je jasan: `raw_content_ref` je **REFERENCA** (npr.
`store://snap-1` + zaseban content store), NE inline body.

```text
$ ingest_brand_sources.py:382-388
content = result.content or b""
snapshot = SourceSnapshot(
    id=SourceSnapshotId(_stable_id(run_id, target.normalized_url)),
    url=target.normalized_url,
    fetched_at=self._clock(),
    content_hash=hashlib.sha256(content).hexdigest(),
    raw_content_ref=base64.b64encode(content).decode("ascii"),  # ← BREACH
    content_type=result.content_type,
    status_code=result.status_code,
)
```

Fix-round 2 upisuje cijeli response kao base64 string → SQLite TEXT
kolona sadrži body, ~33% veći od originala, puni bazu sadržajem
koji contract namjerno drži izvan nje.

```text
$ ingest_brand_sources.py:442-454
if content is None and snapshot.raw_content_ref:
    try:
        content = base64.b64decode(snapshot.raw_content_ref)
    except Exception as exc:
        ...
```

NEMA type/scheme discriminator-a. Codex potvrđuje:
`base64.b64decode("store://snap-1")` tiho vraća 9 garbage bajtova
(Python permissive). Budući stvarni reference URI može biti tiho
protumačen kao website body i proizvesti pogrešne chunk-ove umjesto
fail-loud ponašanja.

## Zašto je MEDIUM (ne HIGH)

- Funkcionalno: BF-1 (functional recovery) i dalje radi, hard-kill
  reproducer prolazi (Codex round 2: snapshots=2, chunks=4,
  candidates=4)
- Rizik: tiha reinterpretacija contract-a. Budući content store
  bi tiho radio sa website body-jem umjesto referencom
- Resurs: +33% storage overhead po fetch-u, SQLite TEXT kolona
  raste sadržajem koji ne bi trebao biti u njoj

## Codex-ova preporuka (round-2 review, "Required fix")

> "Ne koristiti `raw_content_ref` kao inline payload. Najmanji
> scope-compliant put je vratiti FETCHED target bez dostupnog
> procesa-body-ja u siguran refetch/recovery put prije EXTRACT-a
> (deterministički snapshot upsert već postoji), pa zadržati
> durable stats. Ako se bira pravi content store, to zahtijeva
> zaseban/eksplicitno proširen contract i port/adapter jer su
> `ports/` i persistence infrastruktura forbidden u ovom tasku."

Ključni constraint: **`ports/` i persistence infrastruktura su
forbidden u G6 scope-u** (po task contract-u). Zato **pravi
content store NIJE opcija** za ovu fix-rundu. Refetch/recovery
put JE opcija.

## Opcije za fix (preporuka: opcija A)

### Opcija A — refetch/recovery put (Codex preporučena, scope-minimalna)

**Šta**:
1. Ukloniti `raw_content_ref=base64.b64encode(content).decode("ascii")`
   iz `SourceSnapshot` konstruktora na `:388`. `raw_content_ref`
   ostaje `None` (default).
2. U `_extract_snapshot`, ako `content is None` (in-memory body
   nedostupan, in-db raw_content_ref takodjer None) za target u
   state-u FETCHED:
   - Postaviti `target.state = PENDING` sa
     `last_error="missing_raw_body_refetch"`
   - Vratiti prazan tuple
3. U `_extract` petlji, NE označavati takav target kao EXTRACTED
   (ostaje PENDING; na sljedećem `_fetch` ciklusu, `claim_next_crawl_target`
   će ga vratiti i `_fetch` će ga refetchovati; `save_source_snapshot`
   sa istim `id` je deterministički upsert).
4. Ažurirati `_compute_run_stats` da broji unique URL-ove sa
   `snapshot_id is not None` u `DONE` state-u kao `fetched_pages`
   (ne mijenjati semantiku, samo dokumentirati u komentar).

**Zašto scope-minimalna**:
- NE dodaje nove port/repo metode
- NE dodaje novi content store
- NE proširuje `SourceSnapshot` contract
- Koristi već postojeći `update_crawl_target_state(target.id,
  CrawlTargetState.PENDING, last_error=...)` iz G2
- Koristi već postojeći `save_source_snapshot` (deterministički
  upsert po `id`)
- Koristi već postojeći `claim_next_crawl_target` (vraća PENDING)

**Trade-off**: refetch zahtijeva ponovni HTTP GET. Ako je
originalni fetch već završio i body je nekako izgubljen (cancel
između `fetcher.fetch()` i `_extract`), refetch je jedini
deterministički način da se dobije body.

### Opcija B — typed/scheme discriminator na `raw_content_ref`

Dodati prefiks (`b64:`, `store:`, itd.) na `raw_content_ref` tako
da `b64decode` NE tiho prihvati `store://` URI. ALI: OPCIJA B
i dalje inline-uje body (ako koristimo `b64:`), samo dodaje
discriminator. NE rješava contract breach — samo ga čini
manje opasnim. **NE PREPORUČUJEM**.

### Opcija C — pravi content store

Zabranjeno po G6 task contract-u (`ports/` i persistence su
forbidden). Zahtijeva:
- Novi `ContentStorePort` u `ports/`
- Novi `LocalFileContentStore` u `infrastructure/`
- Migraciju 0010
- Proširenje `SourceSnapshot` contract-a

Van scope-a za G6. Otvoriti kao zaseban S2-G7b+ zadatak.

## Acceptance (fix-round 3 PASS kada)

### Obavezno

1. **`raw_content_ref` NIKAD inline body**:
   - Nema `base64.b64encode(content)` nigdje u
     `ingest_brand_sources.py`
   - `SourceSnapshot` konstruktor pozvan sa `raw_content_ref=None`
     (ili eksplicitno bez tog parametra)
   - `raw_content_ref` ostaje `None` za sve fetchan-e targete
     u CI/integration testovima

2. **Refetch put radi za missing body**:
   - Novi reprodukcioni test: cancel/kill IZMEĐU
     `fetcher.fetch()` (linija 345) i `_extract` (linija 225)
     → resume ne smije imati `DONE` sa `chunks=0`,
     `candidates=0`
   - Ponašanje: na resume-u, target u FETCHED bez body-ja
     postaje PENDING, `_fetch` ga refetchuje, normalan
     pipeline do DONE sa chunks/candidate
   - **VAŽNO**: postojeći `test_cancel_after_fetch_recovers_body_on_resume`
     i `test_hard_kill_after_first_fetch_resumes_both_targets`
     MORAJU i dalje prolaziti (dokaz da refetch put je
     functionally ekvivalentan inline base64)

3. **Type/scheme safety**:
   - Ako `raw_content_ref` ikad bude neprazan string,
     `b64decode` na njemu MORA baciti grešku (fail-loud)
   - Predlažem: u `_extract_snapshot`, eksplicitno
     `if snapshot.raw_content_ref and not snapshot.raw_content_ref.startswith("store://"):`
     return () sa warning-om
   - ILI: `raw_content_ref` uvijek None (opcija A gore)

4. **Stats ostaju tačni**:
   - `_compute_run_stats` broji unique URL-ove u DONE sa
     `snapshot_id is not None` kao `fetched_pages`
   - Ne mijenjati semantiku, samo dokumentirati

### Standardna verifikacija (mora i dalje vrijediti)

```text
python -m ruff check .: All checks passed
python -m mypy src: 211 source files, 0 errors
python -m pytest -q: svi postojeći testovi + novi reprodukcioni
git diff --check main...HEAD: clean
```

### Specifični novi testovi

- `test_raw_content_ref_is_never_inline_body`: assert da
  za svaki `SourceSnapshot` sačuvan tokom pipeline-a,
  `snapshot.raw_content_ref is None` (ILI
  `isinstance(snapshot.raw_content_ref, str) and
  snapshot.raw_content_ref.startswith("store://")` ako se
  bira opcija A.1 sa typed referencom)
- `test_refetch_path_recovers_body_on_resume`: scenarij
  cancel-poslije-fetch, dokaz da resume radi preko refetch-a
- `test_b64decode_on_unprefixed_ref_raises`: sigurnosni
  test (opcionalan, ako se bira typed referenca opcija)

## Šta NE SMIJEŠ (ne dirati)

- `recover_expired_leases` / `claim_next_crawl_target` G2
  atomic claim/recovery logiku (Codex round 2 potvrdio da je
  ispravna)
- `HttpFetcher` / `UrlSafetyPolicy` SSRF kod
- `SourceSnapshot` contract definiciju u
  `domain/ingestion/entities.py` (NE mijenjati `raw_content_ref`
  type/schema, samo ga ne koristiti)
- `SourceSnapshot` import-ovani u drugim modulima (testovi,
  document extractori, deduplicator) — oni očekuju
  `raw_content_ref: str | None`, ne mijenjati contract
- Deterministički 1:1 chunk→candidate (BUILD_FACTS)
- S2-G7a (Approve/Reject FactCandidate)
- `_checkpoint` logika (F1 fix)
- Repository/port METODE (ne dodavati nove)
- Scope produkcijskog koda (allowed_paths iz F1 task
  contracta)
- `application/ingestion/__init__.py` export lista (nije
  potrebno dodavati nove simbole)
- BF-2/3/4/5 fix-ove (već CLOSED u round 2, ne dirati)

## CI koordinator napomena

PR #29 (CI install follow-up) MERGED, CI zelen za G3/G4 testove.
PR #32 CI `test` job bio SUCCESS na `9104893` (prije rebase-a).
Fix-runda 3 treba zadržati CI zeleno — svi testovi koji su
prolazili u round 2 MORAJU i dalje prolaziti.

## Vraćanje

Ako imaš pitanja, javi sa **output-om komande**, ne opisom:

- "Opcija A implementirana" → output `git diff main..HEAD` i
  `python -m pytest -q tests/integration/application/ingestion/`
- "Novi reprodukcioni test prolazi" → output pytest
- "Rebase na main završio" → output `git log --oneline main..HEAD -10`
  i `git diff --stat main..HEAD`

Bez outputa = bez odgovora.

## Poslije tvog fix-a (koordinator protocol)

1. Pull-ati tvoj branch, `git diff --stat main..HEAD`
2. Pročitati tvoj novi evidence fajl
3. Pokrenuti: mypy, pytest (puni suite), ruff
4. **Nezavisni mutation-test R2-BF-1**:
   - Reverzirati fix
   - Pokrenuti reprodukcioni test
   - Asertirati da pada
   - Restaurirati
   - Asertirati da prolazi
5. Poslati Codex-u fresh adversarial re-review (round 3)
6. Ako Codex PASS: sažeti za Human Owner-a, tražiti
   eksplicitno odobrenje (HIGH = ne §29)
7. Merge tek nakon Human Owner odobrenja
