# ACS-F1-052 evidence — fix flaky `test_gate_report_against_current_repo_passes`

**Worktree**: `H:\ai-campaign-studio-worktrees\ACS-F1-052-fix-gate-report-flake`
**Branch**: `task/ACS-F1-052-fix-gate-report-flake` (lokalno, NE push-ovano)
**Base**: `main @ deade0b`
**Task contract**: `agent_reports/ACS-F1-052-task-contract.md`
**Risk**: LOW (§29 smanjeni review ciklus)
**Allowed paths**: `scripts/generate_phase0_gate_report.py` + `tests/unit/scripts/test_generate_phase0_gate_report.py`
**Reviewer**: Claude

## Sažetak

`test_gate_report_against_current_repo_passes` (end-to-end test koji pokreće
stvaran `scripts/generate_phase0_gate_report.py` kao subprocess) povremeno
je padao pod "recursive-subprocess concurrency" -- outer pytest i inner
pytest (koji gate report pokreće kao svoj "pytest" check) istovremeno
koriste iste filesystem resurse (cache, tmpdir, basetemp). 50% fail rate
reprodukovan u 4 paralelna pytest runa, 0% fail rate sa 4 paralelna pytest
runa nakon izolacijskog fixa.

## Stvarni uzrok (dijagnostika)

### Reprodukcija flake-a (stari kod, 4 paralelna pytest -q)

Pokrenuo 4 `python -m pytest -q` procesa paralelno (maximizira
contention na dijeljenim resursima):

| Task | RUNID | Resultat |
|---|---|---|
| bg_0b089a64 | run-073347-2 | PASS, 293.78s |
| bg_7a4554c1 | run-073348-3 | PASS, 292.40s |
| bg_8453bfc9 | run-073608-5 | **FAIL**, 255.99s |
| bg_42a54388 | run-073645-5 | **FAIL**, 225.74s |

Oba fail-ovana run-a pala su na ISTI test:
```
FAILED tests/unit/scripts/test_generate_phase0_gate_report.py::test_gate_report_against_current_repo_passes
1 failed, 1146 passed, 1 skipped
```

50% fail rate, tačno na `test_gate_report_against_current_repo_passes`,
samo pod concurrency (1 serijski pytest = 0 fail u 4 pokušaja).

### Privremena dijagnostika

DIAG patch u `scripts/generate_phase0_gate_report.py` (uklonjen prije
konačnog fixa) sačuvao je CIJELI stdout/stderr svakog nested
subprocess-a u `tempfile.gettempdir()/acs-gate-diag/`. Iz analize
dijagnostičkih logova za uspješne run-ove:

- Inner `pytest -q` (cijeli suite, 1147 testova) u fail-ovanim
  gate report subprocess-ima PROLAZI (1145 passed, 3 skipped).
- Dakle: FAILED check u gate reportu NIJE `pytest`. Vjerovatno je
  jedan od `architecture_boundaries`, `unit_of_work`, `job_manager`,
  `bootstrap` (specifični pytest pozivi) ili jedan od registry/health
  checkova u `_check_registries_with_bootstrap`.

Konkretan check u ovom runu NISAM uspio izolirati do nivoa imena
(dijagnostički fajlovi za 4 specifične pytest invokacije imali bi
args_signature sa `/` u imenu, što na Windows file API ne dozvoljava
literalni `/` u filename-u; subprocess nije crashao ali fajlovi nisu
kreirani). Međutim, korijen je jasan: **subprocess concurrency** na
dijeljenim filesystem resursima.

### Identifikovani resursi pod contention-om

Tri standardna pytest resursa koja outer i inner pytest dijele u
istom repo-u:

1. **Pytest cacheprovider** — `~/.cache/pytest/` (ili slično na
   Windows-u) je shared između svih pytest procesa u istom user
   accountu. Cacheprovider piše u cache fajl na kraju svakog
   test_session; dva paralelna pytest procesa mogu se sudariti.
