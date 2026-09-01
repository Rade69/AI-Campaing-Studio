---
task_id: ACS-P0-008
phase: P0
title: "Resource validators + CI quality gate + security/no-secret checks + P0 gate report"
risk: HIGH
coordinator: claude
implementer: minimax
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-09-01
dependencies: [ACS-P0-001, ACS-P0-002, ACS-P0-003, ACS-P0-004, ACS-P0-005, ACS-P0-006, ACS-P0-007]
allowed_paths:
  - scripts/validate_resources.py
  - scripts/check_no_secrets.py
  - scripts/generate_phase0_gate_report.py
  - src/ai_campaign_studio/resources_validation.py
  - .github/workflows/ci.yml
  - artifacts/phase0_foundation_gate.json
  - artifacts/.gitkeep
  - tests/unit/scripts/
  - tests/unit/resources_validation/
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/localization/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/jobs/
  - src/ai_campaign_studio/presentation/
  - src/ai_campaign_studio/bootstrap.py
  - src/ai_campaign_studio/main.py
  - presentation_qt/
  - presentation_webview/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  repository: "H:\\AI Campaing Studio"
  worktree: main (pre-branch pre-impact)
  branch: main
  head: 65a02de
  index_status: stale (last indexed 4e78a90) — analyze re-run recommended before merge, not blocking for this pre-impact
  targets:
    - symbol: "all allowed_paths files"
      upstream_risk: NONE
      upstream_count: 0
      downstream_notes: "Every file this task creates is a new standalone script/artifact (validate_resources.py, check_no_secrets.py, generate_phase0_gate_report.py) or a CI config edit. None are imported by existing runtime code (bootstrap.py, main.py, jobs/, presentation/) — this task only adds tooling on top of the finished foundation, it does not wire anything new into the composition root."
      affected_processes: ["CI pipeline only"]
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Posljednji P0 coding task. Sva 7 prethodnih P0 taskova (001–007) su merged
— puna foundation površina postoji: config, logging, common errors,
localization, channel/platform registry, AI provider/model registry,
secret store, SQLite + migrations + UoW, JobManager, framework-neutral
presentation contracts/state, i pun `bootstrap.py` composition root sa
`--health-check`.

Ovaj task NE dodaje novu runtime funkcionalnost u `src/ai_campaign_studio/`
osim opcionog `resources_validation.py` helper modula. Umjesto toga
proizvodi alate koji PROVJERAVAJU da je sve prethodno stvarno ispravno:
resource validaciju, CI quality gate, security/no-secret sken, i finalni
machine-readable P0 gate izvještaj.

**HIGH risk** — security-critical (no-secret scan, authoritativni PASS/FAIL
artefakt za cijelu P0 fazu) — ostaje na punom Codex+Claude+Human Owner
ciklusu (workflow §29).

**Implementer za ovaj task: MiniMax** (novi agent, dodat 2026-09-01, isti
implementer/reviewer profil kao Codex — za ovaj task angažovan kao
implementer). Isti "implementer != reviewer" princip važi.

GitNexus pre-impact: sve što ovaj task pravi su novi standalone
skripte/artefakti bez postojećih upstream callera — nema rizika od
skrivenog uticaja na postojeći kod. `scope_fit: PASS`.

