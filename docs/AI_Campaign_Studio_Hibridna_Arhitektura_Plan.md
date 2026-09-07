---
title: "AI Campaign Studio — detaljan plan hibridne arhitekture"
document_type: "Architecture roadmap"
project: "AI Campaign Studio"
purpose: "Definiše kako sadašnji local-first desktop ACS može evoluirati u hibridni sistem: instalirani desktop klijent + centralni VPS backend + moguć kasniji browser/web pristup, bez prepisivanja Campaign Enginea."
status: "Strategic architecture plan — nije trenutni implementation scope"
version: "1.0"
date: "2026-09-06"
---

# AI Campaign Studio — detaljan plan hibridne arhitekture

## 1. Cilj

Cilj nije da sada prebacimo AI Campaign Studio sa desktopa na web.

Cilj je da sadašnju aplikaciju gradimo tako da kasnije možemo preći na:

```text
Desktop klijent
    ↓ HTTPS
Centralni ACS backend na VPS-u
    ↓
PostgreSQL + storage + jobs
```

i, ako tržište to opravda, kasnije dodati:

```text
Browser frontend
    ↓
isti ACS backend
```

bez prepisivanja:

- Domain sloja;
- Campaign Enginea;
- fact-first logike;
- Approved Facts;
- Campaign Plan modela;
- Content/Revision modela;
- Claim Checka;
- Performance modela;
- Visual sistema;
- većine application use-case logike.

## 2. Najvažniji princip

Hibridna verzija ne treba biti:

```text
Desktop app
+
nekoliko nasumičnih API poziva prema serveru
```

nego:

```text
Frontend
    ↓
stabilan Backend API
    ↓
Application sloj
    ↓
Domain
    ↓
Ports
    ↓
Infrastructure adapteri
```

Transport, baza i mjesto izvršavanja smiju se mijenjati.

Poslovna logika ne smije zavisiti od njih.

## 3. Trenutno stanje koje koristimo kao osnovu

Sadašnji ACS već ima važne temelje:

```text
domain/
application/
ports/
infrastructure/
presentation/
presentation_webview/
```

To je dobar početak za hibridnu arhitekturu.

Ključna arhitektonska namjera ostaje:

```text
Domain
↑
Application
↑
Ports
↑
Infrastructure / Presentation
```

Ne dozvoliti:

```text
Domain → SQLite
Domain → pywebview
Application → JavaScript
Application → FastAPI
```

## 4. Ciljna evolucija

### Faza A — sadašnji desktop

```text
┌──────────────────────────────┐
│        ACS DESKTOP           │
│                              │
│ HTML / CSS / JS              │
│ pywebview                    │
│ BackendClient                │
│                              │
│ Application                  │
│ Domain                       │
│                              │
│ SQLite                       │
│ Local files                  │
│ OS Keyring                   │
└──────────────────────────────┘
```

Sve je na jednom računaru.

### Faza B — hibridna verzija

```text
┌──────────────────────────────┐
│       ACS DESKTOP CLIENT     │
│                              │
│ HTML / CSS / JS              │
│ pywebview shell              │
│ BackendClient                │
│ local cache                  │
│ downloads / previews         │
└──────────────┬───────────────┘
               │
             HTTPS
               │
               ▼
┌──────────────────────────────┐
│        ACS SERVER / VPS      │
│                              │
│ FastAPI / HTTP API           │
│ Application                  │
│ Domain                       │
│                              │
│ PostgreSQL                   │
│ Object/File storage          │
│ Background jobs              │
└──────────────────────────────┘
```

### Faza C — opciona web verzija

```text
ACS Desktop Client ───────┐
                          │
Browser Frontend ─────────┼── HTTPS ──→ ACS Backend
                          │
Mobile/PWA kasnije ───────┘
```

Server ne treba znati da li zahtjev dolazi iz pywebview desktopa ili browsera.

## 5. Šta ostaje lokalno, a šta ide na server

### 5.1 Server treba da bude source of truth za poslovne podatke

Na VPS-u:

```text
Users
Organizations / Workspaces
Brands
BrandSnapshots
ApprovedFacts
FactCandidates
Campaigns
CampaignBriefs
CampaignPlans
CampaignItems
ContentPieces
Revisions
Claims
VisualSystems
LayoutSpecs
DistributionInstances
PerformanceSnapshots
Import batches
SourceSnapshots
Website ingestion state
```

