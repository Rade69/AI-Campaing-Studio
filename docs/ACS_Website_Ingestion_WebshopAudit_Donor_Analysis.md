---
title: "AI Campaign Studio — Website Ingestion: WebshopAudit donor analiza"
document_type: "Architecture / reuse analysis"
project: "AI Campaign Studio"
source_project: "Rade69/webshop-audit"
status: "Arhivski nalaz i prijedlog"
version: "1.0"
date: "2026-09-08"
---

# AI Campaign Studio — Website Ingestion: WebshopAudit donor analiza

## 1. Zaključak

Nakon pregleda projekta `Rade69/webshop-audit`, Website Ingestion za ACS ne treba tretirati kao novi crawler projekat od nule.

WebshopAudit već ima veliki dio potrebne osnove:

- sitemap discovery i rekurzivni sitemap traversal;
- robots.txt sitemap discovery;
- HTTP fetch sa timeoutom, retry/backoff i concurrency;
- progress i stop signal;
- Playwright fallback;
- JS-render detection;
- HTML extraction;
- JSON-LD extraction;
- evidence snapshots;
- checkpoint/resume koncept;
- run-to-run diff;
- testove ključnih dijelova.

Preporuka:

> **WebshopAudit koristiti kao donor projekat, ne kopirati ga 1:1. Novi crawler framework ne uvoditi dok stvarni testovi ne pokažu da donor rješenje nije dovoljno.**

ACS mora dodati ono što WebshopAudit nije morao rješavati:

```text
SSRF/security guard
brand-page klasifikaciju
crawl budget/ranking
SourceSnapshot
FactCandidate pipeline
dedupe/conflict
human approval
ApprovedFact / BrandSnapshot integraciju
```

---

# 2. Potvrđeni donor dijelovi

## F1 — Sitemap discovery

`audit/sitemap.py` već ima:

```text
standardne sitemap candidate putanje
robots.txt Sitemap: direktive
urlset parsing
sitemapindex parsing
rekurzivni child-sitemap traversal
deduplikaciju URL-ova
```

Za ACS vrijedi prenijeti logiku:

```text
discover_sitemap_urls()
fetch_sitemap()
parse_sitemap()
collect_urls_from_sitemap()
```

Ne prenositi `filter_product_like_urls()` kao ACS politiku.

---

## F2 — HTTP fetch

`audit/fetcher.py` već rješava:

```text
per-thread requests.Session
timeout
retry
429 backoff
HTTP status handling
content-type provjeru
parallel fetching
progress callback
stop_event
Playwright fallback
```

Dobra postojeća odluka je thread-local Session.

---

## F3 — JS detection i Playwright fallback

`audit/parser.py` već detektuje JS-heavy stranice preko signala:

```text
thin content + large HTML
SPA root
script-heavy page
nema semantic content
title postoji, ali nema H1/schema
```

Rezultat:

```text
is_likely_js_rendered
js_render_confidence
js_render_signals
```

Za ACS predlažem adaptive tok:

```text
HTTP fetch
↓
JS detection

none/low
→ koristi HTTP rezultat

medium/high
→ Playwright retry
```

Time Playwright ostaje fallback, ne default.

---

## F4 — HTML extraction

Postojeći parser već izvlači:

```text
title
meta description
H1
canonical
robots meta
breadcrumb
visible text
images
price
shipping
returns
description
feature list
spec table
language signal
```

To je dobar donor za ACS extraction sloj.

---

## F5 — JSON-LD

`audit/schema_parser.py` već radi:

```text
JSON-LD extraction
@graph flatten
Product
Offer
brand
SKU
GTIN
price
currency
availability
```

ACS treba proširenje na:

```text
Organization
LocalBusiness
WebSite
WebPage
AboutPage
ContactPage
FAQPage
Product
Offer
Service
BreadcrumbList
ContactPoint
PostalAddress
```

Opcije:

1. proširiti postojeći parser;
2. testirati `extruct` kao structured-data adapter.

Ne odlučivati unaprijed; napraviti mali spike na realnim webovima.

---

## F6 — EvidenceSnapshot

`audit/evidence.py` ima dizajn veoma blizak ACS Fact-First principu:

