# AGENTS.md — AI Campaign Studio

Ovo je ulazni fajl za Codex, Pi, Crush i sve druge coding agente koji rade na AI Campaign Studio projektu.

**Ovaj fajl je thin router.** Ne duplira puni proces. Kanonski procesni dokument je:

`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`

## Start here — obavezni redoslijed

`AGENTS.md` je **jedini prvi ulaz za sve agente**.

Prije bilo kakvog rada, nakon ovog fajla:

1. Pročitaj `CLAUDE.md` radi projektnih premisa i dodatnog routera.
2. Pročitaj `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`.
3. Pročitaj `.agent/CURRENT_STATE.md`.
4. Pročitaj `.agent/PROJECT_MAP.md`.
5. Pročitaj konkretan `agent_reports/<TASK-ID>-task-contract.md`.
6. Koristi `.agent/TASK_ROUTING.md` da odrediš dodatni read-set.
7. Ako task dira postojeći kod, koristi GitNexus prema `.agent/GITNEXUS_PROTOCOL.md` PRIJE izmjene.
8. Tek tada čitaj relevantne source/test fajlove i radi implementaciju.

Nikad ne počinji od `CLAUDE.md`, `CURRENT_STATE.md`, projektnog plana ili Task Contracta bez prethodnog čitanja ovog fajla.

## Izvori istine

Redoslijed autoriteta:

1. najnovija eksplicitna odluka Human Ownera;
2. `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md`;
   - za Performance/Analytics odluke obavezna dopuna je `AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`;
3. aktivni Implementation Phase 0 / Faza 1 plan označen u `.agent/CURRENT_STATE.md`;
4. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` za proces rada;
5. konkretan Task Contract;
6. kod + testovi + migracije za ono što je stvarno implementirano.

Ako postoji konflikt, NE nagađaj. Prijavi ga koordinatoru.

## Non-negotiable pravila

- Task Contract se piše PRIJE koda.
- Implementer nije reviewer sopstvenog taska.
- Svaki netrivijalan task dobija svoj git worktree i branch.
- Prije paralelnog rada koristi `scripts/coordination.py claim`.
- Agent ne širi scope sam; koristi `OUT_OF_SCOPE_FINDING`.
- MEDIUM/HIGH i svaki shared-contract/refactor task mora imati GitNexus impact analizu prije izmjene.
- GitNexus `detect-changes` je obavezan prije reviewa za MEDIUM/HIGH.
- Ne vjeruj implementer izvještaju bez stvarnog diff-a i execution evidence.
- Nema merge-a bez eksplicitnog odobrenja Human Ownera — **osim** LOW/MEDIUM
  taskova pod smanjenim review troškom (workflow §29, od 2026-09-01), gdje
  Claude PASS dovoljan za odmah commit/push/merge. HIGH/bezbjednosno-kritični
  taskovi ostaju na punom ciklusu bez izuzetka.
- Nakon merge-a obavezan je post-merge integration gate.
- API ključevi se nikad ne commit-uju niti čuvaju plaintext u SQLite/config fajlovima.
- Domain/Application boundary se ne probija radi "bržeg" rješenja.
- UI framework nije izabran dok UI-GATE ne prođe.
- Social media je prvi output, ali Campaign Engine ostaje channel-agnostic.
- Provider/model izbor ne smije procuriti u Campaign Engine.
- Performance/Analytics se ne implementira prerano: agent mora koristiti `.agent/TASK_ROUTING.md` sekciju `Performance / Analytics task`; runtime Slice 1.5 počinje tek poslije potvrđenog `G10 Vertical Slice PASS`.

## Agent-friendly file headers

Relevantni source fajlovi (services/registries/adapters/ports/domain/models/
composition roots — vidi puno pravilo) treba da počinju kratkim header-om
(2–5 linija) koji kaže šta fajl posjeduje i šta namjerno NE radi. Header je
navigaciona pomoć (progressive disclosure), ne source of truth — stvaran kod
je autoritet. Puno pravilo, format po jeziku i touched-file politika:
`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §30.

## GitNexus — obavezno

Ako repo još nije indeksiran, nakon početnog foundation skeletona:

```bash
npx gitnexus analyze --skip-agents-md
```

Za svakodnevni rad koristi `.agent/GITNEXUS_PROTOCOL.md`.

Ne dozvoli GitNexusu da zamijeni ovaj fajl kao projektni source of truth.

## Uloge

Default:

- Human Owner — scope, prioritet, konačno odobrenje merge-a.
- Claude Code — koordinator + architecture/integration reviewer.
- Codex — nezavisni test/adversarial reviewer.
- Pi / Crush — implementeri.
- MiniMax — implementer i nezavisni reviewer (isti status kao Codex/Pi/Crush
  po sposobnostima; trenutno angažovan kao implementer i pregledač, kao
  Codex).

Tačna uloga za konkretan task mora stajati u Task Contractu.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **AI-Campaing-Studio** (14650 symbols, 21443 relationships, 168 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
