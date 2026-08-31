---
task_id: ACS-P0-004
phase: P0
title: "Channel / Platform / Format registry"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [codex, claude]
status: "OPEN — contract written before code"
created_at: 2026-08-31
dependencies: [ACS-P0-002]
allowed_paths:
  - src/ai_campaign_studio/channels/__init__.py
  - src/ai_campaign_studio/channels/enums.py
  - src/ai_campaign_studio/channels/definitions.py
  - src/ai_campaign_studio/channels/registry.py
  - src/ai_campaign_studio/ports/channels.py
  - resources/platforms/instagram.yaml
  - resources/platforms/facebook.yaml
  - resources/platforms/linkedin.yaml
  - resources/platforms/x.yaml
  - resources/platforms/tiktok.yaml
  - resources/platforms/youtube.yaml
  - resources/platforms/pinterest.yaml
  - resources/platforms/threads.yaml
  - resources/platforms/snapchat.yaml
  - tests/unit/channels/
  - tests/integration/channels/
forbidden_paths:
  - src/ai_campaign_studio/localization/
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
      downstream_notes: "empty package, no existing callers; ports/channels.py is a new sibling file to (parallel) ports/localization.py from ACS-P0-003 — different files, no overlap"
      affected_processes: []
  scope_fit: PASS
  unknowns: []
---

# Kontekst

Četvrti coding task Implementation Phase 0, drugi od dva paralelna taska
(ACS-P0-003 + ACS-P0-004) pokrenuta nakon merge-a ACS-P0-002. `allowed_paths`
ovog taska i ACS-P0-003 su potpuno disjoint (provjereno) — sigurno za
paralelan rad po workflow §10.

Prije koda implementer mora pročitati:

```text
AGENTS.md
CLAUDE.md
docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md
.agent/CURRENT_STATE.md
.agent/PROJECT_MAP.md
.agent/TASK_ROUTING.md
AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md
  sekcija 20 (P0.13)
```

Workflow §4 eksplicitno navodi "Channel/Platform/Format registry" kao
oblast koja zahtijeva Codex + Claude review bez obzira na MEDIUM label.

# Objective

Data-driven Channel → Platform → Format registry, bez social-specific
hardkodovanja u Campaign Engine, bez network/API pozivova.

# Implementation steps (P0.13)

1. `channels/enums.py`: stabilni `Channel` enum — `SOCIAL`, `EMAIL`, `WEB`,
   `PAID_AD`, `PRINT`, `DIRECT_MESSAGE`. NE praviti social platform enum
   (platforme su data-driven, ne enum).
2. `channels/definitions.py`: immutable Pydantic/dataclass modeli —
   `TextConstraints` (`max_chars?`, `max_caption_chars?`,
   `max_title_chars?`, `supports_hashtags`, `supports_links` — sve
   opcionalno gdje nema pouzdanog hard constraint-a), `VisualConstraints`
   (`supported_aspect_ratios[]`, `supports_static_image`,
   `supports_video`, `supports_carousel`), `FormatDefinition` (`code`,
   `display_name`, `required_fields[]`, `optional_fields[]`,
   `text_constraints`, `visual_constraints`, `enabled`),
   `PlatformDefinition` (`code`, `display_name`, `channel`,
   `supported_formats[]`, `content_rules[]`, `enabled`).
3. `ports/channels.py`: `PlatformRegistryPort` protocol —
   `list_platforms(channel=None)`, `get_platform(code)`,
   `list_formats(platform_code)`, `get_format(platform_code, format_code)`.
4. `channels/registry.py`: učitava YAML iz `resources/platforms/`,
   validira schema, normalizuje kodove, odbija duplirane platform/format
   kodove, odbija nepoznat channel, odbija supported-format referencu koja
   ne postoji, cache-uje parsed registry poslije validnog load-a. NE smije:
   pozivati web/social API, hardkodovati Instagram ponašanje, sadržavati
   Campaign logiku.