```text
koristi već extracted podatke
↓
napravi mali dokazni snapshot
↓
ne dumpuj cijeli HTML
↓
veži evidence uz konkretan nalaz
```

WebshopAudit:

```text
Page
↓
ProductAuditRow
↓
EvidenceSnapshot
↓
Finding
```

ACS:

```text
Page
↓
SourceSnapshot
↓
ExtractedSignal
↓
FactCandidate
↓
Evidence
↓
Human Review
↓
ApprovedFact
```

Ovaj princip treba zadržati.

---

## F7 — Checkpoint/resume

`audit/pipeline.py` može sačuvati fetch rezultate i nastaviti iz prethodnog checkpointa.

Za ACS zadržati ideju, ali ne storage oblik.

Bolje je:

```text
per-page persisted state
```

nego jedan veliki JSON checkpoint nakon fetch faze.

---

## F8 — Run-to-run diff

`audit/run_diff.py` već ima:

```text
URL normalization
old/new matching
new
removed
unchanged
improved
degraded
```

Za ACS to se može pretvoriti u:

```text
recrawl
↓
changed/new pages
↓
new extraction
↓
new FactCandidates
↓
human review
↓
supersede ApprovedFacts
```

---

# 3. Šta NE treba prenositi 1:1

## R1 — Product-only URL filter

WebshopAudit isključuje stranice poput:

```text
/about
/o-nama
/contact
/dostava
/povrat
/policies
/pages
```

Za ACS su upravo te stranice često veoma važne.

Zato ACS treba novi:

```text
PageClassifier
```

Predložene klase:

```text
HOME
ABOUT
PRODUCT
SERVICE
PRICING
FAQ
SHIPPING
RETURNS
CONTACT
CATEGORY
BLOG
LEGAL
OTHER
```

---

# 4. Brand-page klasifikacija i crawl budget

ACS ne pita:

```text
"Da li URL liči na product page?"
```

nego:

```text
"Koliko je ova stranica korisna za Brand Intelligence?"
```

Signali mogu biti:

```text
URL path
title
H1
breadcrumb
schema.org type
internal-link anchor
meta description
visible text
```

Početni prioritet:

```text
1. HOME
2. ABOUT
3. PRODUCT / SERVICE
4. PRICING
5. FAQ
6. SHIPPING / RETURNS
7. CONTACT
8. key CATEGORY pages
9. selected BLOG/support pages
```

MVP ne treba crawlati cijeli sajt.

Početni budget može biti:

```text
max pages: 20
max depth: 2
same-domain: true
```

---

# 5. Najveća sigurnosna rupa: SSRF

WebshopAudit fetcher nije pravljen za scenario gdje server prima proizvoljan URL od korisnika.

ACS mora blokirati:

```text
localhost
127.0.0.0/8
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
169.254.0.0/16
IPv6 loopback/private/link-local
metadata endpoints
internal hostnames
```

Tok:

```text
URL
↓
scheme allowlist
↓
hostname validation
↓
DNS resolve
↓
IP classification
↓
PUBLIC ONLY
↓
request
```

Svaki redirect mora ponovo proći istu provjeru.

Ne smijemo dozvoliti:

```text
public URL
↓
302
↓
private/internal IP
```

---

# 6. Response budgets

ACS treba eksplicitne limite:

```text
max response bytes
max redirects
max pages
max depth
max wall-clock time
max retries
max concurrent fetches
max cumulative bytes
```

Početna procjena:

```text
timeout: 15 s
max response: 3 MB
max redirects: 5
max pages: 20
max depth: 2
```

Ovo treba potvrditi realnim testovima.

---

# 7. Playwright lifecycle

Trenutni donor otvara Playwright/Chromium po URL-u.

Za ACS je bolje:

```text
BrowserWorker
↓
1 Chromium process
↓
više isolated BrowserContext/Page objekata
↓
bounded concurrency
```

Zadržati Playwright strategiju, ali ne kopirati lifecycle 1:1.

---

# 8. Main-content extraction

WebshopAudit heuristike su korisne, ali ACS Brand Intelligence treba kvalitetan glavni tekst i sa informativnih stranica.

Predloženo:

```text
HTML
├── donor HTML signals
├── Trafilatura main text
└── structured-data extractor
```

Time dobijamo i:

```text
determinističke signale
+
čist glavni tekst
+
machine-readable podatke
```

