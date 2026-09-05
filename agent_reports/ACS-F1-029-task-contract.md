---
task_id: ACS-F1-029
phase: Faza-1 (post A16) — A13 "Campaign Visual System"
title: "GenerateVisualSystem: AI-generisan CampaignVisualSystem + LayoutSpec za kampanju (plan sekcija 39)"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/visual/__init__.py
  - src/ai_campaign_studio/application/visual/generate_visual_system.py
  - tests/unit/application/visual/test_generate_visual_system.py
  - tests/integration/application/visual/test_generate_visual_system_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/application/schemas/
  - resources/migrations/
  - resources/prompts/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Nov application-layer use-case, ali NE mijenja nijedan postojeći javni
    potpis niti port. Koordinator će pokrenuti detect-changes/impact prije
    merge-a (GitNexus MCP dostupan, indeks trenutno stale — re-index prije
    provjere).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: ed801aa
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

G10/A16 evaluation harness je gotov i live-verifikovan (A16 kontrakti
ACS-F1-026/027, live poređenje preko 5 modela). Sljedeći application-layer
gap na putu do `G10 Vertical Slice PASS` je **A13 — Campaign Visual System
+ LayoutSpec** (plan sekcije 39-41): jedini veći dio pipeline-a
(fixture→brief→plan→review→posts→validation→**render→export**) koji
uopšte nema application-layer kod — `application/render/` i
`application/export/` NE POSTOJE u kodu.

**Ovaj task NE pokušava riješiti cijeli A13/A14/A15 odjednom.** Istražujući
prije pisanja kontrakta (isti disciplinovan pristup kao za A16), otkriveno
je da je VEĆINA fundacije za A13 već izgrađena, ranije, van formalnog
task-praćenja koje ovaj coordinator vidi u `CURRENT_STATE.md` istoriji
(vjerovatno u ranoj P0/A3-A5 fazi):

- `domain/visual/entities.py` — `CampaignVisualSystem` dataclass — **postoji**
- `domain/visual/layout.py` — `LayoutSpec` dataclass — **postoji**
- `domain/visual/slots.py` — `ContentSlotContract`/`BoundingBox` — **postoji**
- `domain/visual/enums.py` — `LayoutPrimitive` (HERO/SPLIT), `HeadlineScale`,
  `Alignment`, `ImagePosition`, `HeadlinePosition`, `Overlay`, `LogoPosition`,
  `CtaStyle`, `ImageTreatment`, `LogoRule`, `CtaRule`, `SlotName`,
  `CaseStyle`, `OverflowPolicy` — **postoje, svi**
- `application/schemas/visual_direction_output.py` — Pydantic boundary
  schema (`VisualDirectionOutput` = `CampaignVisualSystemCandidate` +
  `LayoutSpecCandidate`) — **postoji**
- `ports/repositories.py` — `VisualRepositoryPort`
  (`save_visual_system`/`get_visual_system`) — **postoji**
- `infrastructure/database/repositories/sqlite_visual_repository.py` —
  `SqliteVisualRepository` — **postoji**, sa testovima
  (`tests/integration/database/repositories/test_sqlite_visual_repository.py`)
- `resources/migrations/0002_campaign_content_visual.sql` — tabela
  `campaign_visual_systems` — **postoji**, tačno odgovara entity poljima
- `resources/prompts/visual_direction/v1.yaml` — prompt za
  `VisualDirectionOutput` — **postoji, pripremljen ranije, nikad korišten**
  (isti obrazac kao `ab_control/v1.yaml` otkriven tokom A16)

**Ono što STVARNO nedostaje i što ovaj task pokriva**: application-layer
use-case koji sve ovo POVEŽE — `generate_visual_system.py` (plan sekcija
39). Ništa od gore navedenog trenutno nema nijednog pozivaoca u
`application/` sloju.

