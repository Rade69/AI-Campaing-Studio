---
task_id: ACS-S2-012
phase: "S2-G5 â€” Visual Identity Extraction"
title: "asset_extractor + visual_identity_extractor (adapteri za postojeÄ‡i VisualIdentityExtractorPort + VisualIdentity VO)"
coordinator: MiniMax (privremeno, Claude na pauzi)
implementer: pi
reviewers: [claude, codex]
status: "OPEN -- contract written before code, Äeka implementera"
created_at: 2026-09-10
dependencies: [ACS-S2-001, ACS-S2-002, ACS-S2-009, ACS-S2-010]
risk: MEDIUM
allowed_paths:
  - src/ai_campaign_studio/infrastructure/visual_extraction/
  - src/ai_campaign_studio/infrastructure/visual_extraction/__init__.py
  - pyproject.toml
  - tests/unit/infrastructure/visual_extraction/
  - tests/unit/infrastructure/visual_extraction/__init__.py
  - tests/integration/visual_extraction/
  - tests/integration/visual_extraction/__init__.py
forbidden_paths:
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/presentation_webview/
  - src/ai_campaign_studio/jobs/
  - src/ai_campaign_studio/infrastructure/web_ingestion/  # G3 scope, NE G5
  - src/ai_campaign_studio/infrastructure/extraction/       # G4 scope, NE G5
  - src/ai_campaign_studio/infrastructure/database/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
---

# Kontekst

Sedmi Slice 2 gate (S2-G1/G2/G9 merged, S2-G3+G4 u toku, S2-G5 paralelan
sa njima). Kanonski plan Â§10 "S2-G5 â€” Visual Identity Extraction
(paralelan)": `asset_extractor`, `visual_identity_extractor` â†’ postojeÄ‡i
`VisualIdentity` VO. **Jeftini signali** (CSS custom properties,
favicon, OpenGraph image) â€” NE teÅ¡ka image analiza.

**VAÅ½NO â€” veÄ‡ postoji** (S2-G1 merge-ovano):
- `domain/brand/value_objects.py` (ili `entities.py`) sadrÅ¾i
  `VisualIdentity` VO â€” vidi `Select-String` ranije (7 fajlova
  referencira).
- `ports/web_ingestion.py` (S2-G1) veÄ‡ definira
  `VisualIdentityExtractorPort` interface.

**G5 je wiring/sinteza**: implementira adapter za
`VisualIdentityExtractorPort` koji puni `VisualIdentity` VO iz HTML-a
(fetched ranije, vjerovatno preko G3 `http_fetcher`). NEMA novog porta
(S2-G1 veÄ‡ definisao), NEMA novog VO (S2-G1 veÄ‡ kreirao), NEMA
migracije.

Reference dokumenti (po `.agent/TASK_ROUTING.md` "Website Ingestion task"):
- [Kanonski plan `docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md`](../../docs/AI_Campaign_Studio_Slice_2_Canonical_Plan.md):
  Â§10 S2-G5 specifikacija, Â§11 hard gates, Â§3 DAG, Â§5 sync/async
  (fiksirana, NE preispitivati).
- `domain/brand/value_objects.py` (ili `entities.py`) za `VisualIdentity`
  shape â€” Å¡ta taÄno port contract zahtijeva od adaptera.
- `ports/web_ingestion.py` za `VisualIdentityExtractorPort` signaturu.
- `application/rendering/render_post.py` + `application/schemas/
  brand_fixture.py` + `application/mappers/brand_fixture_mapper.py`
  za downstream potroÅ¡aÄe `VisualIdentity` (context: Å¡ta adapter MORA
  proizvesti da rendering ispravno radi).
- `.agent/GITNEXUS_PROTOCOL.md` (obavezan za MEDIUM).

# Å ta

Implementirati `infrastructure/visual_extraction/` module (lokacija
koordinatorska odluka, alternative: `asset_extraction/`, G5-spec
kaÅ¾e "samo extraction fajlovi"):

1. **`asset_extractor`** â€” prima HTML string, vraÄ‡a `dict[str, str]`
   sa extractovanim asset URL-ovima:
   - **`favicon`**: `<link rel="icon" href="...">`, fallback
     `<link rel="shortcut icon" href="...">`, fallback
     `/favicon.ico` ako niÅ¡ta eksplicitno.
   - **`og_image`**: `<meta property="og:image" content="...">`
   - **`og_title`**: `<meta property="og:title" content="...">`
   - **`og_description`**: `<meta property="og:description" content="...">`
   - **`twitter_image`**: `<meta name="twitter:image" content="...">`
     (fallback za og_image)
   - **`twitter_card`**: `<meta name="twitter:card" content="...">`
   - Parser: `html.parser` stdlib (NE `lxml` jer G5 nema dependencija
     dependency, koristiti built-in). Za viÅ¡e specifiÄnosti moÅ¾e se
     koristiti `re.search` za `og:` i `twitter:` meta tagove.
   - Resolve relative URL-ove (`/favicon.ico`, `/og-image.png`) prema
     `base_url` parametru.

