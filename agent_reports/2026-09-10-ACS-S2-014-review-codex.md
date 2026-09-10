---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: PASS
blocking_findings:
  - "BF-1: cancel/kill nakon uspjeÅ¡nog fetch-a ostavlja FETCHED snapshot bez durable body-ja; resume ga laÅ¾no oznaÄi DONE bez chunkova/kandidata i kvari statistiku"
  - "BF-2: EXTRACT i BUILD_FACTS ne provjeravaju cancellation unutar svojih chunk petlji"
  - "BF-3: dokument prepoznat samo Content-Type headerom se tiho preskaÄe"
  - "BF-4: VisualIdentityExtractorPort se injektuje ali se nikad ne poziva"
  - "BF-5: kontraktovani realni fixture HTTP integration test nije implementiran"
---

# ACS-S2-014 â€” Codex adversarial review PR #32

## Presuda

REJECT za `task/ACS-S2-014-ingestion-pipeline`, HEAD
`50c541133805a3726e9efe589bc70060c3e51f4e`. PR je OPEN, MERGEABLE i GitHub
CI `test` je SUCCESS na istom HEAD-u, ali je nezavisni live SQLite repro
potvrdio recovery data-loss/state-integrity defekt.

## BF-1 â€” HIGH: cancel/kill poslije uspjeÅ¡nog FETCH-a gubi izvuÄeni rad i laÅ¾no zavrÅ¡ava target

`execute()` resetuje `_raw_bodies` pri svakom pozivu
(`ingest_brand_sources.py:180-181`). U `_fetch()` nema cancellation provjere
izmeÄ‘u povratka `fetcher.fetch()` i perzistovanja snapshot-a/FETCHED state-a
(`:344-388`). Na resume-u FETCHED target se ne claimuje ponovo, a
`_extract_snapshot()` bez in-memory body-ja vraÄ‡a prazan tuple (`:427-434`).
`_extract()` ga uprkos tome oznaÄi EXTRACTED (`:410-417`), a `_build_facts()`
zatim DONE (`:501-523`).

Live repro na pravoj SQLite bazi koristio je fetcher koji tokom uspjeÅ¡nog
`fetch()` zatraÅ¾i cancellation i ipak vrati HTTP 200 body. Prvi poziv je
ispravno bacio `CancellationError`, ali je ostavio target `FETCHED` sa
snapshotom. Novi `IngestBrandSources` nad istim `run_id` dao je:

```text
after_cancel.state = FETCHED
resume_fetch_calls = []
after_resume.state = DONE
stats = discovered=1, fetched=0, extracted=0, candidates=0, failed=0
persisted = snapshots=1, chunks=0, fact_candidates=0
```

Isti problem postoji za stvarni hard-kill nakon Å¡to je jedan od viÅ¡e URL-ova
veÄ‡ FETCHED, dok je sljedeÄ‡i ostao LEASED. Drugi live repro je poslije resume-a
imao dva snapshot-a i oba targeta DONE, ali samo chunkove/kandidate drugog
URL-a (`snapshots=2`, `chunks=2`, `candidates=2`; stats `fetched_pages=1` za
dva targeta). Time G-WI-RECOVER nema ni "nula izgubljenog rada" ni taÄne
finalne `IngestionRunStats` brojeve.

PostojeÄ‡a dva recovery testa JESU stvarna durable-state simulacija: koriste
pravu SQLite bazu, pravi atomic claim i direktni SQL lease expiry prije punog
`execute()` resume-a. Nisu kozmetiÄka. MeÄ‘utim, oba ostavljaju jedini target
LEASED, pa resume uvijek refetchuje body i ne ulazi u kvarljivi FETCHED-without-
raw-body put. Drugi test provjerava samo snapshot upsert i ne asertuje finalne
stats/chunk/candidate brojeve.

