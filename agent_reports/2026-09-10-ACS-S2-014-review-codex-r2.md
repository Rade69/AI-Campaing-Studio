---
verdict: REJECT
scope: REJECT
acceptance: REJECT
architecture: REJECT
security: PASS
tests: PASS
gitnexus_impact: PASS
blocking_findings:
  - "R2-BF-1: BF-1 fix inline-uje cijeli raw body kao base64 u raw_content_ref, suprotno SourceSnapshot ugovoru da polje bude referenca i da veliki body ne ulazi u VO/SQLite TEXT"
  - "R2-BF-2: PR je kontaminiran .agent/CURRENT_STATE.md i opÅ¡tim coordinator-handoff fajlom van allowed_paths"
---

# ACS-S2-014 â€” Codex adversarial re-review PR #32, round 2

## Presuda

REJECT za `task/ACS-S2-014-ingestion-pipeline`, HEAD
`9104893590446711df1a9af4493bad10e82d3796`. Originalni BF-1..BF-5
ponaÅ¡ajni defekti su zatvoreni na novom HEAD-u, ali BF-1 fix uvodi novi
shared-contract/persistence problem, a PR diff viÅ¡e nije scope-Äist.

## R2-BF-1 â€” MEDIUM: `raw_content_ref` se koristi kao inline body, ne kao referenca

`SourceSnapshot` kanonski dokumentuje da raw bytes **nisu inline** i da
`raw_content_ref` postoji upravo zato da veliki HTML/PDF body ostane izvan
value objecta (`domain/ingestion/entities.py:39-45`). PostojeÄ‡i repository i
domain testovi koriste referentni oblik `store://snap-1`.

Fix sada upisuje cijeli response kao base64 string direktno u
`raw_content_ref` (`ingest_brand_sources.py:382-390`) i na resume-u polje
bez type/scheme diskriminatora uvijek tretira kao base64 payload
(`:442-454`). Fresh live proba je za 72 source bajta pokazala 96 znakova u
SQLite TEXT koloni, sa prefiksom `PGh0bWw+...`, dakle polje stvarno sadrÅ¾i
body, ne referencu. Na maksimalno dozvoljenim response/page budÅ¾etima ovo
uveÄ‡ava svaki raw body za pribliÅ¾no 33% i puni lokalnu SQLite bazu sadrÅ¾ajem
koji je model namjerno drÅ¾ao van nje.

Kompatibilnost je dodatno problematiÄna: Pythonov permissive
`base64.b64decode("store://snap-1")` ne mora baciti greÅ¡ku â€” u fresh probi
vratio je devet garbage bajtova. BuduÄ‡i ili postojeÄ‡i stvarni reference URI
zato moÅ¾e biti tiho protumaÄen kao website body i proizvesti pogreÅ¡ne
chunkove umjesto fail-loud/content-store resolution ponaÅ¡anja.

Required fix: ne koristiti `raw_content_ref` kao inline payload. Najmanji
scope-compliant put je vratiti FETCHED target bez dostupnog procesa-body-ja u
siguran refetch/recovery put prije EXTRACT-a (deterministiÄki snapshot upsert
veÄ‡ postoji), pa zadrÅ¾ati durable stats. Ako se bira pravi content store,
to zahtijeva zaseban/eksplicitno proÅ¡iren contract i port/adapter jer su
`ports/` i persistence infrastruktura forbidden u ovom tasku. Regression
test mora dokazati originalni cancel/hard-kill scenario uz `raw_content_ref`
koji ostaje `None` ili stvarna typed/schemed referenca â€” nikad raw base64.

## R2-BF-2 â€” MEDIUM: PR sadrÅ¾i task-nepovezane fajlove van `allowed_paths`

Task Contract zahtijeva nula izmjena van `allowed_paths`. PR #32 na HEAD-u
sada ukljuÄuje `.agent/CURRENT_STATE.md` i
`agent_reports/2026-09-10-coordinator-handoff-to-minimax-2.md`.
`CURRENT_STATE` unos opisuje raniji HEAD/F1 stanje ("Äeka Codex review",
1471 test) i workflow nalaÅ¾e njegovo finalno aÅ¾uriranje poslije merge-a.
OpÅ¡ti coordinator handoff nije evidence artefakt implementacije G6 i sadrÅ¾i
plan za buduÄ‡i G7b.

