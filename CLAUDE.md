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

## GitNexus i Graft

GitNexus nije opciona pomoć. Graft je dodatni, preporučen code
intelligence alat (CLI + MCP; identična odluka kao na FlowOS-u,
2026-09-09) — ne zamjenjuje GitNexus §5-§9 pre/post-change protokol,
koristi se kao dodatni, brži prvi prolaz.

Nakon foundation skeletona repo mora biti indeksiran i održavan svježim.

**"Zero callers" nije dokaz bezbjednosti** — potvrđena rupa za pozive kroz
kompozitni/atributni objekat (`self._api.X()`), čak i na svježem, ne
stale indeksu, na OBA alata (cross-project dokaz, ne još lokalno
potvrđeno na ovom kodu). Uvijek grep provjera prije zaključka o niskom
riziku.

Detaljni protokoli:

```text
.agent/GITNEXUS_PROTOCOL.md   (§13 caller-graph ograničenja)
.agent/GRAFT_PROTOCOL.md      (kompletna Graft odluka, dokazi, zabranjeni obrasci)
```

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **AI-Campaing-Studio** (16010 symbols, 23701 relationships, 173 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/AI-Campaing-Studio/context` | Codebase overview, check index freshness |
| `gitnexus://repo/AI-Campaing-Studio/clusters` | All functional areas |
| `gitnexus://repo/AI-Campaing-Studio/processes` | All execution flows |
| `gitnexus://repo/AI-Campaing-Studio/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
