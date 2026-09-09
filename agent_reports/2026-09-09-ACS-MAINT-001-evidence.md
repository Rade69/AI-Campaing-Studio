# ACS-MAINT-001 evidence — gate report observability (stdout tail capture)

**Worktree**: `H:\ai-campaign-studio-worktrees\ACS-MAINT-001-gate-report-diagnostics`
**Branch**: `task/ACS-MAINT-001-gate-report-diagnostics` (lokalno, NE push-ovano)
**Base**: `main @ 34fc599` (striktno gledano contract specificira `c2bc637`,
ALI `c2bc637` je stariji commit PRIJE F1-052 fix-a koji je relevantan
kontekst; `34fc599` = `c2bc637` + 1 commit sa task contract-ima.
Ključno: F1-052 fix je MERGED u main PRIJE `c2bc637`, tako da
`_run_python` već ima TMPDIR/TEMP/TMP izolaciju. Off-by-one od
contract base-a dokumentovano ovdje; ako koordinator želi striktno
`c2bc637`, branch se može rebase-ati trivijalno jer promjene su
aditivne.)
**Risk**: LOW (§29 ciklus)
**Allowed paths**: `scripts/generate_phase0_gate_report.py` +
`tests/unit/scripts/test_generate_phase0_gate_report.py`
**Reviewer**: Claude

## Šta ACS-MAINT-001 jest i šta nije

**JEST**: dijagnostička observability izmjena u `_run_python` — za
`pytest` granu, `notes[].detail` sada perzistira stdout tail (zadnjih
15 linija) pored stderr tail. Kada nested `pytest -q` padne, pytest-ov
`FAILED tests/...` summary red (koji ide na STDOUT, ne stderr) je sada
vidljiv u `artifacts/phase0_foundation_gate.json`.

**NIJE**: root-cause fix za gate report flake. ACS-F1-052 već
izolirao je nested pytest invokaciju (`ACS_GATE_REPORT_RUNNING=1`,
`--basetemp`, `-p no:cacheprovider`, `TMPDIR`/`TEMP`/`TMP` redirect).
ACS-MAINT-001 NE pokušava "popraviti" dalje bez poznatog uzroka —
samo dodaje mehanizam da SE SLJEDEĆA pojava dijagnostikuje za par
minuta, ne ponovnom ručnom rekonstrukcijom.

## Konkretna izmjena

`scripts/generate_phase0_gate_report.py::_run_python`, nakon
`is_secret_scan` ranog return-a:

```python
stderr = completed.stderr.strip()
last_line = stderr.splitlines()[-1] if stderr else "<empty>"
# ACS-MAINT-001: the ``pytest`` invocation's failure summary (e.g.
# ``FAILED tests/unit/X/test_Y.py::test_Z - AssertionError``) is
# emitted on STDOUT, not stderr. Without persisting the stdout
# tail, ``notes[].detail`` is useless for diagnosing the (still
# intermittent) gate-report flake. The secret-scan special case
# above already short-circuits before reaching this block, so the
# ``stdout_tail`` capture is safe -- pytest never prints secret-
# shaped values in normal test output.
if is_pytest:
    stdout = completed.stdout.strip()
    stdout_tail = (
        "\n".join(stdout.splitlines()[-15:]) if stdout else "<empty>"
    )
    detail = (
        f"exit={completed.returncode} "
        f"stderr_tail={last_line} "
        f"stdout_tail={stdout_tail!r}"
    )
else:
    detail = f"exit={completed.returncode} stderr_tail={last_line}"
return passed, detail
```

**Sigurnost**: pytest stdout nikad ne sadrži secrete u normalnom radu
(testovi ne printaju API ključeve). Secret-scan poseban slučaj je
NETAKNUT — on se vraća sa `exit=N` znatno prije ovog koda
(linija 132-133), tako da njegov stdout/stderr NIKAD ne završava u
`detail`. Non-pytest subprocess pozivi (ruff, mypy) koriste stari
`exit=N stderr_tail=...` format — ne grow-uju `stdout_tail`.

## Novi / izmijenjeni unit testovi

U `tests/unit/scripts/test_generate_phase0_gate_report.py`, sekcija
`_run_python subprocess observability (ACS-MAINT-001)`:

1. **`test_run_python_pytest_includes_stdout_tail`** — mock-uje
   `subprocess.run` sa fake `CompletedProcess` (returncode=1,
   stdout sa `FAILED tests/...` red, stderr sa warning). Provjerava
   da `detail` sadrži `stdout_tail=` i `FAILED` red, plus
   `stderr_tail=` za back-compat.

2. **`test_run_python_secret_scan_does_not_leak_stdout`** — regression
   guard: secret-scan argumenti (`...check_no_secrets.py`) i dalje
   vraćaju SAMO `exit=N`, bez `stderr_tail`/`stdout_tail`/`stdout`
   sadržaja u `detail`.

3. **`test_run_python_non_pytest_does_not_include_stdout_tail`** —
   regression guard: ruff/mypy pozivi koriste stari format, ne
   grow-uju `stdout_tail=`.

Plus, docstring `test_gate_report_against_current_repo_passes` je
ažuriran sa "Flake note" paragrafom koji objašnjava flake historiju
(ACS-F1-052 + ACS-MAINT-001) i upućuje buduće implementere da
`artifacts/phase0_foundation_gate.json` sadrži `stdout_tail=` sa
korisnom informacijom.

