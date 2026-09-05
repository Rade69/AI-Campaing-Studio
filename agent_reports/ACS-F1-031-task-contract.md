---
task_id: ACS-F1-031
phase: Faza-1 (post A16) — A13 dio 2b (plan sekcije 40-41)
title: "PlanPostLayout + validate_layout: AI-generisan per-post LayoutSpec + provjera da headline staje u layout"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: [ACS-F1-029, ACS-F1-030]
allowed_paths:
  - resources/prompts/post_layout/v1.yaml
  - src/ai_campaign_studio/application/visual/plan_post_layout.py
  - src/ai_campaign_studio/application/visual/validate_layout.py
  - tests/unit/application/visual/test_plan_post_layout.py
  - tests/unit/application/visual/test_validate_layout.py
  - tests/integration/application/visual/test_plan_post_layout_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/application/schemas/
  - resources/migrations/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/evaluation/
  - src/ai_campaign_studio/application/visual/generate_visual_system.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Prvi stvarni pozivalac `VisualRepositoryPort.save_layout_spec`/
    `get_layout_spec` (ACS-F1-030, do sad nekorišteni) i prvi novi
    application-layer modul koji čita `CampaignVisualSystem` (do sad
    samo pisan, u ACS-F1-029). Koordinator pokreće detect-changes/impact
    prije merge-a (GitNexus MCP dostupan, indeks stale — re-index prije
    provjere) da potvrdi da nema neočekivanih postojećih pozivalaca.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 30f66e5
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

A13 dio 1 (ACS-F1-029) perzistuje `CampaignVisualSystem` po kampanji. A13
dio 2 (ACS-F1-030) je izgradio `layout_specs` fundaciju (migracija +
`LayoutSpecId` + `VisualRepositoryPort.save_layout_spec`/`get_layout_spec`)
ali BEZ ijednog use-case-a koji je stvarno koristi. Ovaj task je taj
use-case — plan sekcije 40-41, posljednji application-layer komad prije
A14 (renderer).

**Ključna dizajn odluka, izvedena iz postojećeg koda (ne nagađanje)**:
plan sekcija 40 kaže input uključuje "supported primitives" — ovo NIJE
cijeli `LayoutPrimitive` enum (trenutno samo HERO/SPLIT postoje pa bi to
bilo skoro besmisleno ograničenje), nego KAMPANJSKI VEĆ ODLUČENI skup iz
`CampaignVisualSystem.primary_layout_family` (+ `secondary_layout_family`
ako postoji). Ovo čuva vizuelnu koherentnost kampanje: `GenerateVisualSystem`
(ACS-F1-029) je već odlučio "ova kampanja koristi HERO kao primarni, SPLIT
kao sekundarni" — svaki pojedinačni post bira IZMEĐU TIH, ne iz cijelog
univerzuma mogućih primitiva. AI koji vrati primitiv van tog skupa je
STVARNO odbijen (InvariantViolation, ništa se ne perzistuje) — ovo je
"invalid layout rejected" iz A13 acceptance kriterijuma, doslovno.

**Druga ključna odluka**: `LayoutSpecCandidate.format` (plan schema polje,
slobodan string) se IGNORIŠE iz AI odgovora i UVIJEK prepisuje na
Slice-1 konstantu `"1080x1350"` prije perzistencije — ne postoji platform
registry→pixel-dimenzija mapiranje u kodu (samo `supported_aspect_ratios`
kao tuple stringova poput "4:5", ne piksel dimenzije), i Vertical Slice 1
prema planu (sekcija "Početni social registry...") ionako renderuje SAMO
jedan dokazni format. Deterministički override je sigurniji od oslanjanja
na AI da dosljedno vrati tačan string.

**Treća odluka**: `validate_layout.py` NE konstruiše pun domain
`ContentSlotContract` (`domain/visual/slots.py`) — taj objekat traži
`bounding_box`/`font_family`/`line_height`/`preferred_case`/`overflow_policy`,
polja koja plan sekcija 41 NE specificira (to su renderer-specific detalji,
tek A14 posao — "Golden/render test treba ih kalibrisati"). Izmišljanje tih
vrijednosti sada bi bilo nagađanje, ne legitimna pojednostavljenje.
Umjesto toga, `validate_layout.py` drži MALU, lokalnu strukturu sa SAMO
onim što sekcija 41 stvarno daje (target_chars/max_chars/max_lines/
min_font_size/max_font_size za HERO i SPLIT headline) — provjerava SAMO
headline dužinu (CTA numerički defaulti NISU dati u planu, CTA provjera
NIJE u scope-u ovog taska).

