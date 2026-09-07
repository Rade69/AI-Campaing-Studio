---
title: "AI Campaign Studio — ACS Companion Single VPS plan"
document_type: "Implementation roadmap / architecture plan"
project: "AI Campaign Studio"
scope: "Desktop ACS + opcioni ACS Companion za udaljeni pregled, komentare, odobravanje i praćenje statusa kampanja"
deployment_model: "Single VPS"
frontend: "React + TypeScript + Vite"
backend: "FastAPI"
database: "PostgreSQL"
reverse_proxy: "Caddy"
status: "Strategic plan — Companion se ne implementira prije product/reviewer validation gate-a"
version: "2.0"
date: "2026-09-07"
supersedes: "AI_Campaign_Studio_Companion_Single_VPS_Plan v1.0"
---

# AI Campaign Studio — ACS Companion plan v2

## 1. Šta je promijenjeno u odnosu na v1

Osnovna arhitektura ostaje:

```text
ACS Desktop = creator
ACS Companion = reviewer / tracker
```

Ali v2 uvodi pet ključnih korekcija:

1. Companion se ne gradi dok ne postoji stvarni reviewer i stvarni review problem.
2. Prije VPS-a prvo pravimo jeftini **Static Review Export**.
3. Uvodi se zajednički **CampaignPresentationPackage** koji mogu koristiti ZIP export, static review i budući Companion.
4. `package_hash` postaje osnova idempotency-ja i review verzioniranja; izbacuje se nepostojeći `source_campaign_revision`.
5. Asset transport i reviewer identity se definišu eksplicitno.

Dodatno:

- postojeći desktop CSS tokeni se mogu koristiti kao vizuelna referenca, ali desktop stylesheet se ne reuse-uje za mobile Companion;
- Companion ostaje single-VPS sistem;
- puni SQLite ↔ PostgreSQL sync ostaje zabranjen;
- Companion ne smije usporiti završavanje stvarnog desktop data-driven toka.

---

# 2. Prvo poslovno pitanje: postoji li stvarni reviewer?

Companion nema smisla samo zato što je ACS desktop aplikacija.

Companion ima smisla tek ako postoji stvaran workflow:

```text
osoba A
kreira kampanju
      ↓
osoba B
pregleda / komentariše / odobrava
```

Osoba B može biti:

- klijent agencije;
- vlasnik firme;
- marketing manager;
- brand owner;
- direktor;
- drugi član tima sa approval odgovornošću.

Ako je stvarni workflow:

```text
napravim kampanju
↓
sam je pregledam
↓
sam je objavim
```

onda Companion vjerovatno nije potreban.

## 2.1 Reviewer Validation Gate

Prije FastAPI/PostgreSQL/VPS rada mora postojati barem jedan stvarni slučaj gdje druga osoba treba pregledati kampanju.

Treba zabilježiti:

```text
ko je reviewer
kako danas dobija sadržaj
kako ostavlja feedback
da li odobrava cijelu kampanju ili pojedinačne objave
da li koristi telefon
šta mu sada smeta
šta bi mu stvarno olakšalo posao
```

## 2.2 GO signal

Companion ima opravdanje ako stvarni reviewer traži nešto poput:

```text
"Želim jedan link gdje vidim sve objave."
"Treba mi komentar po pojedinačnoj objavi."
"Treba mi jasno Odobri / Vrati na doradu."
"Treba mi da vidim šta je već objavljeno."
"Ne želim instalirati desktop aplikaciju."
```

## 2.3 STOP signal

Ako je dovoljno:

```text
PDF / HTML / slike
+
mail / WhatsApp odgovor
```

Companion se ne gradi.

To je validan rezultat.

---

# 3. Cilj proizvoda

Ako Validation Gate prođe, Companion rješava samo udaljeni review i tracking.

Desktop radi:

```text
Brend
→ Approved Facts
→ Campaign Brief
→ Campaign Plan
→ AI generisanje
→ Studio sadržaja
→ Vizuali
→ Revizije
→ Export
```

