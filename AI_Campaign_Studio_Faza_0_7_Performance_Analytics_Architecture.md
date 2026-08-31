# AI Campaign Studio — Faza 0.7
## Performance & Analytics Ready Architecture

**Status:** nova aktuelna arhitektonska dopuna Faze 0  
**Supersedes:** `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md` samo u dijelu gdje uvodi novu Performance/Analytics arhitektonsku odluku; sve ostale odluke iz 0.6 ostaju važeće  
**Cilj:** omogućiti kasniji Performance/Analytics modul bez velikog refaktora Campaign Engine-a, Content modela, exporta ili platformskog sistema  
**Važno:** Analytics nije dio prvog MVP vertical slice-a

---

# 1. Glavna odluka

AI Campaign Studio ostaje:

```text
Brand Intelligence
        ↓
Campaign Brief
        ↓
Campaign Plan
        ↓
Content
        ↓
Approve / Export
```

Ali arhitektura se sada zaključava tako da kasnije može postati:

```text
Brand Intelligence
        ↓
Campaign Brief
        ↓
Campaign Plan
        ↓
Content
        ↓
Approve / Export / Publish
        ↓
Distribution Instance
        ↓
Performance Data
        ↓
Analytics / Learning
        ↓
Next Campaign
```

Performance/Analytics je zaseban modul.

Ne smije se ugrađivati direktno u:

```text
Brand Intelligence
Campaign Engine
ContentPiece generator
AI provider adapter
renderer
```

---

# 2. Zašto ovo uvodimo sada, ali ne implementiramo odmah

Ako bismo Performance dodali tek kada aplikacija već ima desetine kampanja i export formata, mogli bismo otkriti da:

- ne znamo koji tačno `ContentPiece` je objavljen;
- ne znamo koja revizija sadržaja je objavljena;
- isti sadržaj je korišten na više platformi;
- jedan ContentPiece je eksportovan više puta;
- nema stabilne veze između objave i metrike;
- CSV/API podaci se ne mogu pouzdano mapirati nazad na kampanju.

Zato sada zaključavamo samo potrebne identitete i granice.

Ne pravimo još:

```text
Analytics dashboard
Meta/TikTok/LinkedIn API integracije
Performance DB tabele
AI performance recommendations
publishing scheduler
```

---

# 3. Ključna nova domena: Distribution Instance

Metrika ne pripada apstraktnom CampaignPlan itemu.

Metrika pripada konkretnoj distribuciji sadržaja.

Zato se uvodi budući koncept:

```text
DistributionInstance
```

On predstavlja:

> konkretan sadržaj, u konkretnoj verziji, poslat/objavljen na konkretnom kanalu/platformi/formatu.

Predloženi model:

```text
DistributionInstance
- id
- campaign_id
- campaign_item_id
- content_piece_id
- content_revision_id
- channel_code
- platform_code
- format_code
- external_account_id?
- external_content_id?
- published_at?
- distribution_source
- created_at
```

`distribution_source` može biti:

```text
EXPORT
MANUAL
CSV_IMPORT
API
```

U prvom MVP-u `DistributionInstance` se još ne mora persistirati.

Ali svi ID-evi koji mu trebaju moraju postojati stabilno.

---

# 4. Kritično pravilo: metrike se vežu za tačnu reviziju sadržaja

Nije dovoljno:

```text
PerformanceSnapshot → ContentPiece
```

Treba:

```text
PerformanceSnapshot
        ↓
DistributionInstance
        ↓
ContentPiece + content_revision_id
```

Razlog:

Ako korisnik nakon objave promijeni caption, ne smijemo pripisati stare rezultate novoj verziji sadržaja.

Zato:

```text
ContentRevision
```

mora imati stabilan ID ili version identifier koji se može zapisati u export/distribution record.

---

# 5. PerformanceSnapshot

Budući canonical model:

```text
PerformanceSnapshot
- id
- distribution_instance_id
- period_start
- period_end
- observed_at
- source
- source_batch_id?
- reach?
- impressions?
- engagements?
- clicks?
- conversions?
- spend?
- revenue?
- video_views?
- watch_time_seconds?
- raw_metrics
```

Sva polja osim identiteta i perioda mogu biti `null`.

Razlog:

ne podržavaju sve platforme iste metrike.

---

# 6. Canonical vs platform-specific metrike

Ne praviti jedan ogroman enum svih mogućih platformskih metrika.

Koristiti dva sloja:

```text
COMMON CANONICAL METRICS
+
RAW PLATFORM METRICS
```

Canonical:

```text
reach
impressions
engagements
clicks
conversions
spend
revenue
video_views
watch_time_seconds
```

Platform-specific:

```text
raw_metrics: dict[str, number|string|boolean|null]
```

Primjeri:

```text
Instagram saves
TikTok average_watch_time
YouTube returning_viewers
LinkedIn follows_from_post
```

