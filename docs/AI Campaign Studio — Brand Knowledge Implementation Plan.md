# AI Campaign Studio — Brand Knowledge Implementation Plan

## 0. Cilj

Implementirati novi **Structured Brand Knowledge** sloj koji postojeće, ljudski odobrene `ApprovedFact` zapise pretvara u organizovano Brand Intelligence znanje pogodno za Campaign Engine.

Pipeline mora biti:

```text
Website / documents
        ↓
SourceSnapshot
        ↓
SourceChunk
        ↓
FactCandidate
        ↓ HUMAN APPROVAL
ApprovedFact
        ↓
Brand Knowledge Builder
        ↓
KnowledgeEntry PROPOSALS
        ↓ HUMAN REVIEW
Approved Knowledge Entries
        ↓
BrandKnowledgeSnapshot
        ↓
Campaign Engine
```

Ključni princip:

```text
ApprovedFact = dokaz / istina koju je čovjek odobrio

KnowledgeEntry = strukturisana interpretacija te činjenice

BrandKnowledgeSnapshot = uređena slika znanja o brandu
```

LLM NE odlučuje šta je istina.

LLM smije samo:

```text
classify
normalize
group
summarize
infer controlled attributes
```

nad već odobrenim činjenicama.

Nikakav LLM output ne smije automatski postati `APPROVED`.

---

# 1. Obavezni read-set prije implementacije

Prije bilo kakvog koda:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
.agent/GRAFT_PROTOCOL.md
```

Zatim obavezno pročitati relevantne source fajlove:

```text
src/ai_campaign_studio/domain/brand/entities.py
src/ai_campaign_studio/domain/brand/value_objects.py
src/ai_campaign_studio/domain/facts/entities.py
src/ai_campaign_studio/domain/facts/policies.py
src/ai_campaign_studio/domain/common/ids.py

src/ai_campaign_studio/application/ingestion/
src/ai_campaign_studio/ports/repositories.py

src/ai_campaign_studio/infrastructure/database/repositories/
resources/migrations/

src/ai_campaign_studio/presentation_webview/bridge/
src/ai_campaign_studio/presentation_webview/screens/
```

Koristi **Graft**, ne GitNexus.

Prije promjene postojećeg simbola:

```text
graft build
graft map
graft callers <symbol>
graft blast <symbol>
```

Ako:

```text
graft callers <symbol>
```

vrati zero callers, to NIJE dokaz da nema callera.

Obavezno:

```text
graft grep "<symbol>"
```

prije zaključka o blast radiusu.

Najnovija eksplicitna odluka Human Ownera je da je GitNexus zamijenjen Graftom. Ako stariji dokument u repou još tvrdi drugačije, NE vraćati GitNexus u workflow.

Ne miješati dokumentacioni cleanup sa feature implementacijom osim ako Task Contract to eksplicitno dozvoli.

---

# 2. Ne praviti ovo kao jedan veliki task

Implementaciju podijeliti u zasebne gateove.

Preporučeni redoslijed:

```text
BK-G1 — Domain model
BK-G2 — Persistence + migration
BK-G3 — Deterministic knowledge extraction
BK-G4 — LLM structured classification
BK-G5 — Consolidation + conflict detection
BK-G6 — Human review UI
BK-G7 — BrandKnowledgeSnapshot
BK-G8 — Campaign Engine integration
BK-G9 — End-to-end acceptance
```

Koristi sljedeće slobodne ACS task ID-jeve iz trenutnog `CURRENT_STATE.md`.

Svaki gate mora imati zaseban Task Contract.

Migracija = HIGH risk.

GUI lifecycle izmjene = HIGH prema postojećem projektnom workflowu.

Implementer != reviewer.

---

# 3. BK-G1 — Domain foundation

Napraviti novi domen:

```text
src/ai_campaign_studio/domain/brand_knowledge/
    __init__.py
    entities.py
    enums.py
    policies.py
```

NE gurati sve u postojeći `domain/brand/`.

Brand Knowledge jeste vezan za Brand, ali predstavlja poseban lifecycle:

```text
ApprovedFact
    ↓
proposed structured knowledge
    ↓
review
    ↓
