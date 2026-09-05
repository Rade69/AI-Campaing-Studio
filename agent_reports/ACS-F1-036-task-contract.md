---
task_id: ACS-F1-036
phase: Faza 1 v1.5 retrofit (preduslov za Slice 1.5) — export manifest analytics-ready
title: "ExportCampaign: manifest.json + content_revision_id + analytics_match_key (Faza 1 v1.5 §5-6, 11-12)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/domain/analytics/__init__.py
  - src/ai_campaign_studio/domain/analytics/match_key.py
  - src/ai_campaign_studio/application/export/export_campaign.py
  - tests/unit/domain/analytics/test_match_key.py
  - tests/unit/application/export/test_export_campaign.py
  - tests/integration/application/export/test_export_campaign_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/campaign/
  - src/ai_campaign_studio/domain/content/
  - src/ai_campaign_studio/domain/visual/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/visual/
  - src/ai_campaign_studio/application/rendering/
  - src/ai_campaign_studio/application/evaluation/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Modifikuje POSTOJEĆI, VEĆ MERGOVAN use-case (`ExportCampaign`,
    ACS-F1-034) — aditivno (nova polja/fajlovi u ZIP izlazu, nema
    izmjene potpisa `execute()`). Nov domain modul
    (`domain/analytics/match_key.py`) bez zavisnosti od ičega osim
    stdlib-a. Koordinator pokreće detect-changes/impact prije merge-a
    (GitNexus MCP dostupan, indeks stale — re-index prije provjere) da
    potvrdi da nijedan postojeći pozivalac `ExportCampaign` (trenutno
    nema nijednog produkcijskog pozivaoca van testova i koordinatorovih
    live skripti) nije pogođen.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 19fc17b
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

**Ovo NIJE "P1.5-G1 Performance Domain"** (prvi gate iz Faza 1 v1.5 §15-16
liste). Prije pisanja kontrakta, pročitana su OBA obavezna Performance/
Analytics dokumenta (`AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`,
`AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`, per
`.agent/TASK_ROUTING.md` sekcija "Performance / Analytics task") — i otkriven
je STVARAN, ne-opcion tehnički dug:

**Faza 1 v1.5 §5, §6, §11-12 eksplicitno traže** da export (A15) proizvede
`manifest.json` sa `content_revision_id` i `analytics_match_key` po
eksportovanom item-u, PLUS specifičnu listu od 7 testova (§12, imenovani
doslovno). **Ovo je trebalo biti dio ISTE Faza 1 A15 implementacije, PRIJE
G10** — ali `ACS-F1-034` (mergovan, A15 po originalnoj plan sekciji 46 iz
`AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`) je pisan i
review-ovan BEZ unakrsnog čitanja v1.5 dopune, jer u tom trenutku task NIJE
bio prepoznat kao "Performance/Analytics-dodirujući" (iako `.agent/TASK_ROUTING.md`
eksplicitno kaže: "Ako Faza 1 task dira... export manifest ili
analytics_match_key, obavezno primijeniti sekciju Performance / Analytics
task" — ACS-F1-034 JESTE dirao export manifest, ovo pravilo je trebalo biti
primijenjeno tada). Ovo je koordinatorov propust, transparentno priznat, ne
MiniMax-ov/implementerov.

**Zašto ovo MORA biti PRVO, prije P1.5-G1**: `analytics_match_key` je
temeljni identitet na koji će se buduće CSV/API performance podaci
mapirati (Faza 0.7 §14, Faza 1 v1.5 §19 "P1.5-G4 Matching" — prioritet
1. `external_content_id`, 2. `analytics_match_key`, ...). Bez njega u
exportu, P1.5-G3/G4 (CSV import + matching) nemaju STA da matchuju. Ovo
NIJE izbor redoslijeda — to je hard tehnička zavisnost.

