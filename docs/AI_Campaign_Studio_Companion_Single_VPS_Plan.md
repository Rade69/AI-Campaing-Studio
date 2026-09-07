---
title: "AI Campaign Studio — plan izgradnje ACS Companion web dijela na jednom VPS-u"
document_type: "Implementation roadmap / architecture plan"
project: "AI Campaign Studio"
scope: "Desktop ACS + zaseban ACS Companion za pregled, odobravanje, komentare i praćenje statusa kampanja"
deployment_model: "Single VPS"
frontend: "React + TypeScript + Vite"
backend: "FastAPI"
database: "PostgreSQL"
reverse_proxy: "Caddy"
status: "Plan za buduću realizaciju — ne ulazi automatski u trenutni GUI-008/GUI-009 scope"
version: "1.0"
date: "2026-09-07"
---

# AI Campaign Studio — detaljan plan ACS Companion web dijela na jednom VPS-u

## 1. Cilj

Napraviti mali web dio uz postojeći desktop AI Campaign Studio.

Desktop aplikacija ostaje glavni alat za:

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

Web Companion ne kopira cijeli ACS. Njegov posao je:

```text
VIEW
REVIEW
APPROVE
COMMENT
TRACK
```

odnosno pregled kampanja, pregled objava, komentari, odobravanje, zahtjev za izmjenu, kalendar i praćenje statusa objave.

## 2. Osnovni princip

Ne pravimo:

```text
Desktop ACS ⇄ kompletna server baza
```

Ne pravimo puni sync SQLite ↔ PostgreSQL.

Umjesto toga:

```text
ACS Desktop
    ↓
ReviewPackage
    ↓ HTTPS
ACS Companion
    ↓
Browser / telefon / tablet
```

Desktop ostaje **source of truth za kreiranje sadržaja**.

Companion je **source of truth za review proces**.

## 3. Zašto ovako

Ovaj model rješava konkretan nedostatak desktop aplikacije:

- kampanju može pregledati neko ko nema ACS instaliran;
- klijent ili vlasnik firme može odobriti sadržaj preko browsera;
- kampanja se može pratiti sa telefona;
- objave mogu imati status;
- komentari se mogu vratiti u desktop;
- ne moramo odmah praviti punu web verziju.

## 4. Ciljna arhitektura

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

Sve internet komponente su na jednom VPS-u:

```text
Ubuntu VPS
├── Caddy
├── React/Vite build
├── FastAPI
├── PostgreSQL
├── lokalni asset storage
└── backup agent
```

Jedino backup ide van VPS-a.


# 5. Tehnološki stack

## T1 — Frontend

```text
React
TypeScript
Vite
React Router
TanStack Query
Radix primitives
ACS design tokens
```

React/TypeScript daju dobar temelj za više ekrana, review state, comments, approvals, versions i responsive mobile UI.

Vite služi za razvoj i build. Produkcijski rezultat je:

```text
dist/
├── index.html
└── assets/
```

Caddy servira te fajlove direktno.

## T2 — Backend

```text
FastAPI
Pydantic
SQLAlchemy 2.x
Alembic
PostgreSQL
```

FastAPI je tanak HTTP adapter. Ne smije sadržavati Campaign Engine.

Companion backend ima svoj mali review domain.

## T3 — Reverse proxy / HTTPS

```text
Caddy
```

Radi TLS, HTTPS, serviranje React builda i proxy `/api/*` prema FastAPI.

## T4 — Deployment

```text
Docker Compose
```

Predloženi servisi:

```text
caddy
api
db
```

Ne koristiti Kubernetes.

# 6. Granica desktop ACS ↔ Companion

Desktop ne šalje cijelu bazu. Dobija poseban application port:

```text
ReviewPublisherPort
```

Implementacija:

```text
HttpReviewPublisher
```

Tok:

```text
Campaign
↓
CreateReviewPackage
↓
ReviewPublisherPort
↓
HttpReviewPublisher
↓
Companion API
```

# 7. ReviewPackage

`ReviewPackage` je snapshot kampanje za pregled.

Predloženi sadržaj:

```text
source_campaign_id
source_campaign_revision
campaign_name
brand_name
campaign_status
review_version
created_at

items[]
    source_content_id
    content_revision
    campaign_role
    platform
    format
    caption
    scheduled_at
    timezone
    fact_check_summary
    preview_asset
```

