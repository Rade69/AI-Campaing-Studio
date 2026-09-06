---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
tests: PASS
gitnexus_impact: REJECT
blocking_findings:
  - BF-1
  - BF-2
  - BF-3
  - BF-4
---

# ACS-GUI-008 — nezavisni Codex review

## CILJ

Nezavisno provjeriti PR #4 (`task/ACS-GUI-008-studio-sadrzaja-generate`) prema task contractu i fix briefu, s fokusom na stvarnu GUI putanju, parcijalne greške, oporavak nakon approve koraka, konkurentne pozive, tajne, round-robin raspodjelu i `SUPERSEDED` plan.

## PROVJERENO

- Pregledan je diff `0595912...918def3`; svi izmijenjeni produkcijski fajlovi su u ugovorenom scopeu, uz dva agent evidence izvještaja.
- Pregledani su bridge, Studio SSR/JS, DTO modeli, use-case pozivi, SQLite repozitoriji i migracije te relevantni testovi.
- Potvrđen je round-robin za dvije platforme i tri stavke: `INSTAGRAM`, `FACEBOOK`, `INSTAGRAM`.
- Potvrđen je sekvencijalni oporavak nakon prekida iza approve koraka: prvi poziv bez providera ostavlja plan odobrenim i bez sadržaja, a ponovljeni poziv nakon konfiguracije generira dvije stavke bez duplikata.
- Bridge ne vraća API ključ niti `str(exc)`; per-item greška izlaže samo tip iznimke, a provider adapteri koriste fiksne poruke.
- PR #4 je otvoren, GitHub CI `test` je uspješan i commit `918def3` odgovara origin grani.

## GITNEXUS / IMPACT

GitNexus indeks glavnog checkouta bio je svjež za `ccf0a6e`. Eksplicitni impact upiti za postojeće simbole pokazali su nizak upstream utjecaj: `CampaignBridgeApi` koristi presentation entry point, a `ApproveCampaignPlan` i `GenerateSocialPost` produkcijski koristi `run_system_b.py`. Ručni `rg` sweep nije pronašao neočekivane nove produkcijske call-siteove.

Obavezni task-level `detect-changes` ipak nije moguće pouzdano izvršiti nad task worktreeom: CLI ga ne prepoznaje kao indeksiran repo, dok indeks glavnog checkouta ne sadrži task commit. Zato je `gitnexus_impact: REJECT`; ručni sweep je kompenzacijski dokaz, ali nije zamjena za analizu stvarnog task diffa.

## BLOCKING FINDINGS

### BF-1 — produkcijski Studio HTML nema live generate kontrolu

`write_all_pages()` renderira `studio_sadrzaja` bez fixturea, pa `StudioSadrzajaFixture` ima `campaign_id=None` i `plan_id=None`. `_edit_card()` tada ne emitira `data-action="generate-content"`, `data-campaign-id` ni `data-plan-id`, nego fallback poruku. `app.js` query parametre koristi za opće stanje stranice, ali njima ne materijalizira niti aktivira generate dugme.

Reprodukcija produkcijskog generatora stranica vratila je:

```text
live_action=false
campaign_attr=false
plan_attr=false
fallback_message=true
```

To vrijedi i za `studio_sadrzaja/index.html?campaign=...&plan=...`: ID-evi su samo u URL-u, a JS ih ne veže na kontrolu. SSR testovi prolaze jer ručno predaju fixture s ID-evima; ne testiraju produkcijski `write_all_pages()` put. Prirodna navigacija iz drugih ekrana može ostati poseban follow-up, ali izravna URL → live kontrola pripada ovom zadatku i blokira osnovni acceptance kriterij.

### BF-2 — stvarni pywebview API poziv puca na SQLite thread affinityju

Bridge i SQLite konekcija nastaju prije `webview.start()`. `sqlite3.connect()` koristi zadani `check_same_thread=True`, dok pywebview svaki izloženi JS API poziv izvršava u zasebnom Python threadu (`webview/util.py`, `_call` kroz `Thread`).

Reprodukcija je konstruirala bridge i seedala kampanju/plan na glavnom threadu, zatim pozvala `generate_campaign_content()` s worker threada:

```text
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread
{"ok": false, "generated_count": 0, "failed_count": 0,
 "error_code": "INTERNAL_ERROR",
 "error_message": "Ne mogu učitati plan: ProgrammingError."}
```

Stvarni klik kroz pywebview zato ne može ni učitati plan. Testovi ovo ne otkrivaju jer bridge konstruiraju i pozivaju na istom pytest threadu. Popravak mora definirati siguran lifecycle konekcije po pozivu/threadu ili serijalizirani backend executor; samo isključivanje SQLite provjere threada nije dovoljan dokaz sigurnosti.