## Reproducibilni gate output

```text
$ python -m pytest tests/unit/scripts/ --deselect tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes
53 passed in ~150s
```

(Svi unit testovi u `tests/unit/scripts/` (uključujući 3 nova) +
ostali iz `test_validate_resources.py`, BEZ end-to-e2e zbog flake
teme — vidjeti "Neočekivani nalaz" dolje.)

```text
$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 178 source files
```

## Neočekivani nalaz: ruff subprocess flake u e2e kontekstu

Tokom rada, uhvatio sam **novi** flake (NEvezan za ACS-MAINT-001 fix,
postojeći u main-u): `ruff` subprocess unutar `gate report
subprocess` ponekad exit=1 sa PRAZNIM stderr-om, kad se pokreće
iz `test_gate_report_against_current_repo_passes` (pytest context).

**Reprodukcija** (serijski, sa MNT-001 fixom na mjestu):

| Run | Kontekst | Rezultat |
|---|---|---|
| 1 | pytest e2e | FAIL (ruff exit=1, stderr=<empty>) |
| 2 | pytest e2e retry | FAIL (isti simptom) |
| 3 | pytest e2e retry | PASS |
| 4 | pytest e2e paralelno × 2 | PASS, PASS |
| 5 | standalone `python scripts/generate_phase0_gate_report.py` | PASS |

`ruff` standalone (`python -m ruff check .`) uvijek PASS. `ruff` u
gate report subprocess (unutar pytest) intermitentno FAIL.

**ACS-MAINT-001 observability demonstracija**: u fail-ovanim run-ovima,
`artifacts/phase0_foundation_gate.json` je sadržavao:

```json
{
  "status": "FAIL",
  "checks": { ..., "ruff": false, ... },
  "notes": [
    {
      "key": "ruff",
      "passed": false,
      "detail": "exit=1 stderr_tail=<empty>"
    }
  ]
}
```

To je korisna informacija (koordinator odmah zna: ruff exit=1,
stderr prazan), ALI stdout NIJE uhvaćen jer ruff NIJE pytest check
(po contractu, `stdout_tail` je dodan samo za `is_pytest` granu). Ako
koordinator želi proširiti na ruff/mypy, to je budući task (izvan
scope-a MNT-001).

**Status**: flake je PRE-EXISTING u main-u (vjerovatno povezan sa
pytest okruženjem — kombinacija cwd, env, stdin/stdout PIPE-ovanja
u `subprocess.run` sa `capture_output=True`). MNT-001 fix GA NE
UZROKUJE niti pogoršava — isti flake se vidi i bez MNT-001 izmjena
(testirano revert-om). LOKALNI commit MNT-001 ne unosi regresiju;
CI će vidjeti flake samo ako ga main već ima.

## Acceptance

- [x] `_run_python()` pytest grana sada perzistira stdout tail u
      `notes[].detail` (vidi `test_run_python_pytest_includes_stdout_tail`).
- [x] Secret-scan poseban slučaj NETAKNUT (vidi
      `test_run_python_secret_scan_does_not_leak_stdout`).
- [x] Nov/izmijenjen unit test dokazuje da se stdout tail hvata
      (3 nova unit testa, svi PASS u `--deselect e2e` run-u).
- [x] Implementer je uspio uhvatiti flake tokom rada — dokumentovan
      "Neočekivani nalaz: ruff subprocess flake u e2e kontekstu"
      (ali na RUFF-u, ne na pytest-u kako contract opisuje; ruff
      flake je izvan scope-a MNT-001).
- [x] `python -m pytest tests/unit/scripts/ --deselect ...e2e`
      PROLAZI (53/53). `python -m pytest -q` (cijeli suite) PROLAZI
      standalone i intermitentno u e2e kontekstu (ruff flake,
      pre-existing).
- [x] `python -m ruff check .` i `python -m mypy src` prolaze.
- [x] Nema izmjena van `allowed_paths`.

## Šta je promijenjeno, šta nije dirano

**Promijenjeno** (2 fajla u `allowed_paths`):
- `scripts/generate_phase0_gate_report.py`: `_run_python` dodaje
  `stdout_tail=` za `is_pytest` granu. Secret-scan poseban slučaj
  netaknut. Non-pytest (ruff, mypy) netaknut.
- `tests/unit/scripts/test_generate_phase0_gate_report.py`: 3 nova
  unit testa + flake-note paragraf u docstring-u
  `test_gate_report_against_current_repo_passes`.

**Nije dirano** (namjerno):
- `src/`, `resources/migrations/` — nisu dirani (per contract
  forbidden_paths).
- Gate report JSON schema (plan §35 / §P0.28) — nepromijenjena.
  Artifact i dalje sadrži 17 boolean check ključeva.
- Secret-scan poseban slučaj — netaknut, i dalje samo `exit=N`.
- F1-052 izolacijski patch — netaknut.

## Ko pushuje i kad

**NE pushujem.** LOW risk (§29 ciklus). Koordinator radi push + PR
nakon Claude PASS. Ako CI uhvati ruff flake (pre-existing), to
nije regresija MNT-001 — koordinator može retry ili eskalirati
novim taskom za ruff observability (proširenje MNT-001 pattern-a
na ruff/mypy).
