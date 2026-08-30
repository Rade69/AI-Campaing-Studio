# Codex review request — ACS-P0-001

Za: Codex (adversarial/test reviewer)
Od: Claude (koordinator)
Datum: 2026-08-30

## Read protocol prije review-a

Pročitaj ovim redom, ne cijeli repo:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` (posebno §14 review format i
   §15 Codex review fokus)
4. `.agent/CURRENT_STATE.md`
5. `agent_reports/ACS-P0-001-task-contract.md` (konkretan Task Contract —
   obavezna polja, acceptance, allowed/forbidden paths)
6. `agent_reports/2026-08-30-ACS-P0-001-crush.md` (execution evidence koju je
   koordinator prikupio — komande i doslovan output)
7. Sam diff (vidi ispod)

## Šta pregledati

```text
Repo:     H:\AI Campaing Studio  (main branch)
Worktree: H:\ai-campaign-studio-worktrees\ACS-P0-001-repo-foundation
Branch:   task/ACS-P0-001-repo-foundation
Commit:   949d18c (base: main@85c5f41)
```

```bash
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-001-repo-foundation --stat
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-001-repo-foundation
```

9 fajlova, sve unutar `allowed_paths` iz kontrakta: `.gitignore`,
`README.md`, `artifacts/.gitkeep`, `config.example.toml`, `pyproject.toml`,
`src/ai_campaign_studio/__init__.py`, `src/ai_campaign_studio/bootstrap.py`,
`src/ai_campaign_studio/main.py`, `tests/test_foundation.py`.

## Codex review fokus (workflow §15) primijenjen na ovaj task

Ovo je P0.00–P0.05 foundation skeleton, bez business logike, pa većina
standardnih Codex meta (concurrency/state race, migration rollback, schema
output validation) nije primjenjiva. Fokusiraj se na ono što JESTE relevantno
za ovaj task:

1. **Da li testovi zaista dokazuju acceptance, ili su placeholder?**
   `tests/test_foundation.py` ima 3 testa (import, bootstrap instantiation,
   `main()` == 0). Da li išta od ovoga prolazi "slučajno" (npr. `main()`
   vraća 0 čak i ako bi bacio exception koji test ne hvata)?
2. **Missing negative tests** — da li nedostaje test koji bi trebalo da
   postoji za ovaj scope (npr. da `bootstrap.py`/`main.py` NE importuju
   ništa iz nepostojećih `domain/`/`infrastructure/ai/` paketa — trenutno
   nema eksplicitnog testa koji to garantuje, samo činjenica da ti paketi
   ne postoje).
3. **Forbidden dependencies** — nezavisno provjeri da li je neka zabranjena
   dependency (PySide6, pywebview, playwright, openai, anthropic, google
   provider SDK, DeepSeek SDK, Flask, FastAPI, Pillow, PyMuPDF, python-docx,
   openpyxl, vector DB) ušla direktno ili tranzitivno kroz
   `pyproject.toml`/`.venv`. Koordinator je provjerio samo direktan
   `pip list` grep — provjeri i `pip show` tranzitivne zavisnosti ako
   sumnjaš.
4. **Acceptance evidence vs stvaran output** — ponovo pokreni sam, ne
   vjeruj koordinatorovom izvještaju:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-001-repo-foundation"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe -c "import ai_campaign_studio"
   git status --short
   ```
5. **Scope/regression** — da li diff dira išta van `allowed_paths`, ili
   uvodi bilo kakvu skrivenu pretpostavku (hardkodovan path, platform-specific
   kod, itd.) koja će smetati narednim P0 taskovima (002–008)?

## Traženi output format (workflow §14)

Sačuvaj kao `agent_reports/2026-08-30-ACS-P0-001-review-codex.md`, sa YAML
header-om (`verdict`, `scope`, `acceptance`, `architecture`, `security`,
`tests`, `gitnexus_impact`, `blocking_findings`) i narativom (CILJ,
PROVJERENO, GITNEXUS/IMPACT, BLOCKING FINDINGS, STANDARDNA VERIFIKACIJA,
ADVERSARIALNA PROVJERA, NE DIRATI U FIX RUNDI, SLJEDEĆE) — isti format kao
`agent_reports/2026-08-30-ACS-P0-001-review-claude.md`, koji možeš koristiti
kao referencu forme (ne kao rezultat na koji se oslanjaš).

Nakon što dobijem tvoj verdikt, tražim Human Owner odobrenje za merge.