---

# 9. SourceSnapshot

Predloženi ACS model:

```text
SourceSnapshot
    id
    url
    final_url
    fetched_at
    status_code
    content_type
    fetch_method
    content_hash

    title
    h1
    canonical
    meta_description
    main_text

    structured_data
    asset_refs
```

Preporuka:

```text
SourceSnapshot je immutable
```

Novi crawl pravi novi snapshot.

To olakšava:

```text
audit
diff
provenance
fact supersede
debugging
```

---

# 10. EvidenceRef

FactCandidate treba imati provjerljiv izvor.

Primjer:

```text
EvidenceRef
    source_snapshot_id
    source_url
    evidence_type
    field_or_path
    excerpt
```

Evidence ne treba biti cijeli HTML dump.

---

# 11. FactCandidate pipeline

Tok:

```text
SourceSnapshot
↓
ExtractedSignals
↓
FactCandidateBuilder
↓
FactCandidates
```

Primjeri candidate-a:

```text
brand name
founded year
location
phone
email
shipping rule
return policy
product facts
service facts
price facts
certifications
warranty
opening hours
```

Ključno pravilo:

```text
website kaže X
≠
ApprovedFact
```

Mora postojati:

```text
FactCandidate
↓
Human Review
↓
APPROVE / REJECT / EDIT
↓
ApprovedFact
```

---

# 12. Dedupe i conflict

Više stranica mogu dati istu ili kontradiktornu informaciju.

Primjer:

```text
/about  → Founded 2018
/footer → Since 2017
```

ACS treba:

```text
normalize candidates
↓
dedupe
↓
conflict detection
↓
human review
```

Ne donositi automatsku odluku o "istini" bez dovoljno dokaza.

---

# 13. Recrawl i supersede

Tok:

```text
crawl #1
↓
SourceSnapshot A

crawl #2
↓
SourceSnapshot B

normalize URL
↓
compare content_hash
```

Ako je sadržaj isti:

```text
UNCHANGED
→ preskoči novu extraction fazu
```

Ako je promijenjen:

```text
CHANGED
→ extract
→ new FactCandidates
```

Primjer:

```text
OLD:
Besplatna dostava preko 80 KM

NEW:
Besplatna dostava preko 100 KM
```

Human bira:

```text
APPROVE NEW
KEEP OLD
REJECT NEW
```

Ako odobri novi:

```text
old → SUPERSEDED
new → APPROVED
```

---

# 14. Durable ingestion state

Za ACS ne bih koristio samo jedan checkpoint JSON.

Predloženo:

```text
IngestionRun
IngestionPage
```

`IngestionPage.status`:

```text
PENDING
FETCHING
FETCHED
EXTRACTED
FAILED
SKIPPED
```

Time restart/crash recovery postaje mnogo pouzdaniji.

---

# 15. JobManager integracija

Website Ingestion treba koristiti postojeći ACS job model.

```text
StartWebsiteIngestion
↓
JobManager
↓
crawl/extract loop
↓
progress
↓
cancel token
```

Faze:

```text
DISCOVER
CLASSIFY
FETCH
RENDER
EXTRACT
BUILD_FACTS
DONE
```

Cancellation provjeravati:

```text
prije fetch-a
poslije fetch-a
prije Playwright fallbacka
poslije extractiona
prije persistence commit-a
```

---

# 16. Reuse mapa

| WebshopAudit dio | Reuse | ACS akcija |
|---|---:|---|
| `audit/sitemap.py` | visok | prenijeti logiku + security guard |
| `audit/fetcher.py` | srednje-visok | adapter + SSRF + budgets |
| Playwright fallback | srednje-visok | zadržati, preraditi lifecycle |
| JS detector | visok | prenijeti/testirati |
| title/H1/canonical/breadcrumb parser | visok | donor |
| description extraction | srednje-visok | kombinovati sa Trafilatura |
| `schema_parser.py` | visok donor | proširiti ili extruct adapter |
| `EvidenceSnapshot` koncept | veoma visok | prenijeti dizajn |
| checkpoint/resume | srednji | prenijeti ideju, promijeniti storage |
| `run_diff.py` | visok konceptualni reuse | prilagoditi recrawl-u |
| price parser | selektivno | koristiti za offer facts |
| shipping/returns heuristike | selektivno | candidate signals |
| product URL filter | ne | zamijeniti PageClassifierom |
| scoring | ne | nije truth pipeline |
| pandas/CSV pipeline | ne | ACS koristi domain/repositories |
| DOCX report | ne | nije Website Ingestion potreba |