Required fix: ukloniti oba task-nepovezana fajla/commita iz PR diffa prije
merge-a. Task-specific implementer/fix/coordinator/reviewer evidence fajlovi
mogu ostati kao standardni `agent_reports/` workflow artefakti.

## Originalni nalazi â€” status

- **BF-1 functional recovery: CLOSED.** Fresh hard-kill repro je stvarno
  ostavio jedan target FETCHED i drugi LEASED. Poslije SQL lease expiry-a i
  novog use-case procesa resume je refetchovao samo leased URL i zavrÅ¡io sa
  `snapshots=2`, `chunks=4`, `candidates=4`, oba targeta DONE i stats
  `2/4/4/0`. Ovo potvrÄ‘uje ponaÅ¡ajnu popravku, ali trenutno preko
  neispravnog inline-storage mehanizma iz R2-BF-1.
- **BF-2 cancellation checks: CLOSED.** Token se provjerava u svakoj
  chunk/candidate iteraciji; oba side-effect cancel testa asertuju da target
  ne napreduje prerano.
- **BF-3 MIME detection: CLOSED.** Extensionless
  `/download?id=123` + `application/pdf` prolazi kroz PDF extractor i daje
  chunk/candidate.
- **BF-4 visual extraction: CLOSED.** Spy test dokazuje pozive taÄno za HOME
  i ABOUT; produkcijski kod poziva extractor tek poslije HTML Content-Type
  provjere.
- **BF-5 real integration: CLOSED.** Lokalni `ThreadingHTTPServer` pokreÄ‡e
  stvarne `HttpFetcher`, `DomainDiscovery`, `MainContentExtractor`,
  `VisualIdentityAdapter`, `UrlClassifier` i `CrawlBudget` adaptere.

## Standardna verifikacija

Fresh Codex run na HEAD-u `9104893`:

```text
targeted G6 + classifier + integration: 47 passed in 14.86s
python -m ruff check .: All checks passed
python -m mypy src: Success, 211 source files
git diff --check main...HEAD: clean
full pytest, DeepSeek unset: 1471 passed, 2 skipped, 1 warning in 221.40s
GitHub CI test: SUCCESS na HEAD-u 9104893
```

Broj se razlikuje od implementer evidence (`1472 passed, 1 skipped`) zbog
okruÅ¾enja/optional testa; oba fresh lokalna i CI gate-a su zelena. Nema
test-failure blokera.

## GitNexus / impact

Main indeks je up-to-date na `09650ce`. `SourceSnapshot` upstream impact:
MEDIUM, 37 simbola / 8 direktnih consumer fajlova; ukljuÄuje repository,
document extractore, deduplicator i facts policy. `IngestionRepositoryPort`
impact je HIGH, 24 simbola / 19 direktnih importera. PR ne mijenja njihove
definicije, ali reinterpretira shared `raw_content_ref` ugovor u application
calleru, zato je ruÄna contract provjera materijalna.

GitNexus compare ostaje nepouzdan za linked worktree (indeks je vezan za
glavni checkout); kompenzovano je punim `git diff main...HEAD`, `rg` caller/
field sweepom i live SQLite reproima.

## Handoff

```text
CILJ: Fresh re-review svih pet Codex nalaza na PR #32.
URAÄENO: REJECT â€” BF-1..BF-5 ponaÅ¡ajno zatvoreni, ali novi raw_content_ref contract breach i scope kontaminacija blokiraju merge.
NE DIRATI: G2 atomic claim/recovery, G3 SSRF kod, durable stats, inner-loop cancellation, MIME/visual/real-adapter testove i deterministiÄki chunkâ†’candidate mapping.
SLJEDEÄ†E: Uska fix runda za R2-BF-1 i ÄiÅ¡Ä‡enje PR scope-a za R2-BF-2, zatim fresh Codex round 3; i dalje bez merge-a.
```
