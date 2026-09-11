# Sažetak sesije (2026-09-11) — S2-G8 review + Brend GUI ingestion/review tok

**Agent:** Claude
**Datum:** 2026-09-11
**Svrha ovog fajla:** konsolidovan pregled SVEGA urađenog u ovoj sesiji, jer
je posao išao kroz 8 odvojenih task-ova/mergova. Svaki task ima svoj puni
`agent_report` (linkovi ispod) — ovo je pregled sa vezama, ne zamjena.

---

## 1. Nezavisna adversarial provjera S2-G8 (Playwright fallback) — REJECT, pa fix

**Grane/commit-i:** `task/ACS-S2-017-playwright-fallback` → `516fbbc` (merge)

Codex je trebalo da uradi adversarial re-review S2-G8 taska ali je stalno
prekidan, pa sam ja preuzeo. Nalaz: **F2 kritičan** — redirect pre-check
(`_redirect_unsafe_reason`) je fail-ovao OPEN na bilo koju mrežnu grešku
(npr. spor odgovor), što je bio jedini guard protiv top-level navigation
redirect-a ka privatnom/loopback cilju (`context.route` ih ne presreće).
Live-reprodukovano: redirect endpoint koji kasni 3.5s je zaobišao guard i
browser je stigao do loopback cilja.

**Popravljeno** (isti agent, uz eksplicitnu dozvolu korisnika da preskoči
odvojenu review rundu): fail-closed umjesto fail-open, + test za
service_workers="block" koji je otkrio da je claim "registracija se
odbija" bio POGREŠNA pretpostavka (Playwright je zapravo resolve-uje
register() ali nikad ne aktivira worker — ispravljen test da provjerava
STVARNO bezbjednosno svojstvo).

Izvještaji: `2026-09-11-ACS-S2-017-review-claude.md`,
`2026-09-11-ACS-S2-017-fix-round1-brief.md`

---

## 2. ACS-GUI-011 — Unos URL-a u GUI pokreće pravu ingestion

**Grana/commit:** `task/ACS-GUI-011-brand-url-ingestion` → `7ef8e2a`

Otkriveno (nezavisnom provjerom): "unesi URL, vidi rezultat" petlja je bila
zatvorena SAMO na test/arhitektura nivou — `IngestBrandSources` je imao
NULA pozivalaca u produkcijskom kodu, GUI Brend ekran je imao placeholder
"Kasnije: pokreni ingestion/review tok."

Dodano: `CampaignBridgeApi.start_brand_ingestion()` (JobManager pozadinski
posao, ista wiring kombinacija — HttpFetcher/DomainDiscovery/UrlClassifier/
MainContentExtractor/BoilerplateFilter/Deduplicator/VisualIdentityAdapter —
ranije ručno dokazana da radi na `https://example.com/`), URL polje + dugme
na Brend ekranu.

Izvještaj: `2026-09-11-ACS-GUI-011-claude.md`

---

## 3. ACS-GUI-012 — Grupisanje pregleda činjenica po izvornoj stranici

**Grana/commit:** `task/ACS-GUI-012-fact-review-grouping` → `62d4465`

Korisnička primjedba: prikaz preuzetih kandidata je bio ravna lista bez
stila (`.fact-review-row` CSS klasa nije imala NIJEDNO pravilo). Ponuđene
3 opcije (AskUserQuestion) — izabrano grupisanje po stranici (accordion).
Implementirano + testirano (XSS escaping, brojevi, klik→reload i dalje
prolaze nepromijenjeni).

Izvještaj: nema posebnog fajla (dokumentovano u commit poruci).

---

## 4. ACS-GUI-013 — Dugme "Obriši sve" (reset za testiranje)

**Grana/commit:** `task/ACS-GUI-013-clear-ingestion` → `85e85e0`