Required fix: recovery mora ili trajno Äuvati raw body (`raw_content_ref`) ili
sigurno vratiti/refetchovati svaki FETCHED target koji nema dostupan body; ne
smije napredovati u EXTRACTED/DONE bez stvarno materijalizovanog izlaza. Finalne
stats moraju biti izvedene iz durable stanja cijelog run-a, ne samo brojaÄa
trenutnog `execute()` poziva. Dodati oba gore opisana regression testa i
asertovati snapshot/chunk/candidate/stats kompletan zbir.

## BF-2 â€” MEDIUM: cancellation nije provjerena unutar EXTRACT/BUILD_FACTS chunk petlji

Kontrakt traÅ¾i cooperative check unutar svake FETCH/EXTRACT/BUILD_FACTS
petlje. Kod provjerava token samo jednom po targetu (`:402-403`, `:507-508`),
ali ne u unutraÅ¡njim petljama koje perzistuju svaki chunk (`:411-413`) i svaki
candidate (`:511-521`). Cancel koji stigne tokom prvog write-a nastavlja sve
preostale write-ove i moÅ¾e pomjeriti target u EXTRACTED/DONE prije nego Å¡to
sljedeÄ‡i checkpoint konaÄno primijeti token. Za velike stranice/dokumente to
nije prompt cooperative cancellation i kombinuje se sa BF-1/stat-reset
problemom na resume-u.

Required fix: provjeriti token na svakoj chunk/candidate iteraciji i dodati
testove koji requestuju cancel kao side-effect prvog repository write-a;
asertovati posljednji checkpoint i durable target state prije/poslije resume-a.

## BF-3 â€” MEDIUM: Content-Type-only dokumenti se tiho zavrÅ¡avaju bez chunkova

Kontrakt zahtijeva document detection preko file extensiona ILI Content-Type
headera. `_extract_snapshot()` bira document extractor samo preko URL suffixa
(`:436-440`). URL poput `/download?id=123` sa `application/pdf` zatim pada u
non-HTML granu (`:442-444`) i vraÄ‡a `()`, nakon Äega target postaje
EXTRACTED/DONE. To je realan, Äest download oblik i gubi cijeli dokument.

Required fix: mapirati podrÅ¾ane MIME tipove na PDF/DOCX/XLSX extractore i
dodati integration test sa extensionless URL-om + document Content-Typeom.

## BF-4 â€” MEDIUM: visual extraction faza je izostavljena

`visual_identity_extractor` se sprema u `self._visual_identity` (`:137`) ali
nema nijedan poziv u cijelom use-case-u. Kontrakt traÅ¾i poziv barem za HOME
(opcionalno ABOUT), uz eksplicitnu napomenu da persistencija VO-a nije G6 scope.
Implementacija zato ne orkestrira postojeÄ‡i G5 adapter kako je ugovoreno.

Required fix: pozvati injektovani extractor za dogovorene HTML targete i
dodati spy test koji dokazuje HOME minimum i da se ne poziva na svakoj stranici.
Ne dodavati novu repository/port metodu u ovoj fix rundi.

## BF-5 â€” MEDIUM: "full pipeline" test nije kontraktovani realni fixture HTTP tok

`test_full_pipeline_persists_real_counts_and_provenance` koristi
`_FakeDiscovery`, `_FakeFetcher`, `_content_extractor` i `_FakeVisual`
(`test_ingest_pipeline.py:68-138`). Zato ne pokreÄ‡e stvarni mali HTTP server,
`HttpFetcher`, `DomainDiscovery` ni `MainContentExtractor`, iako acceptance
eksplicitno traÅ¾i puni DISCOVERâ†’DONE integration tok na stvarnom fixture
sajtu. Test dobro dokazuje SQLite brojeve/provenance za orkestrator sa
fakeovima, ali ne dokazuje adapter wiring i stvarni pipeline contract.

Required fix: dodati mali lokalni fixture HTTP server i stvarne G3/G4
adaptere, zadrÅ¾avajuÄ‡i postojeÄ‡i brzi test kao uÅ¾i orchestration test.

## PotvrÄ‘eno