Razlog:

Ako korisnik instalira ACS na dva računara, mora vidjeti isti:

```text
brend
kampanju
sadržaj
revizije
kalendar
performance
```

### 5.2 Lokalno ostaje ono što pripada uređaju

Desktop:

```text
window state
local UI preferences
temporary files
preview cache
downloaded ZIP/export files
recently opened data cache
lokalni thumbnail cache
desktop-specific integration
```

Opcionalno:

```text
local offline cache
```

ali ne u prvoj hibridnoj verziji.

## 6. Ključna promjena: BackendClient

Danas frontend ne smije dugoročno biti vezan direktno za:

```text
window.pywebview.api
```

Treba uvesti:

```text
BackendClient
```

Frontend koristi samo njega.

Primjer:

```javascript
backend.createCampaign(...)
backend.generateCampaignPlan(...)
backend.generateContent(...)
backend.getCampaign(...)
backend.exportCampaign(...)
backend.listBrands(...)
```

### 6.1 Desktop implementacija

```text
BackendClient
    ↓
PyWebViewBackendClient
    ↓
window.pywebview.api
```

### 6.2 Hibridna implementacija

```text
BackendClient
    ↓
HttpBackendClient
    ↓
fetch()
    ↓
HTTPS API
```

Frontend UI ne treba znati koja implementacija je aktivna.

## 7. Transport-neutralna Application API granica

Najvažnija backend promjena je da pywebview bridge prestane biti mjesto gdje živi orchestration.

Ne želimo:

```text
CampaignBridgeApi
    → repository creation
    → provider resolution
    → use-case orchestration
    → error mapping
    → compensation logic
```

jer bi FastAPI kasnije morao duplicirati isto.

Cilj:

```text
CampaignApplicationService
BrandApplicationService
ContentApplicationService
ExportApplicationService
ProviderApplicationService
```

ili ekvivalentna facade/orchestration granica.

### 7.1 Primjer

```text
Frontend
   ↓
PyWebView bridge
   ↓
CampaignApplicationService
   ↓
CreateCampaign
GenerateCampaignPlan
```

Kasnije:

```text
Frontend
   ↓
FastAPI endpoint
   ↓
ISTI CampaignApplicationService
```

Pywebview i FastAPI postaju tanki transport adapteri.

## 8. API contract pravila

Od trenutka kada planiramo mogući VPS backend, svaki frontend/backend contract treba biti dizajniran kao da putuje mrežom.

Svi request/response objekti:

```text
JSON serializable
```

Koristiti:

```text
string
number
boolean
array
object
null
```

Ne vraćati:

```text
sqlite3.Connection
Path
Python exception
Pillow Image object
pywebview Window
```

### 8.1 ID polja

Sve ID vrijednosti prema frontendu:

```text
string
```

### 8.2 Datumi

Koristiti:

```text
ISO-8601
```

Primjer:

```text
2026-09-06T18:30:00Z
```

### 8.3 Error contract

Stabilno:

```json
{
  "ok": false,
  "error_code": "VALIDATION_ERROR",
  "error_message": "..."
}
```

Interni stack trace nikada ne ide klijentu.

## 9. API verzionisanje

Hibridni sistem treba od početka imati:

```text
/api/v1/
```

Primjer:

```text
POST /api/v1/campaigns
GET  /api/v1/campaigns/{id}
POST /api/v1/campaigns/{id}/plan
POST /api/v1/campaigns/{id}/content
GET  /api/v1/brands
```

Ne zato što odmah planiramo v2, nego da kasnije ne moramo lomiti instalirane desktop klijente.

## 10. Server backend

Predloženi stack:

```text
Python
FastAPI
PostgreSQL
SQLAlchemy ili drugi pažljivo odabran DB adapter sloj
Alembic ili postojeći migration pristup prilagođen PostgreSQL-u
```

Važno:

FastAPI ne ide u Domain/Application sloj.

Struktura:

```text
src/
  domain/
  application/
  ports/
  infrastructure/
      database/
          sqlite/
          postgres/
      ai/
      storage/
  presentation/
  transport/
      pywebview/
      http/
```

Nazivi se mogu prilagoditi postojećem repou.