**Namjerno IZOSTAVLJENO iz ovog taska** (odvojen budući task, A13 dio 2 —
plan sekcija 40-41, `plan_post_layout.py`/`validate_layout.py`): stvarno
generisanje/perzistencija PO-POST `LayoutSpec`-a. Razlog: `layout_specs`
tabela (plan sekcija 24, `0002_visual.sql` u planu) **NE POSTOJI** u
stvarnim migracijama — samo `campaign_visual_systems` je odavno kreirana.
Dodavanje `layout_specs` tabele je nova migracija + nov port metod, što je
veća, odvojena arhitektonska izmjena (i po `forbidden_paths` disciplini
ovog taska, i po principu "ne širiti scope"). Ovaj task ipak KONSTRUIŠE
domain `LayoutSpec` objekat (iz iste AI response strukture) i vraća ga
IN-MEMORY iz `execute()` — dovoljno da se dokaže "HERO/SPLIT rade" i
"invalid layout rejected" (A13 acceptance iz plana) bez perzistencije koja
još nema gdje da ide.

# Objective

Novi use-case `GenerateVisualSystem` (`application/visual/generate_visual_system.py`):

- Input: `plan_id: CampaignPlanId` (isti obrazac kao `ApproveCampaignPlan`/
  `GenerateSocialPost` — plan mora biti `APPROVED`, campaign/brand snapshot
  se izvode iz plana).
- Jedan AI poziv preko `resources/prompts/visual_direction/v1.yaml` i
  `VisualDirectionOutput.model_json_schema()`.
- Validacija: Pydantic već odbija bilo koju enum vrijednost van dozvoljenog
  seta (`ValidationError` → propagirati kao `InvariantViolation`, isti
  obrazac kao svuda). DODATNO, deterministička provjera da
  `campaign_visual_system.style` sadrži SAMO dozvoljene vrijednosti (plan
  sekcija 39 primjer: `clean, clinical, calm, warm, bold, minimal,
  editorial`) — schema tipizuje `style` kao `list[str]`, ne enum, pa ovo
  MORA biti kod-nivo provjera (isti obrazac kao `_validate_plan_domain` u
  `generate_campaign_plan.py` za role membership).
- Perzistuje SAMO `CampaignVisualSystem` preko VEĆ POSTOJEĆEG
  `VisualRepositoryPort.save_visual_system` (nema izmjene porta).
- Vraća `tuple[CampaignVisualSystem, LayoutSpec]` — sistem je perzistovan,
  `LayoutSpec` je in-memory (dokaz da HERO/SPLIT konstrukcija radi), NIJE
  perzistovan (nema gdje).
- Ne mijenja campaign/plan status (za razliku od `GenerateCampaignPlan`/
  `ApproveCampaignPlan`/`GenerateSocialPost` — vizuelni sistem je paralelna
  odluka, ne dio campaign/plan state machine-a; ako se ovo pokaže pogrešnim,
  budući task to mijenja eksplicitno, ne ovaj).

# Implementation steps

1. **`application/visual/__init__.py`** — prazan, samo paket marker.

