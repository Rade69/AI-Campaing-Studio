---
task_id: ACS-MAINT-001
title: "Dijagnostika ponavljajućeg flaky gate-report testa (capture stdout tail, ne samo stderr)"
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-09
dependencies: []
risk: LOW
allowed_paths:
  - scripts/generate_phase0_gate_report.py
  - tests/unit/scripts/test_generate_phase0_gate_report.py
forbidden_paths:
  - src/
  - resources/migrations/
gitnexus_required: false
adversarial_required: false
---

# Kontekst

`test_gate_report_against_current_repo_passes` je flaky (poznato od
ACS-F1-052) — pao je 2x zaredom u zadnja dva reviewa (ACS-F1-057,
ACS-F1-056), oba puta ISKLJUČIVO kad se pokrene ODMAH nakon punog
1223+ test suite runa (resursno opterećenje), i oba puta izolovano
ponovljen PASS bez izmjena. ACS-F1-052 je već izolovao nested pytest
invokaciju (`ACS_GATE_REPORT_RUNNING=1`, `--basetemp`, `-p
no:cacheprovider`) da izbjegne resource-contention sa spoljnim pytest
procesom — ta izolacija OČIGLEDNO ne pokriva sav resource contention
(flake se i dalje dešava).

**Stvaran problem koji ovaj task rješava**: `_run_python()` u
`scripts/generate_phase0_gate_report.py` za `pytest` check trenutno
perzistira SAMO `stderr` tail u `notes[].detail` (linija ~134-136).
Kad nested `pytest -q` padne, STVARAN razlog (koji test je pao, i
zašto) ide na STDOUT (pytest-ov standardni failure summary format), ne
na stderr. Rezultat: `phase0_foundation_gate.json` sadrži
`"pytest": false` bez ijedne korisne informacije o UZROKU — koordinator
je DVA PUTA morao ručno reprodukovati cijeli scenario iz nule da bi
uopšte saznao KOJI test je pao unutar nested run-a.

