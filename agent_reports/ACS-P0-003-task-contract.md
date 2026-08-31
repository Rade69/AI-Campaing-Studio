---
task_id: ACS-P0-003
phase: P0
title: "Localization EN/BHS + regional-language resources"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-08-31
dependencies: [ACS-P0-002]
allowed_paths:
  - src/ai_campaign_studio/localization/__init__.py
  - src/ai_campaign_studio/localization/enums.py
  - src/ai_campaign_studio/localization/language_context.py
  - src/ai_campaign_studio/localization/translator.py
  - src/ai_campaign_studio/ports/localization.py
  - resources/i18n/en.json
  - resources/i18n/bhs.json
  - resources/regional_language/bhs_neutral_v1.yaml
  - resources/regional_language/bhs_bs_v1.yaml
  - resources/regional_language/bhs_sr_v1.yaml
  - resources/regional_language/bhs_hr_v1.yaml
  - scripts/validate_resources.py
  - tests/unit/localization/
  - tests/integration/localization/
forbidden_paths:
  - src/ai_campaign_studio/channels/
  - src/ai_campaign_studio/ai_registry/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/domain/brand/
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
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
  head: a712ce3
  index_status: up-to-date
  targets:
    - symbol: "src/ai_campaign_studio/ports (folder)"
      upstream_risk: LOW
      upstream_count: 0
      downstream_notes: "empty package, no existing callers; ports/localization.py is a new sibling file to (future) ports/channels.py from ACS-P0-004 — different files, no overlap"
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Treći coding task Implementation Phase 0, prvi od dva paralelna taska
(ACS-P0-003 + ACS-P0-004) pokrenuta nakon merge-a ACS-P0-002. `allowed_paths`
ovog taska i ACS-P0-004 su disjoint (provjereno od strane koordinatora) —
sigurno za paralelan rad po workflow §10.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcije 18–19 (P0.11–P0.12)
```

Napomena: workflow §4 (privremeno pojačan P0 standard) eksplicitno navodi
"localization contracts" kao oblast koja zahtijeva Codex + Claude review bez
obzira na MEDIUM label — obje uloge su obavezne.

# Objective

Napraviti framework-neutral EN/BHS_LATIN lokalizacioni foundation
(translator + language context + BHS regionalni resursi), bez UI-ja, bez
fact/provenance logike.

# Implementation steps (P0.11–P0.12)

## P0.11 — Localization EN/BHS

1. `localization/enums.py`: `AppLocale` (`EN`, `BHS_LATIN`),
   `ContentLanguageFamily` (`EN`, `BHS`), `BHSRegionalVariant` (`NEUTRAL`,
   `BS`, `SR`, `HR`), `Script` (`LATIN`). NE koristiti
   `BOSNIAN_UI`/`SERBIAN_UI`/`CROATIAN_UI`.
2. `localization/language_context.py`: immutable/validated
   `ContentLanguageContext` sa poljima `language_family`,
   `regional_variant`, `script`, `locale`, `preferred_terms`,
   `forbidden_terms`, `regional_vocabulary`, `tone_examples`. Invarijante:
   `EN → regional_variant = NEUTRAL`; `BHS → regional_variant ∈ {NEUTRAL,
   BS, SR, HR}`; Faza 0/1 → `script = LATIN`. Bez fact/provenance logike.
3. `ports/localization.py`: `TranslatorPort` protocol —
   `set_locale(locale)`, `get_locale()`, `t(key, **params)`.
4. `localization/translator.py`: framework-neutral implementacija — učitava
   `en.json`/`bhs.json`, podržava runtime locale switch, jednostavnu
   parameter interpolaciju, fallback BHS missing key → EN, loguje missing
   key. Ako nema ni EN key: vraća `[missing:campaign.create]` i loguje
   warning — NE ruši aplikaciju zbog jednog UI stringa.
5. `resources/i18n/en.json` i `bhs.json`: isti obavezni key set —
   `app.title`, `app.starting`, `app.ready`, `settings.title`,
   `settings.language`, `settings.ai_providers`, `settings.api_key`,
   `settings.test_connection`, `settings.connected`,
   `settings.not_configured`, `common.save`, `common.cancel`,
   `common.close`, `common.retry`, `error.generic`, `error.configuration`,
   `error.database`.

## P0.12 — BHS regional-language resources

6. `resources/regional_language/bhs_{neutral,bs,sr,hr}_v1.yaml`: schema
   `language_family: BHS`, `regional_variant: <BS|SR|HR|NEUTRAL>`,
   `version: 1`, `preferred_terms: []`, `forbidden_terms: []`,
   `regional_vocabulary: []`, `notes: []`. Ovo NISU UI prevodi — koriste se
   kasnije za AI copy context. NE izmišljati lingvističke razlike — ako nema
   potvrđene razlike, lista ostaje prazna.
7. `scripts/validate_resources.py`: validator (novi fajl ili dopuna ako već
   postoji iz drugog paralelnog taska — provjeriti prije pisanja) koji
   provjerava za regional YAML: `family = BHS`, `variant` odgovara
   filename-u, `version` postoji, liste su liste, UTF-8. I za i18n JSON:
   valid JSON, UTF-8, isti obavezni key set, čćšžđ preživljava, nema
   duplikata ključeva.

# Acceptance

- [ ] EN ↔ BHS translator radi bez UI frameworka.
- [ ] `test_language_context.py`: EN+NEUTRAL valid, EN+BS invalid,
      BHS+{NEUTRAL,BS,SR,HR} valid, non-Latin invalid u Phase 0 modelu.
- [ ] `test_translator.py`: EN translation, BHS translation, runtime switch,
      fallback to EN, parameter interpolation, unknown key warning
      behavior.
- [ ] `test_translation_resources.py`: JSON valid, UTF-8, isti obavezni key
      set, čćšžđ survives, no duplicate keys.
- [ ] Sva 4 regional YAML fajla prolaze validation.
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Nema fact/provenance logike u `language_context.py`.
- [ ] `translator.py` ne baca exception na missing key (graceful fallback).

# Adversarial test (obavezno — adversarial_required: true)

Za translator fallback behavior:

1. test tvrdi da BHS missing key pada nazad na EN;
2. privremeno ukloniti fallback granu (vratiti raw missing-key marker i za
   BHS umjesto EN vrijednosti) — test mora FAIL;
3. vratiti ispravnu implementaciju — test mora PASS;
4. dokumentovati oba outputa.

Isto za `en.json`/`bhs.json` key-set parity test: privremeno ukloniti jedan
key iz `bhs.json` — test mora FAIL; vratiti — PASS.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
python scripts/validate_resources.py
git status --short
```