### BF-3 — idempotency nije zaštićen od konkurentnih backend poziva

Bridge jednom učita postojeći sadržaj, zatim za svaku nedostajuću stavku generira novi ID i upisuje zapis. Nema per-campaign/per-plan locka ni in-flight registra. Baza nema unique constraint na `campaign_item_id`, a repository konflikt rješava samo po novom `content_pieces.id`.

Synchronous JS guard (`button.disabled = true`) pokriva obični dvoklik na istom DOM dugmetu, ali ne čini backend operaciju idempotentnom. Pywebview API pozive pokreće u zasebnim threadovima; dva poziva mogu pročitati isti prazan snapshot i oba upisati sadržaj s različitim ID-evima. Kada se BF-2 popravi, ova utrka ostaje i krši eksplicitni kriterij da konkurentni poziv ne stvara duplikate. Potrebna je backend zaštita i konkurentni regression test.

### BF-4 — `SUPERSEDED` plan nije odbijen prije generiranja

Bridge posebno odbija samo `DRAFT`, pa svaki drugi status tretira kao prihvatljiv i ulazi u petlju. Za `SUPERSEDED` je live provjera vratila `GENERATION_FAILED`, `failed_count=2` i dvije `InvariantViolation` greške; zapisi nisu nastali samo zato što `GenerateSocialPost` naknadno provjerava status.

To nije tihi upis stale sadržaja, ali je pogrešna kontrola toka: invalidan plan se prikazuje kao dvije AI greške i nepotrebno pokušava po stavci. Bridge treba eksplicitno dozvoliti samo `APPROVED` nakon eventualnog approve koraka, a druge statuse vratiti kao jednu validacijsku grešku prije provider/generation petlje.

## STANDARDNA VERIFIKACIJA

```text
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -q
253 passed in 14.74s

python -m ruff check .
All checks passed!

python -m mypy src
Success: no issues found in 168 source files

python -m pytest tests/ -q
990 passed, 1 warning in 100.43s

python scripts/secret_scan.py
26 passed in 0.61s
NO CONFIRMED SECRET IN TRACKED FILES
```

`git diff --check` je čist. Rezultati potvrđuju suite i statičke provjere, ali ne pobijaju BF-1/BF-2 jer suite ne izvršava produkcijski static-page bootstrap kroz stvarni pywebview worker thread.

## ADVERSARIALNA PROVJERA

- Worker-thread poziv reproducirao je kvar stvarne GUI izvršne topologije.
- Produkcijski `write_all_pages()` output provjeren je bez test fixturea i ne sadrži live action ni identifikatore.
- `SUPERSEDED` status provjeren je s dvije stavke: nema upisa, ali postoje dva pogrešno klasificirana pokušaja/neuspjeha.
- Dvije platforme i tri stavke potvrđuju očekivani round-robin.
- Sekvencijalni retry nakon prekida iza approve koraka nastavlja bez duplikata.
- Migracije i repository conflict ključ potvrđuju da konkurentna idempotency zaštita ne postoji.

## NE DIRATI U FIX RUNDI

- Domain/Application/Ports semantiku, migracije i ekran `pregled_izvoz` bez eksplicitnog proširenja task contracta.
- Širu prirodnu navigaciju Plan/Kalendar → Studio; dovoljno je zasebno evidentirati follow-up.
- Provider adaptere i njihove error mappere bez novog reproducibilnog dokaza o curenju tajne.

BF-2 vjerovatno zahtijeva pažljivo proširenje scopea na composition/connection lifecycle. Ne uvoditi globalni `check_same_thread=False` kao prečac.

## SLJEDEĆE

Vratiti implementeru koordinirani fix krug za četiri blocking nalaza:

1. povezati URL `campaign` i `plan` s produkcijskom Studio kontrolom te dodati test stvarnog `write_all_pages()` outputa;
2. uvesti thread-safe lifecycle konekcije/Unit of Worka i test poziva iz pywebview-ekvivalentnog worker threada;
3. uvesti backend per-campaign/per-plan konkurentnu idempotency zaštitu i barrier test s dva istodobna poziva;
4. eksplicitno odbiti svaki plan status osim `APPROVED` nakon eventualnog approve koraka.

Nakon popravka ponoviti puni suite, secret scan, worker-thread smoke test, produkcijski static-page test i GitNexus analizu nad task commitom. Ne mergeati PR #4 u sadašnjem stanju.
