# .agent/BOARD.md

Živi "ko šta radi trenutno" pregled — SAMO aktivni taskovi, ne istorija
(istorija je u `.agent/CURRENT_STATE.md` i `agent_reports/`). Ažurira
koordinator (Claude) svaki put kad se task dispatch-uje, evidence stigne,
ili task merguje. Kad task merguje, briše se iz ove tabele (ne ostaje
"DONE" red — to bi ovaj fajl vremenom pretvorilo u drugi CURRENT_STATE.md).

**Zadnje ažurirano:** 2026-09-04

| Task | Implementer | Status | Šta radi |
|---|---|---|---|
| ACS-F1-020 (BF-2) | Pi | **Brief NIJE stigao do Pi-ja** — treba ručno proslijediti [agent_reports/2026-09-04-ACS-F1-020-fix-brief-2-za-pi.md](../agent_reports/2026-09-04-ACS-F1-020-fix-brief-2-za-pi.md) | Glued number+unit u claim_linter-u ("30KM", "3dana") dobija generički umjesto specifičnog reason_code |
| ACS-F1-025 (BF-1) | Crush | Fix još nije primijenjen (provjereno u kodu) | Jaccard sličnost — interpunkcija zalijepljena za riječi vještački snižavala skor |

Kad je tabela prazna: "Nema aktivnih taskova trenutno."