# Review focus — Codex

- da li fallback test stvarno pada na poznato lošoj varijanti;
- da li key-set parity test stvarno hvata nedostajući ključ;
- edge cases: prazan `**params` u interpolaciji, nepostojeći locale u
  `set_locale`, duplirani ključevi u JSON-u.

# Review focus — Claude

- `TranslatorPort` je framework-neutral (nema UI import-a);
- `language_context.py` nema fact/provenance logiku (to je van P0 scope-a);
- nema hardkodovane regionalne lingvističke baze (prazne liste umjesto
  izmišljenih razlika);
- integracija sa `ports/` seam-om iz ACS-P0-002 (isti obrazac kao
  `ports/channels.py` iz paralelnog ACS-P0-004).

# Rollback

MEDIUM/elevated-standard task. Ako review otkrije da fallback/parity testovi
ne dokazuju invariant, ne spajati — fix na istoj branch, bez proširenja
scope-a.

# Dependency baseline

Zavisi od ACS-P0-002 (merged, `e187a56` na `main`). Ne granati sa starijeg
main-a.

# Coordination

Paralelno sa ACS-P0-004 — `allowed_paths` disjoint (provjereno), nema
skrivene semantic zavisnosti (translator i registry ne dijele state niti
integration test).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-003-localization
Branch:   task/ACS-P0-003-localization
Base:     main @ a712ce3
```

Nakon merge-a: post-merge gate, GitNexus detect-changes prije reviewa,
GitNexus re-index poslije merge-a, CURRENT_STATE update.