2. **`application/visual/generate_visual_system.py`**, model po
   `application/campaigns/generate_campaign_plan.py` (isti stil: `_UnitOfWork`
   Protocol lokalno, `_PROMPT_NAME`/`_PROMPT_VERSION` konstante,
   `_build_user_text` helper, modul-level `_validate_visual_domain` helper):

   ```python
   _PROMPT_NAME = "visual_direction"
   _PROMPT_VERSION = "1"

   _ALLOWED_STYLES = (
       "clean", "clinical", "calm", "warm", "bold", "minimal", "editorial",
   )

   class GenerateVisualSystem:
       def __init__(
           self,
           campaign_repo: CampaignRepositoryPort,
           brand_repo: BrandRepositoryPort,
           visual_repo: VisualRepositoryPort,
           prompt_repo: PromptRepositoryPort,
           ai_port: TextGenerationPort,
           unit_of_work: _UnitOfWork,
       ) -> None: ...

       def execute(
           self, plan_id: CampaignPlanId
       ) -> tuple[CampaignVisualSystem, LayoutSpec]:
           plan = self._campaign_repo.get_plan(plan_id)
           # EntityNotFound ako None
           if plan.status is not CampaignPlanStatus.APPROVED:
               raise InvariantViolation(...)  # isti stil kao generate_social_post.py:125
           campaign = self._campaign_repo.get_campaign(plan.campaign_id)
           # EntityNotFound ako None
           brief = self._campaign_repo.get_brief(campaign.brief_id)
           # EntityNotFound ako None
           snapshot = self._brand_repo.get_snapshot(campaign.brand_snapshot_id)
           # EntityNotFound ako None

           prompt = self._prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
           request = AIRequest(
               purpose=_PROMPT_NAME,
               prompt_name=_PROMPT_NAME,
               prompt_version=_PROMPT_VERSION,
               system_text=prompt.instructions,
               user_text=_build_user_text(brief, snapshot, plan),
               json_schema=VisualDirectionOutput.model_json_schema(),
           )
           response = self._ai_port.generate(request)
           # InvariantViolation ako structured_payload je None (isti obrazac)

           output = VisualDirectionOutput.model_validate(response.structured_payload)
           _validate_visual_domain(output)

           system_candidate = output.campaign_visual_system
           visual_system = CampaignVisualSystem(
               id=VisualSystemId(new_id()),
               campaign_id=campaign.id,
               primary_layout_family=system_candidate.primary_layout_family,
               secondary_layout_family=system_candidate.secondary_layout_family,
               headline_scale=system_candidate.headline_scale,
               image_treatment=system_candidate.image_treatment.value,
               logo_rule=system_candidate.logo_rule.value,
               cta_rule=system_candidate.cta_rule.value,
               alignment=system_candidate.alignment,
               created_at=utc_now(),
               style=tuple(system_candidate.style),
           )

           layout_candidate = output.layout_spec
           layout_spec = LayoutSpec(
               primitive=layout_candidate.primitive,
               image_position=layout_candidate.image_position,
               headline_position=layout_candidate.headline_position,
               headline_scale=layout_candidate.headline_scale,
               overlay=layout_candidate.overlay,
               logo_position=layout_candidate.logo_position,
               cta_style=layout_candidate.cta_style,
               alignment=layout_candidate.alignment,
               format=layout_candidate.format,
           )

           with self._unit_of_work:
               self._visual_repo.save_visual_system(visual_system)
               self._unit_of_work.commit()

           return visual_system, layout_spec
   ```

   Napomena implementeru: `CampaignVisualSystemCandidate.image_treatment`/
   `logo_rule`/`cta_rule` su tipizovani kao enum (`ImageTreatment`/
   `LogoRule`/`CtaRule`) u schema-i, ali `domain.visual.entities.CampaignVisualSystem`
   ta ista tri polja drži kao `str` (postojeći dizajn iz A3, ne mijenjati).
   Koristiti eksplicitno `.value` pri konverziji (kod primjera gore) —
   ne oslanjati se prećutno na to da je `StrEnum` instanca već `str`
   podtip, radi čitljivosti i da statička provjera tipova (mypy) prođe bez
   `# type: ignore`.

3. **`_build_user_text(brief, snapshot, plan)`** — isti stil kao u
   `generate_campaign_plan.py`, sadrži:
   - brief.offer/goal/content_language_context;
   - brand snapshot voice polja (formality/preferred_terms/forbidden_terms
     — isti razlog kao svuda: model ne smije birati stil koji je u
     sukobu sa brand voice-om, npr. "bold" stil za brend čiji je ton
     "neformalno-profesionalno, smireno");
   - plan items (role + topic, kratko, kontekst ZA STIL, ne ZA sadržaj —
     ovaj poziv ne generiše tekst posta);
   - eksplicitna lista SVIH dozvoljenih enum vrijednosti za svako polje
     (`LayoutPrimitive`, `HeadlineScale`, `Alignment`, `ImagePosition`,
     `HeadlinePosition`, `Overlay`, `LogoPosition`, `CtaStyle`,
     `ImageTreatment`, `LogoRule`, `CtaRule`) — isti razlog kao
     `campaign_plan`-ov eksplicitan `CampaignRole` popis: prompt YAML
     `instructions` kaže "ne izmišljaj vrijednosti" ali ne nabraja ih,
     `_build_user_text` MORA nabrojati zatvoren vokabular;
   - eksplicitna lista `_ALLOWED_STYLES`.