Korisnik trebao način da isprazni listu između test-URL-ova. Dodano
`IngestionRepositoryPort.delete_ingestion_data_for_brand()` (FK-safe
redoslijed brisanja), NAMJERNO ne dira `approved_facts` (odobrena činjenica
ima svoju kopiju teksta, preživi reset). Testirano: brisanje + idempotentno
ponovno brisanje + odobrena činjenica ostaje netaknuta poslije reset-a.

Izvještaj: `2026-09-11-ACS-GUI-013-claude.md`

---

## 5. ACS-GUI-014 — Traka napretka + KRITIČAN bugfix (dugme se zamrzavalo)

**Grana/commit:** `task/ACS-GUI-014-ingestion-progress-bar` → `6ae0ac8`

Korisnik: "ingestion je spor, ne vidim da li se nešto učitava." Pisanje
Node-VM testa za traku napretka je PRVI PUT stvarno pokrenulo
`startIngestion()` u JS izvršnom okruženju (ne samo Python bridge poziv
direktno) — otkriven **kritičan bug u već mergovanom ACS-GUI-011**:
`POLL_INTERVAL_MS` je referenciran iz POGREŠNOG, nepovezanog IIFE bloka
(app.js je niz odvojenih top-level IIFE-ova koji ne dijele scope). Svaki
klik na "Pokreni ingestion" je pucao odmah nakon što je posao stvarno
krenuo na backend-u — dugme ostajalo zauvijek zaključano, status
zaglavljen, lista se nikad ne osvježi. `node --check` (samo sintaksa) ovo
NIJE mogao uhvatiti. Vjerovatno pravo objašnjenje korisnikovog "izgleda
zamrznuto" utiska.

Popravljeno (lokalna `const` umjesto posezanja u tuđi scope) + dodana
prava vizuelna traka (indeterminate/determinate).

Izvještaj: `2026-09-11-ACS-GUI-014-claude.md`

---

## 6. ACS-GUI-015 — Dijagnostika za "sve završeno za par sekundi, ništa učitano"

**Grana/commit:** `task/ACS-GUI-015-empty-result-diagnostics` → `6254f9b`

Reprodukovano: URL bez `https://` prefiksa ILI URL koji SSRF politika
blokira (npr. loopback) → `IngestBrandSources` javlja SUCCEEDED sa
`fetched=0 candidates=0`, potpuno TIHO (nijedan log, nijedna poruka
korisniku). Dodano: (a) `_LOGGER.warning` na oba mjesta gdje je ovo bilo
tiho (`zero_targets_discovered`, `fetch_skipped_unsafe`) — bez izmjene
ponašanja, samo vidljivost; (b) frontend: automatsko dodavanje `https://`
ako nedostaje, i eksplicitna poruka korisniku kad posao završi sa 0
rezultata umjesto tihog "ništa".

Izvještaj: dokumentovano u commit poruci (`git log` na tu granu).

---

## 7. ACS-GUI-016 — Malformiran /sitemap.xml je ubijao CIJELU diskaveriju sajta

**Grana/commit:** `task/ACS-GUI-016-malformed-sitemap-resilience` → `cc459ad`

Korisnik prijavio: `https://kingdomdoo.com/en/` ništa ne učita. Novi log iz
#6 je ODMAH pokazao uzrok: taj sajt vraća svoju početnu HTML stranicu
(status 200) na `/sitemap.xml` umjesto 404. `SitemapReader` ispravno baca
`SitemapParseError` za to (namjeran dizajn — malformiran ≠ odsutan), ali
`DomainDiscovery.discover()` to nije hvatao ni na jednom od dva poziva —
greška je izlazila iz CIJELE funkcije, gubeći čak i seed URL koji je već
bio dodat u listu. Popravljeno: uzak catch specifično za
`SitemapParseError` (ne generic Exception), tretira se kao odsutan
sitemap. Mutation-testirano (test namjerno pokvaren → pao, vraćen → prošao).

**Live rezultat na TAČNOM prijavljenom URL-u:** prije `fetched=0
candidates=0`, poslije `fetched=3 candidates=210`.