5. 9 platform YAML fajlova (`instagram`, `facebook`, `linkedin`, `x`,
   `tiktok`, `youtube`, `pinterest`, `threads`, `snapchat`) sa minimalnim
   format primjerima iz plana (npr. Instagram: `FEED_POST`, `STORY`,
   `REEL`, `CAROUSEL`; X: `TEXT_POST`, `THREAD`, `IMAGE_POST`; itd. — vidi
   plan sekcija 20 za puni spisak po platformi). Nepotvrđen constraint =
   `max_chars: null`, NE izmišljati vrijednost. P0 cilj je registry
   architecture + schema, ne market knowledge database.
Validacija platform YAML fajlova ide isključivo kroz `registry.py` (load-time
schema/duplicate/reference provjere) i `tests/integration/channels/test_platform_resources.py`
— `scripts/validate_resources.py` NIJE u ovom tasku (taj fajl je u
`allowed_paths` ACS-P0-003, koji ga kreira za i18n/regional resurse; dijeljenje
istog fajla između dva paralelna taska bi kršilo `allowed_paths` disjoint
pravilo). Ako se pokaže potreba za jedinstvenim resource-validator CLI-jem
koji pokriva i platforme, to je `OUT_OF_SCOPE_FINDING` za naredni task, ne
tiho proširenje ovog.

# Acceptance

- [ ] Svih 9 YAML fajlova se učitava.
- [ ] Svi platform kodovi unique, svi format kodovi unique per platform.
- [ ] Svi channels validni.
- [ ] Nepoznat platform → `RegistryError`. Nepoznat format → `RegistryError`.
- [ ] Disabled item isključen iz default liste.
- [ ] Dodavanje privremenog YAML platform fajla ne zahtijeva izmjenu
      Campaign Engine koda (dokazati testom koji doda temp YAML u fixture i
      potvrdi da registry ga učita bez izmjene `registry.py`).
- [ ] `python -m pytest -q`, `ruff check .`, `mypy src` prolaze.
- [ ] Registry je potpuno data-driven — nema `if platform == "instagram"`
      grana u kodu.
- [ ] Nema network/social API poziva.

# Adversarial test (obavezno — adversarial_required: true)

Za duplicate-rejection invariant:

1. test tvrdi da registry odbija duplirani platform code;
2. privremeno ukloniti duplicate-check iz `registry.py` — test mora FAIL;
3. vratiti — test mora PASS;
4. dokumentovati oba outputa.

Isto za "unknown format reference" validaciju (platform YAML koji referencira
format koji ne postoji u `supported_formats`).

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest -q
python -m ruff check .
python -m mypy src
git status --short
```

# Review focus — Codex

- da li duplicate/unknown-reference testovi stvarno padaju na poznato lošoj
  varijanti;
- da li "temporary YAML platform needs no Campaign Engine code" test
  stvarno dokazuje data-driven tvrdnju;
- edge cases: prazan `supported_formats[]`, format sa svim opcionalnim
  poljima izostavljenim, malformed YAML.

# Review focus — Claude

- `channels/registry.py` ne poziva web/social API, ne hardkoduje platform
  ponašanje;
- `PlatformRegistryPort` je framework-neutral;
- nema Campaign/Content business logike u `channels/`;
- integracija sa `ports/` seam-om (isti obrazac kao paralelni ACS-P0-003).

# Rollback

MEDIUM/elevated-standard task. Ako review otkrije da registry ne dokazano
odbija duplicate/unknown-reference slučajeve, ne spajati — fix na istoj
branch.

# Dependency baseline

Zavisi od ACS-P0-002 (merged, `e187a56` na `main`). Ne granati sa starijeg
main-a.

# Coordination

Paralelno sa ACS-P0-003 — `allowed_paths` su potpuno disjoint (potvrđeno od
strane koordinatora; `scripts/validate_resources.py` je namjerno samo u
ACS-P0-003, vidi implementation steps).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-P0-004-channel-registry
Branch:   task/ACS-P0-004-channel-registry
Base:     main @ a712ce3
```

Nakon merge-a: post-merge gate, GitNexus detect-changes prije reviewa,
GitNexus re-index poslije merge-a, CURRENT_STATE update.
