---
task_id: ACS-F1-033
phase: Faza-1 (post A14 dio 1) — A14 dio 2, PRODUKCIJSKI RENDERER (plan sekcije 43-45)
title: "RendererPort + PillowRenderer + RenderPost: prvo stvarno renderovanje slika"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: [ACS-F1-032]
allowed_paths:
  - src/ai_campaign_studio/ports/rendering.py
  - src/ai_campaign_studio/infrastructure/rendering/__init__.py
  - src/ai_campaign_studio/infrastructure/rendering/selected_renderer.py
  - src/ai_campaign_studio/application/rendering/__init__.py
  - src/ai_campaign_studio/application/rendering/render_post.py
  - src/ai_campaign_studio/ports/repositories.py
  - src/ai_campaign_studio/infrastructure/database/repositories/sqlite_visual_repository.py
  - tests/unit/ports/test_rendering.py
  - tests/unit/infrastructure/rendering/test_selected_renderer.py
  - tests/unit/application/rendering/test_render_post.py
  - tests/integration/application/rendering/test_render_post_integration.py
  - tests/integration/database/repositories/test_sqlite_visual_repository.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/schemas/
  - resources/migrations/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/visual/
  - src/ai_campaign_studio/application/evaluation/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    Nov port (`ports/rendering.py`) i prvo stvarno korištenje
    `VisualRepositoryPort.get_layout_spec` (do sad postojao ali bez
    pozivaoca po `layout_spec_id` — ovaj task dodaje NOVU metodu
    `get_layout_spec_by_content_piece` da omogući prirodan lookup po
    postu). Koordinator pokreće detect-changes/impact prije merge-a
    (GitNexus MCP dostupan, indeks stale — re-index prije provjere).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: f251a89
  scope_fit: "PENDING — popuniti kad se GitNexus indeks osvježi prije merge-a."
---

# Kontekst

ACS-F1-032 (renderer spike) je odlučio: **R-B (SVG-source/Pillow rasterizacija)**
pobjeđuje R-A (Playwright) — packaging (nema chromium binary), performance
(15x brže), text measurement (pure-Python `font.getlength()`). Ovaj task
je A14 dio 2: prvo STVARNO renderovanje slike u produkcijskom kodu,
plan sekcije 43-45.

**Namjerna dizajn odluka (obrazloženje ispod)**: produkcijski renderer
KORISTI Pillow direktno (isti pristup dokazan u spike-u), NE dodaje
`cairosvg`/`resvg` kao novu zavisnost. Spike evidence je spomenuo "swap
za pravu SVG biblioteku" kao MOGUĆNOST, ne kao zahtjev — te biblioteke
NISU verifikovane da rade u ovom dev okruženju (cairosvg zahtijeva
nativnu Cairo biblioteku, često problematično na Windows-u bez
GTK runtime-a), i Pillow je VEĆ projektna zavisnost. Dodavanje nativne
zavisnosti sada bi bio nepotvrđen rizik za "local-first desktop app"
cilj (CLAUDE.md) bez dokazane potrebe. `template.svg` iz spike-a ostaje
DOKUMENTACIONA referenca layout dizajna, NE parsira se u runtime-u.
Ako se pokaže potreba za pravim SVG parsing-om (npr. designer workflow),
to je zaseban budući task sa svojom procjenom zavisnosti.

**Druga namjerna dizajn odluka**: `RenderRequest` (plan sekcija 43) NEMA
polje za "brand name"/boju iz `BrandSnapshot`/`VisualIdentity` — plan
eksplicitno nabraja samo `content_piece_id, format, layout_spec, content,
visual_system, image_path?, logo_path?, output_path`. Ovo znači Slice-1
renderer NEMA pristup brand bojama/imenu preko strukturiranog kanala —
koristi FIKSNU, neutralnu paletu (nije brand-driven). Ovo je POZNATO
ograničenje, ne propust: threading pravih brand boja kroz render pipeline
je zaseban budući task (zahtijevao bi proširenje `RenderRequest`-a, izvan
scope-a ovog kontrakta koji prati plan doslovno).