Companion radi:

```text
VIEW
REVIEW
COMMENT
APPROVE
REQUEST CHANGES
TRACK
```

Companion ne radi:

```text
GENERATE
FULL EDIT
BRAND INTELLIGENCE
CAMPAIGN ENGINE
AI PROVIDER ORCHESTRATION
```

---

# 4. Arhitektonska odluka

Ne pravimo:

```text
Desktop ACS ⇄ kompletna PostgreSQL baza
```

Ne pravimo puni sync.

Pravimo:

```text
ACS Desktop
    ↓
CampaignPresentationPackage
    ↓
ReviewPackage
    ↓ HTTPS
ACS Companion
    ↓
Browser / telefon / tablet
```

Desktop je source of truth za creation.

Companion je source of truth za review state.

---

# 5. Novi centralni seam: CampaignPresentationPackage

Uvodi se neutralni objekat:

```text
CampaignPresentationPackage
```

On predstavlja ono što želimo prikazati čovjeku, bez obzira da li završava kao ZIP, HTML ili Companion upload.

Tok:

```text
Campaign
ContentPieces
Revisions
Facts / claim-check rezultat
Visuals
Schedule
      ↓
CampaignPresentationPackage
      ├──→ ZIP Export
      ├──→ Static Review Export
      └──→ ReviewPackage → Companion
```

Ovo sprečava da tri različita dijela sistema ponovo sastavljaju iste podatke.

## 5.1 Predloženi contract

```text
CampaignPresentationPackage
    package_schema_version
    source_campaign_id
    campaign_name
    brand_name
    created_at

    items[]
        source_content_id
        content_revision_id
        content_revision_version
        campaign_role
        platform
        format

        headline
        caption
        hook
        body
        cta
        hashtags

        scheduled_at
        timezone

        fact_check
            approved_fact_count
            unsupported_claim_count
            warning_count

        visual
            asset_sha256
            mime_type
            width
            height
```

Važno:

```text
Campaign nema campaign_revision polje.
```

Ne izmišljati `source_campaign_revision`.

---

# 6. Idempotency i verzioniranje — ispravka v1

V1 je predlagao:

```text
UNIQUE(source_campaign_id, source_campaign_revision)
```

To nije ispravno.

Razlog:

```text
Campaign nema revision
CampaignPlan.version nije isto što i content revision
ContentPiece revizije mogu promijeniti paket bez promjene plana
```

## 6.1 Novi model

Svaki kanonski paket dobija:

```text
package_id
package_hash
```

`package_hash` je SHA-256 nad deterministički serializovanim sadržajem paketa.

```text
canonical JSON
↓
SHA-256
↓
package_hash
```

Pravilo:

```text
isti source_campaign_id
+
isti package_hash
=
isti sadržaj
```

Retry ne pravi novu ReviewVersion.

Promjena relevantnog sadržaja mijenja hash i proizvodi novu ReviewVersion.

Server dodjeljuje:

```text
ReviewVersion.version_number = 1, 2, 3...
```

Desktop nije autoritet za taj broj.

---

# 7. PHASE C-1 — Static Review Validation

Prije FastAPI-ja, PostgreSQL-a i VPS-a desktop iz `CampaignPresentationPackage` generiše:

```text
review-export/
├── index.html
├── campaign.json
└── assets/
```

Stranica prikazuje:

```text
naziv kampanje
brand
objave
caption
vizuale
platforme
uloge
datume
fact-check summary
```

Nema:

```text
login
comments
approval API
PostgreSQL
server state
```

Može se otvoriti lokalno ili privremeno postaviti na statički web link.

## 7.1 Cilj testa

Ne testiramo tehnologiju.

Testiramo:

```text
da li stvarnom čovjeku uopšte treba stateful remote review
```

Reviewer se pita:

```text
Da li je ovaj pregled dovoljan?
Treba li ti komentar unutar stranice?
Treba li ti Odobri / Vrati na doradu?
Treba li istorija verzija?
Treba li status objavljivanja?
Treba li mobilni pregled?
```

