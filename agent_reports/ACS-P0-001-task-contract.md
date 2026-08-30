---
task_id: ACS-P0-001
phase: P0
title: "Repository, tooling and bootstrap skeleton"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-08-30
dependencies: []
allowed_paths:
  - pyproject.toml
  - README.md
  - .gitignore
  - config.example.toml
  - src/ai_campaign_studio/__init__.py
  - src/ai_campaign_studio/main.py
  - src/ai_campaign_studio/bootstrap.py
  - tests/
  - artifacts/.gitkeep
forbidden_paths:
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/infrastructure/ai/
  - presentation_qt/
  - presentation_webview/
gitnexus_required: false
adversarial_required: false
---

# Kontekst

Ovo je prvi coding task Implementation Phase 0.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md
```

Relevantne sekcije Implementation Phase 0:

```text
P0.00
P0.01
P0.02
P0.03
P0.04
P0.05
```

# Objective

Napraviti validan, minimalan Python src-layout foundation sa reproducibilnim tooling setupom, bez business/domain implementacije.

# GitNexus

Nije obavezan prije ovog taska jer još nema korisnog source graph-a.

Odmah NAKON ovog taska koordinator mora pokrenuti:

```bash
npx gitnexus analyze --skip-agents-md
npx gitnexus status
```

i ažurirati `.agent/CURRENT_STATE.md`.

# Implementation steps

1. Provjeri repo root i postojeći Git state.
2. Ne radi `git init` ako repo već postoji.
3. Kreiraj `.venv` lokalno, ali ga ne commituj.
4. Kreiraj `pyproject.toml` prema P0.04.
5. Kreiraj `.gitignore`.
6. Kreiraj minimalni package skeleton iz P0.05.
7. `main.py` i `bootstrap.py` ostaju foundation skeleton, bez GUI/AI/Campaign logike.
8. Instaliraj editable dev dependencies.
9. Napravi minimalne testove potrebne da package import i tooling stvarno rade.
10. Ne kreiraj buduće business module kao prazne placeholder strukture.

# Acceptance

- [ ] `python -c "import ai_campaign_studio"` prolazi.
- [ ] `python -m pytest -q` prolazi.
- [ ] `python -m ruff check .` prolazi.
- [ ] `python -m mypy src` prolazi.
- [ ] nema PySide6/pywebview/provider SDK dependency-ja.
- [ ] nema Campaign/Brand/Content business implementacije.
- [ ] `.venv`, cache, logs i runtime artifacts nisu trackovani.
- [ ] repo nije ugniježđen u dupli project root.

# Verification

```bash
python --version
python -c "import sys; print(sys.executable)"
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
git status --short
```

# Review focus — Codex

- tooling stvarno radi;
- testovi nisu lažni placeholderi;
- forbidden dependencies nisu uvedene;
- acceptance evidence odgovara stvarnom outputu.

# Review focus — Claude

- repo tree prati P0;
- nema premature business/framework strukture;
- `bootstrap.py` nije postao service locator/business container;
- foundation ostavlja Clean/Hexagonal granice otvorenim.

# Coordination

Nema paralelnog P0 coding taska prije merge-a ACS-P0-001.

Branch:

```text
task/ACS-P0-001-repo-foundation
```

Nakon merge-a:

```text
post-merge gate
GitNexus initial index
CURRENT_STATE update
```
