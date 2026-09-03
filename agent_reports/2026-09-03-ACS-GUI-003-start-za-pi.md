# → ZA PI — ACS-GUI-003: počni implementaciju

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-03

Ovo nije materijal za čitanje — ovo je zadatak za **implementaciju, odmah**.

## Radi ovdje

```text
cd H:\ai-campaign-studio-worktrees\ACS-GUI-003-campaign-workflow-screens
```

Branch `task/ACS-GUI-003-campaign-workflow-screens` je već sinhronizovan sa main-om
(`19543a1`) — `agent_reports/ACS-GUI-003-task-contract.md` i
`agent_reports/2026-09-03-ACS-GUI-003-brief-za-pi.md` su već tu, u tom worktree-u.

## Šta konkretno napraviti (kratak sažetak, pun detalj je u kontraktu)

Kreiraj 4 nova Python modula:

```text
src/ai_campaign_studio/presentation_webview/screens/opis_kampanje/__init__.py
src/ai_campaign_studio/presentation_webview/screens/plan_kampanje/__init__.py
src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py
src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/__init__.py
```

Svaki: `@dataclass(frozen=True)` fixture + `DEFAULT_FIXTURE` + `render_body(fixture=None) -> str`
+ `__all__`, tačno prema sadržaju odgovarajućeg `docs/gui-v3/screens/0{4,5,7,8}_*/index.html`
mokapa (pun opis polje-po-polje je u kontraktu, sekcije "opis_kampanje" / "plan_kampanje" /
"studio_sadrzaja" / "pregled_izvoz").

Plus:
- proširi `_static_pages.py` da generiše i ova 4 ekrana (drugi loop, ne diraj `SIDEBAR_ITEMS`)
- `kampanje/__init__.py`: "Otvori" dugme postaje stvaran `<a href>` umjesto toast-a
- `studio_sadrzaja`: STVARAN tab-panel switching (ne kozmetički mokap markup — vidi kontrakt)
- testovi za sva 4 nova ekrana + update postojećih koje diraš

## Kad završiš

Evidence izvještaj kao `agent_reports/2026-09-03-ACS-GUI-003-pi.md`, ne commit-uj sam.