# Objective

1. **`resources/prompts/post_layout/v1.yaml`** (nov prompt) — koristi
   POSTOJEĆI `LayoutSpecCandidate` (iz `application/schemas/visual_direction_output.py`,
   NE novi schema) kao `output_contract`. System instrukcije: dobiješ već
   odlučen `CampaignVisualSystem` + tekst KONKRETNOG posta + dozvoljene
   primitive za ovu kampanju + dozvoljene enum vrijednosti; vrati SAMO
   layout spec (ne novi visual system); ne izmišljaj CSS; koristi tačno
   dozvoljene enum vrijednosti.

2. **`application/visual/plan_post_layout.py`** — `PlanPostLayout` use-case:
   ```python
   class PlanPostLayout:
       def __init__(
           self,
           campaign_repo: CampaignRepositoryPort,
           content_repo: ContentRepositoryPort,
           visual_repo: VisualRepositoryPort,
           prompt_repo: PromptRepositoryPort,
           ai_port: TextGenerationPort,
           unit_of_work: _UnitOfWork,
       ) -> None: ...

       def execute(
           self,
           content_piece_id: PostId,
           visual_system_id: VisualSystemId,
           plan_id: CampaignPlanId,
       ) -> LayoutSpec: ...
   ```
   Tok:
   - `content_repo.get_content_piece(content_piece_id)` → `EntityNotFound`
     ako `None`; `content_piece.payload is None` → `InvariantViolation`
     (post mora već imati generisan tekst — layout bez teksta se ne može
     provjeriti na fit).
   - `visual_repo.get_visual_system(visual_system_id)` → `EntityNotFound`
     ako `None`.
   - `campaign_repo.get_plan(plan_id)` → `EntityNotFound` ako `None`;
     pronaći `item = next((i for i in plan.items if i.id ==
     content_piece.campaign_item_id), None)` → `EntityNotFound` ako nije
     nađen (item mora pripadati datom planu).
   - Sastaviti dozvoljeni skup primitiva:
     `{visual_system.primary_layout_family}` (+ `secondary_layout_family`
     ako nije `None`).
   - AI poziv (`post_layout`/`1`, `LayoutSpecCandidate.model_json_schema()`),
     `_build_user_text` uključuje: visual_system polja (primary/secondary
     layout family, headline_scale, image_treatment, logo_rule, cta_rule,
     alignment, style), item.role/topic (kontekst, ne sadržaj za
     reprodukciju), `content_piece.payload.headline`/`.cta` (STVARAN tekst
     koji layout mora primiti), dozvoljeni primitivi za OVU kampanju
     (ne cijeli enum), i sve dozvoljene enum vrijednosti za ostala
     `LayoutSpecCandidate` polja (isti "nabroji sve" obrazac kao
     ACS-F1-029 `_build_user_text`).
   - `structured_payload is None` → `InvariantViolation`.
   - `LayoutSpecCandidate.model_validate(...)` — nevalidna enum vrijednost
     → `pydantic.ValidationError` propagira sirovo (isti obrazac kao
     ACS-F1-029, NE hvatati).
   - **Provjera pripadnosti primitivu**: `candidate.primitive` MORA biti u
     dozvoljenom skupu za ovu kampanju → ako nije, `InvariantViolation`
     (STVARNO odbijeno, NIŠTA se ne perzistuje — ovo je "invalid layout
     rejected").
   - Konstruisati "draft" `LayoutSpec` (bez `id`/`content_piece_id`/
     `validation_status`, `format` HARDKODIRAN na Slice-1 konstantu, NE
     `candidate.format`).
   - Pozvati `validate_layout(draft, content_piece.payload.headline)` →
     `(is_valid, reasons)`. Za razliku od primitiv-pripadnosti, OVO NIJE
     fatalno — headline koji ne staje se PERZISTUJE sa
     `validation_status="INVALID"` (za buduće ljudsko/automatsko
     razmatranje), NE baca izuzetak.
   - `dataclasses.replace(draft, id=LayoutSpecId(new_id()),
     content_piece_id=content_piece_id, validation_status="VALID" if
     is_valid else "INVALID")`.
   - `visual_repo.save_layout_spec(layout)` unutar UoW, commit.
   - Vratiti perzistovani `layout`.

3. **`application/visual/validate_layout.py`** — čista, deterministička,
   bez I/O (isti stil kao `claim_linter.py`/`content_similarity.py`):
   ```python
   @dataclass(frozen=True)
   class _HeadlineLimits:
       target_chars: tuple[int, int]
       max_chars: int
       max_lines: int
       min_font_size: float
       max_font_size: float

   _HERO_HEADLINE = _HeadlineLimits((28, 42), 55, 2, 48.0, 72.0)
   _SPLIT_HEADLINE = _HeadlineLimits((24, 38), 48, 3, 42.0, 64.0)

   def validate_layout(
       layout: LayoutSpec, headline_text: str
   ) -> tuple[bool, tuple[str, ...]]:
       """Slice-1 headline-only fit check (plan sekcija 41).

       CTA slot provjera NIJE u scope-u — plan ne daje CTA numeričke
       defaulte za Slice 1. Vrijednosti ovdje su POČETNI test parametri
       (per plan §41: "Ovo nisu trajne dizajnerske istine"), ne konačan
       render-kalibrisan zaključak.
       """
   ```
   Provjerava SAMO `len(headline_text) > limits.max_chars` za primitiv
   HERO ili SPLIT (jedina dva koja trenutno postoje). Vraća `(True, ())`
   ako staje, `(False, (razlog,))` ako ne.

# Implementation steps

1. Napisati `resources/prompts/post_layout/v1.yaml` po Objective #1.
2. Napisati `validate_layout.py` po Objective #3 — NAJPRIJE ovaj fajl
   (nema zavisnosti od AI/portova, lako izolovano testirati).
3. Napisati `plan_post_layout.py` po Objective #2, model po
   `generate_campaign_plan.py`/`generate_visual_system.py` stilu
   (`_UnitOfWork` Protocol lokalno, `_PROMPT_NAME`/`_PROMPT_VERSION`
   konstante, `_build_user_text` helper, `_SLICE1_FORMAT = "1080x1350"`
   modul-level konstanta).
4. Testovi `test_validate_layout.py` (unit, bez fake portova):
   - HERO headline unutar 55 karaktera → `(True, ())`.
   - HERO headline preko 55 karaktera → `(False, (...,))`, razlog
     pominje "HERO" i stvarnu dužinu.
   - SPLIT headline unutar 48 karaktera → `(True, ())`.
   - SPLIT headline preko 48 karaktera → `(False, (...,))`.
   - Granica tačno na `max_chars` → `True` (`<=`, ne `<`).
5. Testovi `test_plan_post_layout.py` (unit, fake portovi, isti stil kao
   `test_generate_visual_system.py`):
   - Happy path: `visual_system.primary_layout_family=HERO`,
     `secondary_layout_family=None`, AI vraća `primitive="HERO"`,
     kratak headline → `save_layout_spec` pozvan 1×, `validation_status
     == "VALID"`, `format == "1080x1350"` (NE ono što je AI vratio za
     `format`, dokazati eksplicitno da je override primijenjen čak i ako
     fake AI vrati drugačiji format string).
   - AI vraća `primitive="SPLIT"` kad je `secondary_layout_family=SPLIT`
     (dozvoljeno, dva primitiva u skupu) → prihvaćeno.
   - AI vraća `primitive="SPLIT"` kad `secondary_layout_family=None`
     (samo HERO dozvoljen) → `InvariantViolation`, `save_layout_spec`
     NIJE pozvan (dokaz "invalid layout rejected").
   - AI vraća validan primitiv ali PREDUG headline (preko max_chars za
     taj primitiv) → NE baca izuzetak, `save_layout_spec` pozvan 1× SA
     `validation_status == "INVALID"` (dokaz da headline-fit nije
     fatalan, za razliku od primitiv-pripadnosti).
   - `content_piece.payload is None` → `InvariantViolation`, AI nije
     pozvan.
   - Nedostaje content_piece/visual_system/plan/item (4 GENUINE odvojena
     scenarija, isti oblik kao ACS-F1-029 review fix — svaki mora stvarno
     gađati svoj kod-put, ne spojen sa susjednim) → `EntityNotFound`.
   - Nevalidna enum vrijednost iz AI → `pydantic.ValidationError`.
6. Integration test `test_plan_post_layout_integration.py`:
   - Prava SQLite: fixture → CreateCampaign → GenerateCampaignPlan →
     ApproveCampaignPlan → GenerateSocialPost (pravi
     `content_piece_id`) → `GenerateVisualSystem` (pravi
     `visual_system_id`) → `PlanPostLayout.execute(...)` →
     `visual_repo.get_layout_spec(layout.id)` vraća isti sadržaj
     (round-trip kroz pravi `SqliteVisualRepository`).

# Acceptance

- [ ] `resources/prompts/post_layout/v1.yaml` postoji, koristi POSTOJEĆI
      `LayoutSpecCandidate` (git diff dokaz da `application/schemas/`
      NIJE diran).
- [ ] `PlanPostLayout` odbija primitiv van kampanjskog dozvoljenog skupa
      (`InvariantViolation`, ništa perzistovano) — test dokaz.
- [ ] `PlanPostLayout` NE odbija predug headline (perzistuje sa
      `validation_status="INVALID"`) — test dokaz, jasno razlikovano od
      gornje stavke.
- [ ] `format` je UVIJEK Slice-1 konstanta na perzistovanom objektu,
      bez obzira šta je AI vratio za to polje.
- [ ] `validate_layout` provjerava SAMO headline (HERO/SPLIT), tačne
      brojke iz plan sekcije 41, granica `<=` je `True`.
- [ ] 4 GENUINE odvojena "entity not found" scenarija (ne spojena, isti
      standard kao ACS-F1-029 fix runda).
- [ ] `domain/`, `ports/`, `infrastructure/`, `application/schemas/`,
      `resources/migrations/`, `application/visual/generate_visual_system.py`
      NISU DIRANI.
- [ ] `python -m pytest tests/unit/application/visual/ tests/integration/application/visual/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/visual/test_validate_layout.py -v
python -m pytest tests/unit/application/visual/test_plan_post_layout.py -v
python -m pytest tests/integration/application/visual/test_plan_post_layout_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Primitiv-pripadnost provjera STVARNO koristi kampanjski skup (primary
  [+ secondary]), ne cijeli `LayoutPrimitive` enum — lako pogriješiti i
  slučajno dozvoliti bilo koji enum član;
- `format` override je STVARNO bezuslovan (test sa AI koji vrati NAMJERNO
  drugačiji format string, provjeriti da se ipak perzistuje Slice-1
  konstanta);
- headline-fit i primitiv-pripadnost imaju STVARNO različito ponašanje
  (jedna baca, druga samo flaguje) — ovo je namjerna asimetrija, provjeriti
  da implementacija to ne zamijeni;
- 4 "entity not found" scenarija stvarno gađaju 4 različita mjesta (isti
  standard kao ACS-F1-029 review nalaz — provjeriti da se greška ne
  ponovi);
- `validate_layout.py` ne uvodi `domain/visual/slots.py`
  (`ContentSlotContract`) niti izmišlja bounding_box/font podatke koje
  plan ne specificira.

# Rollback

MEDIUM risk — nov application-layer use-case + nov prompt, reuse
postojećih portova (ACS-F1-029/030), nema domain/port/migracija izmjene.
Fix na istoj branch bez proširenja scope-a. §29: Claude-only review,
PASS → odmah merge.

# Coordination

Zavisi od ACS-F1-029 (mergovano) i ACS-F1-030 (mergovano) — oba već u
main-u, ovaj task je UNBLOCKED. Nakon ovog taska, A13 je POTPUNO gotov u
kodu (sekcije 39-41). Sljedeći korak ka `G10 Vertical Slice PASS`: A14
(renderer spike + produkcijski renderer, plan sekcija 42+), zatim A15
(export).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-031-plan-post-layout
Branch:   task/ACS-F1-031-plan-post-layout
Base:     main @ 30f66e5
```