# Objective

## 1. `ports/rendering.py` (plan sekcija 43)

```python
class RenderStatus(StrEnum):
    SUCCESS = "SUCCESS"
    LAYOUT_VALIDATION_ERROR = "LAYOUT_VALIDATION_ERROR"  # plan sekcija 44, doslovno
    RENDER_ERROR = "RENDER_ERROR"  # neočekivan izuzetak tokom renderovanja

@dataclass(frozen=True)
class RenderRequest:
    content_piece_id: PostId
    format: str  # "1080x1350" itd, isti Slice-1 string kao LayoutSpec.format
    layout_spec: LayoutSpec
    content: SocialPostPayload  # REUSE postojećeg domain tipa, NE nov tip
    visual_system: CampaignVisualSystem
    output_path: str
    image_path: str | None = None
    logo_path: str | None = None

@dataclass(frozen=True)
class RenderResult:
    status: RenderStatus
    output_path: str | None
    warnings: tuple[str, ...]
    measured_slots: dict[str, dict[str, float]]  # npr. {"headline": {"width_px": .., "height_px": ..}}
    render_ms: float

class RendererPort(Protocol):
    def render(self, request: RenderRequest) -> RenderResult: ...
```

Renderer NE zna `CampaignRepositoryPort`/`ContentRepositoryPort` —
dobije SVE kroz `RenderRequest` (plan doslovno: "Renderer ne zna
Campaign repository. Dobije sve kroz request.").

## 2. `infrastructure/rendering/selected_renderer.py` — `PillowRenderer`

Implementira `RendererPort`. Za SVAKI render:

- Parsira `request.format` ("1080x1350" → 1080×1350 canvas).
- Kreira Pillow `Image` platno, popunjava FIKSNOM neutralnom pozadinom
  (implementer bira konkretnu boju/gradient — jedan dosljedan izbor za
  sve rendere, dokumentovan, NE brand-driven).
- **Headline**: koristi `request.content.headline`, font veličinu bira
  po `request.layout_spec.headline_scale` mapiranu na RASPON iz
  `application/visual/validate_layout.py::_HERO_HEADLINE`/`_SPLIT_HEADLINE`
  (`min_font_size`/`max_font_size` po primitivu — `SMALL`→min,
  `LARGE`→max, `MEDIUM`→sredina) — REUSE postojećih brojki, NE
  izmišljati nove. Word-wrap preko `font.getlength()` (isti pristup
  dokazan u spike-u).
- **Pozicija/poravnanje**: `headline_position` (TOP/CENTER/BOTTOM) i
  `alignment` (LEFT/CENTER/RIGHT) MORAJU imati STVARAN, testabilan efekat
  na x/y koordinate teksta — ne smiju biti ignorisani.
- **CTA**: ako `visual_system.cta_rule` (plain string) implicira "hide"
  (implementer definiše tačan match, npr. case-insensitive `"hide"`),
  CTA element se NE crta. Inače, `request.content.cta` tekst se crta
  u dugmetu čiji vizuelni stil zavisi od `layout_spec.cta_style`
  (SOLID/OUTLINE/TEXT moraju izgledati VIDLJIVO drugačije).
- **Logo**: ako `visual_system.logo_rule` implicira "hide", logo se
  preskače. Ako `request.logo_path` nije `None` I fajl postoji na disku,
  učitati i nacrtati na poziciji `layout_spec.logo_position`. Ako je
  `None` ili fajl ne postoji, logo se PRESKAČE (nema fallback
  inicijala/teksta — to je bio spike flourish, nije plan zahtjev).
- **Image**: ako `request.image_path` nije `None` i fajl postoji, koristi
  ga kao pozadinsku/pozicioniranu sliku po `layout_spec.image_position`
  (BACKGROUND/LEFT/RIGHT/TOP/BOTTOM/NONE). Ako `None`, preskočiti (nema
  placeholder slike — Slice 1 nema image upload pipeline).
- **Overlay**: `layout_spec.overlay` (NONE/DARK/LIGHT/GRADIENT) mora
  vidljivo mijenjati kontrast/ton pozadine kad image_path postoji I
  vrijednost nije `NONE`.
- **HERO vs SPLIT**: primitivi MORAJU proizvesti VIDLJIVO različit
  layout (npr. HERO = headline preko cijele širine, SPLIT = headline u
  jednoj polovini) — implementer bira tačnu geometriju, ali razlika
  mora biti stvarna, ne kozmetička.
- **Overflow/`LAYOUT_VALIDATION_ERROR`** (plan sekcija 44): nakon
  word-wrap-a, izmjeriti STVARNU renderovanu visinu headline bloka
  (`measured_slots["headline"]["height_px"]`) protiv budžeta izvedenog
  iz `max_lines × font_size × line_height` (implementer bira razuman
  `line_height`, npr. 1.2). Ako prekoračeno: `status =
  RenderStatus.LAYOUT_VALIDATION_ERROR`, `warnings` sadrži jasnu poruku
  (dovoljno konkretnu da BUDUĆA `SHORTEN_HEADLINE` akcija — NIJE
  implementirana ovdje, plan to eksplicitno ostavlja za application
  sloj — zna ŠTA da skrati). I DALJE upisati PNG na `output_path` (ne
  odbiti render u potpunosti — plan kaže "ne regenerisati cijeli post",
  implicira da se render SVEJEDNO dešava, samo se flaguje).
- Neuhvaćen izuzetak tokom renderovanja (npr. corrupt image fajl) →
  uhvatiti, vratiti `status=RenderStatus.RENDER_ERROR` sa opisom u
  `warnings`, NE propagirati sirov Pillow izuzetak.
- Snimiti PNG na `request.output_path` (kreirati roditeljski direktorijum
  ako ne postoji).
- Izmjeriti `render_ms` (stvarno vrijeme izvršavanja poziva).

## 3. `ports/repositories.py` — nova metoda na `VisualRepositoryPort`

```python
def get_layout_spec_by_content_piece(
    self, content_piece_id: PostId
) -> LayoutSpec | None:
    """Most recently created layout spec for one content piece.

    ``layout_specs.content_piece_id`` nema unique constraint (ACS-F1-030) —
    ako više redova postoji (npr. post je re-planiran), vraća NAJNOVIJI
    (ORDER BY created_at DESC). Ovo je poznato pojednostavljenje, ne
    puna de-duplikacija/superseding logika.
    """
```

Implementirati u `SqliteVisualRepository`. `save_visual_system`/
`get_visual_system`/`save_layout_spec`/`get_layout_spec` NETAKNUTE
(git diff dokaz).

## 4. `application/rendering/render_post.py` — `RenderPost` use-case

```python
class RenderPost:
    def __init__(
        self,
        content_repo: ContentRepositoryPort,
        campaign_repo: CampaignRepositoryPort,
        visual_repo: VisualRepositoryPort,
        renderer: RendererPort,
    ) -> None: ...

    def execute(
        self,
        content_piece_id: PostId,
        visual_system_id: VisualSystemId,
        output_path: str,
    ) -> RenderResult:
        ...
```

**Napomena o `visual_system_id` kao eksplicitnom parametru**: `LayoutSpec`
NEMA `visual_system_id` polje (samo `content_piece_id`), i ne postoji
port metoda koja vrati "campaign koji sadrži ovaj content_piece" preko
`campaign_item_id` lanca. Umjesto dodavanja nove lookup metode, ISTI
obrazac kao `PlanPostLayout` (ACS-F1-031, koji iz istog razloga uzima
`plan_id` eksplicitno) — pozivalac VEĆ ima `visual_system_id` iz ranije
u toku (npr. `GenerateVisualSystem`-ov povratni objekat), pa ga
jednostavno proslijedi. Ovo NIJE otvoreno istraživačko pitanje za
implementera — dizajn odluka je već donesena, primijeniti dosljedno.

Tok:
- `content_repo.get_content_piece(content_piece_id)` → `EntityNotFound`
  ako `None`; `piece.payload is None` → `InvariantViolation` (nema šta
  da se renderuje).
- `visual_repo.get_layout_spec_by_content_piece(content_piece_id)` →
  `EntityNotFound` ako `None` (post mora prvo proći kroz
  `PlanPostLayout`, ACS-F1-031).
- `visual_repo.get_visual_system(visual_system_id)` → `EntityNotFound`
  ako `None`.
- Konstruisati `RenderRequest` (content=`piece.payload`,
  layout_spec=pronađeni, visual_system=pronađeni, format=layout_spec.format,
  image_path=`None` [nema image pipeline], logo_path=
  `brand_snapshot.visual_identity.logo_path` ako se brand snapshot može
  naći, inače `None`, output_path=parametar).
- Pozvati `renderer.render(request)`, vratiti `RenderResult` bez izmjene.
- **BEZ perzistencije** — `render_artifacts` tabela NE postoji (nije u
  stvarnim migracijama), namjerno van scope-a (budući task ako se pokaže
  potrebnim, isti obrazac kao A13 foundation-prije-use-case).

# Implementation steps

1. `ports/rendering.py` po Objective #1.
2. `VisualRepositoryPort.get_layout_spec_by_content_piece` +
   `SqliteVisualRepository` implementacija po Objective #3 — NAJPRIJE
   ovo, testirano izolovano.
3. `infrastructure/rendering/selected_renderer.py` po Objective #2 —
   NAJVEĆI dio posla, testirati inkrementalno (prvo osnovni HERO render,
   pa SPLIT, pa overflow, pa CTA/logo/overlay varijante).
4. `application/rendering/render_post.py` po Objective #4 — TEK nakon
   što je jasno kako doći do `CampaignVisualSystem` iz `content_piece_id`
   (istražiti PRIJE pisanja, ne nagađati).
5. Testovi:
   - `test_rendering.py` (unit, port dataclass shape — isti stil kao
     `test_ai.py` iz evidence pretrage ranije, provjerava da su
     `RenderRequest`/`RenderResult` prave dataclass-e).
   - `test_selected_renderer.py` (unit, direktan poziv `PillowRenderer.render()`
     sa ručno konstruisanim `RenderRequest`, BEZ fake portova — čist
     input/output test): HERO i SPLIT vidljivo različiti (provjeriti
     piksel-nivo razliku, npr. usporediti dva PNG-a da NISU identični
     bajt-za-bajt), `alignment`/`headline_position` mijenjaju tekst
     poziciju (izmjeriti/provjeriti kroz `measured_slots` ili direktnim
     pixel sampling-om), predug headline → `LAYOUT_VALIDATION_ERROR` +
     PNG I DALJE napisan na disk, kratak headline → `SUCCESS`,
     `logo_rule`/`cta_rule` "hide" stvarno izostavljaju element (usporediti
     dva rendera sa/bez), nepostojeći `image_path`/`logo_path` fajl NE
     baca izuzetak (graceful skip).
   - `test_render_post.py` (unit, fake portovi + fake renderer): happy
     path, `EntityNotFound` za nedostajući content_piece/layout_spec,
     `InvariantViolation` za `payload is None`, renderer poziv dobija
     ISPRAVNO popunjen `RenderRequest` (provjeriti sadržaj, ne samo da
     je pozvan).
   - `test_render_post_integration.py` (integration, prava SQLite +
     stvaran `PillowRenderer`, NE fake): puni lanac fixture→brief→plan→
     approve→post→visual_system→layout→**render**, PNG stvarno postoji
     na disku na kraju (`Path(output_path).exists()`), veličina fajla > 0.

# Acceptance

- [ ] `ports/rendering.py` sadrži `RenderRequest`/`RenderResult`/
      `RenderStatus`/`RendererPort` tačno po planu (imena polja).
- [ ] `PillowRenderer` renderuje STVARAN PNG na disk za HERO i SPLIT,
      vizuelno različit (test dokaz, ne samo "ne baca izuzetak").
- [ ] `alignment`/`headline_position`/`overlay`/`cta_style`/`logo_rule`/
      `cta_rule` svaki ima STVARAN, testiran efekat na izlaz.
- [ ] Predug headline → `LAYOUT_VALIDATION_ERROR`, PNG SVEJEDNO napisan
      (ne blokira potpuno).
- [ ] Nepostojeći `image_path`/`logo_path` ne baca izuzetak (graceful).
- [ ] `get_layout_spec_by_content_piece` vraća najnoviji red kad ih ima
      više (test dokaz), `None` kad nema nijednog.
- [ ] `RenderPost` NE perzistuje ništa (nema `render_artifacts` tabele/
      poziva) — vraća `RenderResult` direktno.
- [ ] `domain/`, `application/schemas/`, `resources/migrations/`,
      `application/campaigns/`, `application/posts/`,
      `application/visual/`, `application/evaluation/` NISU DIRANI.
- [ ] Nema nove eksterne zavisnosti (Pillow je već projektna zavisnost —
      git diff na `pyproject.toml` treba biti PRAZAN ili nepostojeći).
- [ ] `python -m pytest tests/unit/ports/test_rendering.py tests/unit/infrastructure/rendering/ tests/unit/application/rendering/ tests/integration/application/rendering/ tests/integration/database/repositories/test_sqlite_visual_repository.py -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/ports/test_rendering.py -v
python -m pytest tests/unit/infrastructure/rendering/ -v
python -m pytest tests/unit/application/rendering/ -v
python -m pytest tests/integration/application/rendering/ -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- OTVORITI stvarno renderovane PNG fajlove iz testova (ne vjerovati
  "renderovano" bez pogleda na sliku) — provjeriti da HERO/SPLIT stvarno
  izgledaju drugačije, da overflow slučaj ipak proizvodi validan PNG;
- `get_layout_spec_by_content_piece` "najnoviji red" logika stvarno
  testirana sa VIŠE redova za isti content_piece_id, ne samo jednim;
- `RenderPost.execute` stvarno prima `visual_system_id` kao eksplicitan
  parametar (isti obrazac kao `PlanPostLayout`), NE pokušava izmisliti
  lookup preko `campaign_item_id` koji ne postoji;
- nema nove zavisnosti u `pyproject.toml` (Pillow već postoji);
- `RenderRequest`/`RenderResult` polja tačno odgovaraju plan sekciji 43
  (nema dodatih/izostavljenih polja bez obrazloženja);
- `LAYOUT_VALIDATION_ERROR` ponašanje (render SVEJEDNO piše PNG) je
  namjerno — provjeriti da implementacija to poštuje, ne blokira render
  u potpunosti.

# Rollback

MEDIUM risk — nov port + nov use-case + nova infrastructure adapter
metoda, jedna nova port metoda na postojećem portu (aditivno). Nema
domain/migracija izmjene, nema nove zavisnosti. Fix na istoj branch bez
proširenja scope-a. §29: Claude-only review, PASS → odmah merge.

# Coordination

Zavisi od ACS-F1-029/030/031/032 (svi već mergovani) — UNBLOCKED. Nakon
ovog taska, A14 je potpuno gotov u kodu. Sljedeći korak ka `G10 Vertical
Slice PASS`: A15 (ZIP export + telemetry summary, plan sekcija 46) —
prvi kandidat koji stvarno spaja render→export u jedan tok, i tačka gdje
`render_artifacts`-stil perzistencija (ako se pokaže potrebnom) prirodno
ulazi u sliku.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-033-render-post
Branch:   task/ACS-F1-033-render-post
Base:     main @ f251a89
```
