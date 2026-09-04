---
task_id: ACS-GUI-006
phase: Faza-1 (post ACS-GUI-005)
title: "Bridge: kompenzaciono brisanje orphan DRAFT kampanje kad GenerateCampaignPlan padne"
risk: MEDIUM
coordinator: claude
implementer: minimax
reviewers: [claude]
status: "OPEN — dispatched 2026-09-04, ACS-F1-024 merged (main @ 4cbb67d), sequencing dependency satisfied"
created_at: 2026-09-04
dependencies:
  - ACS-F1-024 (mora merge-ovati prije ovog — isti bridge fajl, izbjeći
    konflikt sekvenciranjem, ne paralelnim radom na istom fajlu)
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_campaign_repository.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije dispatch-a. `ports/repositories.py` je
    shared-contract fajl (CampaignRepositoryPort) -- ovo je PRVA delete
    metoda uopšte u cijelom repository sloju projekta (svi ostali portovi
    su append-only/get+save), pa je impact provjera posebno bitna ovdje.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: e1177cc
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

MiniMax (implementer ACS-GUI-005) je nakon merge-a sam pregledao svoj rad
i našao ovaj gap; koordinator ga je direktno posmatrao uživo tokom
ACS-GUI-005 live testiranja PRIJE nego je bilo prijavljeno kao nalaz —
prvi live test poziv (prije BF-1 fixa) je ostavio `brands=1, campaigns=2,
campaign_plans=0` u pravoj bazi, tačno ovaj scenario.

Bridge poziva `CreateCampaign.execute(...)` (sopstvena `with
unit_of_work: ... commit()` tranzakcija) pa TEK ONDA
`GenerateCampaignPlan.execute(...)` (DRUGA, odvojena `with unit_of_work:
... commit()` tranzakcija — provjereno, `SqliteUnitOfWork.commit()` radi
stvaran `COMMIT` na SQLite konekciji, ne odloženo). Ako drugi poziv padne
(mrežna greška, loš model_id, kvota), PRVI je već trajno sačuvan —
korisnik dobija `GENERATION_FAILED` toast, ali kampanja postoji u bazi
kao `DRAFT` bez plana, nevidljiva korisniku (Kampanje ekran je i dalje
fixture, ne prikazuje prave redove). Sljedeći klik pravi NOVU kampanju —
duplikat se gomila sa svakim neuspjelim pokušajem.

**Zašto ne "prava" atomičnost (jedna dijeljena transakcija)**: `CreateCampaign`
i `GenerateCampaignPlan` su namjerno samostalne, svaka sa sopstvenim
`with unit_of_work:` blokom (dio njihovog use-case ugovora,
`application/campaigns/`, van dozvoljenih izmjena ovog taska — mijenjanje
njihovog transakcionog ponašanja bi bio širi refaktor sa posljedicama na
sve ostale pozivaoce, ne samo bridge). **Zato je kompenzaciono brisanje
(saga/compensating-action pattern) ispravan nivo popravke ovdje: bridge,
kao orkestrator dva nezavisna use-case-a, snosi odgovornost da počisti
ako drugi korak ne uspije.**

**Zašto je ovo PRVA delete metoda u cijelom repository sloju**: projekat
do sada nema NIJEDNU delete operaciju ni u jednom portu (Revision sistem,
Campaign, Content — sve je append-only/audit-trail orijentisano po
dizajnu). Ovo NIJE brisanje korisničkih podataka u uobičajenom smislu —
kampanja koja nikad nije uspješno završila svoj jedini svrhu (dobiti
plan) tretira se kao neuspio pokušaj, ne kao izgubljen rad. Ali precedent
vrijedi eksplicitno imenovati u review-u.

# Objective

`CampaignBridgeApi.create_campaign_and_generate_plan` mora, ako
`GenerateCampaignPlan.execute(...)` baci grešku (bilo koji trenutni
`GENERATION_FAILED` put), pokušati obrisati kampanju koju je
`CreateCampaign` upravo kreirao — best-effort, ne smije maskirati
originalnu grešku ako brisanje samo ne uspije.

# Implementation steps

1. **`ports/repositories.py`**: dodaj TAČNO jednu novu metodu na
   `CampaignRepositoryPort`:
   ```python
   def delete_campaign(self, campaign_id: CampaignId) -> None: ...
   ```
   Ne dirati ostatak Protocol-a. Docstring mora eksplicitno navesti da je
   ovo namijenjeno SAMO za kompenzacione akcije neuspjelih multi-step
   tokova (npr. bridge orchestration), ne kao opšta "obriši kampanju"
   funkcija za buduću GUI upotrebu.
