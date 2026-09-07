---
task_id: ACS-F1-045
phase: "Kritičan fix — fact-first jezgro (web Claude review 2026-09-07, Nalaz 1+2)"
title: "GenerateCampaignPlan pokazuje AI-ju stvaran katalog odobrenih činjenica; claim_linter ne flaguje telefon/adresu kao unsupported-number"
risk: MEDIUM
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN -- contract written before code, čeka implementera"
created_at: 2026-09-07
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/campaigns/generate_campaign_plan.py
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - resources/prompts/campaign_plan/v1.yaml
  - resources/claim_rules/default_v1.yaml
  - tests/unit/application/campaigns/test_generate_campaign_plan.py
  - tests/unit/application/posts/test_claim_linter.py
  - tests/unit/application/posts/test_select_allowed_facts.py
  - tests/integration/application/campaigns/test_generate_campaign_plan_integration.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/application/posts/select_allowed_facts.py
  - src/ai_campaign_studio/application/posts/generate_social_post.py
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    `GenerateCampaignPlan.__init__` dobija nov OBAVEZAN parametar
    (`fact_repo`) -- javna promjena potpisa postojećeg, mergovanog
    use-case-a. Koordinator MORA provjeriti STVARAN broj pozivalaca
    prije merge-a (očekivano: `bridge/__init__.py`
    `create_campaign_and_generate_plan` + testovi -- provjeriti, ne
    pretpostaviti).
---

# Kontekst

Nezavisna review od strane "web Claude" (2026-09-07, kloniran repo,
stvarno pokrenut kod) otkrila je dva potvrđena, ozbiljna nalaza --
koordinator ih je NEZAVISNO reprodukovao, oba potpuno tačna:

**Nalaz 1** -- `select_allowed_facts` (`application/posts/
select_allowed_facts.py`, NIJE u ovom task-u, van scope-a) radi čist
casefold substring match. Za bosanski/srpski/hrvatski (fleksivan
jezik), `implantati` (nominativ) NE matchuje `implantate` (akuzativ)
unutar teksta činjenice; `adresa` NE matchuje `adresi`; `lokacija
ordinacije` (parafraza, ne fleksija) NE matchuje NIŠTA jer te riječi
uopšte ne postoje u tekstu činjenice. **Dublji, stvaran uzrok:**
`GenerateCampaignPlan._build_user_text()` (`application/campaigns/
generate_campaign_plan.py`) UOPŠTE NE PRIKAZUJE AI-ju listu odobrenih
činjenica kad generiše plan -- AI izmišlja `facts_needed` fraze na
osnovu brief-a (offer/goal/audience), bez ikakvog uvida u stvaran
katalog. Dodatno, `resources/prompts/campaign_plan/v1.yaml` few-shot
primjer AKTIVNO uči model da piše `facts_needed: ["cijena implantata",
"lokacija ordinacije"]` -- TAČNO fraze koje su testirane i vraćaju 0
pogodaka.

**Popravka NIJE u `select_allowed_facts.py`** (ostaje NETAKNUT, van
`allowed_paths`) -- popravka je da AI DOBIJE stvaran katalog i UPUTSTVO
da referencira TAČAN `logical_fact_id`, ne izmišljenu frazu. Egzaktan
ID match već RADI danas (koordinator potvrdio: `['fact-team'] -> 1
pogodak`) -- fali samo da AI ZNA koje ID-eve uopšte da traži.

**Nalaz 2** -- `claim_linter._numeric_reason_code` (`application/
posts/claim_linter.py`) ima fallback `if has_digit: return
"unsupported-number"` koji hvata SVAKU cifru koja nije već
price/percent/duration/date obrazac. Telefon (`065 123 456`) i adresa
(`Ulica Kralja Petra 15`) padaju u ovaj fallback -> `UNSUPPORTED` ->
(preko `derive_content_status`) `NEEDS_REVIEW`. Kombinovano sa Nalazom
1 (činjenice se rijetko vezuju), realna marketinška objava sa
telefonom/adresom skoro UVIJEK završava `NEEDS_REVIEW` -- status koji
je uvijek isti ne nosi informaciju.

**Sporedno, dokumentovano ali van scope-a koda**: `claim_linter.py`
docstring kaže "Rule lists live in YAML, not hardcoded in Python", ali
`_DURATION_UNITS` (21 element) je hardkodirana Python tuple. Ovaj task
NE MORA to riješiti (nije funkcionalan bug, samo netačan komentar) --
implementer MOŽE ispraviti docstring da odražava stvarnost ako je
jeftino, ali nije acceptance kriterijum.

