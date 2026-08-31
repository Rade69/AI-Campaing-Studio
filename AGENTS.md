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
- Nema merge-a bez eksplicitnog odobrenja Human Ownera.
- Nakon merge-a obavezan je post-merge integration gate.
- API ključevi se nikad ne commit-uju niti čuvaju plaintext u SQLite/config fajlovima.
- Domain/Application boundary se ne probija radi "bržeg" rješenja.
- UI framework nije izabran dok UI-GATE ne prođe.
- Social media je prvi output, ali Campaign Engine ostaje channel-agnostic.
- Provider/model izbor ne smije procuriti u Campaign Engine.
- Performance/Analytics se ne implementira prerano: agent mora koristiti `.agent/TASK_ROUTING.md` sekciju `Performance / Analytics task`; runtime Slice 1.5 počinje tek poslije potvrđenog `G10 Vertical Slice PASS`.

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

Tačna uloga za konkretan task mora stajati u Task Contractu.
