---
task_id: ACS-F1-040
phase: CI fix (hitno) -- renderer font mora raditi na Linuxu (GitHub Actions)
title: "PillowRenderer: bundle-ovati open-source font umjesto hardkodovane Windows putanje"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/infrastructure/rendering/selected_renderer.py
  - resources/fonts/
  - pyproject.toml
  - tests/unit/infrastructure/rendering/test_selected_renderer.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/infrastructure/database/
  - resources/migrations/
  - .github/workflows/ci.yml
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Čisto infrastrukturna izmjena unutar jednog modula (font-loading
    helper + konstante), nema promjene javnog potpisa nijedne klase
    ili use-case-a. GitNexus impact nije potreban -- `_load_font` je
    privatna funkcija, `PillowRenderer`-ov javni `render()` potpis se
    ne mijenja.
---

# Kontekst

**Ovo je HITAN CI fix, ne stilski propust.** CI je crven na main-u od
2026-09-05 ~13:53 (potvrđeno uživo preko `gh run list` -- svih zadnjih
8 push-eva na main je `failure`). Uzrok: `_FONT_PATH_BOLD =
r"C:\Windows\Fonts\seguisb.ttf"` (i `_FONT_PATH_REG`,
`selected_renderer.py:65-66`) postoji SAMO na Windows-u.
`.github/workflows/ci.yml` koristi `runs-on: ubuntu-latest`, gdje taj
fajl ne postoji -- `_load_font()` tiho pada na
`ImageFont.load_default()` (bitmap font, potpuno drugačije metrike),
što lomi 2 testa koja mjere tačnu širinu/visinu teksta u pikselima:

- `test_hero_and_split_produce_visibly_different_pngs` -- sa default
  fontom, HERO i SPLIT renderi ispadnu byte-identični (default font ne
  reaguje na `size=` parametar kako FreeType font reaguje).
- `test_long_cta_text_wraps_instead_of_clipping` -- `84.0 > 84` je
  `False` (sa default fontom tekst se ne prelama u 2 reda kako se
  očekuje sa pravim fontom u istoj širini, pa dugme ostaje na
  minimalnoj visini).

Plus 1 kaskadni fail (`test_gate_report_against_current_repo_passes`,
koji pokreće `pytest -q` kao podproces i vidi ta 2 fail-a).

**Ovo NIJE bio propust implementacije** -- fallback je bio namjerno
napravljen i dokumentovan u ACS-F1-033 kao "known acceptance-stage
limitation, ne runtime bug", sa iskrenim komentarom da se glyph-ovi
razlikuju na ne-Windows sistemima. Propust je što niko (uključujući
koordinatora, kroz cijelu ovu sesiju) nije provjerio da CI stvarno
prolazi na GitHub-u -- lokalni Windows test run je uvijek bio zelen,
maskirajući problem. Nalaz je originalno prijavio nezavisan web-Claude
review 2026-09-05, koordinator ga nezavisno reprodukovao uživo
(`gh run view --log-failed`) prije prihvatanja.

Ovo je i suštinski isti princip kao D10 iz jučerašnjeg UX istraživanja
("nema fake success state-a") -- samo na nivou učitavanja resursa, ne
GUI statusa: tiha degradacija na pogrešan font je upravo ono što je
sakrilo problem dok se CI ručno nije provjerio.

# Objective

1. Bundle-ovati STVARAN open-license (OFL ili sličan permisivan)
   TrueType font koji pokriva BHS Latin dijakritike (č ć š đ ž) u
   `resources/fonts/` (npr. Noto Sans -- Regular + Bold/SemiBold
   varijanta), zajedno sa njegovim LICENSE fajlom
   (`resources/fonts/LICENSE` ili `resources/fonts/OFL.txt` --
   licenca MORA biti bundle-ovana uz font, ne samo pomenuta u
   komentaru).
2. `selected_renderer.py`: `_FONT_PATH_BOLD`/`_FONT_PATH_REG` prestaju
   biti hardkodovane apsolutne Windows putanje -- postaju putanje
   izvedene preko `AppPaths().resources_dir / "fonts" / "<ime>.ttf"`
   (isti obrazac kao ostali bundle-ovani resursi, vidi
   `config/paths.py::AppPaths._default_resources_dir`).
3. `_load_font()` fallback na `ImageFont.load_default()` OSTAJE kao
   odbrambena mjera (ako je bundle-ovani font iz nekog razloga
   fizički obrisan/oštećen), ali PRESTAJE biti očekivana, rutinska
   putanja na Linuxu -- nakon ove izmjene, bundle-ovani font MORA
   postojati i učitati se identično na Windows/Linux/macOS. Razmisliti
   da li fallback treba i dalje biti tih, ili treba logovati
   upozorenje (`warnings.warn` ili slično) -- implementer predlaže,
   koordinator odlučuje u review-u.