Ne uključivati podatke koji nisu potrebni za review.

# 8. Immutable review verzije

Svaki upload pravi novu verziju:

```text
ReviewVersion 1
ReviewVersion 2
ReviewVersion 3
```

Stare verzije se ne prepisuju.

Primjer:

```text
Klijent pregleda v1
↓
REQUEST_CHANGES
↓
desktop mijenja sadržaj
↓
desktop šalje v2
↓
isti review link prikazuje v2 kao trenutnu
```

# 9. Minimalni Companion domain model

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
source_campaign_revision
package_hash
created_at
```

## ReviewItem

```text
id
review_version_id
source_content_id
content_revision
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

## ReviewDecision

```text
id
review_item_id
review_version_id
reviewer_identity
decision
comment
created_at
```

Decision:

```text
APPROVED
REQUEST_CHANGES
```

## Comment

```text
id
review_item_id
review_version_id
author
body
created_at
```

## PublicationRecord

```text
id
review_item_id
status
published_url
marked_at
marked_by
```

Statusi za MVP:

```text
PLANNED
MARKED_PUBLISHED
```

Kasnije eventualno:

```text
VERIFIED_PUBLISHED
FAILED
```

## ReviewEvent

Desktop koristi event stream umjesto full sync-a.

Event types:

```text
COMMENT_ADDED
ITEM_APPROVED
CHANGES_REQUESTED
MARKED_PUBLISHED
NEW_REVIEW_VERSION
```

Desktop poziv:

```text
GET /api/v1/reviews/{source_campaign_id}/events?after=<cursor>
```


# 10. Companion statusi

Predloženi statusi:

```text
DRAFT_REVIEW
IN_REVIEW
CHANGES_REQUESTED
APPROVED
PARTIALLY_PUBLISHED
PUBLISHED
ARCHIVED
```

Ne miješati ih sa core Campaign statusima ako nisu semantički isti.

# 11. Reviewer pristup

MVP ne zahtijeva account.

Tok:

```text
owner generiše review link
↓
klijent otvara link
↓
server verificira token
↓
kreira secure review session
↓
redirect na čist URL
```

## ReviewLink

```text
id
campaign_review_id
token_hash
reviewer_email
expires_at
revoked_at
can_comment
can_approve
created_at
```

Originalni token se ne čuva u bazi.

Session cookie:

```text
Secure
HttpOnly
SameSite
```

Auth token ne čuvati u `localStorage`.

# 12. Companion frontend — MVP ekrani

## Screen 1 — Kampanje

Prikazuje:

```text
naziv kampanje
brand
status
broj objava
koliko odobreno
koliko traži izmjenu
koliko objavljeno
```

## Screen 2 — Kampanja

Prikazuje sve stavke kampanje.

Primjer:

```text
Instagram · Problem
08.09.2026 10:00
APPROVED

LinkedIn · Edukacija
09.09.2026 09:30
WAITING REVIEW

Facebook · Offer
10.09.2026 18:00
REQUEST_CHANGES
```

## Screen 3 — Kalendar

Read-only ili skoro read-only.

Prikazuje:

```text
datum
vrijeme
platformu
campaign role
status
```

Bez drag/drop u prvoj verziji.

## Screen 4 — Pregled objave

Prikazuje:

```text
preview sliku
caption
platformu
format
datum
campaign role
fact-check summary
komentare
review status
```

Akcije:

```text
ODOBRI
TRAŽI IZMJENU
DODAJ KOMENTAR
OZNAČI KAO OBJAVLJENO
```

# 13. Responsive UX

Companion mora biti usable na desktopu, tabletu i telefonu.

Prioritet:

```text
mobile review
```

jer je realan scenario da klijent otvori link na telefonu.

# 14. Frontend state

React local state za modal, selected tab i temporary UI state.

TanStack Query za:

```text
campaign data
review items
comments
approvals
publication status
versions
```

Ne uvoditi Redux u MVP.

# 15. API contract

API verzionisati:

```text
/api/v1/
```

Svi response objekti moraju biti JSON-safe.

ID:

```text
string
```

Datumi:

```text
ISO-8601
```


# 16. Predloženi API endpointi

## Campaign review

```text
POST /api/v1/reviews
GET  /api/v1/reviews
GET  /api/v1/reviews/{review_id}
```

## Versions