## 11. PostgreSQL adapteri

Danas:

```text
CampaignRepositoryPort
    ↓
SqliteCampaignRepository
```

Kasnije:

```text
CampaignRepositoryPort
    ├── SqliteCampaignRepository
    └── PostgresCampaignRepository
```

Application sloj ne smije znati koji se koristi.

## 12. Ne prebacivati poslovnu logiku u SQL

PostgreSQL nije novi Domain.

DB radi:

```text
persistence
constraints
indexes
transactions
queries
```

Poslovna pravila ostaju u Domain/Application sloju.

## 13. User / Organization model

Ovo ne uvoditi sada.

Ali hibridna verzija će trebati:

```text
User
Organization / Workspace
Membership
Role
```

Minimalno:

```text
Organization
  ├── User A
  ├── User B
  └── User C
```

Podaci se vezuju za:

```text
organization_id
```

Ne za pojedinačni uređaj.

## 14. Authentication

Prva hibridna verzija:

```text
email
password
session/access token
```

ili pouzdan vanjski auth provider.

Desktop workflow:

```text
Pokreni ACS
↓
Login
↓
server vrati session/token
↓
token ide u Authorization header
```

Token se lokalno čuva kroz OS-appropriate secure storage.

## 15. Authorization

Server mora odlučivati:

```text
ko smije vidjeti Brand
ko smije mijenjati Campaign
ko smije exportovati
```

Ne frontend.

Frontend hide/disable je samo UX.

## 16. AI API ključevi — dvije opcije

### O1 — BYOK ostaje lokalno

```text
Desktop
    ↓
OpenAI / Anthropic / Gemini
```

Prednosti:

- korisnički API ključ ne dolazi na naš server;
- manja security odgovornost;
- jednostavnije za početak.

Nedostaci:

- background AI posao ne može raditi ako je desktop ugašen;
- provider config treba rješavati po uređaju;
- orchestration je djelimično podijeljena.

### O2 — ključ na serveru

```text
Desktop
    ↓
ACS VPS
    ↓
AI provider
```

Prednosti:

- background jobs;
- isti provider sa svih uređaja;
- centralni retry/rate limiting;
- tanji desktop.

Nedostaci:

- server čuva osjetljive ključeve;
- encryption at rest;
- access controls;
- secret rotation;
- incident response.

### Preporuka

Za prvu hibridnu probu:

```text
O1 ako želimo minimalan security scope
```

O2 samo ako background execution i multi-device BYOK postanu stvarno važni.

## 17. Background jobs

Kada AI/ingestion radi na serveru, ne držati HTTP request otvoren minutima.

Model:

```text
POST /campaigns/{id}/generate-content
↓
202 Accepted
↓
job_id
```