Ako static review rješava problem, Companion se ne gradi.

---

# 8. GO / NO-GO za pravi Companion

## GO

Gradimo Companion ako Static Review pokaže konkretnu potrebu za:

```text
comments
approvals
request changes
version history
publication tracking
review activity
```

## NO-GO

Ako static page + mail/WhatsApp feedback rješava dovoljno:

```text
Companion se ne gradi
```

`CampaignPresentationPackage` i Static Review Export i dalje ostaju korisni.

---

# 9. Ciljna Single VPS arhitektura

Ako GO gate prođe:

```text
                           INTERNET

                  https://review.acs.example
                              │
                              ▼
                    ┌─────────────────┐
                    │      Caddy      │
                    │ HTTPS / routing │
                    └───────┬─────────┘
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
   React + TypeScript + Vite            FastAPI
      statički frontend                   API
             │                             │
             └──────────────┬──────────────┘
                            ▼
                       PostgreSQL
                            │
                            ▼
                    Local Asset Storage

ACS Desktop
    │
    └──────────── HTTPS API ───────────────→ FastAPI
```

Na jednom VPS-u:

```text
Ubuntu VPS
├── Caddy
├── React/Vite production build
├── FastAPI
├── PostgreSQL
├── lokalni asset storage
└── backup agent
```

Samo backup ide van VPS-a.

---

# 10. Zašto jedan VPS

Namjerno ne razdvajamo frontend, backend, bazu i storage dok za to nema potrebe.

Single VPS daje:

```text
jedan deployment target
jedan domen
jedan firewall
jedan backup plan
jednostavniji debugging
manje vendor zavisnosti
```

Kasnije se dijelovi mogu izdvojiti ako se pojavi stvaran razlog.

---

# 11. Tehnološki stack

## Frontend

```text
React
TypeScript
Vite
React Router
TanStack Query
Radix primitives
ACS design tokens
```

## Backend

```text
FastAPI
Pydantic
SQLAlchemy 2.x
Alembic
PostgreSQL
```

## Proxy/TLS

```text
Caddy
```

## Deployment

```text
Docker Compose
```

Servisi:

```text
caddy
api
db
```

Ne Kubernetes.

---

# 12. UX korekcija: desktop CSS se ne reuse-uje

Postojeći ACS desktop stylesheet je desktop-only.

Companion je mobile-first.

Reuse-ujemo samo:

```text
boje
radius vrijednosti
spacing logiku
tipografsku hijerarhiju
brand identitet
```

Ne reuse-ujemo cijeli desktop `app.css`, posebno ne desktop layout pretpostavke:

```text
min-width: 1180px
fixed desktop sidebar
desktop-only grids
```

Companion dobija svoj responsive stylesheet/design-token sloj.

---

# 13. Desktop → Companion granica

Desktop dobija port:

```text
ReviewPublisherPort
```

Implementacija:

```text
HttpReviewPublisher
```

Tok:

```text
CampaignPresentationPackage
↓
BuildReviewPackage
↓
ReviewPublisherPort
↓
HttpReviewPublisher
↓
Companion API
```

---

# 14. ReviewPackage

`ReviewPackage` je network-oriented contract izveden iz `CampaignPresentationPackage`.

```text
ReviewPackage
    schema_version
    package_id
    package_hash

    source_campaign_id
    campaign_name
    brand_name
    created_at

    items[]
        source_content_id
        content_revision_id
        campaign_role
        platform
        format
        caption
        scheduled_at
        timezone
        fact_check_summary
        asset_refs[]
```

Ne uključivati:

```text
SQLite paths
Python objects
Path objects
raw DB rows
framework state
secret values
AI provider keys
```

---

# 15. Asset transport — nova eksplicitna specifikacija

V1 je opisao storage, ali ne upload tok.

V2 koristi content-addressed asset model.

Desktop za svaki asset računa:

```text
SHA-256
```

Asset identity:

```text
asset_sha256
```

Tok:

```text
1. desktop izračuna SHA-256
2. pita server postoji li asset
3. ako postoji → dobije asset_id
4. ako ne postoji → upload bytes
5. server validira fajl
6. server upiše metadata
7. server vraća asset_id
8. ReviewPackage referencira asset_id + sha256
```

Retry:

```text
isti bytes
→ isti sha256
→ nema duplikata
```

ReviewVersion se ne kreira dok svi asseti nisu READY.

```text
assets READY
↓
POST ReviewPackage
↓
DB transaction
↓
CampaignReview / ReviewVersion / ReviewItems
```

Ako commit padne, nema polovične ReviewVersion.

---

# 16. Minimalni Companion domain

```text
CampaignReview
ReviewVersion
ReviewItem
ReviewLink
ReviewDecision
Comment
PublicationRecord
AssetReference
ReviewEvent
```

## CampaignReview

```text
id
source_campaign_id
name
brand_name
status
created_at
updated_at
current_version_id
```

## ReviewVersion

```text
id
campaign_review_id
version_number
package_id
package_hash
created_at
```

Zaštita:

```text
UNIQUE(campaign_review_id, package_hash)
```

ili ekvivalentna server-side idempotency logika.

## ReviewItem

```text
id
review_version_id
source_content_id
content_revision_id
role
platform
format
caption
scheduled_at
timezone
fact_count
unsupported_claim_count
asset_id
```

---

# 17. Reviewer identity — ispravka v1

`reviewer_identity` ne smije biti jedna nejasna vrijednost.

Review link bez accounta ne dokazuje identitet osobe.

## ReviewLink

```text
id
campaign_review_id
token_hash

invited_email
invited_display_name

expires_at
revoked_at

can_comment
can_approve
created_at
```

`invited_email` znači email kojem je owner namijenio link.

Ne znači da je dokazano ko je kliknuo.

## IdentityLevel

```text
ANONYMOUS_LINK
EMAIL_VERIFIED
AUTHENTICATED_USER
```

MVP može koristiti:

```text
ANONYMOUS_LINK
```

Kasnije email OTP daje:

```text
EMAIL_VERIFIED
```

## ReviewDecision

```text
id
review_item_id
review_version_id
review_link_id

decision

identity_level
invited_email
verified_email

comment
created_at
```

`verified_email` je `NULL` kod anonymous linka.

UI mora razlikovati:

```text
"Odobreno preko review linka namijenjenog ana@firma.com"
```

od:

```text
"Odobrila ana@firma.com — email potvrđen"
```

---

# 18. Comment model

```text
id
review_item_id
review_version_id
review_link_id
identity_level
author_display
body
created_at
```

---

# 19. PublicationRecord

MVP:

```text
PLANNED
MARKED_PUBLISHED
```

Kasnije:

```text
VERIFIED_PUBLISHED
FAILED
```

Polja:

```text
id
review_item_id
status
published_url
marked_at
marked_by_review_link_id
```

`MARKED_PUBLISHED` znači da je čovjek označio objavu kao objavljenu.

Ne znači platform API potvrdu.

---

# 20. ReviewEvent

Desktop ne radi full sync.

Eventi:

```text
COMMENT_ADDED
ITEM_APPROVED
CHANGES_REQUESTED
MARKED_PUBLISHED
NEW_REVIEW_VERSION
```

Endpoint:

```text
GET /api/v1/source-campaigns/{source_campaign_id}/events?after=<cursor>
```

---

# 21. Companion statusi

```text
DRAFT_REVIEW
IN_REVIEW
CHANGES_REQUESTED
APPROVED
PARTIALLY_PUBLISHED
PUBLISHED
ARCHIVED
```

Ne miješati ih automatski sa desktop Campaign statusima.

---

# 22. Reviewer pristup

MVP:

```text
review link
```

Tok:

```text
owner generiše link
↓
reviewer otvara secret URL
↓
server verificira hash
↓
kreira secure review session
↓
redirect na čist URL
```

Cookie:

```text
Secure
HttpOnly
SameSite
```