---

# 17. Predložene ACS granice

Mogući portovi:

```text
UrlSafetyPort
SitemapDiscoveryPort
PageClassifierPort
PageFetcherPort
RenderedPageFetcherPort
ContentExtractorPort
StructuredDataExtractorPort
SourceSnapshotRepositoryPort
FactCandidateRepositoryPort
```

Ne moraju svi biti zasebni od prvog dana.

Cilj je da donor kod uđe kroz adaptere, ne direktno u application sloj.

---

# 18. Mogući adapteri

```text
WebshopAuditSitemapAdapter
RequestsPageFetcher
PlaywrightPageFetcher
WebshopAuditJsDetector
BeautifulSoupSignalExtractor
TrafilaturaMainTextExtractor
WebshopAuditSchemaAdapter
ExtructSchemaAdapter
```

---

# 19. Predloženi use-case

```text
IngestBrandWebsite
```

Visoki tok:

```text
validate root URL
↓
discover URLs
↓
classify/rank
↓
apply crawl budget
↓
fetch pages
↓
Playwright fallback gdje treba
↓
create SourceSnapshots
↓
extract candidate facts
↓
dedupe/conflict
↓
persist FactCandidates
↓
human review queue
```

---

# 20. Assets

Ne skidati sve slike.

Prvi nivo:

```text
logo candidates
hero image candidates
product image candidates
OpenGraph image
schema image
```

Čuvati:

```text
URL
mime type
dimensions
content hash
source page
```

Bytes preuzimati samo kada su potrebni.

---

# 21. Test strategija

Postojeće WebshopAudit testove koristiti kao donor karakterizaciju.

Za ACS dodati:

```text
SSRF private IP blocked
redirect to private IP blocked
same-domain enforcement
response-size limit
redirect limit
crawl budget
JS fallback
Playwright timeout
duplicate URL normalization
SourceSnapshot persistence
unchanged content hash
changed page diff
FactCandidate evidence link
conflicting candidates
supersede workflow
cancel mid-crawl
resume after crash
```

Prije refaktora donor logike zamrznuti ponašanje testovima.

---

# 22. Ne kopirati cijeli projekat

Ne:

```text
copy audit/ into ACS
```

Nego:

```text
identifikuj donor funkciju
↓
characterization tests
↓
izdvoji neutralnu logiku
↓
smjesti iza ACS porta
↓
prilagodi ACS domain contractu
```

---

# 23. Crawlee — nova odluka

Ranija ideja:

```text
Crawlee vs custom crawler spike
```

više nije prvi korak.

Nova odluka:

```text
WebshopAudit donor
↓
ACS bounded crawler adapter
↓
tek ako queue/retry/browser orchestration postane problem
↓
spike Crawlee
```

Crawlee testirati samo ako se pojavi potreba za:

```text
velikim persistent crawl queueom
naprednim retry schedulingom
više browser contexta
kompleksnim resume mehanizmom
```

---

# 24. Implementaciona sekvenca

## WI-0 — Donor inventory

Definisati:

```text
koji moduli se prenose
koji testovi ih štite
koje ecommerce pretpostavke se uklanjaju
```

## WI-1 — Security boundary

```text
UrlSafetyPort
SsrfGuard
redirect validation
response budgets
```

## WI-2 — Sitemap + discovery

Prenijeti donor logiku.

Dodati:

```text
same-domain
normalization
dedupe
```

## WI-3 — PageClassifier + CrawlBudget

Novi ACS sloj.

## WI-4 — HTTP fetch adapter

Prenijeti:

```text
retry
concurrency
progress
cancel
```

Dodati:

```text
SSRF
size limit
redirect validation
```

## WI-5 — Adaptive Playwright

Prenijeti JS detector.

Poboljšati browser lifecycle.

## WI-6 — SourceSnapshot

Uvesti immutable snapshot.

## WI-7 — Extraction

Kombinovati:

