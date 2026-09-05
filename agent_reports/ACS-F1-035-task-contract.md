---
task_id: ACS-F1-035
phase: Faza-1 (post A15) — bugfix otkriven u A19 live vertical slice provjeri
title: "PillowRenderer: CTA tekst se siječe van platna kad je duži od dugmeta (word-wrap fix)"
risk: LOW
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/infrastructure/rendering/selected_renderer.py
  - tests/unit/infrastructure/rendering/test_selected_renderer.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/application/
  - resources/migrations/
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Izmjena unutar jednog postojećeg fajla (`selected_renderer.py`), bez
    izmjene javnog potpisa (`PillowRenderer.render()` i dalje ima isti
    `RenderRequest → RenderResult` ugovor). GitNexus provjera nepotrebna.
---

# Kontekst

Otkriveno tokom A19 live vertical slice provjere (2026-09-05, koordinator,
stvaran DeepSeek API poziv, ne fixture-hardkodiran tekst): kad AI vrati
CTA tekst kao PUNU REČENICU (npr. `"Zakažite konsultaciju i otkrijte
mogućnosti za vaš osmeh."`, 57 karaktera) umjesto kratke dugme-fraze
(`"Zakažite"`), renderovan PNG prikazuje CTA tekst ODSJEČEN na lijevoj
ivici platna — vidljivo u dvije od šest live renderovanih slika u tom
prolazu.

**Uzrok** (potvrđen čitanjem koda): `PillowRenderer._draw_cta` centrira
tekst preko `x + (w - tw) // 2` gdje je `w` FIKSNA širina dugmeta (540px,
hardkodirano u `render()`) a `tw` STVARNA izmjerena širina teksta
(`draw.textbbox(...)`). Kad je `tw > w` (tekst širi od dugmeta), `(w -
tw)` je NEGATIVAN broj, pa `(w - tw) // 2` gura početnu X koordinatu
teksta ULIJEVO od `x` — dovoljno da tekst iscuri van lijeve ivice platna.
Headline putanja ima `_wrap_text` (word-wrap preko `font.getlength()`) i
overflow detekciju (`LAYOUT_VALIDATION_ERROR`); CTA putanja NEMA NIŠTA
slično — čista pretpostavka da tekst uvijek staje u 540px.

**Zašto ovo nije uhvaćeno u ACS-F1-033 testovima**: SVI test CTA tekstovi
su bili kratki (`"Zakažite konsultaciju"`, `"CTA"`, `"Zakažite"`) —
nijedan nije bio dovoljno dug da prevaziđe 540px. Ovo je genuine gap u
test pokrivenosti otkriven TEK live provjerom sa stvarnim AI odgovorom,
ne fabrikovan test slučaj.

# Objective

Primijeniti ISTU word-wrap logiku koja već postoji za headline
(`_wrap_text`, već korištena funkcija, NE nova) na CTA tekst, tako da
dugačak CTA tekst prelomi u više redova UNUTAR dugmeta umjesto da se
siječe van platna. Dugme ZADRŽAVA fiksnu širinu (540px) — ne postaje
šire za kratak tekst (postojeće ponašanje za kratke CTA fraze OSTAJE
identično, dokazano regresionim testom). Dugme RASTE PO VISINI kad
tekst zahtijeva više od jednog reda.

**Namjerno van scope-a**: ne dodavati `LAYOUT_VALIDATION_ERROR` status
za CTA overflow (ACS-F1-031 je eksplicitno odlučio da CTA slot provjera
nije u scope-u jer plan ne daje CTA numeričke defaulte za Slice 1) — ovaj
task je ČISTO renderer-nivo fix (spriječiti siecenje van platna), ne
novi validation koncept. Takođe van scope-a: rijedak edge slučaj kad je
JEDNA RIJEČ šira od raspoložive širine dugmeta (`_wrap_text` ne dijeli
unutar riječi, isto ograničenje kao za headline — postojeće, ne novo
ovim fixom).

# Implementation steps

1. U `render()`, CTA sekciji (trenutno oko linije 456-475), PRIJE poziva
   `_draw_cta`:
   - Definisati `_CTA_PADDING_X = 24` (horizontalni razmak unutar dugmeta,
     modul-level konstanta, isti stil kao `_LINE_HEIGHT`).
   - `cta_lines = _wrap_text(request.content.cta, cta_font, cta_w - 2 *
     _CTA_PADDING_X)` (reuse POSTOJEĆE `_wrap_text` funkcije, bez izmjene
     njenog potpisa).
   - Izračunati `cta_line_h = int(36 * _LINE_HEIGHT)` (36 = postojeća CTA
     font veličina, `_LINE_HEIGHT` već postoji kao modul-level konstanta
     = 1.2).
   - `cta_h = max(84, len(cta_lines) * cta_line_h + 2 * <vertikalni
     padding, npr. 20>)` — 84 ostaje MINIMALNA visina (identična
     postojećoj vrijednosti za jednoredan tekst, dokazati regresionim
     testom da se NE mijenja za kratak tekst).