ostaju u `raw_metrics` dok ne postoji dokaz da zaslužuju canonical polje.

---

# 7. Izvedene metrike se NE unose ručno

CTR, CPC, CPM, CPA, ROAS i Conversion Rate se računaju deterministički.

Primjeri:

```text
CTR = clicks / impressions
CPC = spend / clicks
CPM = spend / impressions * 1000
CPA = spend / conversions
ROAS = revenue / spend
Conversion Rate = conversions / clicks
```

Pravila:

- divide-by-zero mora dati `null`, ne crash i ne infinity;
- formula mora biti centralizovana;
- AI ne računa ove metrike;
- AI može samo interpretirati već izračunate rezultate.

---

# 8. Campaign Goal → KPI mapping

Aplikacija treba razlikovati cilj kampanje od metrike.

Primjer:

```text
AWARENESS
Primary:
- reach
- impressions

TRAFFIC
Primary:
- clicks
- CTR
- CPC

LEADS
Primary:
- conversions
- conversion_rate
- CPA

SALES
Primary:
- conversions
- revenue
- ROAS
- CPA

VIDEO_ENGAGEMENT
Primary:
- video_views
- watch_time
- completion_rate
```

Ovo kasnije ide kroz:

```text
KpiProfile
```

ali ne treba ga implementirati u prvom MVP-u.

---

# 9. Analytics nije Brand Intelligence

Performance podaci NE ulaze direktno u `ApprovedFact`.

Primjer:

```text
"Naša dostava traje 24h"
```

može biti Brand Fact.

Ali:

```text
"Offer post je imao 4.8% CTR"
```

je Performance Evidence.

To su dvije različite vrste znanja.

Ispravna buduća struktura:

```text
Brand Intelligence
        +
Campaign Performance
        ↓
Campaign Learning / Insights
        ↓
Next Campaign Planning
```

---

# 10. Campaign Learning sloj

Kasnije se može uvesti:

```text
CampaignLearningProfile
```

koji sadrži izvedene, provjerljive uvide:

```text
- education posts avg CTR
- offer posts conversion rate
- best platform by objective
- best format by objective
- best performing audience segment
- average performance by content role
```

Ovaj sloj NE smije biti sirovi LLM zaključak.

Prvo:

```text
deterministička agregacija
```

zatim:

```text
AI interpretation
```

---

# 11. PerformanceSourcePort

Direktne integracije kasnije idu iza porta:

```text
PerformanceSourcePort
```

Primjer:

```text
fetch_performance(distribution_ref, period) -> PerformanceImportBatch
```

Adapteri kasnije:

```text
MetaPerformanceAdapter
TikTokPerformanceAdapter
LinkedInPerformanceAdapter
YouTubePerformanceAdapter
GoogleAdsPerformanceAdapter
CsvPerformanceAdapter
ManualPerformanceAdapter
```

Campaign Engine nikad ne importuje ove adaptere.

---

# 12. Prvi Performance input ne treba biti API

Prvi pravi analytics release treba koristiti:

```text
CSV / Excel import
+
ručni unos
```

Razlog:

- ne zavisi od OAuth/provider API pravila;
- brzo testira da li korisnik uopšte koristi analytics;
- omogućava test sa realnim kampanjama;
- definisanje mapping modela je korisno i kasnijim API adapterima;
- izbjegava prerani vendor complexity.

---

# 13. Metric Import Batch

Budući model:

```text
PerformanceImportBatch
- id
- source
- imported_at
- source_file_name?
- platform_code?
- row_count
- matched_count
- unmatched_count
- mapping_version
- raw_source_snapshot_ref?
```

Svaki import mora biti provjerljiv.

Ne raditi silent matching bez evidence.

---

# 14. Matching između importovanih podataka i sadržaja

Prioritet:

```text
1. external_content_id
2. exported analytics_match_key
3. campaign/content/distribution stable IDs
4. manual user confirmation
```

Nikad:

```text
LLM semantic guess
```

kao primarni automatski matching.

---

# 15. Export manifest — obavezna priprema u Faza 1

Svaki export paket treba dobiti machine-readable manifest.

Primjer:

```json
{
  "campaign_id": "cmp_...",
  "campaign_plan_id": "plan_...",
  "items": [
    {
      "campaign_item_id": "item_...",
      "content_piece_id": "content_...",
      "content_revision_id": "rev_...",
      "channel_code": "SOCIAL",
      "platform_code": "INSTAGRAM",
      "format_code": "FEED_POST",
      "analytics_match_key": "..."
    }
  ]
}
```

Ovo je mala promjena sada, ali kasnije uklanja veliki matching/refactor problem.

---

# 16. Analytics match key

Predloženi ključ:

```text
analytics_match_key
```

Mora biti:

- stabilan za konkretan exported content revision + target;
- ne sadrži lične podatke;
- može se staviti u manifest/file metadata;
- nije user-facing poslovni ID.