Prije koda pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
docs/AI_CAMPAIGN_STUDIO_NACIN_RADA.md
.agent/CURRENT_STATE.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcije 31–35 (P0.24–P0.28)
```

# Objective

1. `scripts/validate_resources.py` — validira sve bundled resurse.
2. `.github/workflows/ci.yml` — proširiti postojeći CI da uključi resource
   validaciju i health-check.
3. `scripts/check_no_secrets.py` — sken tracked fajlova za stvarne secrete.
4. `scripts/generate_phase0_gate_report.py` — pokreće sve P0.27 provjere
   PROGRAMATSKI (ne hardcoded `true` vrijednosti) i piše
   `artifacts/phase0_foundation_gate.json`.

# Implementation steps

## P0.24 — Resource validators

1. `scripts/validate_resources.py` kao thin entrypoint; ako logika postane
   velika, staviti je u `src/ai_campaign_studio/resources_validation.py` i
   script samo poziva tu funkciju.
2. Provjeriti:
   - **i18n**: validan JSON, UTF-8, parity ključeva između lokala, BHS
     dijakritici prisutni gdje se očekuju.
   - **regional language resursi**: validan YAML, `family`/`variant`/
     `version` polja prisutna.
   - **platforms**: validan schema, jedinstveni kodovi, validni channel/
     format referenceovi.
   - **AI providers**: validan schema, jedinstveni provider kodovi, **bez
     secret-like polja** (ovo je i sigurnosna provjera, ne samo shape
     provjera).
   - **migrations**: format imena fajla, jedinstvene verzije, ispravan
     redoslijed, checksum čitljiv.
3. Exit 0 na uspjeh, exit 1 i jasna poruka na bilo koji neuspjeh.
4. Koristiti postojeće registryje/loaders (`PlatformRegistry`,
   `AIProviderRegistry`, `Translator`, migration `discover_migrations`) gdje
   god je moguće umjesto pisanja paralelne parsing logike — ne duplirati
   validaciju koja već postoji u tim klasama, samo je pozvati i provjeriti
   dodatne invarijante (npr. parity ključeva, BHS dijakritici) koje same
   klase ne provjeravaju.

## P0.25 — CI quality gate

5. Proširiti `.github/workflows/ci.yml` (postojeći: checkout → setup Python
   3.12 → install → ruff → mypy → pytest) da doda:
   - `python scripts/validate_resources.py`
   - `python -m ai_campaign_studio.main --health-check` **sa temp/data
     override** (postavi `AI_CAMPAIGN_STUDIO_DATA_DIR`/ekvivalentnu env
     varijablu ili CLI flag na runner-specifičan temp direktorijum — ne
     smije pisati u default user AppData na CI runneru; provjeri kako
     `AppSettings`/`AppPaths` već podržavaju override iz env-a prije nego
     što izmišljaš novi mehanizam).
6. CI ne smije zahtijevati: OpenAI/Anthropic ključ, internet API poziv,
   Playwright browser, desktop GUI, pravi OS keyring. Health-check u CI
   mora raditi sa `EnvironmentSecretStore` (development/test putanja), ne
   sa keyring adapterom.

## P0.26 — Security / no-secret checks

7. `scripts/check_no_secrets.py`: skenira TRACKED fajlove (koristi `git
   ls-files`, ne filesystem walk — ne smije skenirati `.venv`/`node_modules`/
   netracked scratch) za stvarne secret-shaped vrijednosti:
   - `sk-[A-Za-z0-9]{16,}` (stvaran OpenAI-shaped key, ne goli `sk-` substring)
   - `api_key\s*=\s*["'][^"'\s]{8,}["']` sa vrijednošću koja NIJE očigledan
     placeholder (`EXAMPLE`, `REDACTED`, `xxx`, `your-key-here`,
     `placeholder`, prazan string)
   - `Authorization:\s*Bearer\s+[A-Za-z0-9._-]{16,}`
   - `ANTHROPIC_API_KEY\s*=\s*["']?[A-Za-z0-9_-]{16,}`
   - `OPENAI_API_KEY\s*=\s*["']?[A-Za-z0-9_-]{16,}`
8. **VAŽNO — self-referential lažni pozitivi**: ovaj task, njegov task
   contract, plan dokument (`AI_Campaign_Studio_Implementation_Phase_0_v1_1_...md`),
   i sam `check_no_secrets.py` izvorni kod će SADRŽATI stringove poput
   `"sk-"`, `"api_key="`, `"OPENAI_API_KEY="` kao dio regex pattern-a ili
   dokumentacije o tome šta se traži. Scanner MORA razlikovati "pattern
   koji opisuje šta tražiti" od "stvarnu vrijednost nalik ključu". Prije
   svega: **isključi `*.md` dokumentaciju i `agent_reports/` iz skena**
   (to su plan/proces dokumenti, ne runtime konfiguracija) — skeniraj samo
   `src/`, `tests/`, `scripts/`, resource fajlove (`*.json`, `*.yaml`,
   `*.yml`, `*.sql`), i root config (`pyproject.toml`, `config.example.toml`
   ako postoji). Dodatno, regex mora tražiti STVARAN key-shaped string
   (dovoljno dugačak, alfanumeričan), ne goli literal substring — tako da
   scanner-ov sopstveni izvorni kod (koji SADRŽI te literal stringove kao
   dio regex pattern definicije, npr. `PATTERN = r"sk-[A-Za-z0-9]{16,}"`)
   ne self-matchuje na svoj vlastiti pattern-definicioni string ako taj
   string sam po sebi nije key-shaped (regex definicija sadrži `[A-Za-z0-9]`
   metakaraktere, ne 16+ stvarnih alfanumeričkih karaktera zaredom, pa
   prirodno neće pogoditi sopstveni pattern — provjeri ovo eksplicitno
   testom).
9. `.gitignore` mora pokrivati `.env`, `.env.*` (dodati ako nedostaje;
   provjeri prvo šta već postoji).
10. Exit 0 = `NO CONFIRMED SECRET IN TRACKED FILES`, exit 1 + tačna lokacija
    (fajl:linija) na nalaz.

## P0.27 — Full foundation verification (dio P0.28 generatora, ne zaseban fajl)

11. Ovo NIJE zaseban script — to je set provjera koje
    `generate_phase0_gate_report.py` (P0.28) programatski pokreće i čiji
    rezultat upisuje u JSON. Implementer treba i sam ručno pokrenuti ovaj
    set prije predaje (vidi Verification ispod).

## P0.28 — P0 Gate report

12. `scripts/generate_phase0_gate_report.py`: piše
    `artifacts/phase0_foundation_gate.json` prema tačnoj shemi iz plan
    dokumenta (§35), sa key-jevima: `package_import`, `ruff`, `mypy`,
    `pytest`, `architecture_boundaries`, `translations`,
    `regional_language_resources`, `platform_registry`,
    `provider_registry`, `secret_store`, `database_connection`,
    `migrations`, `unit_of_work`, `job_manager`, `bootstrap`,
    `health_check`, `no_secrets_detected`.
13. **Svaki check mora biti STVARNO IZVRŠEN od generatora** (subprocess
    poziv stvarnoj komandi ili import + direktan funkcijski poziv), NE
    hardcoded `true`. Ako generator ne može stvarno provjeriti nešto (npr.
    `unit_of_work` nema samostalnu CLI provjeru), pozvati odgovarajući
    pytest subset (`pytest tests/unit/... -q`) i parsirati exit code —
    ne izmišljati provjeru koja uvijek prolazi.
14. `status` polje: `"PASS"` samo ako su SVI checks `true`. Nikad `PASS` sa
    bilo kojim `false` check-om (eksplicitna zabrana iz plana).
15. `ui_framework`: `"NOT_SELECTED"` (tačno, UI-GATE nije još prošao).
    `campaign_engine_implemented`/`website_ingestion_implemented`: `false`.
16. Fajl `artifacts/phase0_foundation_gate.json` se COMMIT-uje samo ako
    `status == "PASS"` na finalnoj verziji koda (implementer generiše i
    prilaže rezultat u evidence report; coordinator ponovo generiše i
    verifikuje prije merge-a).

# Acceptance

- [ ] `python scripts/validate_resources.py` exit 0 na trenutnom stanju
      resursa.
- [ ] `python scripts/validate_resources.py` exit 1 kad se namjerno pokvari
      jedan resurs (adversarial dokaz, vidi ispod).
- [ ] `python scripts/check_no_secrets.py` exit 0 na trenutnom stanju repoa.
- [ ] `python scripts/check_no_secrets.py` exit 1 kad se namjerno ubaci
      stvaran key-shaped string u tracked fajl unutar skeniranog scope-a
      (adversarial dokaz).
- [ ] `python scripts/check_no_secrets.py` NE prijavljuje lažni pozitiv na
      sopstveni izvorni kod niti na `config.example.toml`-style placeholder.
- [ ] `.github/workflows/ci.yml` sadrži resource validation + health-check
      korake, i dalje ne zahtijeva nijedan live servis/ključ/GUI/keyring.
- [ ] `python scripts/generate_phase0_gate_report.py` proizvodi
      `artifacts/phase0_foundation_gate.json` sa `status: "PASS"` i svim
      check-ovima `true` na finalnom stanju koda.
- [ ] Gate report generator: kad se namjerno pokvari jedan check (npr.
      privremeno slomljen test), `status` postaje `"FAIL"` i taj konkretan
      check je `false` — NE `PASS` sa skrivenim `false` (adversarial dokaz).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` i dalje prolaze
      (uključujući nove testove za validatore/scanner/generator).
- [ ] Nema izmjena u `forbidden_paths` (postojeći runtime kod netaknut).

# Adversarial test (obavezno — adversarial_required: true)

## 1. Resource validator hvata pokvaren resurs

Privremeno pokvariti jedan bundled resurs (npr. dupliciraj platform code u
`platforms/*.json`, ili ukloni jedan i18n ključ iz jednog lokala) → potvrdi
`validate_resources.py` FAIL sa jasnom porukom → vrati originalno stanje →
potvrdi PASS.

## 2. Secret scanner hvata stvaran ključ, ignoriše sopstveni pattern-definicioni kod

- Privremeno dodaj fajl (van git-ignorisanih putanja, u skeniranom scope-u,
  npr. `src/ai_campaign_studio/_adversarial_probe.py`) sa sadržajem koji
  liči na stvaran ključ, npr.
  `OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"` → potvrdi
  `check_no_secrets.py` FAIL, prijavljuje tačnu lokaciju → ukloni fajl →
  potvrdi PASS.
- Zasebno dokazati da scanner-ov VLASTITI izvorni kod (`check_no_secrets.py`
  sam, koji sadrži pattern-definicione stringove poput `"sk-"` unutar
  regex-a) NE self-matchuje — ako scanner naivno grep-uje bez razumijevanja
  regex konteksta, ovo će biti false positive na sopstveni fajl; dokazati
  da nije.

## 3. Gate report generator ne laže o statusu

Privremeno slomiti jedan pravi check (npr. privremeno unesi sintaksnu
grešku u jedan test fajl tako da `pytest` padne) → pokreni generator →
potvrdi da `pytest` check postaje `false` I `status` postaje `"FAIL"` (ne
`PASS` sa skrivenim `false`) → vrati original → potvrdi `status: "PASS"`
ponovo.

Dokumentuj sva tri FAIL→PASS ciklusa doslovno (output, ne parafraza).

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
python scripts/validate_resources.py
python scripts/check_no_secrets.py
python -m ai_campaign_studio.main --health-check
python scripts/generate_phase0_gate_report.py
cat artifacts/phase0_foundation_gate.json
git status --short
```

# Review focus — Codex

- da li secret scanner ima realne bypass forme (npr. multi-line
  konkatenacija ključa, base64-enkodovan ključ, ključ razbijen preko dva
  stringa `"sk-" + "abc..."`) — vjerovatno van P0 scope-a da se sve pokrije,
  ali procijeni da li je trenutni nivo proporcionalan;
- da li gate report generator STVARNO izvršava svaki check (subprocess/
  import + poziv) ili neki key ima hardcoded/lažnu proveru;
- da li CI health-check korak stvarno izoluje temp/data path (provjeri da
  CI runner ne pokušava pisati u pravi user AppData ili pristupiti pravom
  keyring-u);
- da li `validate_resources.py` duplira validacionu logiku koja već postoji
  u `PlatformRegistry`/`AIProviderRegistry`/`Translator`/`migrations.py`
  umjesto da je ponovo koristi;
- edge case: šta se desi ako `artifacts/` direktorijum ne postoji kad
  generator pokuša da piše (mora ga kreirati, ne pući).

# Review focus — Claude

- scope discipline — nema dirania `forbidden_paths`, nema nove business
  logike u `src/ai_campaign_studio/`;
- da li je `resources_validation.py` (ako je kreiran) framework-neutral i
  bez suvišnih zavisnosti;
- konzistentnost sa postojećim error-handling/exit-code konvencijama iz
  `main.py --health-check`;
- da li je secret-scanner scope (koji fajlovi se skeniraju/isključuju)
  razuman i dokumentovan u samom kodu (ne samo u contract-u).

# Rollback

HIGH task (security-critical, finalni P0 gate). Ako adversarial dokaz za
secret scanner ili gate report generator ne dokazuje invarijant — NE
spajati, fix na istoj branch bez proširenja scope-a.

# Dependency baseline

Zavisi od SVIH prethodnih P0 taskova (001–007), svi merged, `main`@`65a02de`.
Ne granati sa starijeg main-a.

# Coordination

Nema paralelnog P0 taska — ovo je jedini i posljednji preostali P0 task.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-008-validators-ci-security-gate
Branch:   task/ACS-P0-008-validators-ci-security-gate
Base:     main @ 65a02de
```

Nakon merge-a i P0-GATE PASS: post-merge gate, GitNexus re-index,
CURRENT_STATE update na `P0-GATE: PASS`, priprema za prelazak na Faza 1
(nakon eksplicitnog Human Owner STOP/GO — vidi plan §37, P0.30).
