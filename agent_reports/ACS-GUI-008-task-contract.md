---
task_id: ACS-GUI-008
phase: Faza-1 (post ACS-GUI-007 / post G10 PASS)
title: "Studio sadržaja: stvarno generisanje objava (odobri plan + generiši sve objave preko postojećeg pipeline-a)"
risk: HIGH
coordinator: claude
implementer: TBD
reviewers: [claude, codex]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-06
dependencies:
  - ACS-GUI-005/006/007 (merged) -- bridge composition pattern (CampaignBridgeApi, _resolve_provider, _err helper obrasci)
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py
  - src/ai_campaign_studio/presentation_webview/static/app.js
  - src/ai_campaign_studio/presentation/contracts.py
  - src/ai_campaign_studio/presentation/ui_models.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  - tests/unit/presentation_webview/test_studio_sadrzaja_ssr.py
  - tests/unit/presentation/test_contracts.py
  - tests/unit/presentation/test_ui_models.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - resources/migrations/
  - src/ai_campaign_studio/presentation_webview/screens/pregled_izvoz/
gitnexus_required: true
adversarial_required: true
gitnexus:
  required: true
  note: >
    Koordinator MORA pokrenuti impact provjeru na
    `CampaignBridgeApi.__init__` i na `ApproveCampaignPlan`/
    `GenerateSocialPost` prije merge-a -- ovaj task ih PRVI PUT poziva
    iz GUI konteksta. Očekivano: `ApproveCampaignPlan` danas ima SAMO
    test pozivaoce + `run_system_b.py`; `GenerateSocialPost` isto.
    Provjeriti STVARAN broj, ne pretpostaviti.
---

# Kontekst

**Ovo NIJE dodavanje novog ekrana.** `docs/gui-v3/screens/07_studio_sadrzaja/`
je već portovan u `presentation_webview/screens/studio_sadrzaja/`
(ACS-GUI-003/004 era) kao STATIČAN mockup: dugmad "Sačuvaj nacrt" i
"Pošalji na reviziju" su `data-action="toast"` STUBOVI (doslovno u
kodu: `Bridge stub: {action}`). Bridge (`CampaignBridgeApi`) danas ima
TAČNO dvije `js_api` metode (ACS-GUI-005 `create_campaign_and_
generate_plan`, ACS-GUI-007 `configure_provider`) -- ništa poslije
generisanja PLANA nije povezano. Korisnik danas može napraviti plan
kampanje, ali NE MOŽE preko GUI-ja dobiti nijednu stvarnu objavu.

**Postojeći pipeline VEĆ postoji i radi** (korišten u
`run_system_b.py`, A16/G10 evaluation harness-u, i u desetinama
integration testova): `ApproveCampaignPlan.execute(plan_id) ->
CampaignPlan` (DRAFT -> APPROVED) zatim `GenerateSocialPost.execute(
campaign_id, plan_id, campaign_item_id, target: CampaignTarget) ->
ContentPiece` -- POZVANO JEDNOM PO campaign_item-u. Ovaj task NE
DODAJE nijedan nov use-case -- samo ih poziva iz bridge-a, isti obrazac
kao ACS-GUI-005 (koje je `CreateCampaign`+`GenerateCampaignPlan`
povezalo prvi put).

**Odakle dolaze target-i (channel/platform/format) za generisanje.**
`CampaignBrief.targets: tuple[CampaignTarget, ...]` je VEĆ perzistiran
kod `CreateCampaign`-a (iz `CampaignBriefInput.targets`, koje korisnik
već popunjava u `create_campaign_and_generate_plan` formi -- provjeri
`presentation_webview/static/app.js` oko postojeće forme, i
`application/schemas/campaign_brief.py`). `run_system_b.py` pokazuje
TAČAN precedent za dodjelu target-a po item-u: `targets[index %
len(targets)]` (round-robin ako ima manje target-a nego item-a) --
`application/evaluation/run_system_b.py:86`. **Ponovi ISTU logiku**
(ili je izdvoji u malu deljenu funkciju ako se prirodno uklapa -- ali
NE mijenjaj `run_system_b.py`, on je van `allowed_paths`).

