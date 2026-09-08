---
task_id: ACS-F1-052
phase: "Test infrastructure -- fix the recursive gate-report flake"
title: "Dijagnostikovati i popraviti povremeni fail test_gate_report_against_current_repo_passes"
risk: LOW
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - scripts/generate_phase0_gate_report.py
  - tests/unit/scripts/test_generate_phase0_gate_report.py
forbidden_paths:
  - src/
  - resources/migrations/
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Test/tooling-only izmjena, nula produkcijskog koda, nula
    novih/izmijenjenih execution flow-ova. GitNexus impact provjera
    nije potrebna, ali `gitnexus_detect_changes()` prije commit-a i
    dalje obavezan (workflow non-negotiable pravilo, primjenjuje se na
    SVAKI task bez izuzetka).
---

# Kontekst

`test_gate_report_against_current_repo_passes`
(`tests/unit/scripts/test_generate_phase0_gate_report.py`) je
end-to-end test koji pokreće STVARAN
`scripts/generate_phase0_gate_report.py` kao subprocess. Taj skript,
kao dio svog "pytest" provjere, SAM pokreće `python -m pytest -q`
(cijeli suite, ~1120+ testova) kao SVOJ VLASTITI subprocess, sa
`ACS_GATE_REPORT_RUNNING=1` da spriječi beskonačnu rekurziju (unutrašnji
pytest, kad stigne do ISTOG ovog testa, ga preskoči zahvaljujući tom
env varu).

**Poznat, dva puta nezavisno potvrđen problem:** kad se PUN test suite
pokrene normalno (`pytest -q`, BEZ `ACS_GATE_REPORT_RUNNING=1` na
spoljašnjem nivou), ovaj test POVREMENO padne -- ali IZOLOVANO (samo
ovaj test, `-k test_gate_report_against_current_repo_passes`) UVIJEK
prolazi. Ovo je potvrđeno:

1. Od strane implementera (Crush) u
   `agent_reports/2026-09-07-ACS-F1-049-brend-read-path-evidence.md` --
   "pada SAMO kad se pokreće unutar celog suite-a (rekurzivni
   subprocess pytest -q pokreće 1123 testova dok spoljašnji suite još
   radi); izolovano prolazi".
2. Nezavisno reprodukovano od strane koordinatora (Claude) istog dana
   -- izolovan pokreni PASS, pun suite pokreni PASS (ali sporo, drugi
   put).
3. Nezavisno potvrđeno od strane Codex-a u
   `agent_reports/2026-09-08-ACS-F1-049-review-codex.md` -- "postojeći
   `google.genai` ... deprecation warning; nije povezano s ovim fixom"
   (ali gate-report testa flakiness NIJE bio predmet tog reviewa, samo
   napomenut kao poznat/pre-existing).

**Stvaran trošak, ne samo kozmetički problem:** svaki `pytest -q` pun
suite run PLAĆA cijenu JOŠ JEDNOG punog nested suite run-a (~130-175s
duplo vrijeme) SAMO zbog ovog jednog testa. Ovo usporava SVAKI review
ciklus u projektu (implementer verifikacija, coordinator nezavisna
verifikacija, CI) i stvara tačno onu vrstu intermitentnog faila koji
troši vrijeme na debagovanje "da li je ovo moja izmjena ili poznat
flake" -- pitanje koje se ovog dana postavilo DVA PUTA.

# Objective

## 1. Dijagnostikovati STVARAN uzrok (PRIJE bilo kakvog fixa)

Trenutno NIKO nije utvrdio KOJI konkretan nested test (od ~1120) puca
pod concurrency-om, niti ZAŠTO (resource contention -- fajl/port/
SQLite lock/temp dir sudar između spoljašnjeg i unutrašnjeg pytest
procesa koji rade istovremeno -- je najvjerovatnija hipoteza, ali NIJE
POTVRĐENA). Implementer MORA:

1. Reprodukovati flake pouzdano (npr. pokrenuti pun suite VIŠE puta
   zaredom, ili namjerno pokrenuti gate-report subprocess dok drugi
   pun suite proces radi paralelno, da izazove isti resource
   contention).
