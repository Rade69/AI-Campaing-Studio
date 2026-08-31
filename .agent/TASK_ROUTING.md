# .agent/TASK_ROUTING.md — dodatni read-set po tasku

Ovaj fajl određuje **dodatno** čitanje van baznog protokola (AGENTS.md → CLAUDE.md →
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md → .agent/CURRENT_STATE.md → .agent/PROJECT_MAP.md →
konkretan Task Contract) prije koda. Ne čitati cijeli plan dokument — samo navedene sekcije.

Svi P0 taskovi dodatno čitaju aktivni Implementation Phase 0 dokument naveden u
`.agent/CURRENT_STATE.md` (trenutno: `AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md`),
ograničeno na svoj P0.xx opseg ispod.

| Task ID | P0 opseg | Dodatna obavezna literatura |
|---|---|---|
| ACS-P0-001 | P0.00–P0.05 | — (samo Phase 0 v1.1, taj opseg) |
| ACS-P0-002 | P0.06–P0.10 | — |
| ACS-P0-003 | P0.11–P0.12 | Faza 0.6 §lokalizacija/regionalne varijante (EN/BHS_LATIN, NEUTRAL/BS/SR/HR) |
| ACS-P0-004 | P0.13 | Faza 0.6 §Channel/Platform/Format (registry je data-driven, ne hardcoded if/elif) |
| ACS-P0-005 | P0.14–P0.15 | Faza 0.6 §AI Provider/Model/LLM Registry; API ključ pripada provideru ne modelu; keyring, ne plaintext |
| ACS-P0-006 | P0.16–P0.19 | Faza 0.6 §persistence/SQLite odluke |
| ACS-P0-007 | P0.20–P0.23 | rezultati/kontrakti iz 003/004/005/006 (moraju biti merged u main prije branch-a) |
| ACS-P0-008 | P0.24–P0.30 | svi prethodni P0 task contracti i njihova acceptance polja (CI/security gate mora pokriti sve) |

Za taskove iz Faze 1 (tek nakon `P0-GATE = PASS`): dodatno čitati
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`, relevantnu vertical-slice sekciju,
i ovaj fajl ažurirati novim redovima kada Faza 1 taskovi budu paketovani.

Ako Faza 1 task dira analytics-ready identitete, revisions, export manifest ili `analytics_match_key`,
obavezno primijeniti i sekciju **Performance / Analytics task** ispod, zajedno sa:
`AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md` i
`AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`.

## Performance / Analytics task

Ova sekcija je obavezna za svaki task koji dira ili uvodi:

```text
analytics-ready stable IDs
content revision identity za export/performance
analytics_match_key
export manifest identitete
DistributionInstance
PerformanceSnapshot
PerformanceImportBatch
metric calculator
CSV/manual performance import
performance matching
Campaign/Content Performance read modele ili UI
PerformanceSourcePort / buduće platform API adaptere
Campaign Learning / AI performance interpretation
```

### A. Faza 1 PRIJE `G10 Vertical Slice PASS`

Analytics runtime modul se NE implementira.

Obavezno čitati:

1. `AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`
   - posebno `DistributionInstance`, revision identity, export manifest i anti-refactor pravila;
2. `AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`
   - samo sekcije koje pripadaju trenutnom A-tasku;
3. aktivni `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`
   - relevantni business/vertical-slice blok;
4. relevantne domain/export/renderer modele i njihove testove;
5. `.agent/GITNEXUS_PROTOCOL.md`.

Dozvoljeno prije G10:

```text
stable IDs
content_revision_id
channel/platform/format identity
manifest.json
analytics_match_key
artifact metadata link
```

Zabranjeno prije G10:

```text
PerformanceSnapshot persistence
DistributionInstance runtime tabela
Analytics dashboard
CSV performance import
Meta/TikTok/LinkedIn/Google performance API integracije
AI performance recommendations
```

### B. Poslije potvrđenog `G10 Vertical Slice PASS` — Slice 1.5

Koordinator prvo ažurira `.agent/CURRENT_STATE.md`:

```text
Performance / Analytics status: SLICE 1.5 ACTIVE
```

Svaki Slice 1.5 Task Contract mora dodatno čitati:

1. `AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`;
2. odgovarajući `P1.5-G*` gate iz `AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`;
3. postojeće `Campaign`, `CampaignItem`, `ContentPiece`, `Revision` i export manifest contracte;
4. Channel/Platform/Format registry;
5. SQLite migration/UoW/repository foundation;
6. relevantne testove;
7. `.agent/GITNEXUS_PROTOCOL.md`.

GitNexus je **obavezan za svaki Slice 1.5 task**:

```text
pre-change context
upstream impact
downstream impact kada je relevantno
detect-changes prije reviewa
post-merge re-index
```

### C. Prvi Performance input

Prvo implementirati:

```text
CSV / Excel import
+
manual mapping / correction
```

Ne počinjati direktnim platformskim API integracijama.

### D. Authoritative matching

Prioritet:

```text
1. external_content_id
2. analytics_match_key
3. stable content/distribution IDs
4. manual user confirmation
```

LLM semantic guess nije dozvoljen kao primarni authoritative matcher.

### E. Izvedene metrike

CTR, CPC, CPM, CPA, ROAS i Conversion Rate računaju se deterministički iz raw vrijednosti.

AI nije source of truth za numerički rezultat.

### F. Direktne platform API integracije

Tek poslije uspješnog Slice 1.5 i dokazane potrebe kroz realnu upotrebu CSV/manual importa.

Svaki novi adapter ide iza `PerformanceSourcePort`; Campaign Engine ne smije znati concrete adapter.

## Napomena o paralelizaciji

Prije nego što se dva taska pokrenu paralelno, provjeriti (workflow §10):

1. `allowed_paths(A) ∩ allowed_paths(B) = ∅` (iz njihovih Task Contracata);
2. da nema skrivene semantic zavisnosti (npr. oba mijenjaju stanje koje isti integration test očekuje);
3. GitNexus shared-caller provjeru kada lista fajlova nije dovoljna (nije primjenjivo dok GitNexus nije indeksiran).

Trenutno je jedino ACS-P0-001 unblocked — nema kandidata za paralelan rad dok se 001 ne merguje.