2. **`visual_identity_extractor`** â€” prima `html: str` + `base_url: str`,
   vraÄ‡a `VisualIdentity` VO (S2-G1):
   - Koristi `asset_extractor` za dobijanje assets.
   - **CSS custom properties** (`:root { --brand-color: #abc; }`):
     regex `r'--([\w-]+)\s*:\s*([^;}]+)'` na `<style>` blokovima
     i inline style atributima. Vrati `dict[str, str]` sa ime â†’
     vrijednost.
   - **Logo**: `asset_extractor.og_image` (ako postoji) ILI
     `asset_extractor.favicon` (fallback). NE teÅ¡ka image analiza
     (NE Pillow, NE color clustering).
   - **Palette** (opciono, MINIMALNA implementacija): iz CSS
     custom properties izvuci one koje izgledaju kao boje
     (regex `#[0-9a-fA-F]{3,8}`). Vrati kao `list[str]`.
   - KonstruiÅ¡i `VisualIdentity` VO sa svim prikupljenim signalima.
   - Ako NEMA signala (prazan HTML, nema meta tagova, nema CSS vars) â†’
     vrati `VisualIdentity` sa svim praznim/default vrijednostima (NE
     raise). Log warning.

3. **Adapter** za `VisualIdentityExtractorPort` (S2-G1):
   - Klasa `VisualIdentityAdapter(VisualIdentityExtractorPort)` koja
     wrap-uje `visual_identity_extractor.extract(html, base_url)`.
   - Implementira port signaturu, vraÄ‡a `VisualIdentity`.
   - Registrovati u `infrastructure/visual_extraction/__init__.py` kao
     dependency injection entry point.

4. **`__init__.py` exports** â€” `AssetExtractor`,
   `VisualIdentityExtractor`, `VisualIdentityAdapter` klase.

# Acceptance

- [ ] `asset_extractor` parsira `<meta property="og:image">` i
      `<link rel="icon">` (oba sa apsolutnim URL-ovima, NE relativnim)
- [ ] `asset_extractor` resolve-uje relative URL-ove prema `base_url`
- [ ] `visual_identity_extractor` parsira CSS custom properties iz
      `<style>` blokova (`--brand-color: #abc;` pattern)
- [ ] `visual_identity_extractor` NE throw exception za prazan HTML
      (vraÄ‡a `VisualIdentity` sa praznim/default vrijednostima + log
      warning)
- [ ] `VisualIdentityAdapter` implementira `VisualIdentityExtractorPort`
      iz S2-G1 (provjeriti runtime-checkable test)
- [ ] Edge case testovi:
    - Prazan HTML â†’ prazan `VisualIdentity`
    - HTML sa samo favicon-om â†’ `VisualIdentity.logo = favicon URL`
    - HTML sa og:image, bez favicon â†’ `VisualIdentity.logo = og:image URL`
    - HTML sa oba â†’ `VisualIdentity.logo = og:image URL` (og:image ima
      prioritet)
    - HTML sa CSS custom properties â†’ `VisualIdentity.palette` popunjen
    - HTML sa `<base href="...">` tag â†’ relativni URL-ovi se resolve-uju
      prema `<base href>` NE prema prosleÄ‘enom `base_url`
    - Relative URL `/favicon.ico` + `base_url="https://example.com/"` â†’
      `https://example.com/favicon.ico`
- [ ] `tests/integration/visual_extraction/` â€” live test sa stvarnim
      HTML fajlom (fixture u `tmp_path` kao i G4/G9)
- [ ] NEMA novog porta u `ports/`
- [ ] NEMA izmjena u `domain/`, `application/`, `presentation_webview/`,
      `jobs/`, `infrastructure/web_ingestion/`,
      `infrastructure/extraction/`, `infrastructure/database/`,
      `resources/migrations/`
- [ ] `python -m pytest tests/unit/infrastructure/visual_extraction/ -v`
      PROLAZI
- [ ] `python -m pytest -q` (DeepSeek unset) PROLAZI
- [ ] `python -m ruff check .` i `python -m mypy src` PROLAZE
- [ ] GitNexus `detect_changes` pokazuje SAMO nove simbole +
      `pyproject.toml` izmjene (ako ima novih dependency-ja)
- [ ] Mutation-test demonstriran (min 1 mutacija â†’ FAIL â†’ restore â†’
      PASS)

# Implementation steps

1. ProÄitati `domain/brand/value_objects.py` (ili `entities.py`) za
   `VisualIdentity` shape (koja polja postoje).
2. ProÄitati `ports/web_ingestion.py` za
   `VisualIdentityExtractorPort` signaturu.
3. ProÄitati `application/rendering/render_post.py` za downstream usage
   (kako se `VisualIdentity` koristi u renderingu â€” provjeriti da
   adapter proizvodi DOVOLJNO za downstream).
4. ProÄitati `application/schemas/brand_fixture.py` za sheme (kako se
   `VisualIdentity` mapira u output).