```text
donor signals
Trafilatura
structured-data adapter
```

## WI-8 — FactCandidate builder

## WI-9 — Dedupe/conflict

## WI-10 — Human Review

```text
APPROVE
REJECT
EDIT
```

## WI-11 — ApprovedFacts / BrandSnapshot

## WI-12 — Recrawl/diff

Tek nakon osnovnog ingestiona.

---

# 25. Gateovi

## G-WI1 — Secure fetch

Private/internal targets ne mogu biti dohvaćeni.

## G-WI2 — Discovery

Realni sajt daje relevantne brand stranice.

## G-WI3 — Adaptive rendering

JS-heavy stranica koristi Playwright, obična ne.

## G-WI4 — Evidence

Svaki FactCandidate pokazuje izvor.

## G-WI5 — Human approval

Nijedan candidate ne postaje ApprovedFact automatski.

## G-WI6 — Real brand E2E

```text
website
↓
SourceSnapshots
↓
FactCandidates
↓
review
↓
ApprovedFacts
↓
BrandSnapshot
```

## G-WI7 — Recrawl

Promjena na sajtu daje jasan diff i candidate update.

---

# 26. Šta ne uvoditi prerano

```text
distributed crawler
Redis
Celery
Kafka
browser farm
proxy rotation
anti-bot evasion
headless scraping service
vector DB samo radi ingestiona
LLM za svaku stranicu
automatic fact approval
```

---

# 27. Uloga LLM-a

LLM nije crawler i ne odlučuje sigurnosna pravila.

LLM se eventualno koristi poslije determinističke extraction faze za:

```text
candidate normalization
semantic grouping
brand summary draft
conflict explanation
```

Ne odobrava činjenice sam.

---

# 28. Ciljna arhitektura

```text
                  WebshopAudit donor
                         │
        ┌────────────────┼──────────────────┐
        │                │                  │
    sitemap.py       fetcher.py         parser/schema
        │                │                  │
        ▼                ▼                  ▼
──────────────── ACS WEBSITE INGESTION ────────────────
        │
        ▼
URL Validator + SSRF Guard
        │
        ▼
Sitemap Discovery
        │
        ▼
Page Classification
        │
        ▼
Crawl Budget
        │
        ▼
HTTP Fetch
        │
        ▼
JS Detection
        │
        ├── normal ────────────────┐
        │                          │
        └── JS needed → Playwright │
                                   ▼
                           SourceSnapshot
                                   │
                   ┌───────────────┴──────────────┐
                   ▼                              ▼
              Main text                     Structured data
           Trafilatura/donor               donor/extruct
                   │                              │
                   └───────────────┬──────────────┘
                                   ▼
                              Evidence
                                   │
                                   ▼
                            FactCandidates
                                   │
                          dedupe/conflict
                                   │
                                   ▼
                             Human Review
                                   │
                                   ▼
                             ApprovedFacts
                                   │
                                   ▼
                             BrandSnapshot
```

---

# 29. Finalna preporuka

Website Ingestion za ACS više ne treba procjenjivati kao potpuno novi crawler subsystem.

Realnija slika je:

```text
WebshopAudit
=
već riješen značajan dio crawl/extract/evidence problema

ACS
=
security hardening
+
brand-oriented page selection
+
SourceSnapshot
+
FactCandidate semantics
+
human approval
+
fact provenance
```

Najvredniji donor dijelovi su:

```text
sitemap
fetch
JS detection
HTML/schema extraction
EvidenceSnapshot
checkpoint koncept
run diff
testovi
```

Najvažnije što ne smijemo prenijeti bez izmjene:

```text
product-only URL filtering
Playwright lifecycle po URL-u
redirect trust bez SSRF zaštite
nedostatak response budgets
CSV/pandas pipeline
audit scoring logiku
```

> **Prvi izbor treba biti adaptacija WebshopAudit donor koda iza ACS portova. Crawlee i drugi crawler frameworkovi ostaju rezervna opcija tek ako stvarni testovi pokažu da donor ne može dovoljno dobro riješiti crawl orchestration.**

To smanjuje količinu novog koda i zadržava fokus ACS-a na njegovoj stvarnoj vrijednosti:

```text
Source
→ FactCandidate
→ Human Approval
→ ApprovedFact
```