4. **`_validate_visual_domain(output: VisualDirectionOutput) -> None`**:
   - `style` podskup `_ALLOWED_STYLES` (case-sensitive, isti stil vrijednosti
     kao primjer u planu — implementer odlučuje da li normalizovati
     casefold, dokumentovati odluku u docstring-u ako se razlikuje od
     "case-sensitive").
   - Nema drugih domain provjera predviđenih za ovaj task (layout
     kompatibilnost sa formatom je A13 dio 2 posao).

5. **Testovi — `tests/unit/application/visual/test_generate_visual_system.py`**
   (fake repos/ai_port/prompt_repo/uow, isti fake-stil kao postojeći
   `test_generate_campaign_plan.py`):
   - Happy path: plan APPROVED, AI vraća validan HERO output → vraća
     `(CampaignVisualSystem, LayoutSpec)`, `visual_repo.save_visual_system`
     pozvan tačno jednom sa ispravno mapiranim poljima (uključujući
     `.value` konverziju za image_treatment/logo_rule/cta_rule).
   - Isto za SPLIT primitive (dokaz "HERO/SPLIT rade" — oba primitiva
     eksplicitno testirana, ne samo jedan).
   - Plan status != APPROVED (npr. DRAFT) → `InvariantViolation`, AI port
     NIJE pozvan (provjeriti fake poziv-brojač).
   - Plan/campaign/brief/snapshot ne postoji → `EntityNotFound` (4 odvojena
     testa ili parametrizovano, po postojećem obrascu u projektu).
   - AI vraća `structured_payload=None` → `InvariantViolation`.
   - AI vraća JSON sa NEVALIDNOM enum vrijednošću (npr.
     `"primary_layout_family": "DIAGONAL"`) → odbijeno. **Provjereno u
     postojećem kodu**: ni `generate_campaign_plan.py` ni
     `generate_social_post.py` ne hvataju `pydantic.ValidationError`
     eksplicitno — puštaju je da propagira sirovu. Ovaj task ostaje
     konzistentan sa TIM obrascem: `VisualDirectionOutput.model_validate(...)`
     baca `pydantic.ValidationError` direktno, BEZ pretvaranja u
     `InvariantViolation`. Test provjerava da je podignut
     `pydantic.ValidationError` (ili `pydantic_core.ValidationError`, u
     zavisnosti od importa), ne `InvariantViolation`.
   - AI vraća `style` sa nedozvoljenom vrijednošću (npr. `"aggressive"`) →
     `InvariantViolation` sa jasnom porukom koja nabraja koje vrijednosti
     nisu prepoznate.

6. **Integration test —
   `tests/integration/application/visual/test_generate_visual_system_integration.py`**:
   - Prava SQLite baza (isti fixture-setup obrazac kao
     `test_generate_campaign_plan_integration.py`/ekvivalent), fake AI port
     koji vraća fiksiran validan JSON.
   - End-to-end: `CreateCampaign` → `GenerateCampaignPlan` → `ApproveCampaignPlan`
     → `GenerateVisualSystem.execute(plan.id)` → `visual_repo.get_visual_system(result[0].id)`
     vraća isti sadržaj koji je snimljen (round-trip dokaz kroz pravu
     `SqliteVisualRepository`, ne fake).

# Acceptance