**Namjerno ODVOJENO od postojećeg `campaign.json`**: `ACS-F1-034` već
proizvodi `campaign.json` (kampanjski-nivo sažetak: brief, plan_version,
visual_system_id, content_piece_ids[]) — VEĆ testiran, VEĆ live-verifikovan
(A19). `manifest.json` je NOVI, STROGO specificiran fajl (Faza 1 v1.5 §5,
tačna šema) sa DRUGAČIJIM oblikom (per-item, ne kampanjski-nivo) — dodaje
se KAO NOVI ZIP unos, `campaign.json` OSTAJE nepromijenjen (regresija
zabranjena). Ovo je namjerna odluka da se NE miješaju dva različita
ugovora (opšti izvoz vs strogi analytics-matching kontrakt) u jedan fajl.

# Objective

## 1. `domain/analytics/match_key.py` — `compute_analytics_match_key`

```python
def compute_analytics_match_key(
    content_piece_id: str,
    content_revision_id: str,
    platform_code: str,
    format_code: str,
) -> str:
    """Deterministic, stable key for matching future performance data
    back to an exported content revision + target (Faza 0.7 §16, Faza 1
    v1.5 §6).

    - Deterministic za isti input (isti 4-torka → isti izlaz, uvijek).
    - Mijenja se ako se `content_revision_id` promijeni (nova revizija
      istog posta = nov identitet za matching).
    - Mijenja se ako se `platform_code`/`format_code` promijeni (isti
      sadržaj na drugom target-u = nov identitet).
    - NE sadrži tajne/PII (samo interni UUID-i i registry kodovi,
      heširani preko SHA-256).
    """
```

Implementacija: `hashlib.sha256` preko `"|"`-spojenih argumenata,
skraćeno na razuman broj heksa karaktera (implementer bira, npr. 24-32)
— DOVOLJNO dugo da izbjegne kolizije za realan broj postova po kampanji,
NE mora biti kriptografski pun SHA-256 hex (64 karaktera) jer ovo je
identitet za matching, ne bezbjednosni token.

**Čista funkcija, bez I/O, bez zavisnosti van stdlib-a** (isti stil kao
`application/posts/claim_linter.py`/`content_similarity.py`, ali u
`domain/` jer je ovo pravi domain-nivo identitet koncept, ne
application-orchestration — reusuje se BUDUĆI put i iz P1.5-G3/G4 CSV
matching koda, ne samo iz exporta).

## 2. `application/export/export_campaign.py` — dopuna (NE prepisivanje)

Dodati u POSTOJEĆI `ExportCampaign.execute()`:

- Za svaki eksportovani piece, izračunati `content_revision_id =
  piece.revision_ids[-1]` (najnovija revizija). **Ako je
  `piece.revision_ids` prazan tuple** (piece ima `payload` ali NIKAD
  nijednu Reviziju — ovo NE bi trebalo biti moguće u trenutnom kodu,
  `GenerateSocialPost` UVIJEK kreira Reviziju pri prvom generisanju) →
  `InvariantViolation` (STVARAN podatak-integritet bug, ne normalan
  "nije još spreman" skip razlog kao missing payload/LayoutSpec).