Secret token ne ostaje u URL-u nakon inicijalnog exchange-a.

---

# 23. Companion frontend — MVP ekrani

## 1. Review landing

Direktan review link otvara trenutnu kampanju.

Eksterni reviewer ne mora imati globalnu listu svih kampanja.

## 2. Kampanja

Prikazuje:

```text
naziv
brand
review version
progress
items
status svakog itema
```

## 3. Pregled objave

Prikazuje:

```text
preview
caption
platformu
format
datum
role
fact-check summary
comments
review status
```

Akcije:

```text
ODOBRI
TRAŽI IZMJENU
DODAJ KOMENTAR
```

## 4. Kalendar

Read-only:

```text
datum
vrijeme
platforma
role
status
```

## 5. Publication tracking

Može biti dio Campaign screen-a:

```text
PLANNED
MARKED_PUBLISHED
published URL
```

---

# 24. Mobile-first UX

Primarni reviewer scenario je telefon.

Minimalni viewport testovi:

```text
360px
390px
768px
desktop
```

Ne koristiti desktop-only `min-width`.

---

# 25. Frontend state

React local state:

```text
modal
selected tab
temporary form state
```

TanStack Query:

```text
review
items
comments
decisions
versions
publication status
```

Bez Redux-a u MVP-u.

---

# 26. API contract

Version:

```text
/api/v1/
```

Pravila:

```text
JSON-safe
string IDs
ISO-8601 datumi
stable error codes
no Python/framework objects
```

---

# 27. API endpointi

## Assets

```text
HEAD /api/v1/assets/{sha256}
POST /api/v1/assets
GET  /api/v1/assets/{asset_id}
```

## Review/version

```text
POST /api/v1/reviews
POST /api/v1/reviews/{review_id}/versions
GET  /api/v1/reviews/{review_id}
GET  /api/v1/reviews/{review_id}/versions
```

## Items

```text
GET /api/v1/reviews/{review_id}/items
GET /api/v1/reviews/{review_id}/items/{item_id}
```

## Comments

```text
POST /api/v1/reviews/{review_id}/items/{item_id}/comments
GET  /api/v1/reviews/{review_id}/items/{item_id}/comments
```

## Decisions

```text
POST /api/v1/reviews/{review_id}/items/{item_id}/approve
POST /api/v1/reviews/{review_id}/items/{item_id}/request-changes
```

## Publication

```text
POST /api/v1/reviews/{review_id}/items/{item_id}/mark-published
```

## Review links

```text
POST   /api/v1/reviews/{review_id}/links
DELETE /api/v1/reviews/{review_id}/links/{link_id}
```

## Desktop event pull

```text
GET /api/v1/source-campaigns/{source_campaign_id}/events?after=<cursor>
```

---

# 28. API client generation

```text
Pydantic
↓
FastAPI OpenAPI
↓
generated TypeScript client
↓
React
```

Ne održavati ručno duplicirane DTO definicije gdje to nije potrebno.

---

# 29. PostgreSQL

Companion source of truth za:

```text
review state
review versions
comments
decisions
review links
publication tracking
event cursor
asset metadata
```

PostgreSQL nije javan:

```text
FastAPI → PostgreSQL
```

---

# 30. Migracije

```text
Alembic
```

Svaka promjena:

```text
schema code
+
migration
+
test
```

---

# 31. Asset storage

MVP:

```text
/var/lib/acs-companion/assets/
```

Iza:

```text
AssetStoragePort
```

Implementacija:

```text
LocalAssetStorage
```

Podržati:

```text
PNG
JPEG
WebP
```

Metadata:

```text
asset_id
sha256
storage_key
mime_type
size
width
height
created_at
```

Kasnije:

```text
AssetStoragePort
→ R2/S3
```

---

# 32. Realtime

MVP:

```text
polling
```

Kasnije:

```text
SSE
```

Ne WebSocket bez stvarne potrebe.

---

# 33. Email

Nije potreban za prvi technical prototype.

Kasnije:

```text
EmailPort
→ Brevo/Postmark adapter
```