- [ ] `GenerateVisualSystem` postoji, koristi ISKLJUČIVO postojeće portove
      (`CampaignRepositoryPort`, `BrandRepositoryPort`, `VisualRepositoryPort`,
      `PromptRepositoryPort`, `TextGenerationPort`) — nema novog port
      metoda, nema nove migracije (git diff dokaz na `forbidden_paths`).
- [ ] Zahtijeva `CampaignPlanStatus.APPROVED`; DRAFT/druge vrijednosti →
      `InvariantViolation`, AI NIJE pozvan.
- [ ] HERO i SPLIT oba dokazano rade (dva odvojena testa, ne samo jedan
      primitive).
- [ ] Nedozvoljena enum vrijednost iz AI response-a → odbijena (test
      dokaz), ne tiho prihvaćena/koercirana.
- [ ] Nedozvoljena `style` vrijednost → `InvariantViolation` (kod-nivo
      provjera, ne oslanjanje na schema).
- [ ] `image_treatment`/`logo_rule`/`cta_rule` ispravno konvertovani iz
      enum candidate polja u `str` domain polja (`.value`, ne implicitna
      koercija).
- [ ] Perzistovan SAMO `CampaignVisualSystem`; `LayoutSpec` vraćen
      in-memory, BEZ pokušaja perzistencije (nema `layout_specs` tabele —
      git diff dokaz da `resources/migrations/` nije diran).
- [ ] `domain/`, `ports/`, `infrastructure/`, `application/schemas/`,
      `resources/migrations/`, `resources/prompts/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/application/visual/ tests/integration/application/visual/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/visual/test_generate_visual_system.py -v
python -m pytest tests/integration/application/visual/test_generate_visual_system_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Da li je `plan.status is APPROVED` zahtjev stvarno konzistentan sa
  ostatkom pipeline-a, ili je ovo mjesto gdje bi trebalo dozvoliti i DRAFT
  (vizuelni stil možda NE zavisi od odobrenja sadržaja) — implementer i
  reviewer procjenjuju, ovo NIJE strogo zaključana odluka u planu, samo
  konzistentan default sa postojećim precedentom;
- `_validate_visual_domain` stvarno hvata nedozvoljen `style`, ne samo
  prazan/None slučaj;
- enum→str konverzija (`image_treatment`/`logo_rule`/`cta_rule`) je
  eksplicitna i tipski ispravna (mypy čist, ne `# type: ignore`);
- `_build_user_text` stvarno nabraja SVE dozvoljene enum vrijednosti (lako
  je promašiti jedno polje uz ovoliko enuma — provjeriti liniju po liniju
  protiv `domain/visual/enums.py`);
- nema pokušaja perzistencije `LayoutSpec`-a (git diff na
  `resources/migrations/`, `ports/repositories.py`);
- testovi za HERO i SPLIT su STVARNO odvojeni, ne isti test parametrizovan
  sa dvije vrijednosti gdje bi jedna grana mogla proći neopaženo slomljena.

# Rollback

MEDIUM risk — nov application-layer fajl, reuse postojećih portova, nema
domain/port/migracija izmjene. Fix na istoj branch bez proširenja scope-a.
§29: Claude-only review, PASS → odmah merge.

# Coordination

Nezavisan od ACS-F1-028 (claim_linter data fix, disjoint fajlovi). Namjerno
implementer=TBD — sljedeći korak u redoslijedu ka `G10 Vertical Slice
PASS`, nije hitno, čeka da neko bude slobodan. Sljedeći task nakon ovog
(A13 dio 2 — `plan_post_layout.py`/`validate_layout.py`, zahtijeva NOVU
`layout_specs` migraciju + nov port metod) NIJE još napisan — čeka da se
ovaj task završi i pokaže da li dizajn (in-memory `LayoutSpec` iz jednog
kombinovanog poziva) stvarno ima smisla u praksi prije nego što se
per-post tok projektuje.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-029-generate-visual-system
Branch:   task/ACS-F1-029-generate-visual-system
Base:     main @ ed801aa
```
