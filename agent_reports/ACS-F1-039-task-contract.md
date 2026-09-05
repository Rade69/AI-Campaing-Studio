---
task_id: ACS-F1-039
phase: Slice 1.5 retrofit (preduslov za P1.5-G3) — ExportCampaign snima DistributionInstance
title: "ExportCampaign: snimiti DistributionInstance po eksportovanom piece-u (bridge G2 → G3)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: [ACS-F1-038]
allowed_paths:
  - src/ai_campaign_studio/ports/export.py
  - src/ai_campaign_studio/application/export/export_campaign.py
  - tests/unit/application/export/test_export_campaign.py
  - tests/integration/application/export/test_export_campaign_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/ports/rendering.py
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
    MIJENJA JAVNI POTPIS `ExportCampaign.__init__` (nov obavezan
    parametar `performance_repo`) — ovo NIJE čisto aditivno kao
    ACS-F1-036. Koordinator MORA pokrenuti GitNexus impact provjeru
    da potvrdi STVARAN broj postojećih pozivalaca `ExportCampaign(...)`
    prije merge-a (očekivano: nula produkcijskih pozivalaca, samo
    testovi i koordinatorove live skripte — ali ovo se MORA provjeriti,
    ne pretpostaviti). GitNexus MCP dostupan, indeks stale — re-index
    prije provjere.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 5162924
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

**Ovo NIJE "P1.5-G3 CSV Import".** Prije pisanja tog kontrakta, provjereno
je (grep preko cijelog `application/` sloja) da **NIJEDAN kod NIGDJE ne
poziva `save_distribution_instance`, niti konstruiše `DistributionInstance`**
— `ACS-F1-037` (P1.5-G1) je definisao pojam, `ACS-F1-038` (P1.5-G2) mu je
dao mjesto u bazi, ali NIŠTA ga stvarno ne popunjava.

**Zašto je ovo STVARNA blokada, ne stilski detalj**: `PerformanceSnapshot`
(već zaključan domain model, `ACS-F1-037`) MORA pokazivati na
`distribution_instance_id` — NE direktno na `content_piece_id` (Faza 0.7
§4, namjerno pravilo: ako se caption promijeni nakon objave, stari
rezultati se ne smiju pripisati novoj verziji). Bez ijednog stvarnog
`DistributionInstance` reda u bazi, CSV import (P1.5-G3) nema PREMA ČEMU
da matchuje — svaki red uvezenog CSV-a bio bi `UNMATCHED`, uvijek,
bezuslovno.

**Prirodan trenutak da se `DistributionInstance` stvarno napravi**:
export (`ExportCampaign`, `ACS-F1-034`/`036`, mergovano). Export je
momenat kad "sadržaj JESTE distribuiran" postaje istina —
`distribution_source=EXPORT` (Faza 0.7 §3, doslovno jedna od četiri
navedene vrijednosti) postoji TAČNO za ovaj slučaj. `ExportCampaign` VEĆ
prolazi kroz SVE podatke koje `DistributionInstance` traži (piece,
`content_revision_id`, `campaign_item_id`, `platform_code`/`format_code`)
dok gradi `manifest.json` — ovaj task samo DODAJE da se ISTI podaci i
STVARNO snime kao `DistributionInstance` red, ne samo upišu u ZIP JSON.

**Ovo je TREĆA dopuna `ExportCampaign`-a** (nakon `036` manifest.json
dopune) — za razliku od te dopune, OVA MIJENJA javni potpis
(`__init__` dobija nov OBAVEZAN parametar) jer `ExportCampaign` do sad
NEMA pristup `PerformanceRepositoryPort`-u. Ovo je namjerno OBAVEZAN
(ne opcioni sa default-om) parametar — svaki export MORA snimiti
distribution instances, nema "export bez toga" moda (isti princip kao
ostali obavezni portovi u konstruktoru).

# Objective

## 1. `ports/export.py` — `ExportResult` dobija novo polje

```python
@dataclass(frozen=True)
class ExportResult:
    zip_path: str
    exported_content_piece_ids: tuple[str, ...]
    skipped_content_piece_ids: tuple[str, ...]
    distribution_instance_ids: tuple[str, ...]  # NOVO — isti redoslijed kao exported_content_piece_ids
```

(polja su `tuple[str, ...]`, NE tipizovani ID NewType-ovi — potvrđeno
čitanjem POSTOJEĆEG `ports/export.py`, isti stil zadržan za novo polje.)

Nema default vrijednosti (ExportResult se konstruiše SAMO unutar
`ExportCampaign.execute()`, koji ovaj task ažurira — nema drugih
pozivalaca koji bi se pokvarili).

## 2. `application/export/export_campaign.py` — dopuna

- `ExportCampaign.__init__` dobija nov OBAVEZAN parametar
  `performance_repo: PerformanceRepositoryPort` (dodati NA KRAJ liste
  parametara — pozicioni pozivaoci u POSTOJEĆIM testovima trebaju
  ažuriranje, imenovani pozivaoci ne).