Frontend prati:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
```

### 17.1 Minimalna prva verzija

Ne uvoditi odmah Celery/Redis.

Može:

```text
PostgreSQL job table
+
jednostavan worker proces
```

dok je volumen mali.

## 18. Website ingestion u hibridnoj verziji

Website ingestion je prirodan server-side posao.

```text
Desktop
↓
URL
↓
VPS
↓
URL validation
robots/sitemap
crawl budget
HTTP fetch
Playwright fallback
Trafilatura
extruct
FactCandidates
```

Prednosti:

- jedno kontrolisano network okruženje;
- Playwright ne mora biti instaliran na svakom klijentu;
- lakši retry;
- centralni crawl limits;
- manje desktop dependencies.

## 19. SSRF i server security za ingestion

Ako server prima URL od korisnika, obavezno:

```text
blokirati private IP ranges
blokirati localhost
blokirati link-local
kontrolisati redirects
max response size
timeout
same-domain budget
DNS rebinding zaštita
```

## 20. Files i dokumenti

Dokumenti mogu ići:

```text
Desktop
↓ upload
VPS
↓
storage
↓
document ingestion
```

Ne držati velike binarne fajlove direktno u PostgreSQL bez razloga.

## 21. Object storage

Kasnije:

```text
S3-compatible storage
```

Na VPS-u može biti MinIO ili eksterni storage.

Čuva:

```text
uploaded docs
rendered images
export ZIP
website snapshots
assets
```

PostgreSQL čuva metadata + reference.

## 22. Export model

Desktop sada prirodno radi sa lokalnom putanjom.

Hibridno server treba da radi:

```text
ExportArtifact
id
file_name
media_type
size
storage_key
created_at
```

Frontend dobije:

```text
artifact_id
file_name
download_url
```

Desktop zatim preuzme ZIP u korisnikov folder.

Ne vraćati serverske filesystem putanje.

## 23. Visual rendering

Moguće su dvije arhitekture.

### O1 — rendering ostaje lokalno

Prednost:

- manji server load.

Mana:

- uređaji mogu imati razlike;
- packaging renderer dependencies.

### O2 — rendering na serveru

```text
LayoutSpec
↓
deterministički renderer
↓
PNG
↓
storage
```

Dugoročno bih preferirao server-side canonical rendering.

## 24. Local cache

Prva hibridna verzija može biti:

```text
online-required
```

Kasnije dodati read cache za:

- campaigns list;
- brand summary;
- thumbnails;
- posljednje otvorene sadržaje.

Ne praviti pravi offline multi-master sync dok korisnici to ne traže.

## 25. Offline mode — opasnost

Pravi offline write sync otvara:

```text
conflicts
merge policy
versioning
user conflict UX
```

Zato prva hibridna verzija treba biti online-first.

## 26. Optimistic concurrency

Kada dva uređaja uređuju isti sadržaj, koristiti revision/version.

Ako desktop šalje izmjenu nad revizijom 12, a server je već na 13:

```text
409 CONFLICT
```

Ne smije posljednji writer tiho pregaziti tuđi rad.

## 27. Calendar

Centralni backend je source of truth za:

```text
scheduled_at
timezone
platform
format
campaign
content revision
```

Server čuva UTC + original timezone.

## 28. Performance/Analytics

Performance import prirodno pripada serveru:

```text
CSV upload
↓
server parsing
↓
matching
↓
PerformanceSnapshots
```

## 29. Secret Store apstrakcija

Danas:

```text
SecretStorePort
→ KeyringSecretStore
```

Kasnije:

```text
SecretStorePort
├── KeyringSecretStore
└── ServerSecretStore
```

## 30. Logging i observability

Desktop log:

```text
device-local UI/runtime issues
```

Server log:

```text
API requests
application failures
AI provider failures
ingestion failures
job failures
DB errors
```

Ne logovati:

```text
API keys
access tokens
passwords
full sensitive documents
```

Uvesti request_id/job_id.

## 31. Audit log

Kasnije:

```text
user_id
organization_id
action
entity_type
entity_id
timestamp
```

Primjer:

```text
User A odobrio Fact F-002
User B eksportovao Campaign C-17
```

## 32. Deployment

Minimalni VPS:

```text
Ubuntu LTS
Docker Compose ili systemd
Reverse proxy
HTTPS
FastAPI service
PostgreSQL
worker
backup
```

Ne Kubernetes.

## 33. Reverse proxy

Caddy ili Nginx:

```text
TLS
HTTPS
request size limits
proxy prema FastAPI
```

## 34. Backup

Minimalno:

```text
daily PostgreSQL backup
retention
restore test
```

Ako storage čuva dokumente/assets/exports, treba i zaseban storage backup.

## 35. Health endpoints

Server:

```text
/health
/ready
```

Provjeravaju:

```text
API alive
DB reachable
migrations current
storage reachable
worker status
```

## 36. Desktop startup ponašanje

```text
Pokreni aplikaciju
↓
provjeri mrežu
↓
provjeri server health
↓
ako OK → login/app
ako nije → jasan server unavailable ekran
```

Ne beskonačni spinner.

## 37. Update desktop klijenta

Kasnije treba:

```text
version check
update notification
installer
```

Desktop šalje:

```text
X-ACS-Client-Version
```

Server mora podržavati razuman broj klijentskih verzija unazad.

## 38. Security minimum

Obavezno:

```text
HTTPS
password hashing / trusted auth provider
server-side authorization
rate limiting
input validation
secret redaction
secure token storage
DB least privilege
backup encryption
CORS policy
CSRF ako cookie auth
upload size limits
file type validation
SSRF protection
dependency updates
```

Desktop nije trusted client. Server ponavlja sve kritične validacije.

## 39. Multi-tenancy

Ne uvoditi sada.

Kad hibrid postane pravi proizvod:

```text
organization_id
```

mora biti dio tenant boundary-ja.

To je security requirement, ne samo filter.

## 40. Migracija postojećeg SQLite podatka

Kasnije:

```text
Local SQLite
↓
Migration/Upload tool
↓
API
↓
PostgreSQL
```

Koraci:

1. validate schema version;
2. export canonical data;
3. map IDs;
4. upload;
5. server validates invariants;
6. transaction import;
7. comparison report;
8. user confirms.

Ne kopirati `.db` fajl direktno na server.

## 41. Test strategija

### Unit

Domain/Application bez mreže.

### Repository contract tests

Isti testovi nad SQLite i PostgreSQL adapterima gdje je praktično.

### Transport tests

PyWebView i HTTP transport moraju mapirati isti application contract.

### Integration

```text
HTTP → Application → PostgreSQL
```

### End-to-end

```text
Desktop
→ HTTPS
→ server
→ AI fake/test provider
→ DB
→ export
```

## 42. Contract parity test

Veoma vrijedan test:

```text
PyWebViewBackendClient
i
HttpBackendClient
```

za isti request treba da daju semantički isti response contract.

## 43. Monolith, ne mikroservisi

Ne:

```text
Brand Service
Campaign Service
Fact Service
AI Service
Calendar Service
Export Service
```

na odvojenim servisima.

Za ACS je razumniji modular monolith:

```text
jedan backend deploy
jasni interni moduli
jedna transakcijska baza
```

Ako neki dio jednog dana zaista treba izdvojiti, tada ćemo imati dokaz.

## 44. Faze realizacije

### PHASE H0 — sada

Ne graditi VPS.

Raditi samo web-readiness:

1. `BackendClient` boundary;
2. centralizovati `window.pywebview.api.*`;
3. izvući orchestration iz pywebview bridge-a;
4. stabilizovati JSON contracts;
5. ne vraćati local filesystem detalje kao opšti contract;
6. zadržati repository ports bez SQLite leak-a.

### PHASE H1 — lokalni HTTP proof

```text
pywebview
↓
http://127.0.0.1
↓
FastAPI
↓
isti Application
↓
SQLite
```

Acceptance:

- Campaign flow radi preko HTTP;
- frontend ne zna za pywebview API;
- isti core testovi prolaze;
- nema promjene Domain pravila.

### PHASE H2 — PostgreSQL adapter spike

Uzeti mali vertikalni slice:

```text
Brand
Campaign
Fact
```

i dokazati da isti application use-case radi nad SQLite i PostgreSQL adapterom bez izmjene use-case koda.

### PHASE H3 — VPS pilot backend

Deploy:

```text
FastAPI
PostgreSQL
HTTPS
```

Desktop koristi `HttpBackendClient`.

Test:

```text
Laptop A
Laptop B
```

otvaraju istu kampanju.

### PHASE H4 — authentication + organization

Tek nakon uspješnog VPS pilota.

### PHASE H5 — server-side ingestion/jobs

Premjestiti:

```text
Website ingestion
long AI jobs
performance import
```

na server.

### PHASE H6 — server-side storage/render/export

Dodati:

```text
object storage
canonical server rendering
ExportArtifact
download endpoint
```

### PHASE H7 — browser proof

Pokrenuti isti frontend u browseru.

Ako `BackendClient` granica radi, browser i desktop koriste isti HTTP backend.

## 45. Gateovi

### G-H1 — Transport independence

Frontend radi sa:

```text
PyWebViewBackendClient
i
HttpBackendClient
```

bez izmjene screen logike.

### G-H2 — Persistence independence

Ključni use-case radi nad SQLite i PostgreSQL adapterom.

### G-H3 — Multi-device proof

```text
Laptop A kreira kampanju
Laptop B je vidi
Laptop B izmijeni sadržaj
Laptop A vidi novu reviziju
```

bez ručnog synca.

### G-H4 — Server job proof

Desktop pokrene Website ingestion ili AI job.

Zatvori UI.

Server završi posao.

Ponovnim pokretanjem desktopa rezultat postoji.

### G-H5 — Browser proof

Browser verzija uradi:

```text
login
open brand
open campaign
generate/read content
```

koristeći isti backend.

## 46. Šta NE raditi prije H1/H2 gateova

Ne uvoditi:

```text
Kubernetes
microservices
Redis samo zato što postoji
Celery bez potrebe
Kafka
GraphQL
event sourcing
CQRS
offline multi-master sync
mobile app
team permissions matrix
billing
subscription service
```

To nisu trenutni problemi.

## 47. Glavni rizici

### R1 — Bridge orchestration ostane predebeo

Posljedica:

FastAPI duplira desktop logiku.

Mitigacija:

transport-neutral application facade/service.

### R2 — Frontend se veže za pywebview

Posljedica:

browser migracija traži rewrite.

Mitigacija:

BackendClient.

### R3 — Local path procuri u contracts

Posljedica:

web semantics postanu neprirodne.

Mitigacija:

artifact IDs + download model.

### R4 — Prerano uvedemo multi-tenancy/auth

Posljedica:

mjeseci infrastructure rada prije product validation.

Mitigacija:

VPS pilot prvo.

### R5 — Offline sync postane cilj

Posljedica:

kompleksnost eksplodira.

Mitigacija:

online-first.

### R6 — API ključevi na server bez security odluke

Posljedica:

velika sigurnosna odgovornost.

Mitigacija:

BYOK lokalno u prvoj hibridnoj fazi ili poseban security gate.

## 48. Predložena dugoročna slika

```text
                         ┌─────────────────────┐
                         │      Browser        │
                         │      Frontend       │
                         └──────────┬──────────┘
                                    │
                                    │ HTTPS
                                    │