knowledge snapshot
```

## 3.1 KnowledgeCategory

Implementirati:

```python
class KnowledgeCategory(StrEnum):
    COMPANY = "COMPANY"
    OFFERING = "OFFERING"
    AUDIENCE = "AUDIENCE"
    DIFFERENTIATOR = "DIFFERENTIATOR"
    PRICING = "PRICING"
    CONTACT = "CONTACT"
    BRAND_VOICE = "BRAND_VOICE"
    TRUST = "TRUST"
```

## 3.2 KnowledgeStatus

```python
class KnowledgeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONFLICT = "CONFLICT"
```

## 3.3 EvidenceType

```python
class EvidenceType(StrEnum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
```

`EXPLICIT` znači da informacija direktno postoji u jednom ili više `ApprovedFact`.

`INFERRED` znači da je izvedena iz obrasca kroz više činjenica.

Primjer:

```text
"We develop web shops."

→ OFFERING / service
→ EXPLICIT
```

ali:

```text
20 tekstova koriste kratke rečenice,
direktne CTA poruke i malo stručnog žargona

→ BRAND_VOICE
→ "direct, accessible"
→ INFERRED
```

---

# 4. KnowledgeEntry

Centralni objekat treba biti generički dovoljno da ne pravimo novu tabelu za svaku kategoriju.

Predloženi domain model:

```python
@dataclass(frozen=True)
class KnowledgeEntry:
    id: KnowledgeEntryId
    brand_snapshot_id: BrandSnapshotId

    category: KnowledgeCategory
    field: str

    value: str

    evidence_type: EvidenceType
    status: KnowledgeStatus

    source_fact_ids: tuple[FactId, ...]

    confidence: float | None

    conflict_group_id: str | None

    created_at: datetime
    reviewed_at: datetime | None = None
```

Invariant:

```text
source_fact_ids ne smije biti prazan.
```

Izuzetak se može dozvoliti samo za buduće `HUMAN_MANUAL` znanje, ali to NIJE dio ovog taska.

`confidence`:

```text
deterministički extractor → 1.0
LLM klasifikacija → 0.0–1.0
human-approved ručna vrijednost → može biti None
```

`confidence` NIJE vjerovatnoća da je činjenica istinita.

Istinitost je već određena kroz `ApprovedFact`.

Confidence ovdje znači:

> koliko je klasifikator siguran da činjenica pripada toj kategoriji/field-u.

---

# 5. Polja po kategorijama

Nemoj dozvoliti proizvoljne field nazive iz LLM-a.

Napraviti kontrolisani registry.

## COMPANY

```text
name
description
industry
company_type
location
founded
mission
```

## OFFERING

```text
service
product
package
feature
benefit
```

## AUDIENCE

```text
target_segment
industry
geography
need
pain_point
objection
motivation
```

## DIFFERENTIATOR

```text
advantage
unique_selling_point
expertise
guarantee
capability
```

## PRICING

```text
price
starting_price
price_range
discount
payment_terms
pricing_model
```

## CONTACT

```text
email
phone
address
website
social_profile
```

## BRAND_VOICE

```text
tone
formality
vocabulary
preferred_phrase
forbidden_phrase
sentence_style
cta_style
technical_language
```

## TRUST

```text
testimonial
customer
certification
award
statistic
case_study
years_experience
project_count
```

Unknown field iz LLM outputa mora biti odbijen kao schema/validation error.

Nikad ga automatski upisivati kao novi field.

---

# 6. IDs

U:

```text
domain/common/ids.py
```

dodati tipizovane ID-jeve:

```python
KnowledgeEntryId
BrandKnowledgeSnapshotId
```

Eventualno:

```python
KnowledgeConflictGroupId
```

samo ako se pokaže da je potreban pravi domain identitet.

Ne dodavati apstrakciju unaprijed.

---

# 7. BK-G2 — Persistence

Dodati novu inkrementalnu migraciju sa sljedećim slobodnim brojem.

NE mijenjati stare migracije.

Predložene tabele:

```sql
brand_knowledge_entries
brand_knowledge_entry_facts
brand_knowledge_snapshots
brand_knowledge_snapshot_entries
```

## brand_knowledge_entries

Minimalno:

```text
id
brand_snapshot_id
category
field_name
value
evidence_type
status
confidence
conflict_group_id NULL
created_at
reviewed_at NULL
```

FK:

```text
brand_snapshot_id
    → brand_snapshots(id)
```

## brand_knowledge_entry_facts

```text
entry_id
fact_id
position
```

FK:

```text
entry_id → brand_knowledge_entries(id)
fact_id  → approved_facts(id)
```

Primary key:

```text
(entry_id, fact_id)
```

Ova tabela je veoma važna.

NE čuvati provenance samo unutar JSON-a.

Mora postojati stvarna relacija:

```text
KnowledgeEntry
    ↓
ApprovedFact
```

## brand_knowledge_snapshots

```text
id
brand_snapshot_id
version
created_at
```

Constraint:

```text
UNIQUE(brand_snapshot_id, version)
```

## brand_knowledge_snapshot_entries

```text
knowledge_snapshot_id
entry_id
position
```

Time jedan immutable Knowledge Snapshot dobija tačno definisan skup odobrenih entry-ja.

---

# 8. Repository port

Dodati:

```python
BrandKnowledgeRepositoryPort
```

Ne proširivati postojeći repository bez razloga ako bi to stvorilo veliki interface sa nevezanim odgovornostima.

Potrebne operacije okvirno:

```python
save_entry(entry)
get_entry(entry_id)
list_entries_for_brand_snapshot(snapshot_id)
list_entries_by_status(snapshot_id, status)

save_knowledge_snapshot(snapshot)
get_knowledge_snapshot(snapshot_id)
get_latest_knowledge_snapshot(brand_snapshot_id)

replace_entry_status(...)
```

Ako postoji jasan projekat-wide pattern immutable replace kroz `save_*`, pratiti njega umjesto izmišljanja `update_*`.

Agent prvo mora pregledati postojeće repository konvencije.

SQLite adapter:

```text
infrastructure/database/repositories/sqlite_brand_knowledge_repository.py
```

---

# 9. Ključna arhitektonska odluka

`BrandKnowledgeSnapshot` NE zamjenjuje postojeći `BrandSnapshot`.

Odnos je:

```text
BrandSnapshot
    │
    ├── postojeći:
    │   voice
    │   audiences
    │   services
    │   visual_identity
    │   restrictions
    │   approved_fact_ids
    │
    └── derived extension
        BrandKnowledgeSnapshot
```

`BrandKnowledgeSnapshot.brand_snapshot_id` pokazuje na tačnu verziju BrandSnapshot-a iz koje je znanje izvedeno.

To znači da dva različita BrandSnapshot-a mogu dati dva različita Brand Knowledge snapshot-a.

Nikada ne dozvoliti da novi Knowledge Snapshot miješa činjenice iz više različitih BrandSnapshot verzija bez eksplicitnog future migration/use-case dizajna.

---

# 10. BK-G3 — Deterministička ekstrakcija

Prije LLM-a izdvojiti stvari koje pouzdano možemo parsirati.

Implementirati nešto tipa:

```text
application/brand_knowledge/
    deterministic_classifier.py
```

ili odgovarajući projekat-compatible naziv.

Deterministički obrađivati prvenstveno:

```text
email
phone
URL
social URL
cijene
valute
procenat
godine
```

Primjer:

```text
"Paketi počinju od 299 EUR mjesečno."
```

rezultat:

```text
category = PRICING
field = starting_price
value = "299 EUR / month"
evidence_type = EXPLICIT
confidence = 1.0
source_fact_ids = [...]
```

Ne pokušavati regexom određivati:

```text
target audience
USP
brand voice
service semantics
```

To je posao LLM klasifikatora.

---

# 11. Deterministički extractor ne smije izmisliti novu činjenicu

Original:

```text
"Plan starts from €299 per month."
```

Dozvoljena normalizacija:

```text
299 EUR/month
```

Nije dozvoljeno:

```text
Affordable plan for small businesses
```

jer original to nije rekao.

---

# 12. BK-G4 — LLM Structured Classification

Za ovo koristiti postojeću AI abstrakciju projekta.

NE importovati:

```text
openai
anthropic
google
deepseek
```

direktno u Brand Knowledge application layer.

Koristiti postojeći AI port/factory obrazac.

Prije implementacije Graftom pronaći kako:

```text
GenerateCampaignPlan
GenerateSocialPost
```

šalju structured request i validiraju output.

Slijediti isti pattern.

---

# 13. Prompt

Dodati verzionisani prompt, npr.:

```text
resources/prompts/brand_knowledge/v1.yaml
```

Prompt mora eksplicitno reći modelu:

```text
You receive only human-approved factual statements.

Your task is classification and normalization.

You MUST NOT introduce facts that are not supported by supplied facts.

Every output entry MUST reference one or more input fact IDs.

For EXPLICIT entries, provide an evidence quote copied verbatim
from one of the referenced facts.

If the evidence is insufficient, return no entry.

Do not guess missing prices, locations, audience segments,
company size, benefits or differentiators.

Use only allowed categories and fields.
```

---

# 14. Structured output schema

LLM ne smije vraćati slobodan tekst.

Primjer:

```json
{
  "entries": [
    {
      "category": "AUDIENCE",
      "field": "target_segment",
      "value": "Small and medium retailers",
      "evidence_type": "EXPLICIT",
      "source_fact_ids": ["fact-123"],
      "evidence_quotes": [
        "designed for small and medium retailers"
      ],
      "confidence": 0.94
    }
  ]
}
```

---

# 15. Anti-hallucination validator

Ovo je obavezan dio.

Poslije LLM response-a application layer mora deterministički validirati:

```text
category postoji
field pripada category
confidence je 0..1
source_fact_ids nisu prazni
svaki source_fact_id je bio u INPUT batchu
svaki source Fact ima status APPROVED
evidence_quote postoji u tekstu odgovarajućeg ApprovedFact-a
value nije prazan
```

Ako LLM kaže:

```text
fact-999
```

a nije bio u prompt inputu:

```text
REJECT OUTPUT
```

Ako evidence quote nije stvarni substring ApprovedFact teksta:

```text
REJECT ENTRY
```

Nikada:

```text
"model je vjerovatno mislio na..."
```

---

# 16. Batch obrada

Ne slati stotine činjenica u jednom promptu.

Napraviti deterministički batching.

Poželjno:

```text
20–40 ApprovedFact po batchu
```

ali konačan limit odrediti prema postojećem AI request modelu i testovima.

Batch mora zadržati:

```text
fact_id
content
```

i po potrebi provenance metadata.

LLM-u NE treba slati cijeli HTML.

---

# 17. BRAND_VOICE izdvojiti kao poseban inference pass

Brand voice nije obična faktografska klasifikacija.

Ne pokušavati:

```text
jedan Fact → kompletan tone profile
```

Napraviti zaseban use-case, npr.:

```text
InferBrandVoice
```

koji dobija više odobrenih reprezentativnih činjenica/tekstualnih uzoraka.

Output može biti:

```text
tone:
- professional
- direct
- friendly

formality:
MEDIUM

sentence_style:
SHORT_TO_MEDIUM

technical_language:
MODERATE

cta_style:
DIRECT
```

Svaki takav entry:

```text
evidence_type = INFERRED
```

i mora imati više `source_fact_ids`.

Preporuka za v1:

```text
INFERRED Brand Voice zahtijeva najmanje 3 source facts
```

osim ako neka činjenica eksplicitno kaže:

```text
"Our communication style is..."
```

što onda može biti `EXPLICIT`.

---

# 18. BK-G5 — Deduplication i consolidation

Poslije klasifikacije možemo dobiti:

```text
SMEs
small and medium businesses
small/medium companies
small businesses
```

Ne želimo četiri gotovo ista KnowledgeEntry-ja.

Pipeline:

```text
classified proposals
        ↓
exact deterministic dedup
        ↓
semantic consolidation proposals
        ↓
human review
```

## Exact dedup

Normalizovati:

```text
case
whitespace
obvious punctuation
```

Identičan:

```text
category + field + normalized value
```

spojiti u jedan entry.

`source_fact_ids` postaje union svih izvora.

---

# 19. Semantic consolidation

Za semantički slične vrijednosti koristiti poseban LLM pass.

Primjer input:

```text
AUDIENCE.target_segment

A: SMEs
B: small and medium-sized businesses
C: small/medium companies
```

LLM može predložiti:

```text
Small and medium-sized businesses
```

ali rezultat mora zadržati:

```text
source_fact_ids = A ∪ B ∪ C
```

I status ostaje:

```text
PROPOSED
```

Nikada auto-approved.

---

# 20. Conflict detection

Ovo je hard requirement.

Primjer:

```text
Fact A:
Plans start at €49/month.

Fact B:
Plans start at €59/month.
```

Rezultat NE SMIJE biti:

```text
€59/month
```

samo zato što LLM misli da je noviji.

Napraviti dva entry-ja:

```text
PRICING.starting_price = 49 EUR/month
PRICING.starting_price = 59 EUR/month
```

oba dobijaju isti:

```text
conflict_group_id
```

i:

```text
status = CONFLICT
```

Čovjek rješava konflikt.

Za v1 automatsku conflict detection fokusirati na jasna single-value polja:

```text
company name
phone
email
address
starting price
price
founded
```

Ne označavati automatski dvije različite usluge kao konflikt.

---

# 21. Human Review

Nijedan LLM-generated KnowledgeEntry ne smije odmah postati APPROVED.

Implementirati use-caseove:

```text
ApproveKnowledgeEntry
RejectKnowledgeEntry
```

i eventualno:

```text
EditKnowledgeEntry
```

Za edit:

human edit mora zadržati provenance.

Poželjno je dodati:

```text
origin = HUMAN_EDITED
```

samo ako projektni domain review potvrdi da taj enum ima smisla.

Ne uvoditi ga unaprijed bez Task Contract odluke.

---

# 22. BK-G6 — GUI

Dodati novu sekciju na `Brend` ekran.

Ne praviti zaseban veliki ekran u prvoj verziji ako nije potreban.

Predloženi UX:

```text
Brand Intelligence

[Izgradi strukturu] [Osvježi]

Tvrtka                  5
Usluge                  8
Ciljna skupina          4
Prednosti               6
Cijene                  3
Kontakt                  5
Ton komunikacije        6
Povjerenje               4
```

Svaka kategorija je collapsible.

---

# 23. Knowledge Entry kartica

Primjer:

```text
CILJNA SKUPINA

Small and medium-sized retailers

Target segment
AI classified · 94%
2 izvora

[Odobri] [Odbaci] [Pogledaj dokaze]
```

Za inferred:

```text
TON KOMUNIKACIJE

Professional, direct

AI inferred
5 izvora

[Odobri] [Odbaci] [Pogledaj dokaze]
```

Nikada UI-em ne prikazivati inferred podatak kao jednako direktnu činjenicu.

`EXPLICIT` i `INFERRED` moraju biti vizuelno razlikovani.

---

# 24. Evidence drawer

Klik na:

```text
Pogledaj dokaze
```

mora prikazati:

```text
Knowledge value:
Small and medium-sized retailers

Derived from:

Fact #abc
"Designed specifically for small and medium retailers."

Source:
https://example.com/solutions

Snapshot:
...

Chunk:
...
```

Ako entry ima više factova prikazati sve.

Ovo je jedna od glavnih vrijednosti sistema.

---

# 25. Conflict UI

Conflict nikad ne sakriti.

Primjer:

```text
⚠ Konflikt — početna cijena

A
49 EUR/month
Source: /old-pricing

B
59 EUR/month
Source: /pricing

[Koristi A] [Koristi B] [Odbaci oba]
```

Rješavanje konflikta mora biti eksplicitna human akcija.

---

# 26. Bulk approval

Bulk approval može postojati za:

```text
PROPOSED + EXPLICIT
```

ali NE preporučujem bulk approve za:

```text
CONFLICT
INFERRED
```

bez posebne svjesne korisničke akcije.

---

# 27. BK-G7 — BrandKnowledgeSnapshot

Kada korisnik završi review, napraviti immutable:

```python
@dataclass(frozen=True)
class BrandKnowledgeSnapshot:
    id: BrandKnowledgeSnapshotId
    brand_snapshot_id: BrandSnapshotId
    version: int
    approved_entry_ids: tuple[KnowledgeEntryId, ...]
    created_at: datetime
```

Snapshot sadrži samo:

```text
APPROVED
```

entry-je.

Ne uključuje:

```text
PROPOSED
REJECTED
CONFLICT
```

Svako ponovno finalizovanje pravi:

```text
version + 1
```

stari snapshot se ne mijenja.

---

# 28. Existing BrandSnapshot integration

Ne uklanjati postojeće:

```text
BrandVoice
Audience
ServiceDefinition
VisualIdentity
Restriction
approved_fact_ids
```

U prvoj verziji napraviti mapper:

```text
Approved Knowledge
        ↓
existing Brand value objects
```

Primjeri:

```text
OFFERING.service
    → ServiceDefinition

AUDIENCE.target_segment
    → Audience

AUDIENCE.need
    → Audience.needs

AUDIENCE.objection
    → Audience.objections

BRAND_VOICE.tone
    → BrandVoice.tone

BRAND_VOICE.preferred_phrase
    → BrandVoice.preferred_terms

BRAND_VOICE.forbidden_phrase
    → BrandVoice.forbidden_terms
```

Ali NE pokušavati nasilno ugurati:

```text
pricing
contact
trust
differentiators
company metadata
```

u postojeće `ServiceDefinition` ili `Audience`.

To ostaje u Brand Knowledge sloju.

---

# 29. Campaign Engine integration

Tek nakon što Brand Knowledge backend + review budu stabilni.

Campaign Engine mora moći dobiti:

```text
BrandSnapshot
+
latest approved BrandKnowledgeSnapshot
```

Ako Knowledge Snapshot ne postoji:

```text
postojeći Campaign Engine mora nastaviti raditi kao danas
```

Dakle novi sistem mora biti backward-compatible.

---

# 30. Context za generaciju

LLM-u za campaign generation ne slati cijelu bazu.

Napraviti selector.

Primjer Campaign Brief:

```text
goal = lead generation
target audience = SME retailers
```

Knowledge selector može dati:

```text
COMPANY
relevant OFFERINGS
selected AUDIENCE
DIFFERENTIATORS
relevant PRICING
BRAND_VOICE
TRUST proof points
```

Kontakt nije potreban za svaki post.

Ne slati sve samo zato što postoji.

---

# 31. Fact-first ostaje konačni sigurnosni sloj

Structured Knowledge NE smije zamijeniti Approved Facts kao provenance authority.

Ako Campaign Engine koristi:

```text
"Over 120 successful projects"
```

mora biti moguće pratiti:

```text
Campaign claim
    ↓
KnowledgeEntry
    ↓
ApprovedFact
    ↓
SourceChunk
    ↓
SourceSnapshot
    ↓
URL
```

Knowledge layer služi da agent zna **šta činjenica znači**, ne da ukine originalni dokaz.

---

# 32. Testovi — Domain

Obavezno pokriti:

```text
KnowledgeEntry frozen
source_fact_ids coerced to tuple
empty source_fact_ids rejected
invalid confidence rejected
valid categories
valid statuses
EXPLICIT/INFERRED semantics
BrandKnowledgeSnapshot frozen
snapshot approved_entry_ids tuple
```

---

# 33. Testovi — Persistence

Integration testovi sa pravim SQLite:

```text
save/read KnowledgeEntry
entry↔facts provenance
više factova po entry-ju
više entry-ja po factu
status persistence
conflict_group persistence
snapshot version uniqueness
snapshot↔entries ordering
FK integrity
rollback behaviour
```

Migration test obavezan.

---

# 34. Testovi — LLM validator

Ovo je kritično.

Napraviti fake structured AI responses i dokazati:

```text
unknown category → reject
unknown field → reject
unknown fact_id → reject
non-approved fact → reject
fake evidence_quote → reject
confidence > 1 → reject
empty source facts → reject
empty value → reject
valid response → accept as PROPOSED
```

---

# 35. Hallucination regression test

Input:

```text
fact-1:
"We build web shops."
```

Fake LLM output:

```text
category: OFFERING
field: service
value: "Web shop development for companies with 50-200 employees"
```

Ako evidence quote pokušava podržati samo:

```text
"We build web shops."
```

sistem NE smije tretirati:

```text
50-200 employees
```

kao dokazanu informaciju.

Za v1 validator može biti stroži:

LLM normalizovana vrijednost mora ostati semantički bliska evidence quote-u.

Ako to ne možemo deterministički dokazati, takav output ide:

```text
NEEDS_REVIEW / PROPOSED
```

i nikada nije auto-approved.

Važnije je ne lažirati sigurnost nego napraviti „pametan“ validator koji sam nagađa.

---

# 36. Testovi — Conflict

Obavezni slučajevi:

```text
49 EUR vs 59 EUR → CONFLICT

isti email iz 3 facta
→ jedan entry sa 3 provenance veze

dvije različite usluge
→ NISU conflict

dvije različite audience grupe
→ NISU conflict
```

---

# 37. Testovi — Human Review

Provjeriti:

```text
PROPOSED → APPROVED

PROPOSED → REJECTED

APPROVED → ponovni approve
mora failovati ili pratiti postojeću invariant politiku

REJECTED → approve
ne smije tiho uspjeti

CONFLICT → obični approve
ne smije zaobići conflict resolution
```

---

# 38. GUI testovi

Postojeći projekt koristi Node/VM testove za `app.js`.

Dodati stvarne lifecycle testove, ne samo static string assertions.

Provjeriti:

```text
load knowledge
render categories
XSS escaping
approve
reject
reload
evidence drawer
conflict rendering
explicit/inferred badge
empty state
API failure state
pywebview ready exactly-once pattern
```

Ne ponoviti ranije pywebview greške gdje syntax-only test prolazi, a runtime click puca.

---

# 39. E2E acceptance scenario

Napraviti deterministički end-to-end test bez live LLM-a.

Fake AI adapter mora dati unaprijed definisane structured rezultate.

Scenario:

```text
1. Seed Brand.

2. Seed/ingest ApprovedFacts:

   "ACME develops custom web shops."
   "Our solutions are designed for small and medium retailers."
   "Plans start at 299 EUR per month."
   "Contact us at sales@acme.test."
   "We have delivered more than 120 projects."

3. Build Brand Knowledge.

4. Assert proposals:

   OFFERING.service
   AUDIENCE.target_segment
   PRICING.starting_price
   CONTACT.email
   TRUST.project_count

5. Human approve.

6. Finalize BrandKnowledgeSnapshot.

7. Reload from SQLite.

8. Assert every entry retains source FactId.

9. Load Campaign Engine context.

10. Assert structured Brand Knowledge is available.

11. Assert original ApprovedFacts still exist unchanged.
```

---

# 40. Real LLM smoke test

Live-provider test neka bude zaseban i opciono pokretan env varom.

NE smije biti dio determinističkog CI acceptance-a.

Razlog: projekt već ima iskustvo sa nondeterminističkim live DeepSeek testom.

CI mora moći proći bez API ključa.

---

# 41. Performance

Ne optimizovati prerano, ali ne praviti N+1 pozive za svaki fact.

Repository mora imati batch metode gdje su potrebne.

Za LLM:

```text
facts → batches
```

ne:

```text
1 fact = 1 API call
```

120 činjenica ne smije napraviti 120 LLM requestova.

---

# 42. Observability

Logovati:

```text
knowledge_build_started
facts_loaded
deterministic_entries_created
llm_batches_started
llm_entries_proposed
entries_rejected_by_validator
conflicts_found
knowledge_build_completed
knowledge_snapshot_created
```

NE logovati API ključeve.

Ne logovati cijele promptove ako mogu sadržavati osjetljiv business sadržaj bez posebne odluke.

---

# 43. Idempotency

Ponovni build nad istim:

```text
BrandSnapshot
+
istim ApprovedFacts
+
istom classifier verzijom
```

ne smije nekontrolisano praviti duplikate.

Definisati `build_key`, npr. deterministički hash:

```text
brand_snapshot_id
classifier_version
sorted fact ids + versions
```

Ako nema promjene, use-case može vratiti postojeći build rezultat ili eksplicitno napraviti novu verziju samo na korisnički zahtjev.

Tačna politika mora biti fiksirana u Task Contractu prije implementacije persistence dijela.

---

# 44. Versioniranje classifiera

Čuvati verziju semantičkog buildera.

Primjer:

```text
classifier_version = "brand-knowledge-v1"
```

Jer:

```text
isti factovi
+
novi prompt/schema
```

mogu dati drugačiju strukturu.

Mora biti moguće kasnije znati kojim algoritmom je entry nastao.

Ako je potrebno, dodati:

```text
builder_version
```

na KnowledgeEntry ili build/snapshot metadata.

---

# 45. Šta NE implementirati u v1

Ne uvoditi:

```text
vector database
embeddings
RAG framework
knowledge graph database
Neo4j
fuzzy entity resolution framework
automatic truth scoring
automatic web-wide fact verification
background continuous recrawling
automatic replacement of conflicting facts
LLM auto-approval
```

Za trenutni problem to je nepotrebna složenost.

SQLite + postojeći Fact model + structured LLM classification su dovoljni.

---

# 46. Posebno važna zabrana

NE raditi:

```text
website → LLM → Brand Profile → database
```

Time bismo zaobišli cijeli postojeći provenance/human-review sistem.

Isključivo:

```text
website
→ extraction
→ FactCandidate
→ HUMAN APPROVAL
→ ApprovedFact
→ Knowledge classification
→ HUMAN REVIEW
→ BrandKnowledgeSnapshot
```

---

# 47. Definition of Done za kompletan feature

Feature nije završen samo zato što postoje nove tabele ili classifier.

Mora biti dokazano:

```text
ApprovedFacts se stvarno učitavaju.

Determinističke informacije se strukturiraju bez LLM-a gdje je moguće.

Semantičke informacije idu kroz structured-output AI port.

Svaki KnowledgeEntry ima provenance prema ApprovedFact.

Nijedan unknown FactId iz LLM-a ne prolazi.

Fake evidence quote ne prolazi.

LLM output nikad nije automatski APPROVED.

Exact duplicates se konsoliduju.

Jasni konflikti se ne skrivaju.

Human review radi iz GUI-ja.

BrandKnowledgeSnapshot je immutable/versioniran.

Campaign Engine može koristiti novi snapshot.

Campaign Engine i dalje radi kada Knowledge Snapshot ne postoji.

CI je deterministički i ne zahtijeva live API key.

Full test suite, ruff, mypy i relevantni integration gateovi prolaze.
```

---

# 48. Preporučeni redoslijed implementacije

Nemoj odmah krenuti na GUI.

Prvo:

```text
BK-G1
Domain

↓ review

BK-G2
Migration + repository

↓ review

BK-G3
Deterministic extractor

↓ review

BK-G4
LLM classifier + strict validation

↓ review

BK-G5
Consolidation + conflicts

↓ review

BK-G6
Human review GUI

↓ review

BK-G7
Immutable BrandKnowledgeSnapshot

↓ review

BK-G8
Campaign Engine consumption

↓ review

BK-G9
Deterministic complete E2E
```

Poslije svakog gate-a ažurirati `.agent/CURRENT_STATE.md` prema postojećoj konvenciji.

Ne proglašavati sljedeći gate završen zato što njegov backend postoji — dokazati njegov stvarni caller/runtime tok.

---

# 49. Prvi task koji treba otvoriti

Prvi konkretni task neka bude isključivo:

```text
Brand Knowledge Domain Foundation
```

Scope:

```text
KnowledgeCategory
KnowledgeStatus
EvidenceType
KnowledgeEntry
BrandKnowledgeSnapshot
typed IDs
domain policies
unit tests
```

Bez:

```text
SQLite
migration
LLM
GUI
Campaign Engine
```

Razlog:

prvo treba zaključati domain contract.

Tek kada je taj model pregledan i prihvaćen, otvoriti HIGH-risk persistence/migration task.

---

# 50. Arhitektonski rezultat koji želimo

Na kraju sistem treba izgledati ovako:

```text
                 ┌────────────────────┐
                 │    WEB / DOCS      │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │   SourceSnapshot   │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │    SourceChunk     │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │   FactCandidate    │
                 └─────────┬──────────┘
                           │
                      HUMAN REVIEW
                           │
                           ▼
                 ┌────────────────────┐
                 │   ApprovedFact     │
                 │  source of truth   │
                 └─────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
         deterministic          structured LLM
          extractors             classifier
                │                     │
                └──────────┬──────────┘
                           ▼
                 ┌────────────────────┐
                 │   KnowledgeEntry   │
                 │     PROPOSED       │
                 └─────────┬──────────┘
                           │
                    consolidate /
                     conflicts
                           │
                           ▼
                      HUMAN REVIEW
                           │
                           ▼
                 ┌────────────────────┐
                 │ BrandKnowledge     │
                 │     Snapshot       │
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │  Campaign Engine   │
                 └────────────────────┘
```

Najvažniji invariant cijelog sistema:

```text
Svaka marketinški korisna strukturisana informacija mora biti
sljediva nazad do činjenice koju je čovjek odobrio.

AI organizuje znanje.
AI ne određuje istinu.
```