Za:

```text
review invitation
new comment
changes requested
approval
OTP
```

---

# 34. Caddy routing

```text
/         → React build
/api/*    → FastAPI
/assets/* → kontrolisani asset pristup
```

Jedan domen:

```text
review.aicampaignstudio.com
```

---

# 35. Docker Compose

```text
deploy/
├── docker-compose.yml
├── Caddyfile
├── .env.example
└── backup/
```

Servisi:

```text
caddy
api
db
```

Volumeni:

```text
postgres_data
companion_assets
caddy_data
caddy_config
```

---

# 36. Backup

Sve je na jednom VPS-u radi jednostavnosti.

Backup nije.

Nightly:

```text
PostgreSQL dump
+
assets
+
restore-critical config
↓
offsite lokacija
```

Restore se periodično testira.

---

# 37. Operativni trošak

Single VPS smanjuje kompleksnost, ali ne uklanja odgovornost.

Održavati:

```text
OS updates
Docker images
PostgreSQL updates
TLS
backup
restore test
security monitoring
disk usage
service uptime
```

Cash cost može biti mali.

Operational responsibility nije nula.

Zato VPS ne uvodimo dok Validation Gate ne opravda stateful Companion.

---

# 38. Security minimum

```text
HTTPS
PostgreSQL nije javno dostupan
review token hash
token expiry
token revocation
secure session cookie
Pydantic validation
asset MIME/size/decode validation
rate limiting
security headers
secret redaction
DB least privilege
offsite backup
```

---

# 39. Logging

Logovati:

```text
request_id
endpoint
status
duration
review_id
event_type
```

Ne logovati:

```text
raw review secret
session cookie
password
API key
full sensitive payload
```

---

# 40. Health

```text
GET /health
GET /ready
```

`/ready` provjerava:

```text
DB
migrations
asset storage
```

---

# 41. Error contract

```json
{
  "ok": false,
  "error_code": "REVIEW_NOT_FOUND",
  "error_message": "..."
}
```

Bez raw tracebacka prema browseru.

---

# 42. Desktop integration

Novi use-case:

```text
PublishCampaignForReview
```

Tok:

```text
CampaignPresentationPackage
↓
BuildReviewPackage
↓
ensure assets
↓
ReviewPublisherPort
↓
Companion
```

Desktop čuva:

```text
review_id
review_url
last_package_hash
last_event_cursor
review_status
```

Ne koristi nejasni `last_published_revision`.

---

# 43. Povratni tok

Desktop povlači:

```text
ReviewEvent[]
```

i prikazuje:

```text
Nova 2 komentara
Objava 3 odobrena
Objava 5 traži izmjenu
Objava 6 označena kao objavljena
```

Nema full bidirectional sync-a.

---

# 44. Publication tracking

MVP:

```text
PLANNED
↓
MARKED_PUBLISHED
+
published_url
```

UI mora pisati:

```text
"Označeno kao objavljeno"
```

Ne:

```text
"Potvrđeno objavljeno"
```

dok nema platform API dokaza.

---

# 45. Performance kasnije

Tek kasnije:

```text
PublicationRecord
↓
DistributionInstance
↓
PerformanceSnapshot
```

Nije MVP.

---

# 46. Novi redoslijed realizacije

## PHASE P0 — završiti stvarni desktop tok

Prije Companion rada mora raditi:

```text
fact-grounded planning
real campaign read path
content generation
stvaran GUI state
real export
real desktop click-through
```

## PHASE P1 — Real Brand/Product Validation

```text
real brand
real campaign
real content
real export
```

Cilj:

```text
dokazati da osnovni ACS proizvod vrijedi
```

## PHASE C-1 — CampaignPresentationPackage

Izvući zajedničku projekciju za:

```text
ZIP
Static Review
future Companion
```

Ovo je jedini Companion-related seam koji ima smisla napraviti rano ako prirodno sjeda uz Export kod.

## PHASE C-0 — Static Review Export

Generisati HTML iz istog `CampaignPresentationPackage`.