2. Uhvatiti STVARAN nested test failure (ne samo "subprocess vratio
   exit 1") -- `generate_phase0_gate_report.py`-ov `_run_python`
   trenutno hvata SAMO `stderr` posljednji red u `detail` polju; možda
   treba privremeno instrumentisati da se vidi puni pytest output iz
   unutrašnjeg subprocess-a dok se dijagnostikuje (NE ostavljati tu
   instrumentaciju u finalnom fixu ako širi `no_secrets_detected`-stil
   rizik curenja).
3. Identifikovati TAČAN uzrok i prijaviti ga u evidence-u PRIJE
   predlaganja fixa -- isti "investigate and report" standard kao
   G5-ova valuta/G6-ova agregaciona semantika.

## 2. Odabrati najmanji siguran fix

Implementer bira pristup na osnovu STVARNOG nalaza iz #1. Mogući
pravci (implementer NIJE ograničen na ovu listu, ali svaki izbor mora
biti argumentovan):

- Ako je uzrok resource contention na specifičnom testu (fajl/port/temp
  dir) -- popraviti TAJ test da bude concurrency-safe (npr. jedinstven
  temp path po test run-u umjesto fiksnog). **Ako je taj test VAN
  `allowed_paths`, NE širiti scope sam -- prijaviti tačnu lokaciju kao
  `OUT_OF_SCOPE_FINDING`, koordinator odlučuje da li se scope proširuje
  ili se bira drugi pristup.**
- Ako je uzrok generička concurrency krhkost (npr. dijeljen SQLite fajl
  put), razmotriti da li `generate_phase0_gate_report.py`-ov nested
  pytest treba raditi u izolovanijem okruženju (npr. eksplicitan
  `-p no:cacheprovider` ili drugi radni direktorij za artefakte) --
  ovo OSTAJE u `allowed_paths` (sam skript).
- Ako se pouzdan root cause NE MOŽE naći u razumnom vremenu, prihvatljiv
  fallback je smanjiti frekvenciju/trošak nested run-a (npr. dodati
  eksplicitan retry sa jasnom porukom UNUTAR
  `test_gate_report_against_current_repo_passes` SAMO ako se dokaže da
  je flake istinski nedeterministički a ne bug koji retry sakriva --
  implementer mora argumentovati da retry NE maskira stvaran bug prije
  nego što ga doda).

**NE prihvatljivo:** obrisati/skip-ovati test bez zamjene (gate report
mora ostati stvarno provjeren), niti tiho promijeniti šta "pytest
check" znači u gate report schema-i (§35/§P0.28 kontrakt) bez
eksplicitnog navoda te promjene u evidence-u.

# Implementation steps

1. Reprodukovati flake, uhvatiti stvaran nested failure (Objective #1).
2. Prijaviti tačan uzrok u evidence-u.
3. Implementirati najmanji siguran fix (Objective #2), sa
   obrazloženjem zašto je taj pristup izabran nad alternativama.
4. Dokazati fix: pokrenuti PUN suite VIŠE puta zaredom (bar 3x) i
   potvrditi 0 flake-ova; ako je root cause bio specifičan test,
   dokazati mutation-style da bi STARI kod i dalje flake-ovao pod istim
   uslovima (npr. privremeno vratiti staru verziju, reprodukovati fail,
   vratiti fix).
5. Puni gate (uključujući samu `test_gate_report_against_current_repo_passes`
   koju je ovaj task upravo mijenjao -- posebno paziti da se ne uvede
   novi flake).

# Acceptance

- [ ] Stvaran uzrok flake-a identifikovan i dokumentovan u evidence-u
      (ne pretpostavljen).
- [ ] Fix primijenjen, argumentovan protiv alternativa.
- [ ] Pun suite pokrenut bar 3x zaredom bez ijednog flake-a na ovom
      testu (dokazano u evidence-u sa stvarnim output-om, ne tvrdnjom).
- [ ] `test_gate_report_against_current_repo_passes` i dalje STVARNO
      provjerava gate report protiv trenutnog repo-a (nije oslabljen/
      isprazan da bi "uvijek prošao").
- [ ] Ako je root cause zahtijevao izmjenu VAN `allowed_paths`,
      prijavljeno kao `OUT_OF_SCOPE_FINDING`, NE tiho prošireno.
- [ ] `src/`, `resources/migrations/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/scripts/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, pokrenuto bar 3x
      zaredom, 0 flake-ova, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze (ako je
      `scripts/` pod mypy/ruff obuhvatom -- provjeriti `pyproject.toml`).
- [ ] Nema izmjena van `allowed_paths` (osim eksplicitno prijavljenog
      i odobrenog OUT_OF_SCOPE_FINDING proširenja).
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/scripts/ -v
python -m pytest -q
python -m pytest -q
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-052-fix-gate-report-flake
gh pr create --base main --title "ACS-F1-052: Fix flaky gate report end-to-end test"
gh pr checks
```

# Review focus — Claude (LOW, §29)

- Dijagnoza je stvarna (ima konkretan uhvaćen nested failure, ne
  nagađanje).
- Fix je najmanji mogući, ne širi scope, ne slabi test.
- 3x zaredom pun suite PASS je stvarno dokazan u evidence-u.
- Test i dalje ima smisao (nije pretvoren u no-op).

# Rollback

LOW risk -- izolovana test/tooling izmjena, nula produkcijskog koda,
nula uticaja na runtime/GUI/domain. Claude-only review → odmah merge
po §29 ako PASS.

# Coordination

Potpuno nezavisno od ACS-F1-050 (P1.5-G6, `domain/performance/` +
`application/performance/` + `ports/` + `infrastructure/database/`) i
ACS-F1-051 (Početna dashboard, `presentation_webview/` +
`presentation/`) -- `allowed_paths` (`scripts/` + jedan test fajl) se
ne preklapa ni sa jednim od njih. Bezbjedno za treći paralelan task u
istoj rundi.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-052-fix-gate-report-flake
Branch:   task/ACS-F1-052-fix-gate-report-flake
Base:     main @ 941ae97
```