2. **`infrastructure/database/repositories/sqlite_campaign_repository.py`**:
   implementiraj `delete_campaign` — `DELETE FROM campaigns WHERE id = ?`
   (i `campaign_briefs`/`campaign_plans`/`campaign_items` ako foreign key
   cascade nije već postavljen u šemi — PROVJERI `resources/migrations/`
   PRIJE pisanja koda da li postoje `ON DELETE CASCADE` klauzule; ako ne
   postoje, obriši eksplicitno u ispravnom redoslijedu, dijete-prije-roditelj,
   unutar iste metode. NE MIJENJATI migracije — ovaj task ne smije
   dirati `resources/migrations/`).
3. **`bridge/__init__.py`**: u `except` bloku za `GenerateCampaignPlan`
   grešku (trenutno mapira na `GENERATION_FAILED`), PRIJE `return
   self._err(...)`, pokušaj:
   ```python
   try:
       self._campaign_repo.delete_campaign(campaign.id)
   except Exception:
       self._bootstrap.logger.exception(
           "compensating delete failed for orphan campaign %s", campaign.id
       )
       # swallow -- ne maskirati originalnu GENERATION_FAILED grešku
   ```
   Originalna `GENERATION_FAILED` poruka i error_code se VRAĆAJU
   nepromijenjeni bez obzira da li je kompenzaciono brisanje uspjelo.
4. Testovi:
   - Unit/integration: `GenerateCampaignPlan` padne → potvrdi da
     `campaigns` tabela NEMA red za tu kampanju nakon poziva (bilo
     direktnim SQL upitom ili `campaign_repo.get_campaign(...)`
     vraća `None`).
   - Test da kompenzaciono brisanje koje SAMO padne (npr. mock
     `delete_campaign` da baci) NE mijenja `error_code`/`error_message`
     povratne vrijednosti — korisnik i dalje vidi tačno
     `GENERATION_FAILED` poruku, ne neku drugu grešku o brisanju.

# Acceptance

- [ ] `CampaignRepositoryPort.delete_campaign` postoji, sa docstring-om
      koji objašnjava namjenu (kompenzaciona akcija).
- [ ] `SqliteCampaignRepository.delete_campaign` briše kampanju i sve
      zavisne redove (brief/plan/items ako postoje), bez orphan foreign
      key redova.
- [ ] Bridge poziva `delete_campaign` SAMO u `GenerateCampaignPlan`
      failure putu, nikad u `CreateCampaign` failure putu (taj put nema
      šta da čisti — kampanja tamo nikad nije ni sačuvana).
- [ ] Neuspješno kompenzaciono brisanje NE mijenja korisnički vidljivu
      grešku — i dalje `GENERATION_FAILED` sa istom porukom.
- [ ] `domain/`, `application/`, `presentation/`, `resources/migrations/`
      NISU DIRANI (git diff dokaz).
- [ ] `python -m pytest tests/unit/presentation_webview/bridge/
      tests/unit/infrastructure/database/repositories/ -v` prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py tests/unit/infrastructure/database/repositories/test_sqlite_campaign_repository.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `delete_campaign` briše SVE zavisne redove, ne ostavlja orphan
  brief/plan/item redove iza sebe;
- kompenzaciono brisanje je stvarno best-effort (try/except, ne
  propagira);
- ovo je PRVA delete metoda u portovima — provjeri da docstring jasno
  ograničava namjenu, da se ne pretvori tiho u opštu "delete" API
  površinu koju bi neko drugi kasnije zloupotrijebio za nešto van ovog
  uskog svrhe;
- `CreateCampaign` failure put (prije nego što kampanja uopšte postoji)
  ostaje netaknut — nema šta tamo da se kompenzuje.

# Rollback

MEDIUM risk — dodaje prvu delete operaciju u repository sloj, ali usko
scoped i samo bridge je poziva. Fix na istoj branch bez proširenja
scope-a. §29: Claude-only review, PASS -> odmah merge.

# Coordination

**Čeka ACS-F1-024** (isti `bridge/__init__.py` fajl) — dispatch-ovati tek
nakon što ACS-F1-024 merguje, bazirati novi worktree na main-u NAKON tog
merge-a (ne na `e1177cc`, taj head će biti zastario do tada — koordinator
će ažurirati `Base` prije dispatch-a).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-006-orphan-campaign-cleanup
Branch:   task/ACS-GUI-006-orphan-campaign-cleanup
Base:     main @ 4cbb67d
```
