---
task_id: ACS-F1-056
phase: "P1.5-G8 — Integration acceptance (Faza 1 v1.5 §23, posljednji Slice 1.5 gate)"
title: "Deterministički E2E test cijelog Performance lanca preko bridge-a"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-08
dependencies: []
allowed_paths:
  - tests/integration/presentation_webview/bridge/test_campaign_bridge_g8_acceptance.py
forbidden_paths:
  - src/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Test-only task, nula produkcijskog koda -- svi bridge/application
    pozivi koji se koriste (`create_campaign_and_generate_plan`,
    `generate_campaign_content`, `export_campaign_package`,
    `confirm_performance_import`, `get_campaign_performance`,
    `get_campaign_content_performance`) VEĆ POSTOJE i VEĆ SU
    pregledani (ACS-F1-046...055). GitNexus impact je preventivan
    (potvrditi da nijedan potpis nije promijenjen između merge-a i
    ovog taska), ne traži se za novi produkcijski simbol jer ga nema.
---

# Kontekst

Faza 1 v1.5 §23 traži poslednji Slice 1.5 gate — end-to-end scenario
koji dokazuje da je CIJELI Performance lanac (G1-G7) stvarno spojen:

```text
create campaign
generate content
approve
export
take manifest key
import synthetic CSV
match data
calculate metrics
show campaign aggregate
show content result
```

"Sve deterministic" — plan EKSPLICITNO traži da ovaj test NE zavisi od
stvarnog, nedeterminističkog LLM poziva (za razliku od ACS-F1-047-ovog
`test_campaign_bridge_end_to_end.py`, koji namjerno koristi PRAVI
DeepSeek poziv i postoji za DRUGU svrhu — dokazati da stvaran AI
provajder radi, ne da je pipeline ožičen). G8 dokazuje ožičenje, ne AI
kvalitet -- odvojena, komplementarna svrha istom stilu testa.

**Istraga PRIJE ovog kontrakta potvrdila je da CIJELI lanac VEĆ
POSTOJI i VEĆ RADI end-to-end -- ovaj task je ČISTO test-only,
NULA produkcijskog koda:**

1. `ExportCampaign` (`application/export/export_campaign.py`) VEĆ
   kreira `DistributionInstance` po exportovanom content piece-u
   (`distribution_source=EXPORT`) I piše `analytics_match_key` u
   `manifest.json` po stavci (`compute_analytics_match_key(
   content_piece_id, content_revision_id, platform_code, format_code)`).
2. `MatchPerformanceImportBatch._match_row` (`application/performance/
   match_performance_import_batch.py`) koristi TAČNO istu formulu
   (`_compute_match_key`) kao priority-2 matching ključ.
3. `column_aliases_v1.yaml` VEĆ ima `analytics_match_key`/`match_key`
   kao prepoznate CSV header alias-e za canonical polje
   `analytics_match_key`.
4. `confirm_performance_import` (bridge, ACS-F1-055) VEĆ poziva I
   `ConfirmPerformanceImport` I `MatchPerformanceImportBatch` u JEDNOM
   pozivu -- "import" i "match" koraci iz §23 scenarija se dešavaju u
   JEDNOM bridge pozivu.
5. `get_campaign_performance`/`get_campaign_content_performance`
   (bridge, ACS-F1-053/054) VEĆ pokrivaju "show campaign aggregate"/
   "show content result".

**Zaključak: sinteza svih ovih VEĆ postojećih, VEĆ pregledanih dijelova
u JEDAN deterministički scenario test je JEDINI posao ovog taska.**

# Objective

## 1. Deterministički fake AI adapter (test-lokalan, ne novi produkcijski kod)

Bridge uvijek zove `build_text_generation_adapter(provider_code,
api_key)` (uvezen kao top-level ime u `presentation_webview/bridge/
__init__.py`, dakle patch-ovan preko
`unittest.mock.patch("ai_campaign_studio.presentation_webview.bridge.
build_text_generation_adapter", ...)` -- isti test-only patch stil kao
ACS-F1-055-ov `sys.modules["webview"]` patch, NIJE produkcijska
izmjena).