- U istoj petlji koja gradi `manifest_items` (gdje se već zna
  `content_revision_id` za svaki eksportovani piece), za SVAKI
  eksportovani piece:
  ```python
  distribution_instance = DistributionInstance(
      id=DistributionInstanceId(new_id()),
      campaign_id=campaign.id,
      campaign_item_id=e.piece.campaign_item_id,
      content_piece_id=e.piece.id,
      content_revision_id=RevisionId(content_revision_id),
      channel_code=e.piece.target.channel,
      platform_code=e.piece.target.platform_code,
      format_code=e.piece.target.format_code,
      distribution_source=DistributionSource.EXPORT,
      created_at=utc_now(),
  )
  self._performance_repo.save_distribution_instance(distribution_instance)
  ```
  (`external_account_id`/`external_content_id`/`published_at` ostaju
  `None` — export NE zna te podatke, popunjavaju se KASNIJE ako/kad
  korisnik poveže stvaran platformski nalog — van scope-a ovog taska).
- `ExportResult.distribution_instance_ids` = tuple svih kreiranih id-eva,
  ISTIM redoslijedom kao `exported_content_piece_ids`.
- **`campaign.json`/`telemetry`/`content-NN`/`manifest.json` OSTAJU
  POTPUNO NEPROMIJENJENI** (regresija zabranjena, isti standard kao
  `036`).

# Implementation steps

1. `ports/export.py` dopuna po Objective #1.
2. `export_campaign.py` dopuna po Objective #2.
3. Ažurirati POSTOJEĆE testove koji konstruišu `ExportCampaign(...)`
   (`test_export_campaign.py`, `test_export_campaign_integration.py`) da
   proslijede fake/pravi `performance_repo` — MEHANIČKA dopuna, NE
   promjena onoga što ti testovi provjeravaju.
4. Novi testovi:
   - Unit: happy path 2 pieces → `performance_repo.save_distribution_instance`
     pozvan 2×, sa ISPRAVNIM poljima (uporediti `content_revision_id`
     sa onim iz `manifest.json`-a ISTOG testa — MORA biti identičan,
     ne dva odvojena izračuna koja bi mogla divergirati).
   - `ExportResult.distribution_instance_ids` ima 2 unosa, ISTIM
     redoslijedom kao `exported_content_piece_ids`.
   - Piece koji je PRESKOČEN (bez payload-a ili bez LayoutSpec-a) → NE
     dobija `DistributionInstance` (samo eksportovani piece-ovi).
   - `distribution_source` je UVIJEK `DistributionSource.EXPORT` (nema
     drugog moda u ovom tasku).
5. Integration test dopuna: nakon punog lanca, `performance_repo.get_distribution_instance(...)`
   STVARNO vraća red iz baze (pravi round-trip, ne fake) za svaki
   eksportovani piece; `content_revision_id` u tom redu odgovara PRAVOJ
   Reviziji iz `revision_repo` (isti standard kao `036`-ov manifest
   test).

# Acceptance

- [ ] `ExportResult` ima `distribution_instance_ids` polje.
- [ ] `ExportCampaign` STVARNO snima `DistributionInstance` za svaki
      eksportovani (NE preskočeni) piece preko
      `performance_repo.save_distribution_instance`.
- [ ] `content_revision_id` u snimljenom `DistributionInstance`-u JESTE
      identičan onom u `manifest.json`-u ISTOG exporta (test dokaz —
      nije dovoljno da oba "izgledaju ispravno" odvojeno).
- [ ] `distribution_source` je UVIJEK `EXPORT`.
- [ ] `campaign.json`/`telemetry/ai_summary.json`/`content-NN/*`/
      `manifest.json` NEPROMIJENJENI (regresija zabranjena).
- [ ] `domain/`, `ports/repositories.py`, `ports/rendering.py`,
      `infrastructure/`, `resources/migrations/`, `application/campaigns/`,
      `application/posts/`, `application/visual/`, `application/rendering/`,
      `application/evaluation/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/application/export/ tests/integration/application/export/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/export/test_export_campaign.py -v
python -m pytest tests/integration/application/export/test_export_campaign_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- OTVORITI integration test dokaz — potvrditi `content_revision_id` u
  STVARNO snimljenom `DistributionInstance`-u odgovara STVARNOJ Reviziji
  (ne dva odvojena "izgleda ispravno" izračuna koja bi mogla tiho
  divergirati ako neko kasnije refaktoriše `_latest_revision_id`);
- GitNexus impact STVARNO pokrenut, STVARAN broj pozivalaca
  `ExportCampaign(...)` provjeren (ne pretpostavljeno "nula");
- `campaign.json`/`manifest.json`/itd. STVARNO nepromijenjeni (git diff,
  red po red);
- preskočeni piece-ovi (bez payload/LayoutSpec) STVARNO nemaju
  `DistributionInstance` (test dokaz, ne samo tvrdnja).

# Rollback

MEDIUM risk — mijenja javni potpis POSTOJEĆEG, već-mergovanog use-case-a
(treći put), ali izolovano (jedan fajl + jedan port fajl). Fix na istoj
branch bez proširenja scope-a. §29: Claude-only review, PASS → odmah
merge.

# Coordination

Zavisi od ACS-F1-038 (mergovano) — UNBLOCKED. **Blokira P1.5-G3** (CSV
Import) — bez STVARNIH `DistributionInstance` redova, CSV matching nema
prema čemu da radi. Sljedeći task nakon ovog: **P1.5-G3 CSV Import**
(Faza 1 v1.5 §18 — `ImportPerformanceCsv`/`PreviewPerformanceMapping`/
`ConfirmPerformanceImport`), koristeći kao referencu obrasce iz
korisnikovog `deklarant_pro` projekta (column-mapping preko liste
sinonima, odvojena validacija od parsiranja — vidi razgovor
2026-09-05).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-039-record-distribution-instance
Branch:   task/ACS-F1-039-record-distribution-instance
Base:     main @ 5162924
```