**Scope odluka koju review MORA potvrditi: "Odobri plan" postaje
TRANSPARENTAN korak, ne novo dugme.** `docs/gui-v3` mockup za
"Pregled i izvoz" (SLJEDEĆI ekran, ACS-GUI-009, NIJE ovaj task) ima
SVOJE "Odobri kampanju" dugme -- ALI domain model zahtijeva da plan
bude APPROVED PRIJE nego što se ijedan `GenerateSocialPost` poziv
uopšte može desiti (`InvariantViolation` inače). Ovaj task rješava tu
kontradikciju ovako: **plan approval + bulk generacija SVIH objava
dešava se u JEDNOM bridge pozivu, automatski, odmah nakon što je plan
napravljen** -- korisnik NE vidi poseban "odobri" klik za PLAN (isti
princip kao "GUI hides complexity": provider-plumbing, AI SDK, pipeline
koraci ostaju iza scene). "Odobri kampanju" dugme na Pregled/izvoz
ekranu ostaje van ovog taska -- ACS-GUI-009 ga redefiniše (vjerovatno
kao potvrda prije exporta, ne kao domain-state promjena) ili ga
ostavlja kao stub uz jasnu napomenu. Reviewer treba PROVJERITI da ova
interpretacija ima smisla, ne samo prihvatiti.

# Objective

## 1. Nova `js_api` metoda: `generate_campaign_content(raw_payload: dict) -> dict`

- Ulaz: `{"campaign_id": "<str>"}` (isti stil kao postojeće metode --
  validacija tipa PRIJE bilo kakvog poziva).
- Koraci (isti try/except-po-koraku obrazac kao
  `create_campaign_and_generate_plan`, NIKAD ne puca u JS):
  1. Učitati kampanju + njen ODOBREN ili DRAFT plan preko
     `campaign_repo` (kampanja mora postojati -- `EntityNotFound` ->
     `VALIDATION_ERROR` ako ne).
  2. Ako je plan status DRAFT: pozvati `ApproveCampaignPlan.execute(
     plan_id)`. Ako je već APPROVED, preskoči (idempotentno -- korisnik
     može ponovo kliknuti "generiši" bez pucanja).
  3. Provajder resolution -- PONOVO ISKORISTITI POSTOJEĆI
     `self._resolve_provider()` + `build_text_generation_adapter` (ne
     duplirati logiku).
  4. Učitati `brief.targets` preko `campaign_repo.get_brief(
     campaign.brief_id)`.
  5. Za SVAKI `CampaignItem` u planu (u `item.order` redoslijedu), ako
     TA stavka VEĆ ima generisan `ContentPiece` (provjeri
     `content_repo.list_campaign_content` ili ekvivalent -- izbjeći
     DUPLIKATE ako korisnik klikne dvaput), preskoči; inače pozovi
     `GenerateSocialPost.execute(campaign_id, plan_id, item.id,
     target)` sa target-om iz round-robin dodjele (Kontekst sekcija).
  6. Pojedinačna AI generacija MOŽE pući (mreža/kvota) -- NE prekidati
     cijelu petlju zbog jednog neuspjeha. Sakupiti
     `generated_count`/`failed_count`, nastaviti sa sljedećom stavkom.
     Ovo je NAMJERNO drugačije od `create_campaign_and_generate_plan`-a
     (koji je sve-ili-ništa) -- djelimičan uspjeh ovdje je koristan
     rezultat (korisnik vidi šta je gotovo, može ponovo pokrenuti za
     ostatak).
- Povratna vrijednost: nov `GenerateContentResultUiModel` (ili slično
  ime) -- `ok`, `campaign_id`, `generated_count`, `failed_count`,
  `content_piece_ids: list[str]`, `error_code`, `error_message`. `ok`
  je `True` i kad `failed_count > 0` ali `generated_count > 0`
  (djelimičan uspjeh nije potpuni fail) -- implementer dokumentuje
  tačan prag u docstring-u.

## 2. `studio_sadrzaja/__init__.py` -- stvarno povezivanje

- "Sačuvaj nacrt"/"Pošalji na reviziju" dugmad OSTAJU van scope-a ovog
  taska (to je REVIZIJA već-generisanog sadržaja --
  `application/posts/revise_content_piece.py` postoji ali NIJE ovaj
  task -- van `allowed_paths` je `application/`, pa se ni ne može
  dirati).
- Ekran treba, pri učitavanju (ili preko novog dugmeta -- implementer
  bira UX detalj, dokumentuje odluku), pozvati
  `generate_campaign_content` preko `app.js` i prikazati STVARAN broj
  generisanih objava (ne fixture placeholder).
- `app.js` dobija novu funkciju analognu postojećem
  `create_campaign_and_generate_plan` pozivu (provjeri
  `window.pywebview.api` postoji prije poziva, isti error-handling
  stil).

## 3. `presentation/contracts.py` + `ui_models.py`

- `PresentationFacade` Protocol dobija `generate_campaign_content`
  potpis (isti stil kao postojeća dva).
- Nov UI model dataclass po Objective #1.

# Implementation steps

1. Bridge metoda (Objective #1) + jedinični testovi: happy path (2+
   stavke, sve uspiju), djelimičan neuspjeh (1 od 2 AI poziva pukne --
   `generated_count=1, failed_count=1, ok=True`), idempotentnost (drugi
   poziv na već-generisanu kampanju ne duplira `ContentPiece`-ove),
   plan već APPROVED (ne puca, samo generiše), kampanja ne postoji
   (`VALIDATION_ERROR`), nijedan provajder podešen
   (`NO_PROVIDER_CONFIGURED`, isti kod kao postojeći).
