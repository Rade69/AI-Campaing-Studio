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

## Aktivni projektni dokumenti

Aktuelne verzije se navode u `.agent/CURRENT_STATE.md`.

Ne oslanjaj se na starije Faza 0/Faza 1 verzije ako CURRENT_STATE kaže da su superseded.

## Non-negotiable engineering pravila

- Implementer != reviewer.
- Task Contract prije koda.
- Netrivijalan task = worktree.
- Scope se ne širi bez redefinisanja kontrakta.
- Execution evidence prije reviewa.
- GitNexus je obavezan za MEDIUM/HIGH i shared-contract/refactor izmjene.
- Review prije Human Owner approval-a.
- Merge tek nakon eksplicitnog odobrenja.
- Post-merge test/lint/type/integration gate.
- Ne uvoditi framework/abstrakciju "za svaki slučaj".
- Ne tvrditi da nešto radi bez stvarnog testa/outputa.

## GitNexus

GitNexus nije opciona pomoć.

Nakon foundation skeletona repo mora biti indeksiran i održavan svježim.

Detaljan protocol:

`.agent/GITNEXUS_PROTOCOL.md`