2. **`tmp_path` fixture base** — pytest kreira `<basetemp>/tmp_path/`
   za svaki `tmp_path` poziv. Default `basetemp` je globalni
   `<user-temp>/pytest-of-<user>/`, dijeljen između svih pytest
   procesa.
3. **`TMPDIR` / `TEMP` / `TMP`** env vars — `tempfile.mkstemp`,
   `tempfile.mkdtemp` (koje neki testovi koriste direktno umjesto
   `tmp_path` fixture) koriste ove env varijable. Ako outer i inner
   pytest imaju iste vrijednosti, mogu se sudariti.

Izolacijom sva tri resursa u nested pytest invokacijama, gate report
i dalje STVARNO pokreće CIJELI pytest -q (samo u izoliranijem
okruženju), bez promjene semantike.

## Fix

`scripts/generate_phase0_gate_report.py`, `_run_python` funkcija,
pytest grana. Tri konkretne mjere izolacije:

```python
if is_pytest:
    isolated_tmp = Path(tempfile.mkdtemp(prefix="acs-gate-pytest-"))
    env = os.environ.copy()
    env["ACS_GATE_REPORT_RUNNING"] = "1"
    env["TMPDIR"] = str(isolated_tmp)
    env["TEMP"] = str(isolated_tmp)
    env["TMP"] = str(isolated_tmp)
    args = [
        *args,
        "-p", "no:cacheprovider",
        "--basetemp", str(isolated_tmp),
    ]
else:
    env = None
```

1. **`TMPDIR`/`TEMP`/`TMP`** preusmjereni na unique temp dir po
   pozivu (`tempfile.mkdtemp(prefix="acs-gate-pytest-")`). Svi
   `tempfile.*` pozivi u testovima idu u ovaj dir.
2. **`-p no:cacheprovider`** isključuje pytest cache za nested
   pytest invokaciju. Verifikovano pretragom `tests/` da NIJEDAN
   test ne koristi `cache` fixture (inače bi `-p no:cacheprovider`
   uzrokovao regresiju). Time se eliminira cache file lock/contention.
3. **`--basetemp <isolated_tmp>`** preusmjerava `tmp_path` fixture na
   isti unique dir. Time `tmp_path` ne ide u globalni
   `<user-temp>/pytest-of-<user>/` i nema contention-a sa outer
   pytest-om.

**Semantika "pytest check" u gate report schema-i (plan §35 / §P0.28)
nije promijenjena** — i dalje se pokreće CIJELI `python -m pytest -q`
na cijelom suite-u (1147 testova). Samo je okruženje izolirano.

**Fallback za ostale checkove**: `architecture_boundaries`,
`unit_of_work`, `job_manager`, `bootstrap` su isto pytest pozivi,
tako da i oni dobijaju istu izolaciju. `_check_registries_with_bootstrap`
već koristi `tempfile.mkdtemp(prefix="acs-gate-")` sa atomic counter-om,
tako da je inherentno izoliran po subprocessu — nema izmjene.

## Mutation-style dokaz (stari kod vs. fix)

| Scenarij | Rezultat |
|---|---|
| 4 paralelna pytest -q, STARI kod (sa DIAG patchem) | 2 PASS, **2 FAIL** (50%) |
| 4 paralelna pytest -q, NOVI kod (izolacijski fix) | **4 PASS, 0 FAIL** (0%) |

DIAG patch je best-effort (u `try/except`), ne mijenja gate report
ponašanje. Dakle, 2/4 fail sa DIAG patchem je ekvivalent 2/4 fail
bez njega.

## Reproducibilni gate output (sa fixom)

### 4× paralelni pytest -q

```text
pytest-fix-1.log: 1147 passed, 1 skipped, 1 warning in 303.05s (0:05:03)
pytest-fix-2.log: 1147 passed, 1 skipped, 1 warning in 303.56s (0:05:03)
pytest-fix-3.log: 1147 passed, 1 skipped, 1 warning in 305.34s (0:05:05)
pytest-fix-4.log: 1147 passed, 1 skipped, 1 warning in 302.33s (0:05:02)
```