- `test_recover_expired_lease_resumes_without_duplicate_work` i
  `test_fetch_succeeded_before_crash_does_not_duplicate_snapshot` koriste
  pravu SQLite bazu, pravi claim i stvarnu SQL lease manipulaciju. Snapshot
  ID/upsert zatvara taÄno crash-prozor prije FETCHED state update-a, ali ne
  BF-1 prozor poslije FETCHED update-a.
- `claim_next_crawl_target` ima taÄno jedan call-site u sekvencijalnoj while
  petlji (`ingest_brand_sources.py:328`); G6 ne reimplementira G2 atomicity.
- SSRF granica je poÅ¡tovana: HTTP ide iskljuÄivo kroz injektovani
  `HttpFetcherPort`; `http_fetcher.py` i `url_safety_policy.py` nemaju diff.
- BUILD_FACTS je deterministiÄki 1:1 chunkâ†’candidate. Grep u
  `application/ingestion/` nije naÅ¡ao `AIRequest`, `TextGenerationPort`,
  provider SDK niti direktni HTTP klijent (`urllib.parse.urlsplit` je samo
  URL parsing).
- URL classifier je deterministiÄki, URL-only i testira EN+BHS_LATIN
  segmente. Application sloj ne importuje infrastructure.
- Scope produkcijskog/test koda je unutar dozvoljenih putanja; jedanaesti
  fajl je implementer evidence report, legitimni workflow artefakt. Nema
  forbidden production izmjena.

## Standardna verifikacija

```text
targeted ingestion/G7a suite: 54 passed in 3.13s
python -m ruff check .: All checks passed!
python -m mypy src: Success: no issues found in 211 source files
python -m pytest -q (DeepSeek unset): 1464 passed, 2 skipped, 1 warning
git diff --check main...HEAD: PASS
GitHub PR CI test: SUCCESS
```

Lokalno je prikupljeno 1464 PASS, ne prenesenih 1471; nema faila, ali ovaj
izvjeÅ¡taj navodi stvarni nezavisni output umjesto ranijeg summary broja.

## GitNexus / impact

Main indeks je osvjeÅ¾en na `H:\AI Campaing Studio` commit `09650ce` i
`status` je up-to-date. `IngestionRepositoryPort` ima HIGH upstream blast
radius (24 impacted, 19 direct imports); `JobManager` LOW (4 impacted, 1
direct). Metode `claim_next_crawl_target`/`recover_expired_leases` nisu
razrijeÅ¡ene kao zasebni simboli, pa je caller provjeren `rg`-om.

Poznato worktree-binding ograniÄenje se ponovilo: compare iz PR worktree-a uz
eksplicitni repo indeks analizirao je glavni checkout i prijavio samo lokalne
AGENTS/CLAUDE izmjene, ne PR. Taj rezultat nije koriÅ¡ten kao scope dokaz;
kompenzovan je punim `git diff main...HEAD`, `rg` caller sweepom, stvarnim
SQLite reproima i punim gate-om.

Codex nije mijenjao implementation, mergeao niti pushao. Nakon fix runde
potreban je fresh re-review na novom HEAD-u; HIGH task i nakon PASS-a i dalje
traÅ¾i eksplicitno Human Owner odobrenje prije merge-a.

## Handoff

```text
CILJ: Nezavisno dokazati ACS-S2-014 G-WI-RECOVER, cancellation, stats, SSRF i deterministic BUILD_FACTS acceptance.
URAÄENO: REJECT â€” live SQLite repro potvrÄ‘uje data loss i laÅ¾ni DONE nakon cancel/kill FETCH prozora; joÅ¡ Äetiri acceptance rupe su potvrÄ‘ene.
NE DIRATI: G2 atomic claim/recovery implementaciju, HttpFetcher/UrlSafetyPolicy SSRF kod, deterministic chunkâ†’candidate ID/upsert princip i S2-G7a.
SLJEDEÄ†E: Implementer radi usku fix rundu za BF-1..BF-5, pokreÄ‡e targeted/full gate i predaje novi HEAD Codexu na fresh adversarial re-review; bez merge-a.
```