Fake adapter implementira `TextGenerationPort` (`ports/ai.py`) i vraća
DETERMINISTIČKE, schema-validne `AIResponse.structured_payload`
odgovore. `AIRequest.purpose` je polje po kojem fake razlikuje KOJI
poziv je u pitanju (plan generation vs content generation) -- pogledati
STVARNE `purpose` vrijednosti koje `generate_campaign_plan.py`/
`generate_social_post.py` postavljaju PRIJE pisanja fake-a, ne
pretpostaviti. Reference za "schema-validan fake" stil:
`tests/unit/application/campaigns/test_generate_campaign_plan.py`-ov
lokalni fake adapter (isti princip, ovaj put na bridge/E2E nivou umjesto
unit nivoa).

Provider config: pisati STVARAN `ProviderConfig` red preko
`SqliteProviderConfigRepository` (`configured=True`,
`credential_ref="provider/MOCK/api_key"` ili slično, sa NEPRAZNIM
placeholder ključem preko `EnvironmentSecretStore` -- isti obrazac kao
ACS-F1-047-ov `_configure_deepseek` helper). Vrijednost ključa je
nebitna jer je `build_text_generation_adapter` u potpunosti patch-ovan
-- nikad se ne poziva stvaran SDK.

## 2. Scenario (jedan test, sekvencijalni koraci preko bridge-a)

```text
1. create_campaign_and_generate_plan (bridge) -- fake adapter vraća
   validan CampaignPlanOutput.
2. generate_campaign_content (bridge, job-backed -- pričekati terminal
   stanje preko get_job_status, isti obrazac kao ACS-F1-047) -- fake
   adapter vraća validan SocialPostPayload-oblik po pozivu.
3. "approve" -- UI-only gate (ACS-GUI-009 dokumentovano), NEMA bridge
   poziva -- test ovaj korak NE simulira jer ne postoji backend
   akcija za njega.
4. export_campaign_package (bridge) -- pravi ZIP + manifest.json.
5. Pročitati manifest.json, izvući `analytics_match_key` PO STAVCI.
6. Konstruisati sintetički CSV sadržaj (in-memory string, `tmp_path`
   fajl) sa `period_start`/`period_end`/`analytics_match_key`/bar
   jednom numeričkom metrikom (npr. `impressions`) PO redu, koristeći
   TAČNE `analytics_match_key` vrijednosti iz koraka 5. Bar 2 reda (za
   bar 2 stavke iz manifesta) da "show campaign aggregate" ima
   smislenu agregaciju.
7. confirm_performance_import (bridge) sa tim CSV file_path-om --
   ovaj JEDAN poziv radi i import i match (Kontekst tačka 4).
8. get_campaign_performance (bridge) -- "show campaign aggregate".
9. get_campaign_content_performance (bridge) -- "show content
   result".
```

## 3. Determinističke asercije (ne "ne baca izuzetak", stvarne vrijednosti)

- Korak 7 rezultat: `matched_count == broj redova u CSV-u` (SVI redovi
  se MORAJU poklopiti -- ako bilo koji red ostane unmatched/ambiguous,
  test MORA pasti, to je znak da je synthetic CSV pogrešno
  konstruisan).
- Korak 8: `distribution_instance_count == broj generisanih content
  piece-ova`, `derived.ctr`/itd. ručno izračunati iz CSV vrijednosti
  koje je implementer sam upisao (isti "ručno provjerene vrijednosti"
  standard kao G5/G6/G7a testovi -- NE samo "nije None").
- Korak 9: broj redova == broj content piece-ova, svaki red ima
  ispravan `content_piece_id`.

# Implementation steps

1. Pronaći stvarne `AIRequest.purpose` vrijednosti (grep
   `generate_campaign_plan.py`/`generate_social_post.py`) PRIJE
   pisanja fake adaptera.
