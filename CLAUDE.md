# CLAUDE.md — AI Campaign Studio

Ovaj fajl vodi Claude Code i druge agente kroz projektne premise AI Campaign Studio projekta.

**Proces rada nije definisan ovdje.** Kanonski proces je:

`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`

## Start here

Ovaj fajl se čita **tek nakon `AGENTS.md`**. Ne vraća agenta ponovo na početak.

Nakon `AGENTS.md` i ovog fajla:

1. Pročitaj `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`.
2. Pročitaj `.agent/CURRENT_STATE.md`.
3. Pročitaj `.agent/PROJECT_MAP.md`.
4. Pročitaj konkretan Task Contract.
5. Koristi `.agent/TASK_ROUTING.md`.
6. Za postojeći kod obavezno slijedi `.agent/GITNEXUS_PROTOCOL.md`.

## Šta je AI Campaign Studio

Desktop-first, local-first AI aplikacija za strukturisano pravljenje marketinških kampanja.

Društvene mreže su prvi i prioritetni output kanal, ali:

- Brand Intelligence je channel-agnostic;
- Campaign Brief je u osnovi channel-agnostic;
- Campaign Plan postaje channel/platform/format-aware;
- core output je `ContentPiece`;
- social sadržaj je prvi implementirani payload.

## Ključna arhitektura

```text
Presentation
    ↓
Application / Use Cases
    ↓
Domain
    ↑
Ports
    ↑
Infrastructure adapters
```

AI je servis, ne arhitektura.

Campaign Engine ne zna konkretan OpenAI/Anthropic/Google/DeepSeek/OpenRouter SDK.

UI framework se ne zaključava prije UI spike gate-a.

## Zaključane projektne odluke

- Clean/Hexagonal core.
- `Channel → Platform → Format`.
- Social platform registry je data-driven.
- Početne platforme: Instagram, Facebook, LinkedIn, X, TikTok, YouTube, Pinterest, Threads, Snapchat.
- EN i BHS_LATIN UI.
- Generated content: EN ili BHS sa NEUTRAL/BS/SR/HR regionalnom varijantom.
- BHS MVP = latinica.
- API ključ pripada provideru, ne modelu.
- API ključevi idu u OS keyring.
- SQLite je lokalni persistence foundation.
- Fact-first/provenance: Approved Facts prije generacije tvrdnji.
- Human-in-loop odobravanje plana/sadržaja.
- Website ingestion dolazi tek poslije Campaign Engine proof-a.
- Renderer i UI framework su odvojene tehničke odluke.
- Performance/Analytics je arhitektonski planiran, ali runtime modul nije dio P0 niti ranog Campaign Engine MVP-a.
- Faza 1 mora sačuvati stable campaign/content/revision/target identitete, `manifest.json` i `analytics_match_key` da Slice 1.5 ne zahtijeva veliki refaktor.
- Stvarni Performance modul (`DistributionInstance`, `PerformanceSnapshot`, CSV/manual import, metric calculator) počinje tek poslije `G10 Vertical Slice PASS`, prije Website Ingestion Slice 2.

## Aktivni projektni dokumenti

Aktuelne verzije se navode u `.agent/CURRENT_STATE.md`.

Za Performance/Analytics zadatke dodatni obavezni source of truth su:

```text
AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md
AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md
```

Tačan read-set i trenutak korištenja određuje `.agent/TASK_ROUTING.md` sekcija
`Performance / Analytics task`.

Ne oslanjaj se na starije Faza 0/Faza 1 verzije ako CURRENT_STATE kaže da su superseded.

## Non-negotiable engineering pravila

- Implementer != reviewer.
- Task Contract prije koda.
- Netrivijalan task = worktree.
- Scope se ne širi bez redefinisanja kontrakta.
- Execution evidence prije reviewa.
- GitNexus je obavezan za MEDIUM/HIGH i shared-contract/refactor izmjene.
- Review prije Human Owner approval-a.
- Merge tek nakon eksplicitnog odobrenja — **osim** LOW/MEDIUM taskova pod
  smanjenim review troškom (workflow §29, od 2026-09-01): tamo je Claude
  PASS dovoljan da koordinator odmah commit-uje/push-uje/merguje, bez
  posebnog per-task odobrenja. HIGH/bezbjednosno-kritični taskovi ostaju na
  punom ciklusu bez izuzetka.
- Post-merge test/lint/type/integration gate.
- Ne uvoditi framework/abstrakciju "za svaki slučaj".
- Ne tvrditi da nešto radi bez stvarnog testa/outputa.
- Relevantni source fajlovi imaju kratak "owns / does not own" header na
  vrhu (workflow §30) — navigaciona pomoć za agente, ne source of truth.

## GitNexus

GitNexus nije opciona pomoć.

Nakon foundation skeletona repo mora biti indeksiran i održavan svježim.

Detaljan protocol:

`.agent/GITNEXUS_PROTOCOL.md`