4. Ažurirati/potvrditi da postojeći testovi
   (`test_hero_and_split_produce_visibly_different_pngs`,
   `test_long_cta_text_wraps_instead_of_clipping`) prolaze SA
   bundle-ovanim fontom na trenutnom (Windows) dev okruženju --
   ponašanje se ne smije promijeniti na Windows-u (isti font
   family/weight vizuelno, čak i ako tačan fajl više nije Segoe UI).
5. `pyproject.toml`: potvrditi da `resources/fonts/*.ttf` fajlovi
   ulaze u bilo koji postojeći package-data/MANIFEST mehanizam ako
   takav postoji za `resources/` (provjeriti kako se ostali
   `resources/` podfolderi trenutno paketuju -- ako se NE paketuju
   eksplicitno nego se čitaju repo-relativno preko `AppPaths`, font
   folder prati isti obrazac, nema dodatne izmjene potrebne).

# Implementation steps

1. Pronaći i preuzeti stvaran, permisivno licenciran font (npr. Noto
   Sans Regular + Bold sa google/fonts repozitorija, ili slično) --
   provjeriti da glyph coverage stvarno pokriva č ć š đ ž (test
   dokaz, ne pretpostavka).
2. Dodati fontove + licencu u `resources/fonts/`.
3. Zamijeniti `_FONT_PATH_BOLD`/`_FONT_PATH_REG` konstante da koriste
   `AppPaths().resources_dir / "fonts" / "<ime>.ttf"`.
4. Pokrenuti CIJELI test suite lokalno (Windows) -- 0 regresija.
5. Push na task branch i pratiti da GitHub Actions CI (ubuntu-latest)
   STVARNO prođe -- ovo je JEDINI pravi dokaz da je fix ispravan
   (`gh run watch` ili `gh run list` nakon push-a).

# Acceptance

- [ ] Nema više nijedne hardkodovane `C:\Windows\Fonts\...` putanje u
      `selected_renderer.py`.
- [ ] Bundle-ovan font postoji u `resources/fonts/` sa licencom.
- [ ] `python -m pytest tests/unit/infrastructure/rendering/ -v`
      prolazi na Windows-u (implementerovo dev okruženje).
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] **GitHub Actions CI na task branch-u STVARNO prolazi (zeleno)**
      -- ovo je acceptance kriterijum koji se NE MOŽE zaobići lokalnim
      dokazom, mora se vidjeti uživo na GitHub-u prije review-a.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] Nema nove eksterne Python zavisnosti (font je statički resurs,
      ne paket).

# Verification

```bash
python -m pytest tests/unit/infrastructure/rendering/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src
git push -u origin task/ACS-F1-040-bundle-open-font
gh run watch   # ili gh run list --branch task/ACS-F1-040-bundle-open-font
```

# Review focus -- Claude

- Font licenca je STVARNO permisivna (OFL/Apache/slično) i STVARNO
  bundle-ovana (fajl postoji u repou, ne samo referenca).
- CI na task branch-u je STVARNO zeleno (provjeriti preko `gh run
  list`/`gh run view`, ne vjerovati implementerovoj tvrdnji).
- Vizuelna provjera da bundle-ovani font i dalje pokriva sve BHS Latin
  dijakritike (otvoriti bar jedan render sa č/ć/š/đ/ž u headline-u i
  vizuelno potvrditi da se glyph-ovi ispravno prikazuju, ne kao
  "missing glyph" box).
- Da se ponašanje na Windows-u (postojeći dev okruženje) nije
  suptilno promijenilo za korisnike koji već imaju Segoe UI -- ako
  se font family/weight vizuelno primjetno razlikuje, to je nalaz za
  raspravu, ne automatski blocker (fontovi se i dalje mogu razlikovati
  u detaljima, ali NE smiju izgledati "slomljeno").

# Rollback

MEDIUM risk -- popravlja aktivno crven CI na main-u, ali je izolovan
na jedan infrastrukturni fajl + nov resurs folder. Fix na istoj branch
bez proširenja scope-a. §29: Claude-only review, ALI merge se ne
odobrava dok CI na task branch-u nije STVARNO zeleno (ne samo lokalni
dokaz) -- ovo je jači uslov od uobičajenog §29 zbog prirode buga
(nevidljiv lokalno, vidljiv samo na CI infrastrukturi).

# Coordination

Nema zavisnosti -- može se raditi odmah, paralelno sa bilo kojim
drugim Slice 1.5 taskom. Blokira: pouzdanost CI-ja za SVAKI budući
merge (trenutno svaki push na main ispada crven, što maskira budale
regresije koje CI inače hvata).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-040-bundle-open-font
Branch:   task/ACS-F1-040-bundle-open-font
Base:     main @ dca6209
```