- Izračunati
  `analytics_match_key = compute_analytics_match_key(str(piece.id),
  str(content_revision_id), piece.target.platform_code,
  piece.target.format_code)`. **Napomena**: funkcija prima TAČNO ova 4
  argumenta (content_piece_id, content_revision_id, platform_code,
  format_code) — BEZ `channel_code`, per Faza 0.7 §16 formula doslovno
  ("Može biti izveden iz: content_piece_id, content_revision_id,
  platform_code, format_code").
- Sastaviti `manifest.json` (NOV ZIP unos, `files["manifest.json"] =
  _json_bytes(manifest)`, KORISTI POSTOJEĆI `_json_bytes` helper, ne nov):
  ```json
  {
    "schema_version": 1,
    "campaign_id": "...",
    "campaign_plan_id": "...",
    "exported_at": "...",
    "items": [
      {
        "campaign_item_id": "...",
        "content_piece_id": "...",
        "content_revision_id": "...",
        "channel_code": "SOCIAL",
        "platform_code": "INSTAGRAM",
        "format_code": "FEED_POST",
        "analytics_match_key": "...",
        "artifacts": ["content-01/feed.png", "content-01/caption.txt", "content-01/content.json"]
      }
    ]
  }
  ```
  (`items` SAMO za eksportovane, NE preskočene piece-ove, ISTIM
  redoslijedom kao `content-NN` folderi — reuse VEĆ POSTOJEĆE
  `_order_pieces_by_plan` logike, ne novu.)
- **`campaign.json`, `telemetry/ai_summary.json`, `content-NN/*` OSTAJU
  POTPUNO NEPROMIJENJENI** (postojeći testovi za njih MORAJU proći bez
  izmjene — regresija zabranjena, dokazati git diff-om da se te sekcije
  koda nisu ticale, samo DODATE nove linije).
- Dodati `content_revision_id` takođe u POSTOJEĆI `content-NN/content.json`
  (`_content_json` helper) — ovo polje TRENUTNO nedostaje tamo, a Faza 1
  v1.5 §12 test (`test_export_manifest_contains_content_revision_id`) se
  odnosi na `manifest.json`, ALI dosljednost zahtijeva da i
  `content.json` ima isto polje (implementer PRIMJEĆUJE ovo, DODAJE ga,
  reviewer provjerava da nije zaboravljeno).

# Implementation steps

1. `domain/analytics/match_key.py` po Objective #1. Testovi PRVO (izolovan,
   bez ičega drugog).
2. `export_campaign.py` dopuna po Objective #2.
3. Testovi (Faza 1 v1.5 §12, IMENA TAČNO ova ili vrlo bliska varijanta —
   ne izmišljati drugačija imena):
   - `test_export_manifest_contains_stable_ids` (unit, fake portovi) —
     `manifest.json` sadrži `campaign_id`/`campaign_plan_id`/
     `campaign_item_id`/`content_piece_id` za svaki item.
   - `test_export_manifest_contains_content_revision_id` — svaki item
     ima `content_revision_id` KOJI ODGOVARA `piece.revision_ids[-1]`
     (ne proizvoljna vrijednost).
   - `test_export_manifest_contains_target_identity` — svaki item ima
     `channel_code`/`platform_code`/`format_code`.
   - `test_manifest_has_schema_version` — `manifest.json["schema_version"] == 1`.
   - `test_analytics_match_key_is_stable_for_same_revision` (u
     `test_match_key.py`, domain-nivo, BEZ export-a) — isti 4 argumenta
     → isti izlaz, ponovljeno.
   - `test_analytics_match_key_changes_on_revision_change` — isti
     content_piece_id/platform/format, DRUGAČIJI content_revision_id →
     drugačiji izlaz.
   - `test_analytics_match_key_changes_on_target_change` — isti
     content_piece_id/revision, DRUGAČIJI platform_code ILI format_code
     → drugačiji izlaz.
   - Regresioni test: piece BEZ nijedne Revizije (prazan `revision_ids`,
     ručno konstruisan fake `ContentPiece` sa `payload` popunjenim ali
     `revision_ids=()`) → `InvariantViolation`.
4. Integration test dopuna (`test_export_campaign_integration.py`,
   POSTOJEĆI fajl): pravi lanac (uključuje `GenerateSocialPost` koji
   STVARNO kreira Reviziju) → OTVORITI stvaran `manifest.json` iz ZIP-a,
   parsirati, potvrditi `content_revision_id` u manifestu STVARNO
   odgovara pravoj Reviziji snimljenoj preko `RevisionRepositoryPort`
   (NE fabrikovana vrijednost — uporediti sa `revision_repo.list_entity_revisions(...)`
   rezultatom direktno u testu).

# Acceptance

- [ ] `domain/analytics/match_key.py` postoji, `compute_analytics_match_key`
      čista funkcija (nema I/O, nema zavisnosti van stdlib-a).
- [ ] Determinizam/promjena-na-reviziju/promjena-na-target dokazani (3
      odvojena testa, imena iz Faza 1 v1.5 §12).
