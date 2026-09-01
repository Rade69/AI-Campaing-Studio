---
task_id: ACS-HOTFIX-001
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
tests: PASS
gitnexus_impact: LOW (single-file fix to already-analyzed jobs/manager.py, no new upstream/downstream surface)
blocking_findings: 0
---

# ACS-HOTFIX-001 — Claude review

## CILJ

Popraviti `JobManager` `CREATED`/`STARTED` event-ordering race, regresiju
otkrivenu na `main`-u preko GitHub Actions CI nakon ACS-P0-007 merge-a.

## PROVJERENO

- `git status --short` na `57b28a7`: tačno `src/ai_campaign_studio/jobs/manager.py`
  i `tests/unit/jobs/test_manager.py`, oba unutar `allowed_paths`.
- Pun diff pročitan i razumljen: `threading.Lock()` → `threading.RLock()`,
  `self._emit(CREATED)` pomjeren unutar `submit()`-ovog `with self._lock:`
  bloka, `_emit()` sada drži lock kroz cio callback dispatch (ne samo
  snapshot korak).
- BF-1/R2-BF-1 regression testovi iz ACS-P0-007 (submit-after-shutdown,
  queued-job-shutdown-cancellation) i dalje prolaze nepromijenjeni.

## Proces napomena — greška koordinatora tokom verifikacije, riješena

Tokom pokušaja reprodukcije "prvog neuspješnog pokušaja fix-a" preko
`git stash`/`checkout stash@{0} -- <path>` manevra, greškom sam vratio
`tests/unit/jobs/test_manager.py` na zadnju commit-ovanu (pred-hotfix)
verziju, brišući MiniMax-ov jedini novi, tada još necommit-ovan test iz
radnog stabla. `manager.py` nije bio pogođen. MiniMax je ponovo dodao test;
nezavisno sam potvrdio njegovo prisustvo i sadržaj prije nastavka reviewa.
Ostatak adversarial rada rađen isključivo preko Edit/Read alata (ne dalje
git history manipulacije) da se izbjegne ponavljanje greške.

## GITNEXUS / IMPACT

Jednofajlni fix na već analiziranom `jobs/manager.py` (GitNexus pre-impact
za ovaj fajl već urađen na ACS-P0-007 — 0-1 upstream callera, sve u
`bootstrap.py`/testovima). Nema nove površine. Post-change re-index nije
pokrenut (poznat worktree-binding gap) — nije blokirajuće za jednofajlni
concurrency fix bez promjene javnog API-ja.

## BLOCKING FINDINGS

Nema.

## STANDARDNA VERIFIKACIJA (nezavisno pokrenuto od koordinatora, sa eksplicitnim PYTHONPATH override-om preko dijeljenog .venv-a)

```
python -m pytest -q                                → 171 passed
python -m pytest tests/unit/jobs/test_manager.py -v → 17 passed
python -m ruff check .                              → All checks passed!
python -m mypy src                                  → Success: no issues found in 51 source files
20x loop -k "event_sequence or event_ordering_under_slow" → 20/20 clean
```

## ADVERSARIALNA PROVJERA — nezavisna, otišla dalje od implementerovog dokaza

Reprodukovao sam fix, i pritom otkrio nešto što implementerov sopstveni
dokaz nije pokazao:

1. Djelomičan revert #1 (samo `_emit`-ovo držanje lock-a kroz callback-e
   vraćeno na snapshot-pa-otpusti obrazac, RLock + emit-unutar-submit-lock-a
   netaknuti): test i dalje PASS, 10/10. RLock rekurzivno brojanje kroz
   `submit()`-ov vanjski blok je SAMO PO SEBI dovoljno.
2. Djelomičan revert #2 (plain `Lock` umjesto `RLock`, `CREATED` emit
   vraćen izvan `submit()`-ovog lock bloka, `_emit`-ovo držanje lock-a kroz
   callback-e netaknuto, čak i sa 2-sekundnim prozorom): test i dalje PASS,
   5/5. `_emit`-ovo držanje lock-a kroz dispatch je SAMO PO SEBI dovoljno.
3. Pun revert (sva tri elementa istovremeno pokvarena): test pouzdano
   FAILUJE, 5/5, sa tačnim originalnim simptomom.
4. Vraćeno na tačan fix (bez ostatka), potvrđen PASS ponovo (171 testova,
   20/20 ciljana petlja).

**Zaključak**: isporučeni fix ima stvarnu redundanciju — bilo koja dva od
tri elementa su samostalno dovoljna za ovaj specifičan test. Nije defekt
(razumna defense-in-depth za concurrency fix, i kombinacija ima nezavisnu
vrijednost za druga emit mjesta koja ne dijele `submit()`-ov specifičan
lock-nesting oblik), ali ispravlja evidence report-ovu tvrdnju da je "fix
kompletan samo sa sve tri promjene" — nije sasvim tačna kao minimality
claim. Ne-blokirajuće, zabilježeno radi tačnosti zapisa.

## NE DIRATI U FIX RUNDI

Implementacija je stabilna i minimalna po opsegu (jedan fajl, plus testovi).
Ne dirati: BF-1/R2-BF-1 mehanizme iz ACS-P0-007 (netaknuti, potvrđeno),
ostala emit mjesta (`cancel`, `_finish`, `_finish_cancelled_futures`) — svi
i dalje rade ispravno bez izmjene.

## SLJEDEĆE

Codex review (HIGH risk — regresija na već merge-ovanom foundation kodu,
puni ciklus po §29). Priprema `codex-review-request.md` sa fokusom na
redundant-protection nalaz i .pth environment gotcha.