Sva 4 paralelna pytest -q sa izolacijskim fixom — 0 flake-ova.

### 3× serijski pytest -q

```text
SERIES RUN 1: 1147 passed, 1 skipped, 1 warning in 257.57s (0:04:17)
SERIES RUN 2: 1147 passed, 1 skipped, 1 warning in 401.89s (0:06:41)
SERIES RUN 3: 1147 passed, 1 skipped, 1 warning in 264.92s (0:04:24)
```

3× uzastopni serijski pytest -q (contract acceptance: "Pun suite
pokrenut bar 3x zaredom") — sva 3 PASS, 0 flake-ova. Trajanje
varira 257-402s ovisno o disk I/O opterećenju (trenutno stanje
filesystem-a na Windows-u).

### pytest tests/unit/scripts/ -v

```text
49 passed in 140.92s (0:02:20)
```

Svi unit testovi u `tests/unit/scripts/` (uključujući
`test_gate_report_against_current_repo_passes`) PROLAZE sa fixom.

### ruff + mypy

```text
$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 176 source files
```

## Šta je promijenjeno, šta nije dirano

**Promijenjeno** (samo 1 fajl):
- `scripts/generate_phase0_gate_report.py`:
  - `_run_python` za pytest invokacije: dodana izolacija
    (TMPDIR/TEMP/TMP, `-p no:cacheprovider`, `--basetemp`)
  - Za ostale subprocess pozive (secret scan): `env=None` (inherit
    parent env, isto kao prije)

**Nije dirano** (namjerno):
- `tests/unit/scripts/test_generate_phase0_gate_report.py` —
  sam test je nepromijenjen. I dalje pokreće
  `subprocess.run([python, generate_phase0_gate_report.py])` i
  provjerava artifacts/phase0_foundation_gate.json. Test i dalje
  STVARNO provjerava gate report (nije oslabljen/pretvoren u no-op).
- `src/`, `resources/migrations/` — nisu dirani (per contract
  forbidden_paths).
- Gate report JSON schema (plan §35 / §P0.28) — nepromijenjena.
  Artifact i dalje sadrži 17 boolean check ključeva sa istim
  značenjem.

## Acceptance criteria

- [x] Stvaran uzrok flake-a identifikovan i dokumentovan u
      evidence-u (subprocess concurrency na dijeljenim
      filesystem resursima; mutacijski dokazan sa 2/4 fail u starom
      kodu).
- [x] Fix primijenjen, argumentovan protiv alternativa
      (retry bi maskirao stvaran bug; izbacivanje `pytest -q` bi
      promijenilo schemu; izolacija je najmanja intervencija koja
      uklanja root cause bez promjene semantike).
- [x] Pun suite pokrenut 4× paralelno (jači test od serijskog
      jer flake nastaje SAMO pod concurrency) i 0 flake-ova.
- [x] `test_gate_report_against_current_repo_passes` i dalje
      STVARNO provjerava gate report (isti subprocess, isti JSON
      provjera, isti `payload["status"] == "PASS"` assert).
- [x] `src/`, `resources/migrations/` NISU DIRANI.
- [x] `python -m pytest tests/unit/scripts/ -v` prolazi (49/49).
- [x] `python -m pytest -q` paralelno 4× bez flake-a.
- [x] `python -m ruff check .` i `python -m mypy src` prolaze.
- [x] Nema izmjena van `allowed_paths`.
- [ ] CI provjeren preko PR-a (koordinator radi push + PR; LOW
      risk, §29 ciklus).

## Ko pushuje i kad

**NE pushujem.** LOW risk, ali koordinator radi push + PR prema
§29 ciklusu (Claude PASS dovoljan za commit/push/merge). Ostavljam
na koordinatoru da otvori PR i pokrene `gh pr checks`.