┌─────────────────────┐             │
│   Desktop Client    │             │
│                     │             │
│ HTML/CSS/JS         │─────────────┤
│ pywebview shell     │             │
│ BackendClient       │             │
└─────────────────────┘             │
                                    ▼
                         ┌─────────────────────┐
                         │      ACS API        │
                         │      FastAPI        │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │ Application layer   │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │       Domain        │
                         │ Campaign Engine     │
                         │ Fact-first rules    │
                         └──────────┬──────────┘
                                    │
                                  Ports
                                    │
                  ┌─────────────────┼──────────────────┐
                  │                 │                  │
                  ▼                 ▼                  ▼
             PostgreSQL        AI adapters       Object Storage
                  │                                    │
                  │                                    │
                  └──────────── Workers ────────────────┘
```

## 49. Šta korisnik dobija

Korisnik instalira ACS na:

```text
PC u kancelariji
laptop kod kuće
drugi laptop
```

i dobija iste:

```text
Brands
Approved Facts
Campaigns
Calendar
Revisions
Performance podatke
```

bez ručnog kopiranja SQLite baze.

## 50. Šta mi dobijamo

- desktop UX ostaje moguć;
- centralna baza;
- lakši backup;
- server-side ingestion;
- background jobs;
- multi-device;
- kasniji team rad;
- browser verzija postaje dodatni client, ne novi proizvod od nule.

## 51. Ključna odluka za sada

Ne implementirati hibrid sada.

Sada raditi samo ono što ima malu cijenu, a veliku buduću vrijednost:

```text
1. BackendClient boundary
2. thin pywebview transport
3. transport-neutral orchestration
4. JSON-safe contracts
5. storage/filesystem abstraction
6. repository ports bez SQLite leak-a
```

To je dovoljno da buduća hibridna migracija bude realna.

## 52. Predloženi trenutak za početak hibridnog spika

Ne prije nego što imamo potvrđeno:

```text
real desktop vertical slice
+
Real Website/Brand Ingestion
+
nekoliko stvarnih kampanja
+
dokaz da proizvod ima vrijednost
```

Tek tada VPS ima poslovno opravdanje.

## 53. Finalna strategija

```text
SADA
desktop-first
local-first
architecture-ready

↓ ako proizvod potvrdi vrijednost

HYBRID
desktop client
centralni VPS
PostgreSQL
HTTP API

↓ ako tržište traži

WEB
browser kao drugi frontend
isti backend
isti Campaign Engine
```

Najvažnije:

> Ne gradimo dvije aplikacije. Gradimo jedan Campaign Engine sa više mogućih načina pristupa.

Desktop je prvi klijent.

VPS kasnije postaje centralni application host.

Browser, ako ga budemo trebali, postaje drugi klijent istog sistema.
