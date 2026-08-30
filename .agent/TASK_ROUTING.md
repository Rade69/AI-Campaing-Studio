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

## Napomena o paralelizaciji

Prije nego što se dva taska pokrenu paralelno, provjeriti (workflow §10):

1. `allowed_paths(A) ∩ allowed_paths(B) = ∅` (iz njihovih Task Contracata);
2. da nema skrivene semantic zavisnosti (npr. oba mijenjaju stanje koje isti integration test očekuje);
3. GitNexus shared-caller provjeru kada lista fajlova nije dovoljna (nije primjenjivo dok GitNexus nije indeksiran).

Trenutno je jedino ACS-P0-001 unblocked — nema kandidata za paralelan rad dok se 001 ne merguje.