**G10 napomena (za CURRENT_STATE, ne dio ovog koda)**: G10-ov R1
rezultat (System B uvijek 0 kršenja) mjeri BROJ `claim_linter`
kršenja, NE stopu `VERIFIED_BY_FACT` vezivanja. Ako AI, vidjevši prazan
`AllowedFactSet`, ispravno izbjegava izmišljanje konkretnih brojeva
(umjesto da ih fabrikuje), to objašnjava "0 kršenja" BEZ da dokazuje da
sistem stvarno prenosi ODOBRENE činjenice. Ovaj task, popravljanjem
Nalaza 1, treba PRIRODNO povećati stopu `VERIFIED_BY_FACT` -- to je
mjeriva posljedica koju treba dokazati u Verification sekciji.

# Objective

## Dio A -- Fact-grounded planning (Nalaz 1)

1. `GenerateCampaignPlan.__init__` dobija nov OBAVEZAN parametar
   `fact_repo: FactRepositoryPort`.
2. `execute()` učitava `snapshot_facts = self._fact_repo.
   list_snapshot_facts(campaign.brand_snapshot_id)`, filtrira preko
   `is_fact_usable` (isti obrazac kao `select_allowed_facts`/
   `GenerateSocialPost`), prosljeđuje u `_build_user_text`.
3. `_build_user_text` dobija novu sekciju:
   ```text
   ## Approved facts
   - fact-location: BrightSmile Dental se nalazi u centru grada, na adresi Ulica Primjera 12.
   - fact-implants: Klinika nudi titanijumske zubne implantate sa keramičkim krunicama.
   - fact-team: Tim čine specijalisti oralne hirurgije i protetike sa preko 10 godina iskustva.
   ```
   (format: implementer bira tačan prikaz, ALI mora sadržati
   `logical_fact_id` PO ČINJENICI, čitljivo za AI).
4. `resources/prompts/campaign_plan/v1.yaml`: instrukcije + few-shot
   primjeri MORAJU se promijeniti da `facts_needed` referencira TAČAN
   `logical_fact_id` (npr. `facts_needed: ["fact-implants"]`), NE
   slobodnu frazu. Ako plan item genuinely NE treba nijednu odobrenu
   činjenicu (npr. čisto CTA/kreativni post), `facts_needed: []` je
   ispravno i OSTAJE ispravno.
5. `bridge/__init__.py`: `create_campaign_and_generate_plan` prosljeđuje
   `fact_repo=self._fact_repo` (VEĆ postoji kao property na bridge-u
   od ranije -- provjeriti tačno ime svojstva prije pisanja koda).

## Dio B -- claim_linter phone/address fix (Nalaz 2)

1. `resources/claim_rules/default_v1.yaml` dobija nov, data-driven
   regex/pattern za "kontakt info" (telefon i poštanska adresa) --
   implementer bira tačan format YAML sekcije (konzistentan sa
   postojećim `prohibited_terms` stilom), ALI pravilo mora biti
   PRIJE generičkog `has_digit` fallback-a u `_numeric_reason_code`
   redoslijedu provjere (price → percent → duration → date →
   **contact-info (NOVO)** → generic number).
2. Telefon-nalik obrazac (npr. `\d{2,3}[\s\-\.]?\d{3}[\s\-\.]?\d{3,4}`,
   implementer prilagođava da pokrije BHS formate: `065 123 456`,
   `033/123-456`, `+387 61 123 456`) I street-adresa-nalik obrazac
   (broj odmah nakon riječi tipa "ulica"/"broj"/imena ulice --
   implementer bira razuman heuristički obrazac, DOKUMENTOVAN u
   komentaru zašto je "dovoljno dobar", ne savršen) -> `None` (NEMA
   numeric violation-a) umjesto `unsupported-number`.
3. **Ne slabiti zaštitu za STVARNE numeričke tvrdnje** (cijena, postotak,
   trajanje, datum ostaju TAČNO kako jesu -- test regresija OBAVEZNA).

# Implementation steps

1. Dio A: `fact_repo` dependency + prompt dopuna + YAML izmjena + bridge
   wiring.
2. Test (integration, STVARNA baza + `brightsmile.json` fixture): fake
   AI adapter koji vraća `facts_needed: ["fact-implants"]` (ID, kako
   novi prompt uči) -> `select_allowed_facts` (NETAKNUT kod) STVARNO
   nalazi `fact-implants` (postojeća, dokazano-radeća ID-match logika).
3. Test: prompt-building (`_build_user_text`) STVARNO sadrži sva tri
   `brightsmile.json` facta sa njihovim ID-evima kad se pozove sa
   pravim `snapshot_facts`.
4. Test regresija: postojeći `create_campaign_and_generate_plan` bridge
   test i dalje prolazi (aditivna izmjena, `fact_repo` sad OBAVEZAN
   parametar -- svi pozivi ažurirani).
