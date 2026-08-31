# Codex review request — ACS-P0-003

Za: Codex (adversarial/test reviewer)
Od: Claude (koordinator)
Datum: 2026-08-31

## Kontekst

Ovo je jedan od dva paralelna P0 taska pokrenuta nakon ACS-P0-002 (drugi je
ACS-P0-004, čeka se odvojeno). `allowed_paths` su disjoint od ACS-P0-004
(potvrđeno u oba kontrakta) — nema preklapanja.

## Read protocol

1. `AGENTS.md`, `CLAUDE.md`
2. `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §14/§15
3. `.agent/CURRENT_STATE.md`
4. `agent_reports/ACS-P0-003-task-contract.md`
5. `agent_reports/2026-08-31-ACS-P0-003-pi-confirmed.md` (coordinator evidence)
6. Sam diff (vidi ispod)

## Šta pregledati

```text
Repo:     H:\AI Campaing Studio  (main branch)
Worktree: H:\ai-campaign-studio-worktrees\ACS-P0-003-localization
Branch:   task/ACS-P0-003-localization
Commit:   0c23bcf (base: main@a712ce3)
```

```bash
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-003-localization --stat
git -C "H:\AI Campaing Studio" diff main task/ACS-P0-003-localization
```

Napomena: dva-tačka diff protiv trenutnog `main` tip-a može pokazati i
promjene iz drugih koordinator commit-a (npr. `.agent/CURRENT_STATE.md`)
koje nisu dio ovog taska — koristi merge-base diff ako treba čist prikaz:
`git diff $(git merge-base main task/ACS-P0-003-localization) task/ACS-P0-003-localization`.
Svi fajlovi ovog taska su NOVI (nema izmjene postojećih), pa scope provjera
je jednostavna: sve što je `A` (added) mora biti u `allowed_paths`.

Poznato GitNexus worktree-binding ograničenje i dalje važi — `detect-changes`
iz task worktree-a neće raditi, tretiraj kao `UNKNOWN`.

## Fokus review-a

1. **Translator fallback edge cases** — pored EN-fallback (već testiran),
   probaj: `set_locale` na nepoznat/nevalidan locale (mora `ValueError`, ne
   silent no-op); interpolacija sa VIŠE `{param}` placeholder-a i
   djelimično nedostajućim parametrima; da li `t()` ikad može baciti
   neuhvaćenu exception (npr. malformed template string sa `{` bez
   zatvaranja — `str.format` bi bacio `ValueError`, provjeri da li je to
   uhvaćeno).
2. **`ContentLanguageContext` invarijante** — probaj kreirati instancu sa
   `language_family=BHS, regional_variant=NEUTRAL, locale=EN` (mixed
   combo koji kontrakt ne spominje eksplicitno) — da li validator to
   dozvoljava ili odbija, i da li je to ispravno ponašanje po specifikaciji
   (locale i language_family su namjerno odvojeni koncepti — provjeri da
   li nedostaje invarijanta koja bi trebalo da poveže locale sa
   language_family/regional_variant, ili je namjerno nezavisno).
3. **`validate_resources.py` edge cases** — YAML fajl sa `version: "1"`
   (string umjesto int) mora biti odbijen; YAML fajl sa dodatnim
   nepredviđenim poljem (da li se toleriše ili odbija — nije eksplicitno
   specificirano, provjeri da checker bar ne puca); JSON sa nested
   objektom kao vrijednost (validator pretpostavlja `dict[str,str]` flat
   strukturu — da li bi to prošlo neopaženo i uzrokovalo runtime problem u
   `translator.py`?).
4. **Duplicate-key detekcija** — potvrdi da `object_pairs_hook` pristup
   stvarno hvata duplicate JSON ključeve (Python `json` modul bez ovog hook-a
   tiho overwrite-uje duplikate).
5. **Regresija/standardna verifikacija** — ponovo pokreni nezavisno:
   ```bash
   cd "H:\ai-campaign-studio-worktrees\ACS-P0-003-localization"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m mypy src
   .\.venv\Scripts\python.exe scripts\validate_resources.py
   ```
   (worktree ima svoj `.venv`, kreiran od koordinatora za ovaj review ciklus).

## Traženi output

`agent_reports/2026-08-31-ACS-P0-003-review-codex.md`, isti format kao
`agent_reports/2026-08-31-ACS-P0-003-review-claude.md`.

Ako `PASS`/`PASS_WITH_NOTES` bez blocking findings, tražim Human Owner
odobrenje za merge (ACS-P0-004 se review-uje odvojeno — obje mergu ne moraju
čekati jedna drugu, samo moraju obje biti spremne prije nego što se pokrenu
003–006 zavisni taskovi kao skup).
