# AI Campaign Studio — Faza 1 v1.5
## Analytics-Ready Implementation Plan

**Status:** dopuna Faze 1 v1.4  
**Arhitektonska osnova:** Faza 0.7 Performance & Analytics Ready Architecture  
**Cilj:** implementirati minimalne seam-ove sada da kasniji Performance modul ne zahtijeva refaktor Campaign/Content/Export jezgra

---

# 1. Šta se mijenja u Fazi 1

Faza 1 i dalje NE implementira Analytics modul.

Mora samo garantovati:

```text
stable campaign/content IDs
revision identity
target identity
export manifest
analytics match identity
```

---

# 2. Domain obavezne identifikacije

Kada se implementiraju business modeli, mora postojati:

```text
Campaign.id
CampaignPlan.id
CampaignItem.id
ContentPiece.id
Revision.id
```

Ako je revision model generički:

```text
Revision.id
entity_type
entity_id
version
```

ContentPiece mora moći pokazati na tačnu aktuelnu reviziju.

---

# 3. CampaignItem target mora ostati eksplicitan

Obavezno:

```text
CampaignItem
- channel_code
- platform_code
- format_code
```

Ne oslanjati se na payload da se naknadno pogađa platforma.

---

# 4. RenderArtifact / ExportArtifact identity

Svaki render/export artifact mora biti vezan za:

```text
content_piece_id
content_revision_id
campaign_item_id
channel_code
platform_code
format_code
```

Ako renderer danas radi samo social, ova polja i dalje ostaju generička.

---

# 5. Export manifest

A15 / ZIP Export mora dobiti:

```text
manifest.json
```

Minimalni contract:

```json
{
  "schema_version": 1,
  "campaign_id": "...",
  "campaign_plan_id": "...",
  "exported_at": "...",
  "items": [
    {
      "campaign_item_id": "...",
      "content_piece_id": "...",
      "content_revision_id": "...",
      "channel_code": "SOCIAL",
      "platform_code": "INSTAGRAM",
      "format_code": "FEED_POST",
      "analytics_match_key": "...",
      "artifacts": []
    }
  ]
}
```

---

# 6. analytics_match_key

Implementirati helper/Value Object:

```text
AnalyticsMatchKey
```

Cilj:

kasnije povezivanje CSV/API podataka sa tačno eksportovanim content revision + target kombinacijom.

Acceptance:

- deterministic za isti input;
- mijenja se ako se promijeni revision;
- mijenja se ako se promijeni platform/format target;
- ne sadrži tajne ili PII;
- ima test.

---

# 7. Šta NE dodavati u Faza 1

Ne praviti još:

```text
PerformanceSnapshot table
DistributionInstance table
MetricDefinition table
Analytics screens
Meta/TikTok OAuth
PerformanceSourcePort adaptere
AI performance analysis
```

Arhitektonske definicije iz Faze 0.7 postoje, ali runtime implementacija čeka Slice 1.5.

---

# 8. Promjena A3 — Domain

A3 mora osigurati stable IDs i revision identity.

Dodati acceptance:

```text
AC-A3-AN1:
Campaign/CampaignPlan/CampaignItem/ContentPiece/Revision imaju stabilne IDs.

AC-A3-AN2:
CampaignItem eksplicitno nosi Channel/Platform/Format target.

AC-A3-AN3:
Content revision identity je dostupna export sloju.
```

---

# 9. Promjena A5 — Persistence

P0 foundation ostaje isti.

Business persistence mora podržati stabilne IDs i revisions.

Ne uvoditi Performance tabele u `0001/0002/0003` samo radi budućnosti.

To dolazi u Slice 1.5 migraciji.

---

# 10. Promjena A13/A14 — Visual/Renderer

Renderer output mora zadržati metadata link ka:

```text
campaign_item_id
content_piece_id
content_revision_id
platform_code
format_code
```

Metadata može biti sidecar JSON ili internal artifact metadata.

Nije potrebno embedovati u PNG EXIF.

---

# 11. Promjena A15 — ZIP Export

A15 više nije samo "spakuj slike i caption".

Mora:

1. kreirati `manifest.json`;
2. uključiti stable IDs;
3. uključiti `analytics_match_key`;
4. uključiti relative artifact paths;
5. imati schema version;
6. imati deterministic test.

---

# 12. A15 testovi

Obavezno:

```text
test_export_manifest_contains_stable_ids
test_export_manifest_contains_content_revision_id
test_export_manifest_contains_target_identity
test_analytics_match_key_is_stable_for_same_revision
test_analytics_match_key_changes_on_revision_change
test_analytics_match_key_changes_on_target_change
test_manifest_has_schema_version
```

---

# 13. G8 — Export & Evaluation Gate dopuna

G8 ne prolazi dok:

```text
manifest.json postoji
svaki exported item ima content_piece_id
svaki exported item ima content_revision_id
svaki exported item ima platform/format
svaki exported item ima analytics_match_key
```

---