5. Dio B: claim_linter pattern dodan + testovi: telefon (`065 123
   456`) i adresa (`Ulica Kralja Petra 15`) -> `NON_FACTUAL`/bez
   numeric reason-a (implementer dokumentuje TAČAN očekivan status --
   `None` iz `_numeric_reason_code` znači claim OSTAJE u trenutnom
   statusu, ne postaje automatski nešto drugo -- provjeriti `lint_claim`
   kontrolni tok), cijena (`30 KM`) i dalje `unsupported-price`,
   trajanje (`3 dana`) i dalje `unsupported-duration`, datum i dalje
   `unsupported-date`, GOLI izmišljen broj bez konteksta (npr. "Imamo
   500 zadovoljnih klijenata") i dalje `unsupported-number` (fallback
   OSTAJE za genuinely nepotkrijepljene tvrdnje).

# Acceptance

- [ ] `GenerateCampaignPlan` prikazuje AI-ju STVARAN katalog odobrenih
      činjenica sa `logical_fact_id`-evima.
- [ ] `resources/prompts/campaign_plan/v1.yaml` uči AI da referencira
      ID, ne frazu (test dokaz: stari fraze iz few-shot-a VIŠE NE
      postoje u fajlu).
- [ ] Integration test dokazuje: AI koji vrati ID iz kataloga ->
      `select_allowed_facts` STVARNO nalazi tu činjenicu (koristeći
      NETAKNUT postojeći matching kod).
- [ ] Telefon/adresa NE dobijaju `unsupported-number`.
- [ ] Cijena/postotak/trajanje/datum I DALJE dobijaju svoje SPECIFIČNE
      reason code-ove (regresija zabranjena, test dokaz).
- [ ] Goli izmišljen broj i dalje `unsupported-number` (fallback nije
      uklonjen, samo suzen).
- [ ] `python -m pytest tests/unit/application/campaigns/
      tests/unit/application/posts/test_claim_linter.py
      tests/unit/application/posts/test_select_allowed_facts.py
      tests/integration/application/campaigns/ -v` prolazi.
- [ ] `python -m pytest -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema nove eksterne zavisnosti.
- [ ] Nema izmjena van `allowed_paths`.
- [ ] **CI provjeren preko PR-a.**

# Verification

```bash
python -m pytest tests/unit/application/campaigns/ tests/unit/application/posts/test_claim_linter.py tests/unit/application/posts/test_select_allowed_facts.py tests/integration/application/campaigns/ tests/unit/presentation_webview/bridge/ -v
python -m pytest -q
python -m ruff check .
python -m mypy src

git push -u origin task/ACS-F1-045-fact-grounded-planning
gh pr create --base main --title "ACS-F1-045: fact-grounded planning + claim_linter contact-info fix"
gh pr checks
```

# Review focus -- Claude

- GitNexus impact na `GenerateCampaignPlan` STVARNO pokrenut --
  potvrditi TAČAN broj pozivalaca (`create_campaign_and_generate_plan`
  + testovi, ništa neočekivano).
- Dio A test STVARNO dokazuje end-to-end lanac (prompt sadrži
  katalog -> ID se koristi -> matching radi), ne samo izolovane
  komade.
- Dio B: mutation-test SVAKI od pet slučajeva (contact-info/price/
  percent/duration/goli-broj) -- privremeno ukloniti novi pattern,
  potvrditi da se telefon/adresa VRATE na `unsupported-number`, pa
  vratiti fix.
- Stari few-shot fraze STVARNO uklonjene iz YAML-a (grep dokaz), ne
  samo dodata nova sekcija pored stare.

# Rollback

MEDIUM risk -- mijenja javni potpis POSTOJEĆEG use-case-a (Dio A) i
proširuje postojeći linter (Dio B), oba aditivna/dopunska u ponašanju
(ne mijenjaju POSTOJEĆE tačne klasifikacije). Izolovano, lako revert.

# Coordination

Nema zavisnosti. **Blokira nijedan drugi task, ali je PRIORITET broj 1**
po odluci Human Ownera (2026-09-07, na osnovu web Claude review-a) --
ostali novi use-case-ovi (P1.5-G5 itd.) čekaju dok se fact-first
jezgro ne popravi. Nakon merge-a, koordinator ažurira CURRENT_STATE.md
G10 sekciju sa nijansom (R1 dokazuje "sistem ne fabrikuje", ne "sistem
prenosi stvarne činjenice" -- ovaj task to popravlja).

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-045-fact-grounded-planning
Branch:   task/ACS-F1-045-fact-grounded-planning
Base:     main @ 70c9efa
```