- [ ] `manifest.json` postoji u ZIP izlazu, sadrži TAČNO polja iz Faza 1
      v1.5 §5 (`schema_version`, `campaign_id`, `campaign_plan_id`,
      `exported_at`, `items[]` sa svih 7 pod-polja).
- [ ] `content_revision_id` u manifestu STVARNO odgovara
      `piece.revision_ids[-1]` (test dokaz, ne proizvoljna vrijednost).
- [ ] Piece bez nijedne Revizije → `InvariantViolation` (NE tihi skip —
      ovo je podatak-integritet bug, ne "nije još spreman" stanje).
- [ ] `campaign.json`, `telemetry/ai_summary.json`, `content-NN/*`
      NEPROMIJENJENI (postojeći ACS-F1-034 testovi prolaze BEZ izmjene
      njihovih asercija — samo mehanička dopuna ako se dijeljeni helper
      promijeni, ne promjena onoga što provjeravaju).
- [ ] `content-NN/content.json` dobija `content_revision_id` polje
      (dosljednost sa manifestom).
- [ ] `domain/campaign/`, `domain/content/`, `domain/visual/`, `ports/`,
      `infrastructure/`, `resources/migrations/`, `application/campaigns/`,
      `application/posts/`, `application/visual/`, `application/rendering/`,
      `application/evaluation/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/domain/analytics/ tests/unit/application/export/ tests/integration/application/export/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti (stdlib `hashlib` je dovoljan).
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/domain/analytics/test_match_key.py -v
python -m pytest tests/unit/application/export/test_export_campaign.py -v
python -m pytest tests/integration/application/export/test_export_campaign_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- OTVORITI stvaran ZIP iz integration testa, pročitati `manifest.json`
  ručno, uporediti `content_revision_id` sa STVARNIM Revision redom iz
  baze (ne vjerovati testu na riječ);
- `analytics_match_key` STVARNO reaguje na promjenu revizije/targeta —
  provjeriti da test ne slučajno prolazi zbog istog hash-a (npr. loše
  odabran separator koji dozvoljava koliziju, npr. `"ab"+"c"` ==
  `"a"+"bc"` bez separatora — provjeriti da implementacija KORISTI
  separator između polja);
- `campaign.json`/`telemetry`/`content-NN` sekcije STVARNO nepromijenjene
  (git diff, red po red, ne samo "testovi prolaze");
- piece-bez-revizije scenario je STVARNO testiran (ne teoretski
  spomenut) — ovo je jedini NOVI failure-mode koji ovaj task uvodi.

# Rollback

MEDIUM risk — dopuna postojećeg, već-mergovanog use-case-a (aditivno, bez
izmjene potpisa), nov mali domain modul bez zavisnosti. Fix na istoj
branch bez proširenja scope-a. §29: Claude-only review, PASS → odmah
merge.

# Coordination

Nezavisan od svega trenutno otvorenog. **Blokira P1.5-G1** (Performance
Domain — `DistributionInstance`/`PerformanceSnapshot`/itd.) i SVE
naredne P1.5 gate-ove (Faza 1 v1.5 §15-23) — `analytics_match_key` mora
postojati u exportu prije nego što bilo šta pokuša matchovati performance
podatke na njega. Sljedeći task nakon ovog: **P1.5-G1 Performance
Domain** (plan §16 — `DistributionInstance`, `PerformanceSnapshot`,
`PerformanceImportBatch`, `CanonicalMetricSet`, `MetricPeriod`,
`PerformanceSource` — domain-only, BEZ persistencije, per Faza 1 v1.5
§7 "Ne praviti još: PerformanceSnapshot table... u Faza 1" — ali sad SMO
u Slice 1.5, pa je P1.5-G2 Persistence sljedeći korak odmah nakon P1.5-G1).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-036-export-manifest-analytics
Branch:   task/ACS-F1-036-export-manifest-analytics
Base:     main @ 19fc17b
```