Dati ga stvarnom revieweru.

## GATE RV — Reviewer Validation

Pitanje:

```text
da li stvarna osoba traži stateful remote review?
```

Ako NE:

```text
STOP Companion
```

Ako DA:

```text
nastavi C1
```

## PHASE C1 — backend skeleton

```text
FastAPI
PostgreSQL
SQLAlchemy
Alembic
health
```

## PHASE C2 — assets + ReviewPackage upload

Prvo:

```text
content-addressed asset upload
```

zatim:

```text
atomic ReviewPackage commit
```

## PHASE C3 — React frontend

```text
React
TypeScript
Vite
React Router
TanStack Query
responsive ACS Companion design system
```

## PHASE C4 — secure review link

```text
token hash
expiration
revocation
session exchange
```

## PHASE C5 — comments + decisions

```text
COMMENT
APPROVE
REQUEST_CHANGES
```

sa eksplicitnim `IdentityLevel`.

## PHASE C6 — desktop event pull

```text
review events → desktop
```

## PHASE C7 — publication tracking

```text
MARKED_PUBLISHED
published_url
```

## PHASE C8 — calendar

Read-only.

## PHASE C9 — production deployment

Single VPS:

```text
Caddy
React
FastAPI
PostgreSQL
Assets
```

sa offsite backupom.

---

# 47. Gateovi

## G-P1 — Real desktop campaign

Stvarna kampanja od početka do exporta bez fixture-based zaobilaznica.

## G-R1 — Static Review usefulness

Stvarni reviewer otvara static review.

Mora biti jasno šta mu nedostaje.

## G-R2 — Companion justification

Bar jedna stateful potreba je potvrđena:

```text
comments
approval
request changes
version tracking
publication status
```

Bez toga nema Companion C1.

## G-C1 — Review upload proof

Desktop/test client objavi paket i web ga otvara.

## G-C2 — Reviewer proof

Reviewer preko telefona:

```text
otvori link
↓
pregleda
↓
komentariše
↓
odobri
```

## G-C3 — Roundtrip proof

```text
web feedback
↓
server
↓
desktop
```

## G-C4 — Version proof

```text
v1
↓ request changes
v2
↓ approve
```

stare verzije ostaju immutable.

## G-C5 — Idempotency proof

Isti `package_hash` više puta:

```text
1 ReviewVersion
```

Promijenjen package:

```text
nova ReviewVersion
```

## G-C6 — Asset retry proof

Prekinut/retry upload ne pravi duplikate niti polovičnu review verziju.

## G-C7 — Identity semantics proof

Approval preko anonymous linka se ne prikazuje kao email-verified approval.

## G-C8 — Publication proof

```text
PLANNED
→ MARKED_PUBLISHED
```

konzistentno web ↔ desktop.

## G-C9 — Deployment proof

Novi telefon/browser može otvoriti review i odobriti bez desktop instalacije.

---

# 48. Test strategija

## Backend

```text
pytest
```

Testirati:

```text
package hashing
idempotency
asset dedupe
atomic version commit
versioning
comments
approval
identity level
token expiry
token revocation
event cursor
publication status
```

## Frontend

```text
Vitest
React Testing Library
```

Testirati:

```text
mobile states
loading/error/empty
comments
approval
identity labels
version switching
publication labels
```

## E2E

```text
Playwright
```

Glavni scenario:

```text
1. napravi CampaignPresentationPackage
2. izračunaj package_hash
3. uploaduj assets
4. publish ReviewPackage
5. generiši review link
6. otvori mobile viewport
7. komentariši item
8. REQUEST_CHANGES
9. desktop povuče event
10. desktop pošalje izmijenjen paket
11. novi package_hash → ReviewVersion 2
12. reviewer odobri v2
13. identity level je korektan
14. MARKED_PUBLISHED
15. desktop povuče status
```

---

# 49. Šta NE raditi u MVP-u

Ne uvoditi:

```text
full ACS web editor
AI generation na serveru
Campaign Engine na serveru
full SQLite ↔ PostgreSQL sync
multi-device editing core ACS-a
offline sync
Meta/TikTok/LinkedIn direct publishing
OAuth social integrations
WebSockets
Redis
Celery
Kubernetes
microservices
GraphQL
billing
subscription management
full reviewer account system
complex team permission matrix
shared desktop stylesheet reuse
```

---

# 50. Glavni rizici

## R1 — gradimo reviewer za korisnika koji ga nema

Mitigacija:

```text
Static Review + real reviewer gate prije VPS-a
```

## R2 — Companion preraste u drugi ACS

Mitigacija:

```text
creator/reviewer granica
```

## R3 — puni sync

Mitigacija:

```text
CampaignPresentationPackage
ReviewPackage
ReviewEvent
```

## R4 — pogrešna idempotency semantika

Mitigacija:

```text
package_hash
```

## R5 — asset retry ostavi polu-stanje

Mitigacija:

```text
content-addressed upload
+
atomic ReviewVersion commit
```

## R6 — lažni audit identitet

Mitigacija:

```text
IdentityLevel
+
odvojeni invited_email / verified_email
```

## R7 — Companion CSS postane desktop CSS na telefonu

Mitigacija:

```text
reuse tokens
ne reuse layout stylesheet
mobile-first design
```

## R8 — VPS postane nepotreban operativni teret

Mitigacija:

```text
GO gate prije C1
single VPS
bez mikroservisa
```

---

# 51. Trenutni projektni kontekst

Plan ne smije sugerisati da je Companion blizu implementacije samo zato što je arhitektura razrađena.

Prvo mora biti završen stvarni desktop tok:

```text
real read paths
stvaran state u GUI-u
job lifecycle stabilnost
real export
real brand/product validation
```

Plan se zato ne veže trajno za pojedinačne task brojeve, nego za capability gateove.

---

# 52. Mogući razvoj nakon MVP-a

Ako Companion dobije stvarnu upotrebu:

```text
Stage 1
review + comments + approval + tracking

Stage 2
notifications + owner dashboard + performance

Stage 3
small caption edit + schedule adjustment

Stage 4
browser campaign creation
```

Tek Stage 4 počinje stvarnu migraciju creation funkcija na web.

---

# 53. Konačna slika

```text
               ┌──────────────────────────┐
               │       ACS Desktop        │
               │                          │
               │ CREATE                   │
               │ GENERATE                 │
               │ EDIT                     │
               │ VERIFY                   │
               │ RENDER                   │
               └────────────┬─────────────┘
                            │
             CampaignPresentationPackage
                            │
                 ┌──────────┴───────────┐
                 │                      │
                 ▼                      ▼
           ZIP / Static Review     ReviewPackage
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │   ACS Companion     │
                             │   Single VPS        │
                             │                     │
                             │ VIEW                │
                             │ COMMENT             │
                             │ APPROVE             │
                             │ TRACK               │
                             └──────────┬──────────┘
                                        │
                                        ▼
                             Browser / Telefon
                             Klijent / Owner
```

---

# 54. Finalna odluka v2

Tehnička arhitektura Companion-a ostaje:

```text
React + TypeScript + Vite
FastAPI
PostgreSQL
Caddy
Docker Compose
Single VPS
```

ali Companion više nije automatski sljedeća razvojna faza.

Novi redoslijed:

```text
1. završiti stvarni desktop proizvod
2. napraviti CampaignPresentationPackage
3. generisati Static Review Export
4. dati ga stvarnom revieweru
5. dokazati da postoje comments/approval/tracking problemi
6. tek tada graditi Companion
```

Najvažnija promjena:

> **Ne gradimo web Companion da bismo nadoknadili činjenicu da je ACS desktop. Gradimo ga samo ako stvarni review workflow pokaže da udaljeni, stateful review ima stvarnu vrijednost.**

Ako taj dokaz dobijemo, ovaj plan definiše kako Companion treba biti izgrađen bez full sync-a, bez prerane web migracije i bez nepotrebne infrastrukture.