```text
POST /api/v1/reviews/{review_id}/versions
GET  /api/v1/reviews/{review_id}/versions
GET  /api/v1/reviews/{review_id}/versions/{version_id}
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

## Publication status

```text
POST /api/v1/reviews/{review_id}/items/{item_id}/mark-published
```

Body:

```json
{
  "published_url": "https://..."
}
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

# 17. Idempotency

Ako mreža pukne nakon što server primi paket, retry ne smije napraviti duplikat.

Koristiti:

```text
Idempotency-Key
```

i/ili DB constraint:

```text
UNIQUE(source_campaign_id, source_campaign_revision)
```

# 18. API client generation

Tok:

```text
Pydantic models
↓
FastAPI OpenAPI
↓
generated TypeScript client
↓
React frontend
```

Time frontend i backend contracts ostaju usklađeni.

# 19. PostgreSQL

PostgreSQL je source of truth za Companion.

Ne izlagati ga internetu.

Samo:

```text
FastAPI → PostgreSQL
```

preko Docker networka ili localhost-a.

# 20. Migracije

Koristiti Alembic.

Svaka schema promjena:

```text
code
+
migration
+
test
```

Bez ručnih izmjena produkcijske baze.

# 21. Asset storage

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

Dozvoljeni formati za MVP:

```text
PNG
JPEG
WebP
```

Po mogućnosti samo formati koje ACS renderer generiše.

Asset metadata u PostgreSQL-u:

```text
asset_id
storage_key
mime_type
size
sha256
created_at
```

Kasnije:

```text
AssetStoragePort
↓
R2AssetStorage / S3AssetStorage
```

bez promjene business logike.


# 22. Realtime

MVP ne treba WebSocket.

Prva verzija može raditi polling.

Kasnije SSE za:

```text
nov komentar
nova review verzija
promjena statusa
```

# 23. Email notifikacije

Nisu obavezne za prvi prototype.

Kasnije:

```text
EmailPort
↓
Brevo/Postmark adapter
```

Eventi:

```text
review invitation
new comment
changes requested
approval
```

# 24. Caddy routing

```text
/         → React build
/api/*    → FastAPI
/assets/* → protected/static asset route
```

Jedan domen znači i manje CORS komplikacija.

Predloženi host:

```text
review.aicampaignstudio.com
```

API:

```text
review.aicampaignstudio.com/api/v1/
```

# 25. Docker Compose

Predložena struktura:

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

# 26. Backup

Jedina stvar koja ne smije ostati samo na istom VPS-u.

Backup obuhvata:

```text
PostgreSQL dump
assets
config potreban za restore
```

Tok:

```text
nightly backup
↓
druga lokacija
```

Backup nije potvrđen dok restore nije testiran.

Minimalni restore test:

```text
fresh temp environment
↓
restore DB
↓
restore assets
↓
health check
↓
sample review opens
```


# 27. Security minimum

## S1 — HTTPS obavezno

Samo HTTPS.

## S2 — PostgreSQL nije javan

Port 5432 ne izlagati internetu.

## S3 — Review token

Dug slučajan token, u bazi samo hash.

## S4 — Input validation

FastAPI/Pydantic validacija svakog requesta.

## S5 — File validation

Provjeriti:

```text
allowed MIME
extension
size
image decode
```

## S6 — Rate limiting

Posebno za review token, comments i approve endpoints.

## S7 — Security headers

Caddy:

```text
HSTS
X-Content-Type-Options
Referrer-Policy
Content-Security-Policy
```

## S8 — Secret handling

U `.env`:

```text
DB password
session secret
email provider secret
```

Nikada u Git.

# 28. Logging

Server loguje:

```text
request_id
endpoint
status
duration
review_id
event type
```

Ne logovati review token, session cookie, password, API key ili full sensitive payload.

# 29. Health endpoints

```text
GET /health
GET /ready
```

`/ready` provjerava:

```text
DB reachable
migrations current
asset storage reachable
```

# 30. Error model

Standardno:

```json
{
  "ok": false,
  "error_code": "REVIEW_NOT_FOUND",
  "error_message": "..."
}
```

Ne vraćati raw traceback klijentu.

# 31. Desktop integration

Desktop dobija novi application use case:

```text
PublishCampaignForReview
```

Tok:

```text
Campaign
↓
BuildReviewPackage
↓
ReviewPublisherPort
↓
Companion
```

Desktop čuva samo review metadata:

```text
review_id
review_url
last_published_revision
last_event_cursor
review_status
```

Ne praviti full bidirectional DB sync.

# 32. Povratne informacije u desktop

Desktop povlači:

```text
ReviewEvent[]
```

i prikazuje:

```text
Nova 2 komentara
Objava 3 odobrena
Objava 5 traži izmjenu
```

# 33. Publication status

MVP ne pokušava automatski potvrditi da je objava stvarno online.

Korisnik može:

```text
OZNAČITI KAO OBJAVLJENO
+
zalijepiti URL
```

Status je:

```text
MARKED_PUBLISHED
```

Ne `VERIFIED_PUBLISHED` dok ne postoji platform API dokaz.

# 34. Performance kasnije

Kada Performance modul bude spreman:

```text
PublicationRecord
↓
DistributionInstance
↓
PerformanceSnapshot
```

Companion može prikazivati metrics, ali to nije MVP.


# 35. Faze realizacije

## PHASE C0 — priprema

Ne raditi prije nego GUI-008/GUI-009 i real desktop click-through budu stabilni.

### A1
Definisati `ReviewPackage` contract.

### A2
Definisati `ReviewPublisherPort`.

### A3
Definisati Companion minimalni domain.

### A4
Napisati ADR:

```text
Desktop source of truth for creation
Companion source of truth for review
No full DB sync
```

## PHASE C1 — backend skeleton

Napraviti:

```text
FastAPI
PostgreSQL
SQLAlchemy
Alembic
health endpoints
```

Bez UI-a.

Acceptance:

- DB migracije rade;
- API startuje;
- `/health` PASS;
- `/ready` PASS;
- basic create/read review API radi.

## PHASE C2 — ReviewPackage upload

Desktop ili test client šalje `ReviewPackage`.

Server kreira:

```text
CampaignReview
ReviewVersion
ReviewItems
Assets
```

Acceptance:

- idempotent retry;
- duplicate revision se ne pravi;
- invalid package se odbija;
- assets validirani.

## PHASE C3 — React frontend skeleton

Napraviti:

```text
React
TypeScript
Vite
React Router
TanStack Query
ACS design system
```

Screenovi:

```text
Campaign list
Campaign detail
Review item
```

Acceptance:

- responsive;
- mobile usable;
- typed API client radi;
- loading/error/empty states postoje.

## PHASE C4 — review link

Dodati:

```text
ReviewLink
secure token
session cookie
expiration
revocation
```

Acceptance:

- valid link otvara review;
- invalid/expired/revoked link odbijen;
- token nestaje iz URL-a nakon session creation.

## PHASE C5 — comments + decisions

Dodati:

```text
COMMENT
APPROVE
REQUEST_CHANGES
```

Acceptance:

- reviewer može komentarisati;
- odluka je vezana za tačnu review verziju;
- stara verzija se ne prepisuje;
- audit zapis postoji.

## PHASE C6 — desktop event pull

Desktop može povući review događaje.

Acceptance:

- komentar sa weba vidi se u desktopu;
- APPROVED vidi se u desktopu;
- REQUEST_CHANGES vidi se u desktopu;
- cursor sprečava duplikate.

## PHASE C7 — publication tracking

Dodati:

```text
MARKED_PUBLISHED
published_url
```

Acceptance:

- status vidljiv u webu;
- status vidljiv u desktopu;
- URL validiran;
- jasno označeno da je ručno markirano.

## PHASE C8 — calendar

Dodati Companion read-only calendar.

Acceptance:

- svi scheduled items vidljivi;
- timezone korektno prikazan;
- filter po platformi/statusu.

## PHASE C9 — deployment

Jedan VPS:

```text
Caddy
React
FastAPI
PostgreSQL
Assets
```

Acceptance:

- HTTPS;
- DB nije javno dostupna;
- backup radi;
- restore test dokumentovan;
- server reboot vraća servis automatski.


# 36. Gateovi

## G-C1 — Review upload proof

Desktop/test client objavi kampanju.

Web je može otvoriti.

## G-C2 — Reviewer proof

Reviewer preko telefona:

```text
otvori link
↓
pregleda post
↓
komentariše
↓
odobri
```

## G-C3 — Feedback roundtrip proof

```text
web komentar
↓
server
↓
desktop
```

radi bez ručnog kopiranja.

## G-C4 — Version proof