2. Izmijeniti `_draw_cta` potpis da prima `lines: list[str]` umjesto
   `text: str` (svi pozivaoci ažurirani — trenutno samo JEDAN poziv u
   `render()`). Za SVA tri stila (SOLID/OUTLINE/TEXT):
   - Nacrtati pozadinu/okvir dugmeta na PUNOJ (mogu proširenoj) visini
     `h` kao i do sad.
   - Nacrtati SVAKI red teksta horizontalno centriran unutar dugmeta
     (`draw.textbbox` po redu, isti centriranje-po-x obrazac kao
     postojeći kod, ali sada BEZ negativnog `(w - tw) // 2` rizika jer
     je `tw` sada širina JEDNOG WRAPPED reda, garantovano `<= w -
     2*_CTA_PADDING_X` po `_wrap_text`-ovom ugovoru), redove vertikalno
     naslagane (`y + i * cta_line_h` za red `i`, centrirano unutar `h`
     ako ima manje redova nego što `h` dozvoljava — implementer bira
     razumnu vertikalnu centriranje formulu, dokumentovati je).
3. Testovi u `test_selected_renderer.py`:
   - `test_long_cta_text_wraps_instead_of_clipping` — REPRODUKOVATI
     TAČAN slučaj iz A19 live provjere: CTA tekst
     `"Zakažite konsultaciju i otkrijte mogućnosti za vaš osmeh."` (57
     karaktera, isti tekst kao stvaran AI odgovor). Provjeriti da
     RENDEROVAN PNG NE sadrži piksele CTA boje (`_NEUTRAL_ACCENT` za
     SOLID stil) na X koordinati 0 (lijeva ivica) — direktan dokaz da se
     dugme/tekst NE proteže van platna. Implementer bira konkretnu
     asercija-metodu (npr. `img.getpixel((0, cta_y_center))` mora biti
     `_NEUTRAL_BG`, ne `_NEUTRAL_ACCENT`/tekst boja, za CIJELU visinu
     dugmeta).
   - `test_short_cta_button_height_unchanged` — REGRESIONI test: kratak
     CTA tekst (`"Zakažite"`, isti kao postojeći testovi) i dalje daje
     dugme visine TAČNO 84px (dokaz da fix ne mijenja postojeće,
     ispravno ponašanje za kratak tekst).
   - Postojeći testovi (`test_cta_style_changes_pixels`, itd.) MORAJU I
     DALJE PROĆI NEPROMIJENJENI — ako neki zahtijeva izmjenu zbog
     promjene `_draw_cta` potpisa, izmjena mora biti ČISTO mehanička
     (novi poziv oblik), NE promjena onoga što test STVARNO provjerava.

# Acceptance

- [ ] Dugačak CTA tekst (57+ karaktera, realan primjer iz A19 live
      provjere) više NE proizvodi piksele van lijeve ivice platna — test
      dokaz na stvarnom PNG-u, ne samo "ne baca izuzetak".
- [ ] Kratak CTA tekst i dalje daje IDENTIČNO dugme (84px visina, ista
      pozicija) kao prije fixa — regresioni test.
- [ ] `_draw_cta` prima `lines: list[str]`, koristi POSTOJEĆU
      `_wrap_text` (nema duplirane wrap logike).
- [ ] Sva tri CTA stila (SOLID/OUTLINE/TEXT) ispravno crtaju višeredan
      tekst.
- [ ] Nema nove `LAYOUT_VALIDATION_ERROR` semantike za CTA (namjerno van
      scope-a, potvrditi da `RenderResult.status` logika za headline
      overflow ostaje jedini izvor tog statusa).
- [ ] `domain/`, `ports/`, `application/`, `resources/migrations/` NISU
      DIRANI.
- [ ] `python -m pytest tests/unit/infrastructure/rendering/test_selected_renderer.py -v`
      prolazi (uključujući 2 nova + sve postojeće testove).
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/infrastructure/rendering/test_selected_renderer.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

Dodatno, koordinator će nakon merge-a PONOVO pokrenuti A19 live scenario
(stvaran AI poziv sa istim dugačkim CTA tekstom) i vizuelno otvoriti
rezultujući PNG da potvrdi da se problem stvarno vidi popravljen, ne
samo da test prolazi.

# Review focus — Claude

- OTVORITI stvaran renderovan PNG sa dugačkim CTA tekstom (ne vjerovati
  testu na riječ) — potvrditi vizuelno da tekst STVARNO ostaje unutar
  platna;
- kratak CTA tekst STVARNO nepromijenjen (piksel-identičan ako je
  moguće uporediti, ili barem identična dimenzija/pozicija dugmeta);
- `_wrap_text` se STVARNO reusuje (ne nova, duplirana wrap funkcija);
- nema slučajne promjene headline ponašanja (ovaj task NE dira headline
  sekciju koda uopšte).

# Rollback

LOW risk — izolovana izmjena unutar jedne funkcije/renderer sekcije,
nema domain/port/aplikacijske izmjene, nema nove zavisnosti. Fix na
istoj branch bez proširenja scope-a. §29: Claude-only review, PASS →
odmah merge.

# Coordination

Nezavisan od svega trenutno otvorenog. Ne blokira A20 (Kill/Pivot/Proceed
odluku) — taj se može donijeti nezavisno o ovom render-quality fixu, ali
Human Owner je eksplicitno tražio da se ovo popravi ODMAH, prije A20
razgovora.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-035-cta-overflow-fix
Branch:   task/ACS-F1-035-cta-overflow-fix
Base:     main @ 58cebb9
```