2. `contracts.py`/`ui_models.py` dopuna + testovi.
3. `studio_sadrzaja/__init__.py` + `app.js` povezivanje + SSR test
   dopuna (potvrditi da real-data prikaz radi, fixture ostaje default
   kad bridge nedostupan -- isti stil kao postojeći SSR testovi).
4. Integration test (novi ILI dopuna postojećeg bridge test fajla):
   STVARNA SQLite baza + STVARAN `FakeAiPort`/deterministic test
   double za AI (NE pravi provider poziv u testu) -- pun
   `generate_campaign_content` lanac, potvrditi `ContentPiece` redovi
   STVARNO postoje u bazi poslije poziva.

# Acceptance

- [ ] `generate_campaign_content` postoji, poziva
      `ApproveCampaignPlan` (idempotentno) + `GenerateSocialPost` po
      stavci sa round-robin target dodjelom.
- [ ] Djelimičan neuspjeh NE prekida cijelu petlju -- ostale stavke se
      i dalje pokušavaju.
- [ ] Duplo pozivanje NE stvara duplikate `ContentPiece`-ova za istu
      stavku.
- [ ] Nijedan izuzetak ne izlazi u JS (svaki put mapiran na `ok=False`
      + stabilan `error_code`).
- [ ] `api_key`/secret vrijednosti se NIKAD ne pojavljuju u povratnom
      dict-u niti u logu (isti standard kao `configure_provider`).
- [ ] Studio sadržaja ekran prikazuje STVARAN broj generisanih objava,
      ne fixture.
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/`,
      `resources/migrations/`, `pregled_izvoz/` NISU DIRANI.
- [ ] `python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a** (obavezno otvoriti PR, obična `git
      push` na task branch ne pokreće CI).

# Verification

```bash
python -m pytest tests/unit/presentation_webview/ tests/unit/presentation/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-GUI-008-studio-sadrzaja-generate
gh pr create --base main --title "ACS-GUI-008: Studio sadržaja -- stvarno generisanje objava"
gh pr checks
```

# Review focus -- Claude + Codex (adversarial)

- GitNexus impact na `ApproveCampaignPlan`/`GenerateSocialPost`
  STVARNO pokrenut prije merge-a (kontrakt eksplicitno traži).
- Round-robin target dodjela je STVARNO ista logika kao
  `run_system_b.py` (ne suptilno drugačija -- test dokaz sa VIŠE
  target-a nego item-a I VIŠE item-a nego target-a).
- Idempotentnost STVARNO testirana (drugi poziv, provjeriti broj
  `ContentPiece` redova prije/poslije, ne samo "ne puca").
- Djelimičan-neuspjeh putanja STVARNO ne ostavlja bazu u
  nekonzistentnom stanju (djelimično commit-ovane transakcije?
  provjeriti `unit_of_work` granice po pozivu).
- Secret-safety: `api_key` STVARNO nikad ne dotiče povratni dict ili
  log (isti mutation-test standard kao ACS-GUI-007 review).
- Codex adversarial rundа po HIGH-risk standardu (isti kao
  ACS-GUI-005/007) -- namjerno tražiti edge-case-ove koje implementer
  možda nije pokrio.

# Rollback

HIGH risk -- prvi put da GUI poziva `ApproveCampaignPlan`/
`GenerateSocialPost` (stvarna promjena stanja baze + stvaran AI
poziv iz klika), plus djeli isti `bridge/__init__.py` fajl sa
paralelnim ACS-GUI-009 taskom (mogući merge konflikt -- koordinator
rješava rebase/reconcile, isti obrazac kao ranija paralelna sync
razrješenja ove sesije). Pun review ciklus prije merge-a (Human Owner
odobrenje za HIGH, ne §29 skraćeni put).

# Coordination

Zavisi od ACS-GUI-005/006/007 (sve mergovano). **Radi se PARALELNO sa
ACS-GUI-009** (Pregled i izvoz -- layout/render/export) -- razdvojeno
implementerima (npr. Crush ovaj, MiniMax onaj) da se paralelizuje, ALI
oba diraju `bridge/__init__.py`/`contracts.py`/`ui_models.py` -- prvi
koji završi merguje se prvo, drugi rebase-uje na svježi main prije
svog PR-a. Koordinator MORA ovo eksplicitno pratiti kad oba evidence
izvještaja stignu.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-GUI-008-studio-sadrzaja-generate
Branch:   task/ACS-GUI-008-studio-sadrzaja-generate
Base:     main @ 0595912
```