2. Napisati fake `TextGenerationPort` + provider config seed helper.
3. Napisati scenario test (Objective #2), korak po korak, sa
   `_wait_for_job_terminal`-stil helperom za job-backed korak
   (POSTOJI presedan u ACS-F1-047-ovom testu -- pogledati ga kao
   referencu, ne izmišljati novi obrazac).
4. Ručno izračunati očekivane derived/raw vrijednosti iz sintetičkog
   CSV-a PRIJE pisanja asercija (ne unazad iz onoga što test vrati).
5. Pokrenuti test VIŠE puta zaredom (determinizam dokaz -- isti
   rezultat svaki put, nula flake-a pošto nema stvarne mreže/AI
   poziva).

# Acceptance

- [ ] Test postoji, prolazi KONZISTENTNO (pokrenut bar 3x zaredom, isti
      rezultat).
- [ ] NEMA stvarnog mrežnog/AI poziva -- `build_text_generation_adapter`
      potpuno patch-ovan, test radi i BEZ ijednog API ključa u
      okruženju.
- [ ] Svi CSV redovi se poklope (matched_count == broj redova) --
      dokaz da je stvaran `analytics_match_key` lanac (export→CSV→
      match) ispravan, ne zaobiđen.
- [ ] Aggregate/content rezultati provjereni protiv RUČNO izračunatih
      vrijednosti, ne samo "nije None"/"nije prazno".
- [ ] `src/`, `resources/migrations/` NISU DIRANI (potvrđuje da je
      cijeli lanac VEĆ postojao, ne da je ovaj task nešto dogradio).
- [ ] `python -m pytest tests/integration/presentation_webview/bridge/
      test_campaign_bridge_g8_acceptance.py -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze (mypy
      se odnosi na `src/`, koji nije diran -- provjera je formalnost).
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/integration/presentation_webview/bridge/test_campaign_bridge_g8_acceptance.py -v
python -m pytest tests/integration/presentation_webview/bridge/test_campaign_bridge_g8_acceptance.py -v
python -m pytest tests/integration/presentation_webview/bridge/test_campaign_bridge_g8_acceptance.py -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-056-g8-integration-acceptance
gh pr create --base main --title "ACS-F1-056: P1.5-G8 Integration acceptance"
gh pr checks
```

# Review focus — Claude (MEDIUM, §29)

- **Nula stvaranog mrežnog poziva** -- provjeriti da fake adapter
  stvarno presreće SVAKI poziv, test radi bez env var-a.
- Matching je STVARNO dokazan preko pravog `analytics_match_key`
  lanca (export → manifest → CSV → match), ne preskočen/mock-ovan na
  pogrešnom nivou.
- Asercije su ručno izračunate vrijednosti, ne "ne baca grešku".
- Test je stvarno deterministički (3x zaredom identičan rezultat).
- `purpose`-based fake dispatch je tačan (provjeriti da odgovara
  STVARNIM vrijednostima iz koda, ne pretpostavljenim).

# Rollback

MEDIUM risk -- test-only, nula produkcijskog koda, nula GUI/domain/
infrastructure uticaja. Claude-only review → odmah merge po §29 ako
PASS. (Napomena: task je namjerno MEDIUM ne HIGH -- vidi Human Owner-
ovu opasku iz ACS-F1-055 reviewa: "samo ožičavanje/sinteza već
pregledanih dijelova, bez lifecycle rizika" ide kao §29, ne pun
adversarial ciklus.)

# Coordination

Nezavisan od bilo kojeg drugog taska (test-only, `tests/integration/`
folder koji nijedan drugi otvoreni task ne dira). Sigurno za paralelan
rad ako se pojavi drugi nezavisan task istovremeno.

**Ovo je POSLJEDNJI gate Slice 1.5.** Nakon PASS-a: Slice 1.5
(Performance/Analytics) je zvanično zatvoren, Slice 2 (Website
Ingestion) može krenuti po ranijoj Human Owner odluci
(`docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md`).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-056-g8-integration-acceptance
Branch:   task/ACS-F1-056-g8-integration-acceptance
Base:     main @ 6825270
```