Može biti izveden iz:

```text
content_piece_id
content_revision_id
platform_code
format_code
```

ali canonical oblik se zaključava tek u implementaciji.

---

# 17. Gdje Analytics ulazi u UI kasnije

Budući ekran:

```text
Analytics
├── Overview
├── Campaigns
├── Content
├── Platforms
└── Goals
```

Campaign detail:

```text
Plan
Content
Performance
Learnings
```

Content detail:

```text
Content
Facts Used
Revision
Distribution
Performance
```

Ne implementirati ove ekrane u prvom UI production adapteru.

---

# 18. Tačan trenutak implementacije

## Sada — architecture only

Odmah zaključati:

```text
DistributionInstance koncept
PerformanceSnapshot koncept
PerformanceSourcePort seam
stable IDs
content revision identity
Channel/Platform/Format identity
export manifest identity
analytics_match_key seam
```

Bez analytics DB/UI/API implementacije.

---

## Faza 1 — Campaign Engine proof

Tokom prve business implementacije osigurati da postoje:

```text
campaign_id
campaign_plan_id
campaign_item_id
content_piece_id
content_revision_id
target channel/platform/format
export manifest
analytics_match_key
```

To je jedina Analytics implementacija koja je obavezna prije MVP proof-a.

---

## Slice 1.5 — Performance Foundation

**Implementirati odmah nakon što G10 Full Vertical Slice prođe i Campaign Engine proof bude prihvaćen.**

To znači:

```text
Campaign generation
→ fact validation
→ render
→ approval
→ export
→ PASS
```

pa tek onda:

```text
Performance Foundation
```

Prije:

```text
Website Ingestion / Brand crawling
```

Zašto?

Jer tada već postoji stvaran ContentPiece + Export model koji možemo mjeriti, a još nismo proširili sistem velikim ingestion slojem.

To je najjeftinija tačka za uvođenje Performance domena.

---

# 19. Slice 1.5 scope

Implementirati:

```text
DistributionInstance
PerformanceSnapshot
PerformanceImportBatch
Metric calculator
CSV import
manual mapping
manual correction
basic Analytics read model
Campaign Performance screen
Content Performance screen
```

Ne implementirati:

```text
Meta API
TikTok API
LinkedIn API
Google Ads API
auto publishing
AI recommendations
```

---

# 20. Slice 1.5 acceptance

Minimalni dokaz:

1. korisnik eksportuje kampanju;
2. export manifest sadrži stabilne IDs;
3. korisnik importuje CSV performance podatke;
4. aplikacija mapira redove na DistributionInstance;
5. unmatched redovi se ne gube;
6. korisnik može ručno potvrditi mapping;
7. canonical metrics se čuvaju;
8. CTR/CPC/CPM/CPA/ROAS se računaju deterministički;
9. Campaign Performance prikazuje agregate;
10. Content Performance prikazuje pojedinačni rezultat;
11. nema AI interpretacije u računskim rezultatima.

---

# 21. Kada dodati direct API integracije

Tek poslije Slice 1.5 i nekoliko realnih kampanja.

Preporučeni trigger:

```text
najmanje 5–10 stvarnih performance importova
```

i potvrda da:

- korisnik zaista koristi analytics;
- platforma je često korištena;
- ručni/CSV import stvara stvaran trošak;
- API pristup je održiv.

Tada prvo implementirati jednu platformu.

Ne sve odjednom.

---

# 22. Kada dodati AI performance analysis

Tek kada postoji:

```text
dovoljno history data
+
deterministički agregati
+
jasni sample-size pragovi
```

AI smije reći:

```text
"Education objave su u posljednjih 8 objava imale viši prosječni CTR."
```

samo ako underlying data postoji.

AI ne smije iz jednog posta zaključiti:

```text
"Education content uvijek radi bolje."
```

bez dovoljnog uzorka.

---

# 23. Anti-refactor pravila

Od sada ne praviti model u kojem:

```text
metrics → CampaignItem direktno
```

bez DistributionInstance.

Ne vezivati metrics za:

```text
filename
post order number
headline text
caption text
```

kao canonical identitet.

Ne pretpostaviti:

```text
1 ContentPiece = 1 publication
```

Ne pretpostaviti:

```text
1 platform = 1 metric schema
```

Ne čuvati samo derived percentages bez raw numerators/denominators.

---

# 24. Konačna odluka

Performance/Analytics je dio planirane arhitekture OD SADA.

Ali njegova stvarna funkcionalna implementacija ide:

```text
P0
→ Faza 1 Campaign Engine proof
→ G10 PASS
→ Slice 1.5 Performance Foundation
→ Slice 2 Brand Ingestion
→ kasnije API performance integrations
→ kasnije AI learning/recommendations
```

Ovo daje dovoljno ranu arhitektonsku pripremu bez pretvaranja prvog MVP-a u analytics projekat.