**Ovaj task NE pokušava "popraviti" flake bez poznatog uzroka** (nagađanje
fixa bez root cause-a bi bilo suprotno CLAUDE.md pravilu "ne tvrditi da
nešto radi bez stvarnog testa"). Umjesto toga, dodaje OPSERVABILNOST
tako da SLJEDEĆA pojava bude dijagnostikovana za par minuta, ne
ponovnom ručnom rekonstrukcijom cijelog scenarija.

# Objective

U `_run_python()` (`scripts/generate_phase0_gate_report.py`), za
`is_pytest` granu, promijeniti `detail` da uključi i STDOUT tail (ne
samo stderr), analogno postojećem stilu za ne-secret-scan checkove:

```python
stdout = completed.stdout.strip()
stdout_tail = "\n".join(stdout.splitlines()[-15:]) if stdout else "<empty>"
stderr = completed.stderr.strip()
stderr_last_line = stderr.splitlines()[-1] if stderr else "<empty>"
detail = (
    f"exit={completed.returncode} "
    f"stderr_tail={stderr_last_line} "
    f"stdout_tail={stdout_tail!r}"
)
```

(Tačan broj linija/format je implementerova odluka — cilj je da
`notes[].detail` sadrži pytest-ov `FAILED tests/...` summary red(ove)
kad padne, ne da bude prazan/beskoristan kao sada.)

**Sigurnosna napomena (isti princip kao postojeći secret-scan
poseban slučaj u istoj funkciji)**: pytest stdout NIKAD ne sadrži
secrete (za razliku od secret-scanner-a) — testovi ne printaju API
ključeve na stdout u normalnom radu. Ako implementer nađe suprotan
slučaj (neki test ipak printa osjetljivo), MORA eskalirati prije nego
što doda taj stdout u `detail` (isti oprez kao BF-2 iz ACS-P0-008
istorije).

**Opciono, ako implementer ima vremena/prostora u `allowed_paths`**:
dodati kratak komentar/napomenu u `test_gate_report_against_current_repo_passes`
docstring da flake pod resource contention POSTOJI i da je poznat
(referenca na ovaj task + ACS-F1-052), tako da budući implementer ne
paniči kad se ponovo pojavi, nego pogleda `notes[].detail` u
`artifacts/phase0_foundation_gate.json` prvo.

**NE raditi u ovom tasku** (van scope-a, bi zahtijevalo pravi root-cause
prije bilo kakve akcije):

- Retry/auto-rerun logika za flaky test (maskiralo bi stvaran signal).
- Bilo kakva izmjena stvarnog test suite-a van gate-report skripte.
- Bilo kakva izmjena `src/`.

# Implementation steps

1. Pročitati `scripts/generate_phase0_gate_report.py` u cjelini
   (kratak fajl), fokus na `_run_python()` i postojeći secret-scan
   poseban slučaj (referenca za stil).
2. Dodati stdout-tail capture za `pytest` granu (Objective).
3. Pokrenuti pun suite pa ODMAH `test_gate_report_against_current_repo_passes`
   NEKOLIKO puta zaredom, pokušavajući reprodukovati flake (isti obrazac
   koji ga je izazvao dva puta u zadnja dva reviewa) — CILJ je uhvatiti
   BAR JEDAN stvaran flake sa NOVIM detaljnim `stdout_tail` u
   `artifacts/phase0_foundation_gate.json`, da se potvrdi da fix
   stvarno hvata korisnu informaciju. Ako se flake ne reprodukuje u
   razumnom broju pokušaja (npr. 10x), to je OK — prijaviti kao
   "nisam uspio reprodukovati, ali mehanizam je unit-testiran"
   (sljedeća stavka).
4. Unit test za `_run_python()` koji simulira `pytest` subprocess sa
   ne-nultim exit kodom i STDOUT sadržajem (mock `subprocess.run`),
   potvrđuje da `detail` sada sadrži stdout tail, ne samo stderr.
5. Regresija: postojeći gate-report testovi i dalje prolaze (posebno
   secret-scan poseban slučaj — MORA ostati netaknut, nula stdout/stderr
   leak za taj check).

# Acceptance

- [ ] `_run_python()` pytest grana sada perzistira stdout tail u
      `notes[].detail`.
- [ ] Secret-scan poseban slučaj NETAKNUT (i dalje samo `exit=N`, nula
      stdout/stderr sadržaja).
- [ ] Nov/izmijenjen unit test dokazuje da se stdout tail hvata (mock,
      ne stvaran flaky repro nužno).
- [ ] Ako implementer USPIJE reprodukovati stvaran flake tokom rada:
      dokumentovati STVARAN uzrok u evidence izvještaju (npr. "test X
      je pao sa Y greškom pod opterećenjem") — ovo bi bio prvi put da
      neko ZNA šta konkretno flakuje, ne samo da nešto flakuje.
- [ ] `python -m pytest -q` cijeli suite prolazi (isti poznati flake
      MOŽE se pojaviti nezavisno — ako se pojavi, sada bi `detail`
      trebao pokazati koji test, provjeriti da li se poklapa sa
      dosadašnjim zapažanjima).
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze (mypy
      formalnost — `src/` nije diran).
- [ ] Nema izmjena van `allowed_paths`.

# Review focus — Claude (LOW)

- `detail` string ne curi secrete (pytest stdout nikad ne sadrži
  API ključeve u normalnom test radu — ali provjeriti da nijedan
  postojeći test ne printa nešto osjetljivo na stdout).
- Secret-scan poseban slučaj ostaje netaknut.
- Fix je ČISTO observability, ne pokušaj "popravke" nepoznatog uzroka.

# Rollback

LOW risk — dijagnostička izmjena u internoj dev-tooling skripti, nula
produkcijskog/domain koda, nula migracija, nula GUI. Claude-only review
→ odmah merge po §29 ako PASS.

# Coordination — PARALELNI RAD

Ovaj task je NEZAVISAN od [ACS-S2-001](ACS-S2-001-task-contract.md)
(Brand Ingestion Domain + Ports) — `allowed_paths` potpuno disjunktan
(`scripts/`/`tests/unit/scripts/` naspram `domain/`/`ports/`/
`tests/unit/domain/`/`tests/unit/ports/`), gate-report skripta ne uvozi
ni `domain` ni `ports` module (samo `importlib`/`subprocess`/
`pathlib`/`json` standard-lib stil provjere). Siguran za paralelan rad
sa DRUGIM implementerom (npr. Crush ili MiniMax) dok Pi radi na
ACS-S2-001.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-MAINT-001-gate-report-diagnostics
Branch:   task/ACS-MAINT-001-gate-report-diagnostics
Base:     main @ c2bc637
```
