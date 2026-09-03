# → ZA CRUSH — ACS-F1-016: uradi F1 fix, odmah

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-03

Ovo je akcioni zadatak — treba stvarna izmjena koda i verifikacija, ne samo čitanje.

## Radi ovdje

```text
cd H:\ai-campaign-studio-worktrees\ACS-F1-016-openai-adapter
```

Provjereno upravo sada: `pyproject.toml` i dalje nema `httpx` kao deklarisanu zavisnost
(`grep httpx pyproject.toml` pogađa samo komentar, ne pravi unos). F1 nije riješen.

## Šta konkretno uraditi

Pun opis u `agent_reports/2026-09-03-ACS-F1-016-fix-brief-za-crush.md` (već u ovom worktree-u).
Ukratko:

1. Dodaj `httpx` eksplicitno u `pyproject.toml` → `[project.optional-dependencies].dev`
   (kratak komentar zašto, isti stil kao postojeći `openai>=1.30` unos).
2. Verifikuj iz GENUINELY svježeg environment-a — minimalno:
   ```bash
   pip uninstall httpx -y
   pip install -e ".[dev]"
   pytest -q
   ```
   Ako i dalje prolazi nakon ovoga, fix je dokazan.
3. Ništa drugo iz originalnog taska ne diraj (adapter logika, use-case-i, error mapping,
   retry policy, `test_import_boundaries.py` carve-out — sve to je već PASS).

## Kad završiš

Javi mi (evidence update u `agent_reports/2026-09-03-ACS-F1-016-crush.md` ili novi fajl).
Ne commit-uj sam (§29 — HIGH risk task, ide na Codex adversarial review pa tek onda merge,
i pored F1 fix-a).