# 14. G10 — Vertical Slice dopuna

End-to-end proof mora dokazati:

```text
Fixture
→ Brief
→ Plan
→ ContentPiece
→ Approval
→ Render
→ Export
→ manifest identity
```

To je Analytics-ready proof.

Nema performance importa još.

---

# 15. Novi Slice 1.5 — Performance Foundation

Implementirati ODMAH NAKON G10 PASS.

Predloženi gates:

```text
P1.5-G1 Performance Domain
P1.5-G2 Persistence
P1.5-G3 CSV Import
P1.5-G4 Matching
P1.5-G5 Metric Calculation
P1.5-G6 Analytics Read Models
P1.5-G7 Minimal UI
P1.5-G8 Integration
```

---

# 16. P1.5-G1 — Performance Domain

Implementirati:

```text
DistributionInstance
PerformanceSnapshot
PerformanceImportBatch
CanonicalMetricSet
MetricPeriod
PerformanceSource
```

Ne implementirati provider API adaptere.

---

# 17. P1.5-G2 — Persistence

Nova migration:

```text
0004_performance_foundation.sql
```

Predložene tabele:

```text
distribution_instances
performance_snapshots
performance_import_batches
performance_import_rows
```

`raw_metrics_json` ostaje dozvoljen.

---

# 18. P1.5-G3 — CSV Import

Implementirati:

```text
ImportPerformanceCsv
PreviewPerformanceMapping
ConfirmPerformanceImport
```

Korisnik mora vidjeti:

```text
matched
unmatched
ambiguous
invalid
```

Ništa se ne silently dropuje.

---

# 19. P1.5-G4 — Matching

Matching prioritet:

```text
external_content_id
analytics_match_key
stable content/distribution IDs
manual match
```

LLM matching nije dozvoljen kao authoritative matching.

---

# 20. P1.5-G5 — Metric Calculation

Centralni calculator:

```text
CTR
CPC
CPM
CPA
ROAS
Conversion Rate
```

Obavezni edge-case testovi:

```text
zero impressions
zero clicks
zero conversions
zero spend
missing values
negative invalid inputs
currency consistency
```

---

# 21. P1.5-G6 — Analytics Read Models

Implementirati read modele:

```text
CampaignPerformanceSummary
ContentPerformanceSummary
PlatformPerformanceSummary
```

Ne praviti još kompleksan BI warehouse.

---

# 22. P1.5-G7 — Minimal UI

Minimalno:

```text
Campaign → Performance tab
ContentPiece → Performance section
Import Performance button
CSV mapping dialog
```

Ne praviti veliki Analytics centar ako ga korisnici još nisu koristili.

---

# 23. P1.5-G8 — Integration acceptance

Scenario:

```text
create campaign
generate content
approve
export
take manifest key
import synthetic CSV
match data
calculate metrics
show campaign aggregate
show content result
```

Sve deterministic.

---

# 24. Kada ide Website Ingestion

Tek poslije:

```text
G10 Campaign Engine PASS
+
P1.5 Performance Foundation PASS
```

Tada Slice 2:

```text
Website + Documents → Brand Intelligence
```

Razlog:

Campaign Studio tada već zatvara cijeli osnovni poslovni loop:

```text
understand
→ plan
→ create
→ approve
→ export
→ measure
```

---

# 25. Kada ide direktan Meta/TikTok/etc. API

Ne prije Performance Foundation.

Novi adapter se dodaje iza:

```text
PerformanceSourcePort
```

Trigger:

- korisnici koriste CSV import;
- postoji dovoljan broj realnih importova;
- ručni import je stvarno usko grlo;
- konkretna platforma ima dovoljno korištenja.

---

# 26. Kada AI počinje koristiti performance history

Ne u Slice 1.5.

Kasniji slice:

```text
Performance Learning
```

Tek kada postoji dovoljno istorije.

Pipeline:

```text
PerformanceSnapshots
→ deterministic aggregation
→ CampaignLearningProfile
→ AI interpretation
→ next Campaign Brief/Plan assistance
```

---

# 27. Anti-refactor acceptance

Prije završetka Faza 1 mora biti potvrđeno:

```text
1 ContentPiece može imati više distribution instances kasnije
revision identity nije izgubljen
export manifest čuva canonical IDs
target identity nije izvedena iz teksta
analytics ne zavisi od filename-a
Campaign Engine ne zna PerformanceSource adaptere
```

---

# 28. Preporučeni redoslijed projekta

```text
P0 Foundation
        ↓
Faza 1 Campaign Engine
        ↓
G10 Vertical Slice PASS
        ↓
Slice 1.5 Performance Foundation
        ↓
Slice 2 Brand Ingestion
        ↓
Slice 3 Retrieval ako se dokaže potreba
        ↓
Performance API integrations
        ↓
Performance Learning / AI recommendations
```

Ovo je preporučeni trenutak koji minimizira kasniji refaktor bez nepotrebnog širenja prvog MVP-a.