5. Implementirati `asset_extractor` (bez dependency-ja, samo `html.parser`
   + `re`).
6. Implementirati `visual_identity_extractor` (koristeÄ‡i
   `asset_extractor`).
7. `VisualIdentityAdapter` (implementira `VisualIdentityExtractorPort`).
8. `__init__.py` exports.
9. NEMA dependency management potrebe (sve stdlib, ALI ako se
   koristi BeautifulSoup â€” koordinatorska odluka, BeautifulSoup je
   `bs4` i opciona, stdlib je dovoljno).
10. `npx gitnexus detect_changes` PRIJE commit-a.
11. Mutation-test discipline: minimalno jedna mutacija na
    `asset_extractor` (npr. ukloniti `og_image` extraction â†’ test FAIL,
    restore, PASS).

# Å ta NE raditi

- **NE dodavati novi port** â€” `VisualIdentityExtractorPort` veÄ‡
  postoji u S2-G1. Adapter samo implementira.
- **NE dirati `VisualIdentity` VO** â€” veÄ‡ definisan u S2-G1.
- **NE raditi teÅ¡ku image analizu** (pillow color clustering, image
  hashing, perceptual hashing) â€” plan Â§10 G5 eksplicitno kaÅ¾e
  "jeftini signali".
- **NE koristiti Pillow** (dependency) â€” stdlib je dovoljno.
- **NE uvoditi novu shemu** â€” wiring only.
- **NE dirati G3 (`web_ingestion/`) ni G4 (`extraction/`)** scope.

# Acceptance (za review)

- [ ] Svi gore navedeni acceptance PROLAZE
- [ ] Scope Äist: `git diff --stat` ne sadrÅ¾i `ports/`, `domain/`,
      `application/`, `infrastructure/web_ingestion/`,
      `infrastructure/extraction/`, `infrastructure/database/`,
      `resources/migrations/`
- [ ] Adapter runtime-checkable: `isinstance(adapter,
      VisualIdentityExtractorPort)` PROLAZI

# Review focus â€” Claude PRVO, PA Codex (MEDIUM, wiring sa NOVI adapter
implementacijom)

- **Adapter signatura** â€” provjeriti da implementira TAÄŒNO port
  interface (NE dodaje nova polja, NE mijenja return type).
- **`VisualIdentity` shape** â€” provjeriti da SVA polja iz VO su
  pokrivena (NE NEDOSTATAK, NE DODOATAK).
- **CSS custom properties parsing** â€” `re.search` pattern mora
  pokriti `:root`, `:host`, `:host-context`, inline `style=`,
  `<style>` blokovi, sa ili bez `!important`.
- **Relative URL resolution** â€” test sa `<base href="...">` tagom
  (HTML5 specificira da base href override-a prosleÄ‘eni base_url).
- **Graceful fallback** â€” prazan HTML MORA vratiti `VisualIdentity` sa
  default vrijednostima, NE raise.
- **Scope** â€” `gitnexus_detect_changes` potvrda.

**Codex adversarial fokus**: probati HTML sa edge cases â€” XSS
payload u meta tag-u, malformed HTML, HTML sa viÅ¡e `<base href>`
tagova, HTML sa data: URL-ovima, HTML sa `javascript:` URL-ovima u
og:image (mora rejectati).

# Rollback

MEDIUM (nema migracije, nema GUI). Rollback: revert commit.

# Coordination

- **Paralelan sa S2-G3 (Pi, `infrastructure/web_ingestion/`)** i
  **S2-G4 (OpenCode, `infrastructure/extraction/`)** â€” disjunktni
  scope, razliÄite biblioteke.
- **NE MORA Äekati S2-G3/S2-G4** â€” G5 radi nad HTML stringom (NE
  treba HTTP). Za E2E smoke test (live HTML), G5 zavisi od G3
  `http_fetcher` outputa.
- **G6 zavisi od G3+G4+G5+G9** â€” ne dirati G6 scope.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-S2-012-visual-extract
Branch:   task/ACS-S2-012-visual-extract
Base:     main @ d13ad18
```

# Napomena za implementera (Pi)

- G5 je LAKÅ E od G3 (koji ima SSRF) â€” nema mreÅ¾nih poziva, samo HTML
  parsing sa stdlib (`html.parser`, `re`, `urllib.parse.urljoin`).
- VisualIdentityExtractorPort je VEÄ† definisan (S2-G1) â€” NE
  dodavati novi port.
- VisualIdentity VO je VEÄ† definisan (S2-G1) â€” NE dirati.
- Ako trebaÅ¡ dependency (BeautifulSoup), pitaj koordinatora PRIJE
  dodavanja. Default: stdlib.
- **TeÅ¡ka image analiza NE** â€” plan eksplicitno kaÅ¾e "jeftini
  signali". Pillow NE.
- Test fixtures koriste `tmp_path` (kao G4/G9). NEMA
  `tests/_fixtures/visual_extraction/` (van allowed_paths).