```text
v1
↓ request changes
v2
↓ approve
```

stare verzije ostaju dostupne.

## G-C5 — Publication tracking proof

Jedna objava ima:

```text
PLANNED
↓
MARKED_PUBLISHED
+
URL
```

i status je konzistentan web ↔ desktop.

## G-C6 — Deployment proof

Sa potpuno novog telefona/browsera:

```text
review link
↓
HTTPS
↓
review
↓
approve
```

bez lokalnog ACS-a.

# 37. Test strategija

## Backend

```text
pytest
```

Testirati:

- ReviewPackage validation;
- idempotency;
- versioning;
- comments;
- approvals;
- token expiry;
- revocation;
- event cursor;
- publication status.

## Frontend

```text
Vitest
React Testing Library
```

Testirati screen states, review status, button permissions, comment submit i version switching.

## E2E

```text
Playwright
```

Glavni E2E scenario:

```text
1. kreiraj review package
2. objavi na API
3. generiši review link
4. otvori link kao reviewer
5. vidi 6 items
6. komentariši item 2
7. REQUEST_CHANGES
8. objavi v2
9. reviewer vidi v2
10. APPROVE
11. MARKED_PUBLISHED
12. desktop povuče događaje
```

# 38. Šta NE raditi u MVP-u

Ne uvoditi:

```text
full ACS web editor
AI generation na serveru
Campaign Engine na serveru
full SQLite ↔ PostgreSQL sync
multi-device editing ACS-a
offline sync
Meta/TikTok/LinkedIn publishing APIs
OAuth social integrations
WebSockets
Redis
Celery
Kubernetes
microservices
GraphQL
billing
subscription management
full user account system
team permission matrix
```

# 39. Kasniji mogući razvoj

Ako Companion potvrdi vrijednost:

```text
Stage 1
review + approval + comments + tracking

Stage 2
performance + basic owner dashboard + notifications

Stage 3
small edits + caption adjustment + schedule adjustment

Stage 4
browser campaign creation
```

Tek Stage 4 je pravi početak web evolucije cijelog ACS-a.

# 40. Glavni rizici

## R1 — Companion preraste u drugi ACS prerano
Mitigacija: zaključan MVP scope.

## R2 — Krene full sync
Mitigacija: ReviewPackage projection model.

## R3 — Review link sigurnost
Mitigacija: token hash + expiry + revocation + secure session cookie.

## R4 — Asset storage ostane bez backup-a
Mitigacija: nightly offsite backup.

## R5 — Desktop i web statusi se raziđu
Mitigacija: event model + cursor + explicit ownership of state.

## R6 — Web postane DevOps projekat
Mitigacija: jedan VPS, Docker Compose, Caddy, PostgreSQL, bez mikroservisa.

# 41. Redoslijed u odnosu na trenutni ACS

```text
SADA
GUI-008 stabilizacija
↓
GUI-009
↓
real desktop vertical slice
↓
Real Brand/Product Validation

AKO proizvod pokazuje vrijednost
↓
Companion C0
↓
C1-C3 technical proof
↓
C4-C6 review workflow
↓
C7-C9 production-ready MVP
```

Companion ne smije usporiti dokazivanje osnovne vrijednosti Campaign Enginea.

# 42. Konačna slika proizvoda

```text
               ┌─────────────────────┐
               │    ACS Desktop      │
               │                     │
               │ CREATE              │
               │ GENERATE            │
               │ EDIT                │
               │ VERIFY              │
               │ RENDER              │
               └──────────┬──────────┘
                          │
                    ReviewPackage
                          │
                          ▼
               ┌─────────────────────┐
               │   ACS Companion     │
               │   single VPS        │
               │                     │
               │ VIEW                │
               │ COMMENT             │
               │ APPROVE             │
               │ TRACK               │
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │ Browser / Telefon   │
               │ Klijent / Owner     │
               └─────────────────────┘
```

# 43. Najvažnija odluka

Ne pravimo dvije pune aplikacije.

Pravimo:

```text
ACS Desktop = creator
ACS Companion = reviewer / tracker
```

Companion dobija samo onoliko funkcija koliko je potrebno da riješi udaljeni pregled i praćenje.

To zadržava desktop razvoj jednostavnim, a ipak daje ACS-u web prisustvo i pristup sa bilo kog uređaja bez prerane migracije cijelog proizvoda na web.