Izvještaj: `2026-09-11-ACS-GUI-016-claude.md`

---

## 8. ACS-GUI-017 — Masovne akcije (bulk odobri/odbij)

**Grana/commit:** `task/ACS-GUI-017-bulk-review-actions` → `bbf3413`

Fix iz #7 je otkrio NOVI problem: 210 kandidata sa samo 3 stranice
(104+104+2), sitni bullet-fragmenti — pregled neupotrebljiv jedan-po-jedan.
Ponuđene 3 opcije (AskUserQuestion: bulk akcije / spajanje fragmenata /
oboje) — izabrane bulk akcije. Dodano: checkbox po predloženoj stavci,
"odaberi sve" po grupi, sticky traka "Odobri označeno"/"Odbij označeno" sa
novim `bulk_review_fact_candidates` bridge metodom (petlja postojeće
Approve/Reject use-case-ove, partial-success umjesto all-or-nothing).
Live-verifikovano na pravim 210 kandidatima (105 odobreno + 105 odbijeno
u dva klika umjesto 210).

Izvještaj: `2026-09-11-ACS-GUI-017-claude.md`

---

## 9. OTVORENO — "Napravi snimak brenda" pravi snimak koji se ne koristi

Korisnik pitao šta se dešava klikom na "Napravi snimak brenda". Provjereno
direktno u pravoj bazi (`...\database\ai_campaign_studio.db`):

```
brand_snapshots:
  v1 — 3 činjenice — 2026-09-04 (originalni demo fixture)
  v2 — 210 činjenica — 2026-09-11 (korisnikov klik danas)
```

Snimak v2 je STVARNO sačuvan sa svih 210 odobrenih činjenica. ALI
`brand-seed.json` (keš fajl koji određuje koji je snimak "aktivan" za
generisanje kampanje preko `create_campaign_and_generate_plan`) i dalje
pokazuje na v1. `get_latest_snapshot` (koji bi trebalo da čita NAJNOVIJI
snimak) se trenutno poziva SAMO unutar `assemble_brand_snapshot` metode
same (da zna sljedeći broj verzije) — nigdje se ne koristi da ažurira
aktivni keš poslije novog snimka.

**Nije popravljeno — čeka korisnikovu odluku** (da li generisanje kampanje
treba automatski uvijek koristiti najnoviji snimak, ili treba eksplicitan
"aktiviraj ovaj snimak" korak — ovo je proizvodna odluka, ne bug sam po
sebi dok se ne odluči željeno ponašanje).

---

## Zajednički obrazac kroz sesiju

Svaki popravljen problem je otkriven **live testiranjem sa pravim
podacima** (pravi URL-ovi, prava baza), ne pretpostavkom — i skoro svaki
sljedeći problem je postao vidljiv TEK pošto je prethodni popravljen
(zamrznuto dugme → sakrivalo tihi 0-rezultat slučaj → sakrivao malformirani
sitemap slučaj → otkrio problem obima podataka → otkrio da se odobreni
snimci ne koriste). Sva 4 "GUI" taska imaju punu regresiju (1500+ testova)
prije merge-a; svaki merge je pušovan na `main` odmah.

## Puna lista commit-a (main, hronološki)

```
516fbbc  fix(S2-G8): close F2 redirect SSRF fail-open bypass
7ef8e2a  feat(gui): wire Brend URL input to start real brand ingestion (ACS-GUI-011)
62d4465  feat(gui): group fact-review candidates by source page (ACS-GUI-012)
85e85e0  feat(gui): add "Obriši sve" reset button (ACS-GUI-013)
6ae0ac8  feat(gui): ingestion progress bar + fix critical ReferenceError (ACS-GUI-014)
6254f9b  fix(ingestion): diagnose + fix silent empty ingestion runs (ACS-GUI-015)
cc459ad  fix(ingestion): malformed /sitemap.xml no longer kills discovery (ACS-GUI-016)
bbf3413  feat(gui): bulk approve/reject for fact review (ACS-GUI-017)
```
