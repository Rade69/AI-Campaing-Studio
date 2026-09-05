# .agent/CURRENT_STATE.md

Živi status. Ne istorijski arhiv — istorija je u Git-u i `agent_reports/`.
Ažurira koordinator (default Claude) poslije svakog merge-a i svake promjene gate/task stanja.

**Zadnje ažurirano:** 2026-09-05 (coordinator: claude) — **ACS-F1-033 (`RendererPort` +
`PillowRenderer` + `RenderPost`) merged u main — A14 POTPUNO gotov u kodu (plan sekcije 42-45).**
Prvo stvarno renderovanje slike u produkcijskom kodu: HERO/SPLIT vizuelno stvarno različiti,
`alignment`/`headline_position`/`overlay`/`cta_style`/`logo_rule`/`cta_rule` svaki dokazano utiče na
piksele, predug headline → `LAYOUT_VALIDATION_ERROR` ALI PNG se svejedno piše (plan §44 doslovno).
Koordinator otvorio PNG-ove direktno (HERO/SPLIT/overflow) — BHS dijakritici (č/š) čisti. **Dva
pyproject.toml fixa VAN deklarisanih `allowed_paths`** — nezavisno provjerena kao stvarno potrebna,
ne prihvaćena na riječ: (1) Pillow uopšte NIJE bio u `[project.dependencies]` (samo ručno
instaliran u dijeljeni dev venv) — potvrđeno `grep` PRIJE fixa; (2) `pythonpath=["src"]` +
`addopts=["--import-mode=importlib"]` u `[tool.pytest.ini_options]` rješavaju STVARAN test-collection
sudar (dva nova test direktorijuma dijele leaf ime "rendering" pod default prepend import mode-om) —
koordinator reprodukovao grešku SA vraćenim fixom, potvrdio da `importlib` mode sam rješava problem
bez potrebe za dodatnim `__init__.py` markerima. Koordinator uklonio dva nepotrebna `__init__.py`
fajla (za NEPOVEZANE, već postojeće test direktorijume) nakon što je potvrdio da cijeli suite i dalje
prolazi bez njih (899/899). Koordinator pojednostavio `RenderPost._resolve_logo_path` (radio
besmislen `get_campaign` poziv koji nikad nije mogao promijeniti povratnu vrijednost — uvijek `None`
jer `BrandRepositoryPort` nije dio 4-portnog potpisa ovog use-case-a). Post-merge: 899 passed,
ruff/mypy(156) čisti, `pip install --dry-run` potvrđen (Pillow dodavanje nije pokvarilo packaging
metadata, ACS-F1-032 lekcija primijenjena). MEDIUM risk, §29 → odmah merge. Worktree uklonjen.
**Sljedeći korak ka `G10 Vertical Slice PASS`**: A15 (ZIP export + telemetry summary, plan sekcija
46) — posljednji komad prije A19/A20 (puna vertical slice + exit evaluation).

Prethodni entry (2026-09-05): **ACS-F1-033 task contract napisan i
otvoren** (nije implementiran, implementer=TBD, MEDIUM risk) — **A14 dio 2, PRVI stvaran renderer**
(plan sekcije 43-45), nakon ACS-F1-032 odluke (R-B/Pillow). `ports/rendering.py`
(`RenderRequest`/`RenderResult`/`RenderStatus`/`RendererPort`), `infrastructure/rendering/selected_renderer.py`
(`PillowRenderer` — HERO/SPLIT stvarno vizuelno različiti, real font-metrika overflow detekcija →
`LAYOUT_VALIDATION_ERROR` ALI PNG se svejedno piše), `application/rendering/render_post.py`
(`RenderPost` use-case, prima `visual_system_id` eksplicitno kao parametar — isti obrazac kao
`PlanPostLayout`/ACS-F1-031, izbjegava nepostojeći FK lookup). Nova port metoda
`VisualRepositoryPort.get_layout_spec_by_content_piece` (vraća najnoviji red ako ih ima više).
Dvije namjerne dizajn odluke dokumentovane u kontraktu: (1) Pillow direktno, NE
cairosvg/resvg (nepotvrđena zavisnost na Windows-u, `template.svg` ostaje samo dokumentacija);
(2) FIKSNA neutralna paleta, NE brand-driven boje (plan sekcija 43 `RenderRequest` doslovno nema
brand/color polje — poznato Slice-1 ograničenje). NEMA perzistencije (`render_artifacts` tabela ne
postoji, namjerno van scope-a). Vidi `agent_reports/ACS-F1-033-task-contract.md`.

Prethodni entry (2026-09-05): **ACS-F1-032 (renderer spike) merged u main
— A14 DIO 1 ZATVOREN, R-B (SVG-based/Pillow) ODABRAN kao produkcijski renderer pravac.** Oba
kandidata stvarno izgrađena i izmjerena protiv istog BHS/overflow test seta (1080x1350): R-A
(HTML/CSS+Playwright) 745ms warm/377KB PNG, R-B (SVG/Pillow) 48.5ms warm/51KB PNG — R-B pobijedio
3/6 kriterijuma decisivno (packaging — nema chromium ~150MB binary, performance, text measurement).
Odluka u `artifacts/renderer_spike_result.json` (svih 9 planovih polja) + `spikes/renderer/COMPARISON.md`.
R-A ostaje u repou kao referenca za buduće CSS-bogate scenarije. **Runda 1 (Claude review) našla
KRITIČAN packaging bug**: `pyproject.toml` je imao nevažeću ugniježdenu TOML strukturu za novu
`renderer-spike` opcionu zavisnost grupu — `setuptools` je to odbijao, i `pip install -e .`
(BEZ IJEDNOG extra-a!) je u potpunosti padao, neopaženo od pytest/ruff/mypy jer dijeljeni venv je
već bio instaliran od ranije. Koordinator live reprodukovao PRIJE i POSLIJE fixa (`pip install
--dry-run` za sva 3 scenarija: default/.[dev]/.[renderer-spike]). MiniMax premjestio
`renderer-spike` kao sibling ključ u postojeću `[project.optional-dependencies]` tabelu. Dodatno:
`.gitignore` proširen (`!artifacts/renderer_spike_result.json`, isti obrazac kao postojeći
`phase0_foundation_gate.json` izuzetak) — fajl je bio tiho isključen širokim `artifacts/*` pravilom.
Post-merge: 858 passed, ruff/mypy(151) čisti, `pip install --dry-run` (default/.[dev]) potvrđen na
main-u. MEDIUM risk, §29 → odmah merge. Worktree uklonjen. **Sljedeći korak**: A14 dio 2
(produkcijski renderer — `ports/rendering.py`, `infrastructure/rendering/selected_renderer.py`
sa pravom SVG bibliotekom, `application/rendering/render_post.py`) — sljedeći kandidat za task
contract.

Prethodni entry (2026-09-05): **ACS-F1-032 task contract napisan i
otvoren** (nije implementiran, implementer=TBD, MEDIUM risk) — **A14 dio 1, RENDERER SPIKE** (plan
sekcija 42), prvi korak ka stvarnom renderovanju slika. Human Owner eksplicitno odabrao PUN spike
(oba kandidata stvarno izgrađena i uporeñena — R-A HTML/CSS+Playwright vs R-B SVG-based), NASUPROT
skraćivanju kao kod G9 (pywebview odabran bez punog PySide6 poređenja). Izlaz NIJE običan
application-layer kod — throwaway spike pod `spikes/renderer/` (van `src/`/`tests/`, ne prolazi
kroz pytest), plus `artifacts/renderer_spike_result.json` (tačna polja iz plana: candidate,
render_success, overflow_detection, bhs_glyphs_ok, avg_render_ms, memory_notes, packaging_notes,
implementation_notes, decision). `pyproject.toml` dozvoljen SAMO za ruff-exclude spike foldera +
novu `renderer-spike` opcionu zavisnost grupu (Playwright browser binary, itd.) — glavni
`dependencies` niz netaknut, pobjednička zavisnost postaje trajna tek u BUDUĆEM A14 dio 2 tasku.
`ports/rendering.py`/`infrastructure/rendering/selected_renderer.py`/`application/rendering/`
NAMJERNO van scope-a — plan eksplicitno zabranjuje produkcijski renderer prije ove odluke. Vidi
`agent_reports/ACS-F1-032-task-contract.md`.

Prethodni entry (2026-09-05): **ACS-F1-031 (`PlanPostLayout` +
`validate_layout`, A13 dio 2b) merged u main — A13 je time POTPUNO gotov u kodu (plan sekcije
39-41).** Crush implementirao čisto na prvi pokušaj — nema nalaza u review-u (naučeno iz
ACS-F1-029/030 rundi: svih 5 "entity not found" scenarija su genuinno odvojena, nema spojenih grana).
Primitiv van kampanjskog dozvoljenog skupa → `InvariantViolation`, ništa perzistovano; predug
headline → NIJE fatalno, perzistuje se sa `validation_status="INVALID"`; `format` uvijek
Slice-1 konstanta (dokazano AI odgovorom sa namjerno drugačijim stringom). Post-merge: 858 passed,
ruff/mypy(151) čisti. MEDIUM risk, §29 → odmah merge. Worktree uklonjen. **Sljedeći korak ka
`G10 Vertical Slice PASS`**: A14 (renderer spike + produkcijski renderer, plan sekcija 42+) — prvi
put da se bilo šta iz `application/rendering/`/`infrastructure/rendering/` piše.

Prethodni entry (2026-09-05): **ACS-F1-031 task contract napisan i
otvoren** (nije implementiran, implementer=TBD, MEDIUM risk) — **A13 dio 2b, plan sekcije 40-41**,
posljednji A13 komad prije A14 (renderer). `PlanPostLayout` use-case: AI poziv preko novog prompta
`post_layout/v1.yaml` (reuse postojećeg `LayoutSpecCandidate` schema-e), bira layout primitiv SAMO
iz kampanjski VEĆ ODLUČENOG skupa (`CampaignVisualSystem.primary_layout_family` [+ secondary]) —
primitiv van tog skupa je STVARNO odbijen (`InvariantViolation`, ništa perzistovano). `format` polje
iz AI odgovora se IGNORIŠE, uvijek prepisano na Slice-1 konstantu `"1080x1350"` (nema platform
registry→pixel mapiranja u kodu). `validate_layout.py` provjerava SAMO headline dužinu (HERO/SPLIT,
tačne brojke iz plan §41) — NIJE fatalno (predug headline se perzistuje sa
`validation_status="INVALID"`, za razliku od primitiv-pripadnosti koja JESTE fatalna). Namjerno NE
konstruiše pun domain `ContentSlotContract` (bounding_box/font_family nisu specificirani u planu,
to je A14 renderer posao). Zavisi od ACS-F1-029+030 (oba već mergovana) — UNBLOCKED. Vidi
`agent_reports/ACS-F1-031-task-contract.md`.

Prethodni entry (2026-09-05): **ACS-F1-030 (`layout_specs` foundation,
A13 dio 2 prereq) merged u main.** `LayoutSpecId`, tri nova OPCIONA polja na `LayoutSpec`
(`id`/`content_piece_id`/`validation_status`, default `None` — ACS-F1-029 konstrukcija bez njih i
dalje radi), migracija `0005_layout_specs.sql`, `VisualRepositoryPort.save_layout_spec`/
`get_layout_spec` implementirani u `SqliteVisualRepository`. Runda 1 (Claude review) našla stvaran
correctness bug: `save_layout_spec`-ov `ON CONFLICT DO UPDATE` je prepisivao `created_at` na
trenutni "now" pri svakom re-save-u istog id-a (audit timestamp korupcija) — koordinator live
reprodukovao PRIJE i POSLIJE fixa (isti id, dva save-a razmaknuta 1.2s: `created_at` se mijenjao
prije fixa, identičan poslije). Pi izbacio `created_at` iz UPDATE seta + dodao regresioni test.
Post-merge: 842 passed, ruff/mypy(149) čisti. MEDIUM risk, §29 → odmah merge. Worktree uklonjen.
**Sada je otvoren put za A13 dio 2b**: `plan_post_layout.py`/`validate_layout.py` (plan sekcije
40-41 — AI-generisan per-post `LayoutSpec` preko novog prompta + deterministička provjera da
headline tekst staje u odabrani layout prema Slice-1 `ContentSlotContract` defaultima) — sljedeći
kandidat za task contract.

Prethodni entry (2026-09-05): **ACS-F1-030 task contract napisan i
otvoren** (nije implementiran, implementer=TBD, MEDIUM risk) — **A13 dio 2, foundation korak**
(plan sekcija 24: `layout_specs` tabela). Namjerno ODVOJEN od stvarnog use-case-a
(`plan_post_layout.py`/`validate_layout.py`, sekcije 40-41) — isti obrazac kao što je
`campaign_visual_systems`/`VisualRepositoryPort` bilo izgrađeno davno prije nego što ga je
ACS-F1-029 konačno iskoristio. Ovaj task: `LayoutSpecId` (nov ID tip), `LayoutSpec` dobija tri nova
OPCIONA polja (`id`/`content_piece_id`/`validation_status`, svi default `None` — ne lomi postojeću
ACS-F1-029 konstrukciju), nova migracija `0005_layout_specs.sql`, `VisualRepositoryPort` dobija
`save_layout_spec`/`get_layout_spec` (aditivno, postojeće dvije metode netaknute). Use-case
(A13 dio 2b) je blokiran dok se ovaj task ne mergira — zavisi od ovdje uvedenih tipova/metoda. Vidi
`agent_reports/ACS-F1-030-task-contract.md`.

Prethodni entry (2026-09-05): **ACS-F1-029 (`GenerateVisualSystem`, A13,
plan sekcija 39) merged u main.** Nov `application/visual/generate_visual_system.py` povezuje
VEĆ POSTOJEĆU A13 fundaciju (domain/visual/, `VisualRepositoryPort`, `campaign_visual_systems`
tabela, `visual_direction/v1.yaml` prompt) — jedan AI poziv, perzistuje `CampaignVisualSystem`,
vraća `LayoutSpec` in-memory (BEZ perzistencije — `layout_specs` tabela ne postoji, A13 dio 2 je
zaseban budući task). Zahtijeva `APPROVED` plan; enum-only vrijednosti garantovane boundary
schema-om + kod-nivo `style` vokabular provjera. Runda 1 (Claude review) našla test-coverage gap:
parametrizovani "missing entity" test je spojio `campaign`/`brief` u istu granu, pa `brief is None`
put nije imao nijedan test. Pi popravio (genuine zaseban brief-missing fixture); koordinator
mutation-testirao fix (privremeno onemogućio `brief is None` provjeru u produkcijskom kodu — novi
test je pao kako treba, kod vraćen, potvrđen byte-identičan). Post-merge: 835 passed,
ruff/mypy(149)/boundaries svi čisti. MEDIUM risk, §29 Claude-only review → odmah merge. Worktree
uklonjen. **Sljedeći korak ka `G10 Vertical Slice PASS`**: A13 dio 2 (`plan_post_layout.py`/
`validate_layout.py`, sekcija 40-41 — per-post `LayoutSpec` generacija/perzistencija, zahtijeva
NOVU `layout_specs` migraciju), zatim A14 (renderer spike + produkcijski renderer), A15 (export).

Prethodni entry (2026-09-05): **ACS-F1-028 (claim_linter morfološke
varijante garant- korijena) merged u main** (merge commit direktno nakon `0bfa905`). MiniMax
dodao 6 varijanti (`garantovano`, `garantovan`, `garantuje`, `garantujem`, `garantuju`, `garancija`)
u `resources/claim_rules/default_v1.yaml` + 10 novih testova u `test_claim_linter.py` — data-only,
`claim_linter.py` nedirnut. Uključuje honestan regression test
(`test_garantujete_second_person_does_not_match`) koji dokumentuje da fix NE pokriva sve gramatičke
oblike (2. lice množine i dalje van dometa) — priznat, ne skriven scope. Koordinator nezavisno
reprodukovao: 29/29 specifičnih testova, 824/824 cijeli suite, ruff/mypy čisti, git diff potvrđen
na tačno 2 fajla (+ evidence report), oba u `allowed_paths`. LOW risk, §29: Claude-only review PASS
→ odmah merge. Worktree i branch uklonjeni.

Prethodni entry (2026-09-05): **ACS-F1-029 proslijeđen Pi-ju**
(implementer=pi, MEDIUM risk, čeka implementaciju) — **A13 iz plana (Campaign Visual
System + LayoutSpec, sekcija 39), prvi konkretan korak ka `G10 Vertical Slice PASS`** nakon što je
A16 zatvoren. Istraga prije pisanja kontrakta otkrila da je VEĆINA A13 fundacije već izgrađena
ranije (van vidljivog task-praćenja, vjerovatno rana P0/A3-A5 faza): `domain/visual/` (entities,
layout, slots, enums), `application/schemas/visual_direction_output.py`, `VisualRepositoryPort`/
`SqliteVisualRepository`, `campaign_visual_systems` tabela, čak i `resources/prompts/visual_direction/v1.yaml`
prompt — sve postoji, ništa od toga nema pozivaoca u `application/` sloju. Kontrakt pokriva SAMO
nedostajući komad: `GenerateVisualSystem` use-case (`application/visual/generate_visual_system.py`)
koji sve ovo poveže — jedan AI poziv, perzistuje `CampaignVisualSystem`, vraća `LayoutSpec`
in-memory (BEZ perzistencije — `layout_specs` tabela iz plana ne postoji, nova migracija je
namjerno van scope-a). Vidi `agent_reports/ACS-F1-029-task-contract.md`. Slijedeći korak nakon ovog
(per-post `plan_post_layout.py`/`validate_layout.py`, zahtijeva novu migraciju) čeka da se ovaj
task završi.

Prethodni entry (2026-09-05): **ACS-F1-028 task contract napisan i
otvoren** (nije implementiran, implementer=TBD, LOW risk) — poznato ograničenje otkriveno kroz
live A16 verifikaciju: `claim_linter.py` `prohibited_terms` provjera je EXACT-WORD, ne hvata
morfološke varijante istog korijena (`garantovano` ne matchuje registrovani `garantujemo`).
Nalaz potiče iz MiniMax-ove (kodni agent) ručne "Control A" probe (brief:
`agent_reports/2026-09-05-A16-brief-za-minimax-model-test.md`) — MiniMax je sam vjerovao da će
"Garantovano ćete dobiti..." biti uhvaćeno kao kršenje, ali stvaran linter je vratio
`forbidden_phrase_hits=0`. Fix namjerno data-only (proširiti YAML listu varijanti), NE
stemming/lemmatizacija u kodu — vidi kontrakt za obrazloženje. Human Owner eksplicitno tražio da
se ovo "otvori i odmah završi [kao kontrakt] da ostaje za kasnije" — kontrakt je kompletan,
implementer nije dodijeljen, čeka da neko bude slobodan. Vidi
`agent_reports/ACS-F1-028-task-contract.md`.

Prethodni entry (2026-09-05): **ACS-F1-027 (human_eval.py —
blind A/B evaluacioni paket, §49) merged u main** (`5f47c92`, merge `3f332af`) — **A16 (G10 A/B
evaluation harness) je time KOMPLETIRAN u kodu** (run_control_a + run_system_b +
deterministic_metrics + human_eval, sve mergovano).

`build_human_eval_package` mapira Control A / System B `EvaluationPost` tuple-ove u dva nasumično
označena "Campaign X"/"Campaign Y" bucket-a (X/Y dodjela je nasumična PO POZIVU preko injektovanog
`rng`, ne fiksno A=X/B=Y — evaluator koji radi više runova ne može naučiti obrazac), tačna §49
rubrika (6 kriterijuma 1-5 + slobodan komentar). Slijep prikaz posta namjerno izostavlja
`role`/`topic`/`claims`/`platform_code`/`format_code` — bilo šta od toga bi odalo koji je izvor
(System B ima role, Control A nema). `reveal` mapping se vraća ODVOJENO, nikad kao polje na
`HumanEvalPackage`, da se ne desi slučajno serijalizovanje u fajl koji evaluator čita.
`write_human_eval_files` piše tri odvojena fajla (content JSON, prazan scoring CSV, reveal JSON sa
eksplicitnim upozorenjem). Post-merge: 814 passed, ruff/mypy(147)/boundaries(18)/secrets svi
čisti. Worktree uklonjen.

**Sljedeći korak**: koordinator će ručno (scratchpad skripta) pokrenuti CIJELI A16 lanac
(`run_control_a` + `run_system_b` + `deterministic_metrics` + `human_eval`) protiv BrightSmile
fixture-a sa pravim provider ključem — prva stvarna live provjera da li System B pobjeđuje Control
A. Ovo NIJE novi Task Contract, nego direktna koordinatorova post-merge verifikacija (isti
obrazac kao live testovi za ACS-GUI-005/007).

Prethodni entry (2026-09-05): **ACS-F1-026 (A/B evaluation
harness — Control A + System B + determinističke metrike) merged u main** (`b000aa5`, merge
`b39851d`) — **G10/A16 iz Faza 1 v1.4 §47-48, prva stvarna implementacija.**

Human Owner odobrio G10 kao prioritet 2026-09-04. Koordinator prvo istražio tačnu specifikaciju
(§47-50, A16-A20, PROJECT_MAP.md §7) prije pisanja kontrakta — otkrio da A19 (puna vertical slice
kroz render+export) i A20 (višestruki runovi + finalna odluka) zahtijevaju module koji NE POSTOJE
u kodu (nema `application/render/`, `application/export/`), pa je scope namjerno sveden SAMO na
A16 (dio koji stvarno odgovara na R1 pitanje — da li je struktura vrijedna, ne zavisi od
render/export prezentacije). `human_eval.py` (§49) je zaseban budući task (ACS-F1-027).

Novi `application/evaluation/` paket: `run_control_a.py` (naivan single-call baseline, koristi VEĆ
POSTOJEĆI `resources/prompts/ab_control/v1.yaml` prompt koji je neko ranije pripremio a niko nije
koristio, bez DB pisanja), `run_system_b.py` (tanak orchestration wrapper oko VEĆ POSTOJEĆEG
pravog pipeline-a — Create→GeneratePlan→**Approve**→GeneratePost×N; uključuje `ApproveCampaignPlan`
korak koji GUI bridge danas NE poziva, ali System B mora jer `GenerateSocialPost` zahtijeva
APPROVED plan), `deterministic_metrics.py` (11 metrika + heuristic_near_duplicate koji ponovo
koristi `content_similarity.jaccard_similarity` iz ACS-F1-025 — tačno ono što §48 traži: "jednostavna
lexical/Jaccard metrika... heuristic only"). Claim-bazirane metrike čitaju već-lintovane claim-ove
(ponovo koriste `claim_linter.py`, ne dupliraju logiku). `None` vs `0` dosljedno za nemjerljive
metrike (`layout_failure_count` uvijek `None` — vizuelni sistem ne postoji; `unique_role_count`/
`duplicate_topic_count` `None` za Control A). Nijedan postojeći use-case potpis nije mijenjan.

Post-merge: 804 passed, ruff/mypy(146)/boundaries(18)/secrets svi čisti. §29 MEDIUM, Claude-only
review. Worktree uklonjen.

**Sljedeći korak**: ACS-F1-027 (`human_eval.py`, §49 — blind A/B poređenje paket) — zavisi od
`EvaluationPost` oblika zaključanog ovim taskom.

Prethodni entry (2026-09-05): **ACS-GUI-007 (Podešavanja →
AI provajderi, stvarno povezivanje) merged u main** (`f911fe5`, merge `19d5c67`) — **praktičan
usability blocker zatvoren: korisnik sada MOŽE stvarno podesiti API ključ kroz aplikaciju, ne
samo preko ručne skripte.**

`CampaignBridgeApi` dobio `settings` test seam (simetričan postojećem `paths`) — default u
produkciji je `AppSettings(environment="production")`, pa se koristi pravi `KeyringSecretStore`
umjesto read-only dev adaptera. `bootstrap.py`-ov default OSTAJE "development" za sve ostale
pozivaoce (potvrđeno: `settings.environment` ima TAČNO JEDNO mjesto čitanja u cijelom kodu). Nova
`configure_provider` js_api metoda — prva gdje secret string ide OD JS-a U bridge (do sad je samo
IZLAZIO iz njega). Podešavanja ekran dobio real input+Sačuvaj tok za 5 provajdera (OpenAI,
Anthropic, Google, DeepSeek, OpenRouter); "OpenAI kompatibilan" ostaje stub (treba i base_url).

HIGH risk, pun ciklus: koordinator PASS uz live end-to-end test (konfigurisan pravi provider kroz
bridge sa produkcijskim default-om, potvrđeno direktnim čitanjem OS keyring-a, pa u SVJEŽOJ bridge
instanci `create_campaign_and_generate_plan` automatski pronašao provider i završio pravi Gemini
poziv — prvi put da ovaj tok radi bez ručnog seed-ovanja baze). Codex adversarial: TRI runde prije
`PASS_WITH_NOTES` — BF-1 (`configure_provider` error putevi vraćali pogrešan DTO shape preko
dijeljenog helper-a hardkodiranog na campaign-flow model — koordinatoru je ovo promaklo u
sopstvenom review-u), BF-2 (bridge-unavailable JS grana ostavljala uneseni ključ u DOM-u, fix:
try/finally restructure), BF-3 (`logger.exception()` u generic exception grani mogao upisati
secret-bearing exception poruku u log fajl iako je JS povratna vrijednost ostajala čista, fix:
`logger.error()` sa ograničenim metapodacima). Sva tri nezavisno reprodukovana od koordinatora
prije i poslije svakog fixa. Post-merge: 794 passed, ruff/mypy(140)/boundaries(18)/secrets svi
čisti. Worktree uklonjen.

**Poznato preostalo ograničenje**: real-time status refresh na Podešavanja ekranu nije urađen
(status label ostaje statičan "Nije povezano" i nakon uspješnog Sačuvaj-a) — uspjeh se vidi kroz
toast + činjenicu da naredni "Sačuvaj i napravi plan" poziv stvarno pronalazi ključ, ne kroz
vizuelni status na samom ekranu. "OpenAI kompatibilan" real wiring (treba base_url+model_id,
drugačiji oblik forme) takođe ostaje van scope-a, budući task.

**Sljedeći korak (Human Owner odluka 2026-09-04)**: G10 evaluation harness (Control A vs System
B, A16-A20) — dizajn već postoji u planskim dokumentima, nije još implementiran.

Prethodni entry (2026-09-04): **ACS-F1-020 BF-2 i ACS-F1-025
(cross-post sličnost) merged u main** (`c106fda`, merges `7dbbf77`/`1837032`+`11289bf`).

**ACS-F1-020 BF-2**: `_contains_word` dobio `allow_digit_adjacent` keyword — cifra zalijepljena
za currency/duration termin ("30KM", "3dana") sad ispravno daje specifičan `unsupported-price`/
`unsupported-duration` umjesto generičkog `unsupported-number`, preko `(?<![^\W\d])`/`(?![^\W\d])`
lookaround-a (blokira samo slovo/underscore, dozvoljava cifru — `\b` to nije mogao jer su cifra i
slovo oba `\w`). `prohibited_terms` grana netaknuta. Koordinator nezavisno reprodukovao sve
poznate slučajeve (30KM, 3dana, nedana, jedinice, €, 100%) prije odobrenja.

**ACS-F1-025**: novi `content_similarity.py` — deterministička word-set Jaccard sličnost (bez
embeddings), poredi svaki novi generisan post sa svim postojećim u istoj kampanji
(`list_campaign_content`, postojeći port metod), i forsira `NEEDS_REVIEW` ako je skor iznad 0.6.
Ovo je Human Owner-ova prioritet #1 ideja od pet predloženih spoljnim review-om — direktno gađa
originalni strah od "šest generičkih objava" koji je pokrenuo razgovor o smislenosti aplikacije.
Prošao kroz fix rundu (BF-1): `.split()` je ostavljao interpunkciju zalijepljenu za riječi
("zuba." ≠ "zuba"), vještački snižavajući skor — realan BHS parafraza par je scorovao 0.273
umjesto 0.556, ispod praga, tačno slučaj koji je ova provjera trebala uhvatiti. Fix:
`re.findall(r"\w+", ...)` umjesto `.split()`.

Post-merge zajedno: 771 passed, ruff/mypy(140)/boundaries(18)/secrets svi čisti. Oba worktree-a
uklonjena.

**Preostale četiri ideje** (od pet predloženih) su namjerno odgođene — zapisane u koordinatorovoj
memoriji za kasnije, svaka sa nijansom koju treba prvo riješiti (perzistencija, BrandSnapshot
immutability, G10 gate).

Prethodni entry (2026-09-04): **ACS-GUI-006 (kompenzaciono
brisanje orphan DRAFT kampanje) merged u main** (`1dc23df`, merge `79ddb8a`). Rješava gap koji
je koordinator direktno posmatrao tokom ACS-GUI-005 live testiranja (`campaigns=2,
campaign_plans=0` nakon prvog neuspjelog poziva) i koji je MiniMax sam prijavio nakon
samo-pregleda svog ACS-GUI-005 rada. Bridge poziva `CreateCampaign` i `GenerateCampaignPlan` kao
dvije odvojene, zasebno commit-ovane transakcije — ako drugi padne, prvi ostaje trajno sačuvan
kao orphan DRAFT bez plana. Prava dijeljena transakcija bi zahtijevala mijenjanje transakcionog
ugovora samih use-case-a (van scope-a), pa je rješenje usko, best-effort kompenzaciono brisanje —
**PRVA delete metoda u cijelom repository/port sloju** (projekat je inače čist append-only), sa
docstring-om koji eksplicitno ograničava namjenu (samo za multi-step orchestration rollback, ne
opšta delete funkcija). Ispravna parent-prije-child FK ordering logika (campaigns prije
campaign_briefs, jer `campaigns.brief_id` referencira `campaign_briefs.id` pod
`PRAGMA foreign_keys=ON`) — koordinator nezavisno live-testirao protiv prave SQLite konekcije sa
uključenim FK enforcement-om. Nikad ne maskira originalnu `GENERATION_FAILED` grešku čak i ako
samo brisanje padne. 25 novih testova. Post-merge: 756 passed, ruff/mypy(139)/boundaries(18)/
secrets svi čisti. Worktree uklonjen.

Prethodni entry (2026-09-04): **ACS-F1-022 (role_sequence
enforcement + duplicate-topic normalizacija) merged u main** (`80c5d54`, merge `a46cb3a`).
`_validate_plan_domain` sada odbacuje plan ako BILO KOJA generisana uloga NIJE član
`template.role_sequence` (subset provjera, ne order/count-sensitive) — do sada je jedina role
provjera bila "bar 2 različite od bilo koje od 17", template se šalje modelu samo kao tekst u
promptu, ništa nije stvarno garantovalo da AI poštuje strukturu. Dopuna 2 (poslana nakon što je
prvobitna dopuna propuštena) dodala i `casefold().strip()` normalizaciju za duplicate-topics
provjeru. Post-merge: 742 passed, ruff/mypy(139)/boundaries(18)/secrets svi čisti. Worktree
uklonjen.

Prethodni entry (2026-09-04): **ACS-F1-024 (bridge provider
fallback) merged u main** (`e483a87`, merge `591cdbd`). Pi je samostalno pokrenuo i predao ovaj
task BEZ eksplicitnog kickoff briefa od koordinatora — očigledno njegov alat prati nove kontrakte
dodijeljene njemu na main-u i sam kreira worktree/počinje rad (korisna operativna informacija za
buduće taskove — ne treba uvijek čekati da koordinator pošalje "→ ZA PI" brief). `_resolve_provider`
sada iterira kroz SVE konfigurisane providere po prioritetu (ne samo prvog) i vraća prvi sa
stvarnim ključem; `PROVIDER_KEY_MISSING` sad je istinit tek kad su svi probani. Pi je dizajn
odluku (import `_PROVIDER_PRIORITY` kao private simbol iz factory-ja da izbjegne duplirani source
of truth) jasno obrazložio u evidence-u. Ojačan i `test_brand_seed_reused_on_second_call` da
provjerava identitet (`brand_id`), ne samo broj redova. Post-merge: 736 passed,
ruff/mypy(139)/boundaries(18)/secrets svi čisti. Worktree uklonjen.

**Paralelna nezavisna review sesija (druga Claude instanca) je istovremeno pregledala ACS-F1-020**
(prije BF-1 merge-a) i našla dva nalaza: F1 ("100%" prohibited term potpuno neuhvatljiv) — ispalo
da je VEĆ ispravljeno Pi-jevim stvarnim BF-1 fixom, nezavisno potvrđeno, NIJE ponovo otvarano; F2
(brojevi zalijepljeni za jedinicu/simbol bez razmaka — "30KM", "3dana" — dobijaju generički
`unsupported-number` umjesto specifičnog `unsupported-price`/`unsupported-duration`) je STVARAN i
i dalje prisutan u mergovanom main-u — NIJE bezbjednosni regres (status ostaje UNSUPPORTED, samo
je reason_code manje specifičan), ali vrijedi popraviti. Fix brief poslat Pi-ju (BF-2), nov
worktree kreiran jer je original već mergovan:
[agent_reports/2026-09-04-ACS-F1-020-fix-brief-2-za-pi.md](agent_reports/2026-09-04-ACS-F1-020-fix-brief-2-za-pi.md).
Paralelna sesija je predložila dizajn (digit-adjacent lookaround varijanta SAMO za
currency/duration provjere, prohibited_terms grana ostaje strogo `\b...\b`), koordinator ga je
razradio u tačan kod prije slanja Pi-ju.

Prethodni entry (2026-09-04): **ACS-F1-020 (claim_linter
word-boundary) i ACS-F1-023 (UNIQUE indeksi) merged u main** (`4027917`, merges `a41254f`/
`ad1bd0e`).

**ACS-F1-020**: nakon BF-1 fix runde — word-boundary primijenjen SAMO na termine čija OBA kraja
su `\w` (alfanumerički); termini koji počinju/završavaju non-`\w` karakterom (`€`, `100%`) padaju
na plain substring (word-boundary se ne može usidriti oko čistog simbola, a simbol ne može biti
"unutar" veće riječi pa substring tamo nije rizičan). Koordinator nezavisno reprodukovao sve
slučajeve (€ cijena, 100% zabranjen termin, tri originalna substring nalaza) prije odobrenja.
Pi je usput sam otkrio i zatvorio DODATNI regres koji je njegov prvi fix uveo (100% je prestao
biti PROHIBITED) — ista disciplina kao ranije R2-BF-1 adversarial provjere.

**ACS-F1-023**: nova append-only migracija `0004_uniqueness_constraints.sql` —
`UNIQUE(entity_type, entity_id, version)` na `revisions`, `UNIQUE(plan_id, "order")` na
`campaign_items`. Koordinator je LIČNO primijenio migraciju protiv svoje postojeće lokalne dev
baze (korišćene za ACS-GUI-005 live testiranje) prije odobrenja — nula postojećih duplikata,
migracija prošla čisto. Crush je usput ispravio netačnu putanju iz kontrakta
(`tests/integration/infrastructure/database/` ne postoji, stvaran je
`tests/integration/database/`) — transparentno prijavljeno, ne tiho zaobiđeno.

Post-merge verifikacija oba zajedno: 734 passed, ruff/mypy(139)/boundaries(18)/secrets svi čisti.
Oba §29 MEDIUM, Claude-only review. Oba worktree-a uklonjena.

Prethodni entry (2026-09-04): **ACS-F1-021 (GenerateSocialPost
initial Revision) merged u main** (`66dbd5a`, merge `e7cff39`). Spoljni code review je našao
(koordinator nezavisno reprodukovao) da `GenerateSocialPost.execute()` nikad nije kreirao
`Revision` zapis za AI-jevu originalnu generaciju — `revision_ids` je ostajao prazan tuple za
najčešći slučaj (nikad editovan post), što direktno pogađa `content_revision_id` identitet
zaključan kao potreban prije G10 Analytics/Slice 1.5. Fix (Crush): sada se kreira i snima
`Revision(version=1, origin=AI, previous_value=json.dumps(None))` u istoj UoW transakciji kao
`ContentPiece`; `ReviseContentPiece` nedirana, njegov `next_version = len(existing) + 1` sada
prirodno daje `version=2` prvoj pravoj izmjeni — dokazano novim end-to-end regresionim testom
(generate pa revise → verzije `[1, 2]`). §29 MEDIUM put — Claude-only review PASS, odmah merge.
Post-merge: 724 passed, ruff/mypy(139 files)/boundaries/secrets svi čisti. Worktree uklonjen.

**ACS-F1-020 (claim_linter word-boundary, Pi) — u fix rundi (BF-1)**: koordinator nezavisno
testirao Pi-jevu word-boundary implementaciju i našao STVARAN regres — `\b€\b` nikad ne matchuje
(€ nije `\w` karakter, word-boundary se ne može usidriti oko čistog simbola), pa cijena sa €
simbolom više nikad nije flagovana kao `unsupported-price` (bezbjednosna mreža OSLABLJENA za taj
slučaj, ne samo popravljena). Nijedan Pi-jev test nije pokrivao € kao pozitivan slučaj (samo
"KM"). Fix brief poslat:
[agent_reports/2026-09-04-ACS-F1-020-fix-brief-za-pi.md](agent_reports/2026-09-04-ACS-F1-020-fix-brief-za-pi.md).

Prethodni entry (2026-09-04): **ACS-GUI-005 (prvi GUI→backend
pywebview bridge) merged u main** (`fcf1dcc`, merge `33dd144`) — **prvi klik u GUI-ju sada
stvarno kreira kampanju i generiše plan.** "Sačuvaj i napravi plan →" na Opis kampanje ekranu
zove nov `js_api` bridge (`presentation_webview/bridge/CampaignBridgeApi`) koji poziva pravi
`CreateCampaign` + `GenerateCampaignPlan` protiv prave SQLite baze i pravog konfigurisanog AI
providera. Human Owner odobrio nakon punog HIGH-risk ciklusa: Claude review PASS, dva fix kruga
nakon Codex adversarial review-a (BF-1: hardkodovan Google model_id bio pogrešan/zastario —
`gemini-1.5-flash` umjesto stvarno live-verifikovanog `gemini-2.5-flash`, koordinator to otkrio
LIVE testom prije nego što je poslano Codex-u; BF-2: Codex uhvatio da je pywebview acceptance
test izgubio hermetičnost jer `_open_window()` sada gradi pravi bridge/bootstrap inline — fix:
patchable `_build_bridge()` seam), Codex finalni verdikt `PASS_WITH_NOTES`. Live-verifikovano
DVA PUTA od strane koordinatora (prije i poslije BF-1 fixa) direktnim pozivom bridge metode
protiv prave lokalne baze i pravog Gemini API-ja — `CreateCampaign` + brand-seed idempotency
potvrđeni ispravni čak i prije fixa (2 poziva → 1 red u `brands`, ispravno), nakon fixa i
`GenerateCampaignPlan` uspio sa stvarnim redovima u `campaign_plans`. Post-merge:
`check_no_secrets.py` uhvatio lažno pozitivan nalaz (fake test API ključevi
`sk-ant-test`/`goog-test` u novom test fajlu, scanner ne prepoznaje "test" kao placeholder
marker) — koordinator ispravio preimenovanjem u `sk-ant-EXAMPLE`/`goog-EXAMPLE` (već prepoznat
marker), ne širenjem scanner allowlist-e. Finalna verifikacija na main-u: 722 passed,
ruff/mypy(139 files)/import-boundaries(18)/secrets svi čisti.

**Proces napomena za buduće taskove**: implementer (MiniMax) je jednom pitao Human Owner-a
DIREKTNO (svoj vlastiti ask_user alat) za odobrenje izlaska van `allowed_paths`
(`test_import_boundaries.py`), mimo koordinatora — sadržaj je nezavisno pregledan i ispravan, ali
ubuduće provjeriti ovakve "coordinator approved" tvrdnje direktno s Human Owner-om, ne uzeti ih
zdravo za gotovo iz evidence izvještaja.

**Poznat, pre-postojeći gap otkriven ovim taskom** (nije uveden ovim taskom, blokira budući
"Podešavanja provider config" GUI task): stvarna GUI app uvijek konstruiše
`AppSettings(environment="development")`, što znači `EnvironmentSecretStore` (read-only) — pravi
`ConfigureProvider` use-case ne može stvarno persistovati ključ kroz pravu app danas.

**Takođe otvoreno (paralelno, u toku)**: **ACS-F1-020** — spoljna code review sesija je našla
(koordinator nezavisno reprodukovao) substring false-positive bug u `claim_linter.py`
(`"jedinice"` sadrži `"jedini"` zabranjen termin, `"danas"` sadrži `"dan"` duration unit) — ista
klasa greške kao R2-BF-1. Kontrakt napisan, dodijeljen Pi-ju, MEDIUM risk (§29). Worktree kreiran,
implementacija u toku.

Worktree (ACS-GUI-005) uklonjen.

Prethodni entry (2026-09-04): **ACS-F1-017 (DeepSeek/OpenRouter/
OpenAI-kompatibilan, A8 dio 3) merged u main** (`76be81f`) — **A8 (multi-provider AI adapteri)
KOMPLETIRAN, svih 5 provajdera na main-u.** Human Owner odobrio nakon Codex-ove treće (finalne)
adversarial runde: `PASS_WITH_NOTES`, nema blokirajućih nalaza. R2-BF-1 (count-detection regex
lažno hvatao `discount`/`account_id`) potvrđeno zatvoren — koordinator nezavisno reprodukovao fix
(`\bcount\b` word-boundary) protiv i pozitivnih i negativnih slučajeva prije odobrenja. Post-merge
verifikacija na main-u: 698 passed, `ruff check src tests scripts`/`mypy src`/
`test_import_boundaries.py`(18)/`check_no_secrets.py` svi čisti, čist merge bez konflikta (main se
u međuvremenu pomjerio zbog ACS-GUI-005 kontrakt commit-ova, nema preklapanja fajlova). DeepSeek
live-verifikovan (A8 dio 3 rana faza); OpenRouter/generic OpenAI-kompatibilan NISU live-testirani
(konzervativan `json_object` default dok se suprotno ne dokaže) — otvoren item za budući smoke-test
kad ključ bude dostupan. Worktree uklonjen.

**A8 status: SVIH 5 provajdera (OpenAI, Anthropic, Google, DeepSeek, OpenRouter/generic
OpenAI-kompatibilan) merged u main.** Fokus se vraća na GUI-backend bridge (ACS-GUI-005, u toku,
MiniMax implementira).

Prethodni entry (2026-09-04): **ACS-GUI-005 task contract napisan i
push-ovan** (`cdbef5e`) — **prvi GUI→backend bridge**. Human Owner je nakon iskrene procjene stanja
aplikacije ("arhitektura radi, GUI i backend su nepovezani") eksplicitno odobrio promjenu prioriteta
i zadužio MiniMax-a da ovo implementira. Kontrakt:
[agent_reports/ACS-GUI-005-task-contract.md](agent_reports/ACS-GUI-005-task-contract.md). Scope:
klik na "Sačuvaj i napravi plan →" (Opis kampanje) prvi put zove pravi `CreateCampaign` +
`GenerateCampaignPlan` kroz nov pywebview `js_api` bridge (`presentation_webview/bridge/`), pravu
SQLite bazu i pravi konfigurisan AI provider — umjesto static `<a href>`. Ključne zaključane odluke
u kontraktu: brand seeding preko lokalnog `brand-seed.json` (isti idiom kao window-state, jer
`BrandRepositoryPort` nema "postoji li već brend" upit i `LoadBrandFixture` generiše nov ID svaki
put); hardkodovana provider→model tabela (`resolve_default_text_model` ne radi jer registry nema
unaprijed registrovane modele) — DeepSeek/OpenAI/Google modeli preuzeti iz već live-verifikovanih
A8 izvještaja, Anthropic MORA biti nezavisno provjeren prije hardkodiranja (nije live-testiran
nigdje u projektu); zaključana forma→brief mapa (channel/platform_code/format_code tabela,
uključujući LinkedIn edge-case gdje GUI-jev format select ne mapira semantički — uvijek
`PROFESSIONAL_POST`); `content_piece_count` hardkodovan na 3 (forma nema to polje još); Plan
kampanje ekran EKSPLICITNO ostaje fixture u ovom tasku (dinamički render je budući task). Risk:
**HIGH** (prvi js_api bridge, prvi real DB write + real AI poziv iz GUI klika) → pun review ciklus
(Claude + Codex adversarial + Human Owner odobrenje), NE §29 skraćeni put. GitNexus MCP je bio
nedostupan (rekonektuje se) — koordinator mora pokrenuti detect-changes/impact prije review-a.
Worktree kreiran: `../ai-campaign-studio-worktrees/ACS-GUI-005-campaign-bridge`
(`task/ACS-GUI-005-campaign-bridge`, base `main@73f52b1`). Implementacija još nije počela.

Prethodni entry (2026-09-04): **ACS-F1-018 (Anthropic adapter, A8 dio 4)
merged u main** (`6c0287e`). Human Owner odobrio nakon oba review-a (Claude+Codex, oba
PASS/PASS_WITH_NOTES, nema blocking nalaza, dva prihvaćena non-blocking zapažanja — N1 kozmetički
timeout error message, N2 buduć temperature-param razmatranje). Nezavisna post-merge verifikacija:
684 passed, `ruff check src tests scripts`/`mypy src`/`test_import_boundaries.py`(18)/
`check_no_secrets.py` svi čisti. Nije live-testirano protiv pravog Anthropic API-ja (nema ključa)
— otvoren item za budući smoke-test. Worktree uklonjen.

**A8 status nakon ovog merge-a**: OpenAI, Google i Anthropic (3 od 5 provajdera) merged u main.
Preostalo: ACS-F1-017 (DeepSeek/OpenRouter/OpenAI-kompatibilan, Pi) čeka finalni Codex re-review
nakon R2-BF-1 fixa — posljednji preostali A8 task.

Prethodni entry (2026-09-04): **ACS-F1-018 (Anthropic, MiniMax) — oba
review-a PASS_WITH_NOTES, spremno za Human Owner odobrenje.** Codex adversarial review: nema
blocking nalaza. Dva non-blocking zapažanja (N1: `_map_error()` isinstance redoslijed čini timeout
granu nedostupnom — kozmetički, `ErrorCode` ostaje ispravan; N2: buduć rizik ako neko postavi
`temperature` protiv novijih Anthropic modela — trenutno nijedan pozivalac to ne radi). Koordinator
nezavisno potvrdio N1. Nije live-testirano (nema Anthropic ključa). Review:
`H:\ai-campaign-studio-worktrees\ACS-F1-018-anthropic-adapter\agent_reports\2026-09-04-ACS-F1-018-review-claude.md`.

Preostalo u A8: ACS-F1-017 (DeepSeek) čeka finalni Codex re-review nakon R2-BF-1 fixa.

**Zadnje ažurirano:** 2026-09-04 (coordinator: claude) — **ACS-F1-019 (Google/Gemini adapter, A8
dio 5) merged u main** (`be8964e`). Human Owner odobrio nakon oba review-a (Claude+Codex, oba
PASS) i pune live end-to-end validacije protiv pravog Gemini API-ja (plan tačno 3 stavke od prvog
poziva, claim linter uhvatio i blokirao neutemeljenu FACT tvrdnju u PROOF stavci — ista garancija
kao kod OpenAI/DeepSeek, potvrđeno provider-agnostic). Nezavisna post-merge verifikacija: 654
passed, `ruff check src tests scripts`/`mypy src`/`test_import_boundaries.py`(18)/
`check_no_secrets.py` svi čisti (whole-repo `ruff check .` i dalje pada zbog Codex-ovih scratch
fajlova u root-u, nepovezano). Worktree uklonjen.

**A8 status nakon ovog merge-a**: ACS-F1-016 (OpenAI) i ACS-F1-019 (Google) merged. ACS-F1-017
(DeepSeek/OpenRouter/OpenAI-kompatibilan, Pi) čeka finalni Codex re-review (R2-BF-1 fix poslat).
ACS-F1-018 (Anthropic, MiniMax) čeka Codex adversarial review (prvi put).

Prethodni entry (2026-09-04): **A8 status: ACS-F1-017 REJECT (R2-BF-1),
ACS-F1-018 poslat Codex-u, ACS-F1-019 čeka Human Owner odobrenje.**

- **ACS-F1-017 (DeepSeek/OpenRouter/OpenAI-kompatibilan, Pi)**: Codex re-review nakon BF-1 fixa —
  `REJECT`. BF-1 (DeepSeek json_schema) potvrđen zatvoren, ALI nov nalaz R2-BF-1: exact-count regex
  hvata `discount`/`account_id` kao lažan "generiši tačno N stavki" nalog (podstring "count").
  Koordinator nezavisno reprodukovao. Fix brief poslat Pi-ju:
  [agent_reports/2026-09-04-ACS-F1-017-fix-brief-2-za-pi.md](agent_reports/2026-09-04-ACS-F1-017-fix-brief-2-za-pi.md).
- **ACS-F1-018 (Anthropic, MiniMax)**: BF-1 fix (native `output_config` umjesto prompt-based JSON)
  potvrđen — 673 passed, `pyproject.toml` lower bound ispravno `anthropic>=1.0`. Human Owner nema
  Anthropic ključ (nije live-testirano). Poslato Codex-u:
  [agent_reports/2026-09-04-ACS-F1-018-brief-za-codex.md](agent_reports/2026-09-04-ACS-F1-018-brief-za-codex.md).
- **ACS-F1-019 (Google, Crush)**: oba review-a PASS + live-verifikovano protiv pravog Gemini
  API-ja — **spremno za Human Owner odobrenje**, čeka eksplicitno "odobravam".

**Zadnje ažurirano:** 2026-09-04 (coordinator: claude) — **ACS-F1-019 (Google, Crush) — oba
review-a PASS, live-verifikovano protiv pravog Gemini API-ja, spremno za Human Owner odobrenje.**
Codex adversarial review: `PASS_WITH_NOTES` (jedan non-blocking nalaz — adapter ne validira
lokalno protiv `json_schema`, ali application sloj to već radi kroz Pydantic, isti obrazac kao
OpenAI). Koordinator zatim pokrenuo pun end-to-end tok protiv PRAVOG Gemini API-ja (Human Owner-ov
ključ, BrightSmile Dental fixture) — nijedan bug, plan tačno 3 stavke od prvog poziva (server-side
`response_json_schema` enforcement radi besprijekorno, bez DeepSeek-ovog "exact count" problema).
PROOF stavka (najkritičniji test) — Gemini generisao 3 uvjerljive ali neutemeljene FACT tvrdnje,
claim linter sve uhvatio i post vratio u `NEEDS_REVIEW` — ista sigurnosna garancija kao kod
DeepSeek-a, potvrđeno provider-agnostic. Nema zabranjenih termina. Review upgrade-ovan na finalni
`PASS`: `H:\ai-campaign-studio-worktrees\ACS-F1-019-google-adapter\agent_reports\2026-09-04-ACS-F1-019-review-claude.md`.
**Ovo je prvi task gdje su OBA review-a (Claude+Codex) gotova I live-verifikovana prije Human
Owner odobrenja.**

**Zadnje ažurirano:** 2026-09-04 (coordinator: claude) — **ACS-F1-017 BF-1 fix potvrđen i
LIVE-verifikovan, čeka Codex.** Pi dodao `structured_output_mode` parametar na `OpenAIAdapter`
(`json_schema` default netaknut, `json_object` za DeepSeek — schema + exact-count instrukcija iz
dva izvora: `minItems==maxItems` u schema-i i `*_count: N` regex u tekstu). Koordinator nezavisno
pokrenuo `build_deepseek_adapter` protiv PRAVOG DeepSeek API-ja (isti ključ kao ranija ručna
validacija) — tačno 3 stavke, stvaran sadržaj, nema 400 greške. Prvi task u ovoj seriji gdje je i
implementacija I fix live-verifikovan prije Codex runde. 655 passed, ruff/mypy/boundaries/secrets
čisti. Poslato Codex-u:
[agent_reports/2026-09-04-ACS-F1-017-rereview-za-codex.md](agent_reports/2026-09-04-ACS-F1-017-rereview-za-codex.md).
OpenRouter/generic OpenAI-compatible ostaju neverifikovani protiv pravih API-ja (konzervativan
`json_object` default dok se suprotno ne dokaže).

**Zadnje ažurirano:** 2026-09-04 (coordinator: claude) — **ACS-F1-018 (Anthropic, MiniMax) —
evidence predata, REJECT (BF-1), fix runda u toku.** MiniMax-ovo istraživanje SDK-a (protiv
`anthropic 0.105.2`, u SISTEMSKOM Python-u, ne projektnom `.venv`-u — otkriveno i ispravljeno od
koordinatora) je bilo tačno u trenutku istraživanja: "nema native structured output". Ali
`pyproject.toml` ima `anthropic>=0.30` bez gornje granice — fresh install danas povlači
`anthropic 1.3.0`, koja JE dobila native `output_config`/`json_schema` mehanizam (potvrđeno
koordinator protiv stvarno instaliranog paketa). Isti razred rizika kao DeepSeek BF-1 (schema
enforcement vs. prompt-only compliance). Human Owner odlučio: nadograditi sada, ne odgađati. Kod
inače solidan — 671 passed, F1-lekcija nezavisno reprodukovana (MiniMax je otvoreno priznao da to
nije sam uradio), ruff/mypy/boundaries/secrets čisti, scope čist. Fix brief poslat MiniMax-u
(`agent_reports/2026-09-04-ACS-F1-018-fix-brief-za-minimax.md`). Human Owner nema Anthropic ključ
za live probu (za razliku od DeepSeek slučaja) — ostaje neverifikovano protiv pravog API-ja dok
neko sa pristupom to ne uradi.

Prethodni entry (2026-09-04): **Human Owner uradio ručnu end-to-end
validaciju sa pravim DeepSeek ključem (van formalnog review-a) — ACS-F1-017 review downgrade-ovan
na REJECT, stvaran blocking bug pronađen.** Puna kampanja (LoadBrandFixture → CreateCampaign →
GenerateCampaignPlan → ApproveCampaignPlan → GenerateSocialPost) pokrenuta uživo protiv pravog
DeepSeek API-ja (BrightSmile Dental fixture). **Ključni pozitivan nalaz**: fact-grounding stvarno
radi — AI je generisao uvjerljivu ali neutemeljenu FACT tvrdnju u OFFER stavci, claim linter je to
uhvatio (`FACT/UNSUPPORTED`) i post je ispravno vraćen u `NEEDS_REVIEW`, ne tiho propušten. Nema
zabranjenih termina ni u jednom generisanom tekstu. **BF-1 (blocking, za ACS-F1-017)**:
`OpenAIAdapter`-ov hardkodovan `response_format: json_schema` DeepSeek stvarno odbija ("This
response_format type is unavailable now") — nijedan mock-ovan test (Pi-jev, koordinator-ov) to
nije mogao uhvatiti. Potvrđen fix uživo: `json_object` mod + šema ugrađena u prompt tekst + izričita
instrukcija o tačnom broju stavki (bez nje, DeepSeek je generisao 7 umjesto traženih 3). OpenRouter
NIJE testiran uživo — ne pretpostavljati ponašanje. Fix brief poslat Pi-ju
(`agent_reports/2026-09-04-ACS-F1-017-fix-brief-za-pi.md`); Codex NIJE pozvan na staru verziju,
ide tek nakon fixa. ACS-F1-019 (Google/Gemini, implementer Crush) i dalje čeka Codex adversarial
review — ista klasa rizika, ali PROIZVOD nije live-testiran, samo mock — vrijedno razmotriti isti
tip ručne validacije prije Human Owner odobrenja. ACS-F1-018 (Anthropic, implementer MiniMax) i
dalje čeka evidenciju.

Prethodni entry (2026-09-04): **A8 nastavak, tri paralelna HIGH-risk taska otvorena.**

Prethodni entry (2026-09-04): **ACS-F1-016 (OpenAI adapter, A8 dio 2,
HIGH) merged u main** (`1b7a71f`). Human Owner eksplicitno odobrio ("Odobravam") nakon dvije pune
runde review-a (Claude arhitektura + Codex adversarial, oba dva puta). Prvi live AI provider
adapter u projektu: `OpenAIAdapter` implementira `TextGenerationPort` + vlastite
`test_connection()`/`discover_models()` (namjerno NE implementira `AIProviderConnectionPort` —
multi-provider-dispatch potpis preuranjen dok postoji samo jedan provajder), bounded retry (max 2,
samo `RateLimitError`/`APIConnectionError`), sve SDK greške mapirane u domain
`InfrastructureError` (nikad sirov ključ/exception tekst). 4 provider-setup use-case-a
(`ConfigureProvider`/`TestProviderConnection`/`DiscoverModels`/`SelectDefaultModel`) zavise samo
od portova; `TestProviderConnection`/`DiscoverModels` primaju adapter kroz lokalni Protocol (DI
seam) umjesto interne konstrukcije — ispravka greške iz kontrakt-ovog skiciranog potpisa koja bi
izazvala `application→infrastructure` import. `credential_ref` striktno string referenca. Cijeli
test suite mock-ovan, bez pravog API poziva/ključa.

Kroz review popravljeno: **F1** (nedeklarisana `httpx` test-zavisnost, CI rizik — dodato
`httpx>=0.27` u dev extras), **BF-1** (`finish_reason` čitan sa pogrešnog OpenAI SDK objekta —
`message` umjesto `choice`, uvijek `None` sa pravim response-om), **BF-2** (`ConfigureProvider`
nije provjeravao `requires_api_key` prije upisa secreta — sad baca `InvariantViolation` prije bilo
kakvog upisa). Nezavisna post-merge verifikacija: 644 passed, `ruff check .`/`mypy src`/
`test_import_boundaries.py`(18)/`check_no_secrets.py` svi čisti. Worktree uklonjen.

Prethodni entry (2026-09-04): **ACS-F1-016 — OBA review-a PASS (Claude + Codex, dvije runde
svaki), čeka SAMO Human Owner eksplicitno odobrenje.** Codex re-review: `PASS_WITH_NOTES`
(`agent_reports/2026-09-04-ACS-F1-016-review-codex-rereview.md`) — BF-1/BF-2 nezavisno
reprodukovani kao zatvoreni vlastitom repro probom (`finish_reason='stop'`,
`noauth_rejected=InvariantViolation` sa praznim secret_store/config_repo). Jedina napomena (full
pytest 1 failure) je poznat phase0 gate-report Windows sandbox/permission problem, ne F1-016 kod
defekt. Claude review ažuriran na finalni `PASS`
(`agent_reports/2026-09-03-ACS-F1-016-review-claude.md`, u worktree-u). Ovo je posljednji korak
prije merge-a — HIGH risk politika (§3/§29) zahtijeva eksplicitno "odobravam" bez izuzetka, čak i
kad su oba review-a čista.

Prethodni entry (2026-09-03): **ACS-F1-016 — BF-1/BF-2 popravljeni i nezavisno potvrđeni, čeka
Codex re-review.** Crush popravio oba nalaza iz
Codex REJECT-a: `openai_adapter.py` sad čita `finish_reason=getattr(choice, "finish_reason",
None)` (bilo sa `message`), `configure_provider.py` dobio `if not provider.requires_api_key: raise
InvariantViolation(...)` guard prije `set_secret`/`save_provider_config`. Oba regresiona testa
pročitana i potvrđena da testiraju stvarno traženo (BF-2 test eksplicitno dokazuje da ni
secret_store ni config_repo nisu pozvani na guard putanji). Nezavisno: 644 passed, ruff/mypy/
`test_import_boundaries.py`(18)/`check_no_secrets.py` svi čisti, scope nepromijenjen od prošle
runde. Poslat Codex-u na re-review: `agent_reports/2026-09-03-ACS-F1-016-rereview-za-codex.md`.
**I dalje nije merge-spremno** — čeka Codex verdict, pa Human Owner eksplicitno odobrenje.

Prethodni entry (2026-09-03): **ACS-F1-016 — Codex adversarial review vraćen `REJECT`**, dva
nalaza (BF-1: `finish_reason` sa pogrešnog objekta; BF-2: `ConfigureProvider` ne provjerava
`requires_api_key`), oba nezavisno potvrđena prije fix runde 2. F1 (httpx, prethodna runda) ostao
zatvoren, nije ponovo otvoren.

Prethodni entry (2026-09-03): **ACS-F1-016 — F1
zatvoren, čeka Codex adversarial review.** Crush dodao `"httpx>=0.27"` u `[project.optional-
dependencies].dev` (`pyproject.toml`). Koordinator nezavisno reprodukovao Crush-ovu fresh-
environment verifikaciju (uninstall/reinstall `httpx` preko `dev` extras) — `pip install
-e ".[dev]"` sad sam, deterministički, povlači `httpx`. 643 passed, `ruff check .`/`mypy src`/
`test_import_boundaries.py` (18)/`check_no_secrets.py` svi čisti. Review izvještaj ažuriran
(`tests: REJECT`→`PASS`, `blocking_findings` prazan) u worktree-u
(`agent_reports/2026-09-03-ACS-F1-016-review-claude.md`, necommit-ovan po ustaljenom obrascu za
HIGH risk — pun izvještaj ostaje u worktree-u dok se ne zatvori cijeli ciklus). Brief poslat
Codex-u: `agent_reports/2026-09-03-ACS-F1-016-brief-za-codex.md`. **Codex adversarial review i
dalje NIJE pokrenut** — HIGH-risk politika (§3/§29) zahtijeva punu proceduru bez izuzetka; moj
PASS_WITH_NOTES sam po sebi ne otvara put ka merge-u.

**Zadnje ažurirano:** 2026-09-03 (coordinator: claude) — **ACS-GUI-003 (campaign workflow ekrani)
merged u main** (`000c97c`, merge commit prije njega). Implementer Pi. Portovana sva 4 preostala
`docs/gui-v3` ekrana u `presentation_webview`: Opis kampanje, Plan kampanje, Studio sadržaja
(STVARAN `data-tab-target`/`data-tab-panel` tab switching, ne kozmetički mokap markup — namjerna
zamka iz kontrakta, Pi ispravno primijenio ACS-GUI-004 pattern), Pregled i izvoz. Zajednički
5-koračni stepper (`shell.stepper_html`). Kampanje "Otvori" postao stvaran link.

Koordinator dodao TRI izmjene preko Pi implementacije, sve live-verifikovane na Human Owner-ovom
ekranu (implementer nije mogao — harness bez UI-automatizacije):
1. **Kalendar dobio `?campaign=`-gated stepper + forward banner** — kontrakt je pogrešno stavio
   `kalendar/__init__.py` u `forbidden_paths`, iako je postojeći kod već najavljivao da ACS-GUI-003
   treba to dodati (koordinatorova greška u pisanju kontrakta, dokumentovano u post-hoc scope
   napomeni). Bez ovoga: workflow je bio dead-end na koraku 3.
2. **Jezik sadržaja (Opis kampanje)** — dvije iteracije do finalne verzije: pravi `<select>`
   dropdown, SR/HR/BS/EN, bez "BHS" prefiksa, bez "neutralno" opcije.
3. **Studio sadržaja** — dodat stvaran forward link ka Pregled i izvoz (bio je i to dead-end —
   "nema mogućnosti da se izveze") + smanjena visina textarea-e (180→120px) za manje skrolovanja.

Nezavisna verifikacija: 618 passed, `ruff check .` (whole-repo) i `mypy src` i
`test_import_boundaries.py` svi čisti. Pun trag odluka:
`agent_reports/ACS-GUI-003-task-contract.md` (post-hoc scope napomena),
`agent_reports/2026-09-03-ACS-GUI-003-review-claude.md`.

**Poznat, namjerno odgođen item**: Podešavanja ekran ima manji vertikalni skrol (postojeći, od
ACS-GUI-004, izraženiji na trenutno sačuvanoj 830px visini prozora nego na 900px baseline-u).
Human Owner eksplicitno odlučio da se odgodi za zaseban budući task.

**Zadnje ažurirano:** 2026-09-03 (coordinator: claude) — **Preostali necommit-ovani GUI rad
(window-state persistencija, logo wiring, mokap sync) merged u main** (`3eb4636`). Human Owner
potvrdio da niko trenutno aktivno ne radi na tim fajlovima (bio parkiran/napušten rad, ne
work-in-progress) — koordinator preuzeo, nezavisno pregledao i verifikovao prije commit-a (nije
imao implementer evidence izvještaj, jer je rad rađen van formalnog task-sistema). Sadržaj:
`__main__.py` pamti veličinu prozora između pokretanja (per-user data dir, JSON, brani se od
korumpiranog fajla/out-of-range vrijednosti/bool-kao-int trika) + atexit cleanup per-launch temp
foldera; `shell/__init__.py`/`_static_pages.py` sidebar sad renderuje kanonski `brand-logo.png`
umjesto `<h1>` teksta, PNG se kopira u svaki generisani `target_dir`; `docs/gui-v3/*` mokapi
resinhronizovani sa production stanjem (logo + ACS-GUI-004 tab/lang-picker CSS/JS). Dodat i
`run_ai_campaign_studio.bat` (dupli-klik launcher). Obrisan `test_window_close.py` (root-level
ručni debug skript sa hardkodovanom apsolutnom putanjom, nije pytest test, nije trebao u repo-u).
Nezavisna verifikacija: 553 passed, `ruff check src tests scripts`/`mypy src`/
`test_import_boundaries.py` čisti; whole-repo `ruff check .` (koji je prije ovog commit-a padao
baš zbog `test_window_close.py`) sad takođe čist nakon brisanja tog fajla. MEDIUM risk, isti
razred kao ACS-GUI-001/002/004 — Claude-only review, merge po §29.

**Zadnje ažurirano:** 2026-09-03 (coordinator: claude) — **Kanonski sidebar logo asset dodat u
main** (`8d1cc00`). Human Owner dostavio koncept ("Koncept C — Emerald", navy+emerald mrežna
ikonica + "AI Campaign Studio" wordmark). Koordinator izrezao caption tekst ("Koncept C —
Emerald") iz slike (Pillow, band-detekcija redova sa "mastilom" da se nađe tačan bounding box
logo lockup-a) i sačuvao na obje putanje koje MiniMax/Codex-ov necommit-ovani `shell/__init__.py`
`.brand-logo` `<img>` tag i već-mergovano `.brand-logo` CSS pravilo (iz ACS-GUI-004 merge
konflikt rezolucije) očekuju: `docs/gui-v3/shared/brand-logo.png`,
`presentation_webview/static/brand-logo.png`. Commit-ovan SAMO asset (binary PNG), NE i
`shell/__init__.py` wiring — to ostaje MiniMax/Codex-ov necommit-ovani kod, njihov za commit kad
završe. Live-verifikovano od Human Owner-a (screenshot Početna ekrana, logo se ispravno renderuje
u sidebar-u, bez caption teksta, dobra veličina/pozicija).

**Zadnje ažurirano:** 2026-09-03 (coordinator: claude) — **ACS-GUI-004 (real tab-panel switching,
Brend + Podešavanja, MEDIUM) merged u main** (`e534d0f`, merge commit `7246dd6`). Implementer Crush
(kontrakt je originalno pisao "minimax" — koordinator uskladio polje sa stvarnim stanjem).
Portovano iz `docs/gui-v3`: button-style tabovi + stvaran `data-tab-target`→`data-tab-panel`
switching (prije: samo kozmetički `.active` toggle, sav sadržaj stackovan i vidljiv istovremeno).
Brend: 4 panela. Podešavanja: 3 vertikalna panela. Dvije scope-izmjene, obje naknadno odobrene od
Human Owner-a tokom koordinator review-a (nisu bile u originalnom kontraktu): (1) globalni CSS
density/spacing rewrite (manje paddinga na `.nav`/`.topbar`/`.content`/`.card`/`.provider`/
kalendar `.day` itd. — cilj: manje skrolovanja), (2) content-language picker (SR/HR/BS/EN) u
Podešavanja→Jezik (čisto UI, toast + active state, ne veže se još na `PresentationFacade`).
Kontraktom propisana vizuelna provjera (7 screenshot-ova) NIJE bila urađena od implementera
(pywebview zahtijeva display/WebView2) — koordinator je umjesto toga pokrenuo app uživo na Human
Owner-ovom ekranu; potvrđeno da tab-switching radi na oba ekrana, mali preostali skrol u
Podešavanja prihvaćen kao manji ostatak (nije blocking). **Otkriven i riješen realan merge
konflikt**: MiniMax/Codex su nezavisno, necommit-ovano, radili SVOJU verziju istog density
rewrite-a + `.brand-logo` sidebar blok direktno u main working tree-u — `app.css` je jedan
minifikovan red pa je svaka razlika pun konflikt. Riješeno: `git stash` samo tog fajla → merge →
`stash pop` (očekivan konflikt) → zadržana Crush-ova (merge-ovana, odobrena) verzija density-a +
ponovo primijenjen MiniMax-ov `.brand`/`.brand-logo` override blok na kraju (aditivan, nije se
sudarao sa density brojevima). Njihovi ostali necommit-ovani fajlovi (`shell/__init__.py`,
`__main__.py`, `_static_pages.py`, `docs/gui-v3/*`, `test_static_pages_generator.py`) NISU
dirani — i dalje čekaju njihov commit, ali će morati rebase-ovati svoje density brojeve preko
verzije koja je sada u main-u (njihovi brojevi su superseded). Nezavisna verifikacija: otkrivena i
ispravljena poznata ".pth zamka" u worktree-u (editable install je pokazivao na main, ne na sebe),
zatim 525 passed u worktree-u / 553 passed na main-u post-merge, `ruff check src tests scripts` i
`mypy src` čisti (whole-repo `ruff check .` i dalje pada zbog MiniMax/Codex scratch fajlova, kao i
inače — nepovezano), `test_import_boundaries.py` 16 passed. Pun review:
`agent_reports/2026-09-03-ACS-GUI-004-review-claude.md`.

Prethodni entry (2026-09-03): **ACS-F1-016 (OpenAI adapter, HIGH) — Pi
predao, Claude arhitektonski review URAĐEN, U FIX RUNDI.** `PASS_WITH_NOTES` — arhitektura jaka
(implementer ispravio grešku iz kontrakta: `TestProviderConnection`/`DiscoverModels` primaju
adapter kroz lokalni Protocol/DI umjesto interne konstrukcije `OpenAIAdapter`, izbjegavajući
`application→infrastructure` kršenje koje bi moj skicirani potpis izazvao). **Jedan BLOCKING nalaz
(F1), reprodukovan uživo**: `tests/unit/infrastructure/ai/test_openai_adapter.py` radi `import
httpx`, ali `httpx` nigdje nije deklarisan kao zavisnost — oslanja se na tranzitivnu zavisnost
preko `openai` paketa čiji se stvaran resolve u međuvremenu promijenio na `httpx2` (novi paket).
Čist `pip install "openai>=1.30"` danas NE povlači `httpx` → test fajl se ne kolekcioniše →
CI rizik. Implementer-ov "554 passed" je stvaran ali samo zato što je environment već imao
`httpx` od ranije ("radi kod mene"). Pun review: `agent_reports/2026-09-03-ACS-F1-016-review-
claude.md` (u worktree-u, necommit-ovano dok se ne zatvori F1). Fix brief poslat Crush-u:
`agent_reports/2026-09-03-ACS-F1-016-fix-brief-za-crush.md` — predložen fix: dodati `httpx` u
`pyproject.toml` dev extras, verifikovati iz GENUINELY svježeg environment-a. **Codex adversarial
review i dalje NIJE pokrenut** — HIGH-risk politika (§3/§29) zahtijeva punu proceduru čak i nakon
F1 fixa, moj PASS_WITH_NOTES sam po sebi ne otvara put ka merge-u.

Prethodni entry (2026-09-03): **ACS-F1-015 (A8 dio 1 — provider config
+ model selection persistence) merged u main.** `ProviderConfig`/`ModelSelection` dataclass-e +
`ProviderConfigRepositoryPort`/`ModelSelectionRepositoryPort` (`@runtime_checkable`) u
`ports/provider_config.py` + `SqliteProviderConfigRepository`/`SqliteModelSelectionRepository`
nad VEĆ POSTOJEĆIM P0 tabelama (`provider_configs`/`model_selections`, `0000_foundation.sql` —
nula koda ih koristilo do sad, nema nove migracije). `credential_ref` je striktno string
referenca, potvrđeno (grep) da nigdje ne uvozi `ports/secrets.py`/`infrastructure/secrets/`.
`bool` kolone stvarno round-trip-uju kao `bool` (testirano `isinstance`). Koordinator nezavisno
reprodukovao pytest (529 u izolovanom worktree-u, 543 na `main` post-merge)/ruff/mypy/import-
boundaries (16)/`check_no_secrets.py` čisti, pročitao sav kod. MEDIUM risk → Claude-only review →
odmah merge po §29. Merge commit (`--no-ff` u `bb13f53`) + koordinator dodao re-export u
`infrastructure/database/repositories/__init__.py` (isti obrazac kao ACS-F1-006, van
implementer-ovog `allowed_paths`) u istom potezu, commit `cabe1c6`. Worktree uklonjen (clean).
**ACS-F1-016 (OpenAI adapter, HIGH) je sad UNBLOCKED.**

Prethodni entry (2026-09-03): **Task-ID šema VRAĆENA na `ACS-F1-NNN`**
(`docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §31, revidirano). `FLOW-NNNN` (uveden dan ranije,
2026-09-02) je zbunjivao — Human Owner je tražio nazad `ACS-F1-` prefiks, uz i dalje obavezan
kratak opis uz svaki ID. `FLOW-1000`/`FLOW-1001` ostaju kako jesu (već DONE/merged, ne
preimenovati). `FLOW-1002`/`FLOW-1003` (kontrakti napisani isti dan, ništa implementirano) su
preimenovani u **ACS-F1-015**/**ACS-F1-016** — stari worktree-ovi/branch-evi obrisani, novi
kreirani pod ispravnim imenima, sadržaj kontrakata ažuriran.

Prethodni entry (2026-09-03): **A8 (live AI adapters) kreće — dva
kontrakta napisana.** Human Owner odlučio (2026-09-03) da se A8 radi provajder-po-provajder,
počevši od OpenAI — Anthropic/Google/DeepSeek/OpenRouter/OpenAI-compatible dolaze kao odvojeni
budući taskovi. Podijeljeno na dva kontrakta (isti princip kao ACS-F1-009→010/011):

- **ACS-F1-015** (MEDIUM, OPEN, implementer TBD) — `ProviderConfigRepositoryPort`/
  `ModelSelectionRepositoryPort` + SQLite adapter nad `provider_configs`/`model_selections`
  tabelama (postoje od P0 migracije 0000, nula koda ih do sad koristilo — potvrđeno repo-wide
  grep-om). Nema nove migracije, nema SecretStore-a, nema mrežnih poziva.
- **ACS-F1-016** (HIGH, BLOCKED na ACS-F1-015, implementer TBD) — `OpenAIAdapter`
  (`TextGenerationPort` + VLASTITE `test_connection()`/`discover_models()` metode — namjerno NE
  implementira generički `AIProviderConnectionPort`, čiji multi-provider-dispatch potpis je
  preuranjen dok postoji samo jedan provajder) + `ConfigureProvider`/`TestProviderConnection`/
  `DiscoverModels`/`SelectDefaultModel` use-case-i. Prvi task koji dodiruje `SecretStorePort` i
  pravi stvaran vanjski API poziv → puni Codex+Claude+Human Owner ciklus. **Human Owner odluka:
  cijeli automatski test suite mora proći BEZ pravog API ključa** (mock-ovan HTTP/SDK transport u
  potpunosti) — implementer smije ručno probati sa pravim ključem kao DODATNU evidenciju, ali to
  nije obavezan dio review-a. `bootstrap.py` se NE dira (čuva postojeću "fully offline by design"
  invarijantu).

Oba worktree-a kreirana. Detalji: `agent_reports/ACS-F1-015-task-contract.md`,
`agent_reports/ACS-F1-016-task-contract.md`.

Prethodni entry (2026-09-03): **FLOW-1001 — Content revisions
(ReviseContentPiece) merged u main.** `RevisionType` (10 vrijednosti, aditivno u `domain/content/
revisions.py`) + `ReviseContentPiece`: učitava post → odbija `NEW_VISUAL_DIRECTION`/post bez
payload-a odmah → AI poziv sa eksplicitnom "immutable fields" listom → `RevisionOutput.
changed_fields` MORA biti podskup dozvoljenih polja za dati `revision_type` (inače
`InvariantViolation` PRIJE perzistencije) → primjenjuje SAMO promijenjena polja → ponovo lintuje
POSTOJEĆE claims (ne regeneriše) → `derive_content_status`, ALI `APPROVED` post uvijek vraća
`NEEDS_REVIEW` (kodifikuje postojeću `ContentPiece` docstring invarijantu) → atomic persist
`Revision` + ažuriran `ContentPiece`. **Vrijedna implementer odluka**: `_apply_changes` preskače
eksplicitan `null` na promijenjenom polju (tretira kao "bez promjene") umjesto da postavi `None`
na tipiziran `str` field — sprečava type-violation koju bi doslovna kontrakt-pseudokod izazvala,
dobro uočeno i jasno dokumentovano. Prva stvarna upotreba `RevisionRepositoryPort`/
`SqliteRevisionRepository` (postojali od ACS-F1-006, nikad korišteni do sad). Koordinator
nezavisno reprodukovao pytest (515 u izolovanom worktree-u, 529 na `main` post-merge)/ruff/mypy/
import-boundaries (16) čisti, pročitao sav kod (use-case + domain enum diff + sva 3 test fajla),
potvrdio atomicity na pravoj SQLite bazi. MEDIUM risk → Claude-only review → odmah merge po §29.
Merge commit `01be5c9` (`--no-ff` u `0d2630b`). Worktree uklonjen (clean). **A12 plan-grupa
(Claim validator + linter + revisions) je time u potpunosti implementirana** — sekcije 35
(ACS-F1-011), 36-37 (ACS-F1-012), 38 (FLOW-1001) sve gotove.

Prethodni entry (2026-09-03): **FLOW-1001 — Content revisions
(ReviseContentPiece) kontrakt napisan, OPEN, implementer TBD.** Poslednji preostali komad A12
plan-grupe (dio 1 = ACS-F1-012, mergovano). Dodaje `RevisionType` enum (aditivno u
`domain/content/revisions.py`, GitNexus potvrdio LOW impact) + `ReviseContentPiece` use-case koji
koristi VEĆ postojeći `RevisionOutput` schema (ACS-F1-004, partial-update preko
`changed_fields`), VEĆ postojeći `RevisionRepositoryPort`/`SqliteRevisionRepository` (ACS-F1-006,
prva stvarna upotreba), i reuse-uje `claim_validator`/`claim_linter`/`derive_content_status`
(ACS-F1-011/012). Dvije namjerne scope granice dokumentovane u kontraktu:
`NEW_VISUAL_DIRECTION` odbijen (RevisionOutput nema `visual_direction` polje, čeka Visual System
pipeline A13+), claims se ponovo lintuju ali NE regenerišu (RevisionOutput nema `claims` polje).
Kodifikuje postojeću `ContentPiece` docstring invarijantu: revizija prethodno-APPROVED sadržaja
UVIJEK vraća `NEEDS_REVIEW`. Worktree spreman:
`../ai-campaign-studio-worktrees/FLOW-1001-content-revisions`. Detalji:
`agent_reports/FLOW-1001-task-contract.md`.

Prethodni entry (2026-09-03): **FLOW-1000 — Plan-approved guard u
GenerateSocialPost merged u main.** `GenerateSocialPost.execute()` sad odbija bilo koji plan koji
nije `CampaignPlanStatus.APPROVED` (`InvariantViolation`, bačeno PRIJE `campaign_item` pretrage i
PRIJE bilo kakvog AI poziva/perzistencije) — zatvara poznat gap iz ACS-F1-014 (plan sekcija 32:
"Post generation ne smije krenuti sa DRAFT planom"). Postojeći happy-path testovi ažurirani na
`APPROVED` fixture (nisu oslabljeni); novi negativni testovi STVARNO dokazuju da AI port nije
pozvan (`ai_port.calls == []`) za DRAFT/SUPERSEDED plan, plus integration test na pravoj SQLite
bazi (nula persistovanih `content_pieces`). Koordinator nezavisno reprodukovao pytest (502 u
izolovanom worktree-u, 516 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao
cio diff (guard klauzula + import + test izmjene). MEDIUM risk → Claude-only review → odmah merge
po §29. Merge commit `92d2b0c` (`--no-ff` u `1e16b1a`). Worktree uklonjen (clean). **Ovo je bio
prvi task pod novom `FLOW-NNNN` šemom — proces je funkcionisao identično kao za stare
ACS-F1-XXX taskove.**

Prethodni entry (2026-09-02): **FLOW-1000 — Plan-approved guard u
GenerateSocialPost kontrakt napisan, OPEN, implementer TBD.** Prvi task pod novom `FLOW-NNNN`
šemom (§31). Zatvara poznat gap iz ACS-F1-014: `GenerateSocialPost` ne provjerava da je plan
`APPROVED` prije generisanja posta. Worktree spreman:
`../ai-campaign-studio-worktrees/FLOW-1000-plan-approved-guard`. Detalji:
`agent_reports/FLOW-1000-task-contract.md`.

Prethodni entry (2026-09-02): **ACS-F1-014 (A10 — Plan editing/
versioning/approval) merged u main.** `EditCampaignPlan` (pozivalac šalje CIJELU novu listu itema;
stari DRAFT plan → `SUPERSEDED`, novi → `DRAFT` `version+1`, atomično; editovanje APPROVED/
SUPERSEDED plana odbijeno) + `ReorderCampaignItem` (validira permutaciju postojećih item id-jeva,
`order→1..N`, STVARNO delegira na `EditCampaignPlan`, ne duplira logiku — potvrđeno čitanjem) +
`ApproveCampaignPlan` (`CampaignPlan→APPROVED` + `Campaign→PLAN_APPROVED` atomično, provjere:
item count, unique order, non-empty topic/goal). **Vrijedna implementer dizajn odluka**: svaki
item u novoj verziji plana dobija SVJEŽ id (ne zadržava stari), jer je `campaign_items.id`
globalni `PRIMARY KEY` (potvrđeno u migraciji) — stari SUPERSEDED plan i dalje drži stare id-e,
pa bi reuse pucao na constraint. `generate_social_post.py` NIJE diran (poznat gap — post
generation ne provjerava da je plan APPROVED — ostaje dokumentovan, namjerno van scope-a da se
izbjegne konflikt sa ACS-F1-012). Koordinator nezavisno reprodukovao pytest (499 u izolovanom
worktree-u, 512 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod
(3 use-case fajla + svih 5 test fajlova, uključujući 2 prava atomicity testa na SQLite bazi za
edit i approve). MEDIUM risk → Claude-only review → odmah merge po §29. Merge commit `f230db0`
(`--no-ff` u `6aec5ca`). Worktree uklonjen (clean).

Prethodni entry (2026-09-02): **ACS-F1-012 (A12 dio 1 — Claim linter +
final ContentStatus derivacija) merged u main.** `claim_linter.py` (data-driven pravila iz
`resources/claim_rules/default_v1.yaml` — prohibited termini + currency simboli) primijenjen na
SVAKI claim: prohibited termin → `PROHIBITED` (nadjačava ČAK i `VERIFIED_BY_FACT`), numeric signal
(cijena/postotak/trajanje/datum/broj) na claim koji NIJE već `VERIFIED_BY_FACT` → `UNSUPPORTED` sa
reason code-om. `derive_content_status.py` (čista funkcija) → `NEEDS_REVIEW` ako ima
PROHIBITED/UNSUPPORTED, inače `DRAFT`, nikad `APPROVED`. Prežicao `GenerateSocialPost`
(ACS-F1-011) — zamijenio interim `GENERATING`/`NEEDS_REVIEW` logiku ovom finalnom. Ažurirao
POSTOJEĆE ACS-F1-011 testove (GENERATING→DRAFT na happy path-u, nije ih oslabio) + dodao novi
regression test koji dokazuje da `PROHIBITED` stvarno nadjačava fact-backed claim end-to-end.
Koordinator nezavisno reprodukovao pytest (472 u izolovanom worktree-u, 485 na `main` post-merge)/
ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (linter, status derivacija, rewiring diff,
svi test fajlovi). Sekcija 38 (Content revisions) namjerno van scope-a, ide u budući ACS-F1-013.
MEDIUM risk → Claude-only review → odmah merge po §29. Merge commit `a4baeed` (`--no-ff` u
`4218750`). Worktree uklonjen (clean).

Prethodni entry (2026-09-02): **VAŽNO za sve buduće taskove: Task-ID
šema promijenjena (Human Owner odluka, `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §31).**
`ACS-<FAZA>-NNN` (npr. `ACS-F1-014`) je zamijenjen sa **`FLOW-NNNN — <opisan naslov>`** za SVE
NOVE taskove, počevši od `FLOW-1000`. Broj je globalni sekvencijalni brojač (ne resetuje se po
fazi), i NIKAD se ne pominje sam bez naslova ("FLOW-1000 — SocialPostPayload persistence", ne
samo "FLOW-1000"). **Postojećih 14 taskova (ACS-P0-001..008, ACS-F1-001..014, ACS-GUI-001/002,
ACS-HOTFIX-001) OSTAJU pod starim imenima** — retroaktivno preimenovanje nije urađeno (već
DONE/merged, nema koristi od diranja branch/worktree/istorije). ACS-F1-012 i ACS-F1-014 (kontrakti
ispod, napisani PRIJE ove odluke) takođe zadržavaju stara imena. **Sljedeći task koji se otvori
dobija `FLOW-1000`, ne `ACS-F1-015`.**

Prethodni entry (2026-09-02): **Dva nova kontrakta napisana: ACS-F1-012
i ACS-F1-014.**

- **ACS-F1-012** ("A12 dio 1" — Claim linter + final `ContentStatus` derivacija, plan sekcije
  36-37, NE sekcija 38/revizije). Implementer: **Pi**, NIJE blokiran (sve od čega zavisi već
  postoji na main-u), worktree spreman, brief poslat
  (`agent_reports/2026-09-02-ACS-F1-012-brief-za-pi.md`). Prežicava već-mergovan
  `generate_social_post.py` (ACS-F1-011) — mijenja interim status logiku (`GENERATING`/
  `NEEDS_REVIEW`) na finalnu (`DRAFT`/`NEEDS_REVIEW`), zahtijeva ažuriranje ACS-F1-011-ovih
  postojećih testova (Pi upozoren da ih ažurira, ne oslabi).
- **ACS-F1-014** ("A10" plan-numeracija — Plan editing/versioning/approval: `EditCampaignPlan` +
  `ReorderCampaignItem` + `ApproveCampaignPlan`). **Task-ID namjerno ACS-F1-014, ne ACS-F1-013**
  — taj broj je već rezervisan za budući "Content revisions" task (plan sekcija 38) u
  ACS-F1-012-ovim dokumentima. Implementer TBD. Dokumentuje POZNAT, namjerno neriješen gap:
  `GenerateSocialPost` ne provjerava da je plan `APPROVED` prije generisanja posta — nije
  popravljeno u ovom tasku da se izbjegne fajl-konflikt sa paralelnim ACS-F1-012 (oba bi dirala
  `generate_social_post.py`). Nezavisan je od ACS-F1-012 (različit paket), može ići paralelno,
  ali **ne dira `generate_social_post.py`**.

**A8 (live provider adapter) ostaje odgođen po Human Owner odluci — "ostavljamo još malo".**

Prethodni entry (2026-09-02): **ACS-F1-011 (A11 — GenerateSocialPost)
merged u main.** `select_allowed_facts` (deterministički, samo `is_fact_usable` fact-ovi, lexical
matching) + `claim_validator` (plan sekcija 35, SAMO fact-id dio — FACT claim treba postojeći/
usable/dozvoljen fact_id → `VERIFIED_BY_FACT`, inače `UNSUPPORTED` sa reason code-om;
CTA/OPINION/CREATIVE → uvijek `NON_FACTUAL`) + `GenerateSocialPost` orchestration (učitava
Campaign/Plan/CampaignItem/BrandSnapshot/facts → `post_generation` prompt → AI poziv → schema+claim
validacija → interim status `NEEDS_REVIEW`/`GENERATING`, nikad `DRAFT` → atomic persist
`ContentPiece` sa `payload`-om iz ACS-F1-010). Integration test lanči `LoadBrandFixture` →
`CreateCampaign` → (ručno sastavljen plan) → `GenerateSocialPost` na pravoj SQLite bazi sa pravim
fact-om iz `brightsmile.json` fixture-a, PLUS bonus atomicity test (mid-persist failure ostavlja
`content_pieces` praznim). Koordinator nezavisno reprodukovao pytest (458 u izolovanom worktree-u,
471 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, potvrdio `git status` scope
(sve novo, ništa van `application/posts/`+testovi), potvrdio bez `channels`/`ai_registry` importa.
MEDIUM risk → Claude-only review → odmah merge po §29. Merge commit `1c28789` (`--no-ff` u
`13d5b3a`). Worktree uklonjen (clean). **A11 (posljednji "odmah dostupan" application-layer
generation task) je time GOTOV — campaign plan I social post generation sad oba postoje end-to-end
nad mock AI adapterom.**

Prethodni entry (2026-09-02): **ACS-F1-010 merged u main (HIGH risk, puni
ciklus).** Implementer bio Claude (Human Owner odluka) — pošto Claude nije mogao sam sebe
reviewovati ("Implementer != reviewer"), review je uradio Codex (`PASS_WITH_NOTES`, nema blocking
findings, plus nezavisna adversarial provjera: None-vs-prazan-payload distinkcija preživljava
round-trip, potvrđeno na scratch bazi sa samo migracijama 0000-0002 pa dodavanjem 0003). Finalni
decision packet: `agent_reports/2026-09-02-ACS-F1-010-final-decision-packet.md`. Human Owner
odobrenje: "Odobravam". Merge commit `1de7423` (`--no-ff` u `faaa5d7`). Post-merge gate: 455
testova (scoped, isključujući MiniMax-ove necommit-ovane scratch fajlove — vidi napomena ispod),
`ruff check src tests scripts` čist, mypy čist, boundaries (16) čisti. Worktree uklonjen (clean).
**ACS-F1-011 sad UNBLOCKED — Pi je već krenuo** (worktree sinhronizovan sa main-om, `application/
posts/select_allowed_facts.py` i `claim_validator.py` u toku, necommit-ovano).

Prethodni entry (2026-09-02): **Dva nova kontrakta napisana za A11:
ACS-F1-010 i ACS-F1-011, oba OPEN, implementer TBD.** Pri pisanju A11 kontrakta otkriven pravi
gap: `ContentPiece` nema polje za sam generisani post (`SocialPostPayload`) — već dokumentovano
kao svjestan scope-granica u ACS-F1-006. Zatvaranje gap-a zahtijeva prvu `ALTER TABLE` migraciju
u projektu → HIGH risk po CLAUDE.md pravilu (SQLite/migrations), puni Codex+Claude+Human Owner
ciklus, ne streamlined MEDIUM put. Zato DVA odvojena kontrakta:

- **ACS-F1-010** (HIGH, blokira ACS-F1-011): aditivno `ContentPiece.payload` polje +
  `resources/migrations/0003_content_payload.sql` (`ALTER TABLE content_pieces ADD COLUMN
  payload_json TEXT`) + `SqliteContentRepository` read/write. GitNexus impact potvrđuje mali
  stvaran blast radius uprkos HIGH kategoriji (napomenuto u kontraktu za Codex/Human Owner
  kalibraciju review dubine).
- **ACS-F1-011** (MEDIUM, status BLOCKED dok ACS-F1-010 ne merguje): `GenerateSocialPost` —
  `select_allowed_facts` (deterministički, bez embeddings/vector DB) + Fact-ID validator (plan
  sekcija 35, SAMO taj dio — NE puni A12 linter) + orchestration. Dokumentovano interim
  `ContentStatus` pravilo: bilo koji `UNSUPPORTED` claim → `NEEDS_REVIEW`, inače `GENERATING`
  (NIKAD `DRAFT` — taj status je rezervisan za "nema upozorenja" ishod A12-ovog lintera, koji ovaj
  task ne implementira).

Oba worktree-a kreirana, implementer nije dodijeljen. Detalji:
`agent_reports/ACS-F1-010-task-contract.md`, `agent_reports/ACS-F1-011-task-contract.md`.

Prethodni entry (2026-09-02): **ACS-F1-009 (A9 — CreateCampaign +
GenerateCampaignPlan) merged u main.** Prvi task koji stvarno spaja ACS-F1-007 i ACS-F1-008 u
generation pipeline: `CreateCampaign` (validacija → mapper → atomic persist brief+campaign) i
`GenerateCampaignPlan` (Campaign→BrandSnapshot→CampaignBrief→prompt→`TextGenerationPort`→
schema+domain validacija→atomic persist plan + `Campaign.status→PLAN_GENERATED`). `ports/
repositories.py` diff je striktno aditivan (`get_brief`, ništa drugo promijenjeno — lično
diff-ovao). Integration test lanči SVA TRI use-case-a zajedno (`LoadBrandFixture` →
`CreateCampaign` → `GenerateCampaignPlan`) na pravoj SQLite bazi — prvi pravi end-to-end dokaz da
Faza 1 slojevi rade zajedno, ne samo izolovano. Atomicity (oba use-case-a) i role-diversity/
duplicate-topic domain provjere nezavisno reprodukovane na pravoj bazi. Koordinator nezavisno
reprodukovao pytest (439 u izolovanom worktree-u, 452 na `main` post-merge)/mypy/import-boundaries
čisti. **Napomena:** `main` trenutno ima paralelno, van formalnog task-sistema, MiniMax-ove
necommit-ovane izmjene (`presentation_webview/__main__.py` window-state persistencija + scratch
debug fajlovi `diagnose_close.py`/`test_window_close.py` u root-u) — zbog toga
`scripts/generate_phase0_gate_report.py` i whole-repo `ruff check .` trenutno FAIL lokalno (ruff
greške su isključivo u ta dva scratch fajla, ne u ičemu iz ACS-F1-009). CI na GitHub-u vidi samo
pushed/committed stanje pa ostaje zeleno — vidi CI red ispod. Ne dirati ta dva fajla/scratch
fajlove dok MiniMax ne javi da je gotovo (Human Owner eksplicitno tražio da se sačeka).
Worktree uklonjen (clean).

Prethodni entry (2026-09-02): **Human Owner live-pokrenuo pravu
pywebview aplikaciju i podijelio screenshot-e sva 5 sidebar ekrana** (Početna/Brend/Kampanje/
Kalendar/Podešavanja) na stvarnoj mašini, Edge WebView2, stilizovano (CSS/JS se učitavaju —
potvrđuje da `d71d84d` static-assets fix stvarno radi u praksi, ne samo u testu). Koordinator
pregledao svih 5 screenshot-a protiv `DEFAULT_FIXTURE` vrijednosti i `docs/gui-v3` reference:
Kalendar dani 3/5/9 sa tačnim eventima/bojama, Kampanje sva 3 reda sa tačnim statusima/brojevima,
Brend sve 3 činjenice + glas brenda bedževi + status datum, Podešavanja svih 5 providera "Nije
povezano", Početna brojke (3/18/6/12) i liste — sve se poklapa, nema vizuelnih grešaka. Ovo
zatvara jedinu preostalu prazninu iz ACS-GUI-002 review-a (implementer nije mogao live-testirati u
svom env-u, koordinator to nije ponovio pri merge-u za taj konkretan task — vidi ACS-GUI-002 red u
tabeli ispod). **Sva GUI-BASE površina (shell + svih 5 ekrana) je sada live-verifikovana, ne samo
test-verifikovana.**

Prethodni entry (2026-09-02): **Novi task napisan: ACS-F1-009** (A9 —
`CreateCampaign` + `GenerateCampaignPlan` use-caseovi, spaja ACS-F1-007 + ACS-F1-008 u prvi pravi
generation pipeline). A8 (pravi live provider adapter) EKSPLICITNO odgođen po Human Owner odluci —
ACS-F1-009 zavisi samo od `TextGenerationPort` Protocol-a, ne od konkretnog adaptera. Kontrakt
uključuje jednu usko-skopiranu aditivnu izmjenu na `CampaignRepositoryPort` (`get_brief` — zatvara
persistence read-path rupu, GitNexus upstream impact = LOW). Worktree kreiran:
`../ai-campaign-studio-worktrees/ACS-F1-009-campaign-brief-plan-generation`, branch
`task/ACS-F1-009-campaign-brief-plan-generation` @ `main 23b08ca`. Implementer: **Pi** (Human Owner odluka, 2026-09-02). Detalji:
`agent_reports/ACS-F1-009-task-contract.md`.

Prethodni entry (2026-09-02): **ACS-F1-007, ACS-F1-008, ACS-GUI-002 sva tri merged u main** (paralelni round, svi Claude-only MEDIUM review PASS, svi commit-ovani/push-ovani odmah po §29, bez posebnog Human Owner odobrenja per-task). Redoslijed merge-a: F1-007 → F1-008 → GUI-002, svi čisti merge-evi bez konflikta (disjoint `allowed_paths`). Nakon sva tri: **425 testova, ruff/mypy čisti, `python scripts/generate_phase0_gate_report.py` → `status: PASS`, svih 17 checkova true**. Detalji po tasku u tabeli ispod. Sve tri worktree uklonjene (clean, bez force-a); task branch-evi ostavljeni lokalno (isti pattern kao P0/F1-001..006).

Prethodni entry (2026-09-02): **POST-MERGE BAG NAĐEN I POPRAVLJEN (`d71d84d`): `write_all_pages()` nikad nije kopirao `static/app.css`/`app.js` u runtime temp direktorijum**, pa je Human Owner uživo vidio goli, nestilizovan HTML (svaka generisana stranica linkuje `../static/app.css` relativno, ali taj fajl nikad nije postojao u temp dir-u — 404). Promakao kroz OBA ACS-GUI-001 review round-a jer su svi postojeći testovi provjeravali samo STRING sadržaj href/src u HTML-u, nikad da referencirani fajl stvarno postoji na disku; round-2 live-launch test je provjerio samo da se `Chrome_WidgetWin` proces inicijalizuje (edgechromium, ne mshtml), ne da je stranica stvarno renderovana stilizovano. **Lekcija za buduće review-e GUI/file-generation koda: kad test tvrdi da fajl "postoji" ili je "linkovan", provjeriti stvaran filesystem side-effect, ne samo string u generisanom sadržaju.**

---

## Review politika (Human Owner odluka, 2026-09-01) — PROVJERITI PRIJE SVAKOG NAREDNOG TASKA

Puni detalj: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §29.

```text
HIGH-risk / bezbjednosno kritično (SecretStore, SQLite/migrations, architecture
boundaries/bootstrap, AI/Channel/Localization registry contract, itd. — puna
lista u workflow §4) → NEPROMIJENJENO: Codex + Claude + eksplicitno Human
Owner merge odobrenje.

Sve ostalo (LOW/MEDIUM) → SAMO Claude review. Claude PASS → koordinator
ODMAH commit-uje i push-uje/merguje, bez Codex runde i bez posebnog
per-task Human Owner odobrenja.
```

## Agent-friendly file headers (Human Owner odluka, 2026-09-01)

Puni detalj: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md` §30. Faza 1
(ključni P0.00–P0.19 foundation fajlovi sa pretankim header-om) je urađena
2026-09-01 kao LOW-risk docstring-only izmjena, direktno commit-ovana/
push-ovana po review politici iznad (bez Codex runde). Od sada važi
touched-file rule: kad task materijalno mijenja postojeći source fajl,
provjeriti/dodati kvalitetan owns/does-not-own header u istom tasku.

Ako se tokom review-a pokaže da task ipak dira HIGH listu — STOP, vratiti na
puni ciklus, ne nastaviti olakšanim putem tiho.

## Aktivna faza

**Faza 1 — Vertical Slice 1.** P0 Foundation je DONE (`P0-GATE = PASS`, 2026-09-02).
Aktivni plan: `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`. A3–A7 svi
DONE i merged (domain enums/entities, boundary schemas, business persistence, brand
fixture load, prompt+AI+mock infra). GUI paralelno: ACS-GUI-001/002 (shell + svih 5
sidebar ekrana) takođe merged. Sljedeći: A8 (live provider adapter(i) nad
`TextGenerationPort`) i/ili prvi pravi generation use-case (campaign plan/post) koji
koristi ACS-F1-007 (loaded brand) + ACS-F1-008 (prompts/AI port/mock adapter) zajedno.

## Aktivni dokumenti

- Arhitektura/proizvod SoT: `AI_Campaign_Studio_Faza_0_6_Channel_Model_LLM_Registry.md`
- Aktivni P0 plan: `AI_Campaign_Studio_Implementation_Phase_0_v1_1_Agent_Workflow_Integrated.md`
  (supersedes `AI_Campaign_Studio_Implementation_Phase_0_Project_Foundation_Agent_Plan.md` — ne koristiti taj)
- Aktivni Faza 1 plan (blokiran do P0-GATE): `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`
  (supersedes `AI_Campaign_Studio_Faza_1_v1_3_P0_Handoff_Agent_Ready_Tehnicki_Plan.md`)
- Proces: `docs/AI_CAMPAIGN_STUDIO_AGENT_WORKFLOW.md`
- GitNexus: `.agent/GITNEXUS_PROTOCOL.md`
- Performance/Analytics arhitektonska dopuna: `AI_Campaign_Studio_Faza_0_7_Performance_Analytics_Architecture.md`
  - dopunjuje Fazu 0.6 samo za Performance/Analytics odluke;
  - sada zaključava anti-refactor seam-ove, ali NE pokreće Analytics runtime implementaciju u P0.
- Analytics-ready Faza 1 dopuna: `AI_Campaign_Studio_Faza_1_v1_5_Analytics_Ready_Implementation_Plan.md`
  - dopunjuje aktivni Faza 1 v1.4 plan;
  - prije Slice 1.5 uvodi samo stable IDs, revision/target identity, export manifest i `analytics_match_key`;
  - stvarni Performance modul počinje tek poslije potvrđenog `G10 Vertical Slice PASS`.
- **A/B evaluation harness (R1 — "je li Campaign Engine stvarno bolji od plain LLM prompta")**
  je već detaljno specificiran u `AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md`
  §47–50 i A16–A20 (Control A/System B skripte, 11 determinističkih metrika, blind human-eval
  rubrika, Kill/Pivot gate). NE pisati novi "evaluation criteria" dokument kad G10 postane
  aktuelan — vidi `.agent/PROJECT_MAP.md` §7 za tačan pointer po sekciji.

## Performance / Analytics status

```text
ARCHITECTURE: LOCKED / PLANNED
RUNTIME ANALYTICS IMPLEMENTATION: NOT STARTED
```

Tačan redoslijed:

```text
P0 Foundation
→ Faza 1 Campaign Engine
→ G10 Vertical Slice PASS
→ Slice 1.5 Performance Foundation
→ Slice 2 Brand / Website Ingestion
```

Analytics se **NE implementira sada u P0**.

Prije Slice 1.5 Faza 1 mora samo sačuvati seam-ove koji sprečavaju kasniji veliki refaktor:

```text
campaign_id
campaign_plan_id
campaign_item_id
content_piece_id
content_revision_id
channel_code / platform_code / format_code
export manifest.json
analytics_match_key
```

Kada `G10 = PASS`, koordinator mijenja ovaj status u `SLICE 1.5 ACTIVE`. Od tog trenutka svaki
Performance/Analytics Task Contract mora slijediti `.agent/TASK_ROUTING.md` sekciju
**Performance / Analytics task**.

## Trenutni P0 gate

**PASS — 2026-09-02.** Svih 8 P0 taskova (ACS-P0-001 do ACS-P0-008) su merged.
`artifacts/phase0_foundation_gate.json` postoji na `main` (commit `aef1b0d`),
regenerisan protiv stvarnog merge-ovanog main-a (ne stale/worktree stanja):

```json
{
  "phase": "implementation-phase-0",
  "status": "PASS",
  "checks": { ... svih 17 true ... },
  "ui_framework": "NOT_SELECTED",
  "campaign_engine_implemented": false,
  "website_ingestion_implemented": false,
  "notes": []
}
```

`src/ai_campaign_studio/` ima punu foundation površinu: `config/`, `logging/`,
`domain/common/`, `localization/`, `channels/`, `ai_registry/`,
`infrastructure/{secrets,database}/`, svih 5 `ports/` contracta, `jobs/`
(JobManager, sa ACS-HOTFIX-001 event-ordering fix-om), `presentation/`
(framework-neutral state/contracts), pun `bootstrap.py` composition root,
`--health-check` entrypoint, `scripts/{validate_resources,check_no_secrets,
generate_phase0_gate_report}.py`, i `tests/architecture/test_import_boundaries.py`.

**Faza 1 više NIJE blokirana** (uslov iz "Aktivna faza" sekcije je ispunjen).
Prije nego što se formalno pređe na Faza 1 rad: pročitati plan §37 (P0.30
STOP) — agent ne nastavlja automatski sa Brand/Facts/CampaignPlan/
ContentPiece/OpenAI generation/GUI/renderer dok Human Owner eksplicitno ne
potvrdi prelazak. Napomena: SPIKE-001 (pywebview UI validacija, kasnije
prošireno u punu GUI izradu od strane MiniMax-a) je već u toku paralelno —
to je Human Owner odluka da se UI rad počne i prije formalnog P0.29/P0.30
zapisa, van P0 Task Contract sistema (vidi SPIKE_NOTES.md u tom worktree-u).

## ACS-HOTFIX-001 — RIJEŠENO (2026-09-01)

CI regresija otkrivena na `main`-u poslije ACS-P0-007 merge-a (GitHub
Actions run `33502313009`) — `JobManager` `CREATED`/`STARTED` event-ordering
race, popravljena i merged (`bcec979`). Vidi red u tabeli ispod za pun
istorijat. **Ostaje aktivna posljedica**: ACS-P0-008 (grana
`task/ACS-P0-008-validators-ci-security-gate`, još nije merged) je granata
sa main-a PRIJE ovog hotfix-a — kad MiniMax-ov fix round za BF-1/BF-2 stigne,
prije finalizacije treba merge-ovati ažurirani `main` (sa hotfix-om) u tu
granu, pa tek onda ponovo generisati `artifacts/phase0_foundation_gate.json`
tako da `pytest` check stvarno pokriva i JobManager fix.

**Environment napomena (relevantna za sve buduće taskove)**: dijeljeni
`.venv`-ov editable-install `.pth` fajl
(`H:\AI Campaing Studio\.venv\Lib\site-packages\__editable__.ai_campaign_studio-0.1.0.pth`)
može tiho pokazivati na PROŠLI worktree umjesto na fajl koji se trenutno
verifikuje — otkriveno i potvrđeno od implementera (MiniMax), koordinatora
i Codex-a tokom ACS-HOTFIX-001. Nakon svakog merge-a, `.pth` treba ručno
provjeriti/vratiti na `main` checkout
(`H:\AI Campaing Studio\src`) prije post-merge gate-a — inače se gate testira
protiv pogrešnog koda. Za verifikaciju u worktree-u, eksplicitan
`PYTHONPATH` override je pouzdaniji od oslanjanja na `.pth` stanje.

## Aktivni taskovi

| Task | Status | Implementer | Reviewers | Napomena |
|---|---|---|---|---|
| ACS-F1-001 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `2e83911` (`--no-ff`, branch `task/ACS-F1-001-domain-common-brand-facts` @ `47bffde`). Scope: `domain/common` extension (10 typed ID aliasa kao `NewType`, 3 nove `DomainError` podklase) + `domain/brand/` (frozen value objects + entities) + `domain/facts/` (FactStatus, immutable ApprovedFact, versioning policies). Koordinator nezavisno pročitao sav kod, pokrenuo pun test suite (242 testa) + architecture boundary suite (15 testova), i sam reprodukovao immutability/InvariantViolation/non-mutation invarijante van test suite-a. MEDIUM risk → Claude-only review → odmah merge po §29, bez posebnog Human Owner odobrenja. Post-merge gate PASS na `main`, CI zeleno (potvrđeno uživo). Worktree uklonjen (clean). |
| ACS-F1-002 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `b30166b` (`--no-ff`, branch `task/ACS-F1-002-domain-campaign-content-visual` @ `2404ba9`). Korak 1 (enums/roles/templates/slots, bez zavisnosti) + Korak 2 (entities.py, content/claims.py, content/revisions.py, visual/layout.py — nakon što je ACS-F1-001 dao typed ID aliase). Svi typed ID-jevi ispravno importovani iz `domain.common.ids`, bez lokalnih duplikata (0A.5). `LayoutSpec` polja su sva tipizirani enumi (novi `ImagePosition`/`HeadlinePosition`/`HeadlineScale`/`Overlay`/`LogoPosition`/`CtaStyle` dodati u `visual/enums.py`). Koordinator nezavisno pročitao sav kod, pokrenuo pun test suite (263 testa) + architecture boundary suite (15 testova), i sam reprodukovao immutability i `lead_generation_v1` sekvencu (7 uloga, bez duplikata) van test suite-a. MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`, CI zeleno (potvrđeno uživo). Worktree uklonjen (clean). |
| ACS-F1-003 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `b3369f1` (`--no-ff` u `380a279`, branch `task/ACS-F1-003-brand-fixture-schema`). `application/schemas/brand_fixture.py` (Pydantic) + `application/mappers/brand_fixture_mapper.py` (mapira u postojeće `Brand`/`BrandSnapshot`/`ApprovedFact`) + demo fixture `resources/fixtures/brightsmile.json`. `Restriction` NIJE proširen (implementer procijenio da fixture ne treba dodatna polja — dobra disciplina protiv "za svaki slučaj"). Worktree nije bio pre-kreiran od koordinatora (implementer ga sam napravio na `main @ 0a6dbc4` umjesto navedenog `0edae77` — obrazloženo i prihvaćeno, `0edae77` je bio predak kontrakt-commita). Koordinator nezavisno reprodukovao pytest/ruff/mypy/import-boundaries sa čistim `PYTHONPATH` overrideom, pročitao sav schema/mapper/test kod. MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main` (290 testova ukupno nakon oba A4 merge-a). Worktree uklonjen (clean). |
| ACS-F1-004 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `894c457` (`--no-ff` u `380a279`, branch `task/ACS-F1-004-campaign-content-visual-schemas`). Pet Pydantic schema fajlova (campaign_brief, campaign_plan_output, social_post_generation_output, revision_output, visual_direction_output). `domain/visual/enums.py` čisto additivno prošireno (`ImageTreatment`/`LogoRule`/`CtaRule`) — verifikovano `git diff` da nijedan postojeći enum član nije dirat. Isti worktree-base napomena kao ACS-F1-003. Trivijalan `application/schemas/__init__.py` add/add merge konflikt (oba taska dodala docstring-only fajl) — koordinator ručno spojio u opisniji docstring, bez funkcionalnog uticaja. Koordinator nezavisno reprodukovao pytest/ruff/mypy/import-boundaries, pročitao sve schema fajlove + adversarial testove (odbijanje proizvoljnih enum stringova, dupli `order`, partial-update semantika). MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`. Worktree uklonjen (clean, nakon jednog retry-a zbog file lock-a). |
| ACS-F1-005 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `4d9e127` (`--no-ff` u `b3dd5ee`, branch `task/ACS-F1-005-brand-facts-persistence`). Svih 7 repository Protocol-a (`ports/repositories.py`, `@runtime_checkable`) + `SqliteBrandRepository`/`SqliteFactRepository` na postojećem P0 SQLite temelju (migracija `0001_brand_facts.sql`: brands/brand_snapshots/approved_facts/brand_snapshot_facts, `position` kolona na join tabeli da tuple `approved_fact_ids` round-trip-uje bez gubitka redoslijeda — nadograđeno u odnosu na kontrakt-DDL, dokumentovano). `save_*` idempotentni (`ON CONFLICT DO UPDATE`). `TelemetryRepositoryPort` samo interface, bez adaptera/migracije (Performance/Analytics deferral). Usput popravljena 2 P0 assertion-a u `tests/integration/database/test_migrations.py` (van `allowed_paths`, dokumentovano kao OUT_OF_SCOPE_FINDING u evidence izvještaju — postojeći testovi su hardkodirali tačno jednu migraciju, sad tolerantni na dodatne). Koordinator nezavisno reprodukovao pytest (303)/ruff/mypy/import-boundaries, pročitao sav port/adapter/test kod (round-trip dataclass `==`, idempotentnost, FK enforcement, `position`-ordering svi testirani). MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`. Worktree uklonjen (clean). |
| ACS-F1-006 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `6b93ab5` (`--no-ff` u `9def55c`, branch `task/ACS-F1-006-campaign-content-visual-persistence`). Bio blokiran na ACS-F1-005 (korak 2), sekvenca ispoštovana ispravno (provjerio worktree prije nastavka, javio blokadu, nije izmišljao lokalne Protocol definicije). Nakon ACS-F1-005 merge-a: `git merge main` u svoj branch, implementirao `SqliteCampaignRepository`/`SqliteContentRepository`/`SqliteVisualRepository`/`SqliteRevisionRepository` (migracija `0002_campaign_content_visual.sql`, isti DDL stil kao ACS-F1-005 uključujući `position` kolonu na `content_claims` join tabeli — primijenio Pi-jevu lekciju bez da mu je eksplicitno rečeno). `SocialPostPayload` namjerno nije perzistiran (domain `ContentPiece` nema `payload` polje, `ContentRepositoryPort` nema odgovarajuće metode — dokumentovano kao scope granica, ne tiha rupa). `repositories/__init__.py` ispravno NIJE dirao (van `allowed_paths`, ACS-F1-005 teritorija) — koordinator dodao re-export nakon merge-a (`9def55c`). Koordinator nezavisno reprodukovao pytest (320)/ruff/mypy/import-boundaries (52 architecture+integration), pročitao migraciju i sva 4 adaptera + round-trip/idempotentnost/izolacija/FK/ordering testove. MEDIUM risk → Claude-only review → odmah merge po §29. Post-merge gate PASS na `main`. Worktree uklonjen (clean). |
| ACS-GUI-001 | **DONE — merged u main** | MiniMax | Claude (MEDIUM, 2 runde) | Merge commit `cad003e` (`--no-ff` u `9259792`, branch `task/ACS-GUI-001-gui-base-shell`). Prvi produkcijski GUI task nakon G9 zatvaranja. Round 1: sigurnosni dio (edgechromium/debug/WebView2 fail-loud) odličan, ali 3 nalaza (static assets nisu doslovna kopija docs/gui-v3/shared/, neatražen `.lang-toggle`, sidebar/topbar nije DRY) blokirala merge — vidi `agent_reports/2026-09-02-ACS-GUI-001-review-claude-round1.md`. Round 2: sva tri riješena (SHA-256-verifikovana bajt-identična kopija; `.lang-toggle` uklonjen sa regression testom; `screens/_static_pages.py` `write_all_pages()` renderuje svih 5 ekrana kroz jedan `render_shell()`, DRY-enforcement test). Koordinator nezavisno reprodukovao pun test suite (346 na `main` post-merge)/ruff/mypy/import-boundaries, pročitao sav izmijenjen kod, verifikovao SHA-256 sam, i live-pokrenuo `python -m ai_campaign_studio.presentation_webview` na stvarnoj mašini — proces log potvrđuje pravi `Chrome_WidgetWin` (Edge WebView2), ne mshtml fallback. MEDIUM risk → Claude-only review (2 runde) → merge po §29 nakon PASS. Worktree uklonjen (clean). |
| ACS-F1-007 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `5bcbf41` (`--no-ff`, branch `task/ACS-F1-007-load-brand-fixture` @ `70127d2`). A6 `LoadBrandFixture` use-case (`application/brands/load_brand_fixture.py`) orkestrira ACS-F1-003 schema/mapper + ACS-F1-005 repositories: validira JSON kroz `BrandFixtureSchema` PRIJE bilo kakvog repository poziva, mapira, perzistira brand+facts+snapshot u jednoj `SqliteUnitOfWork` transakciji. Zavisi samo od `BrandRepositoryPort`/`FactRepositoryPort` + lokalni duck-typed `_UnitOfWork` Protocol (implementer ga dodao kao treći konstruktor parametar van kontrakt-primjera, opravdano za atomicity — prihvaćeno), bez SQLite importa. Atomicity STVARNO testirana na pravoj SQLite bazi (mid-load failure na 2. `save_fact`, sve 4 tabele COUNT=0 poslije), `fixture://` provenance provjerena čitanjem nazad, invalid-fixture (prazan `facts`) odbijen od `BrandFixtureSchema`-inog `_validate_facts` validatora prije ijednog repo poziva. Implementer sam kreirao worktree na `main @ ed5b8d4` umjesto navedenog `b4b324f` (noviji commit, prihvatljivo, dokumentovano). Koordinator nezavisno reprodukovao pytest (352 u izolovanom worktree-u, 354 na `main` post-merge)/ruff/mypy/import-boundaries (15), pročitao use-case + oba test fajla + `SqliteUnitOfWork.__exit__` semantiku. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-008 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `2aed9fe` (`--no-ff`, branch `task/ACS-F1-008-prompt-ai-mock` @ `0aaef6d`). A7 — `ports/ai.py` (`AIMessage`/`AIRequest`/`AIResponse`/`AITelemetry` + `TextGenerationPort` Protocol) i `ports/prompts.py` (`PromptDefinition` + `PromptRepositoryPort`), oba framework-neutral (nema yaml/http/SDK importa — verifikovano čitanjem). `YamlPromptRepository` učitava i validira svih 8 metadata polja za svih 5 obaveznih promptova (`campaign_plan`/`post_generation`/`revision`/`visual_direction`/`ab_control`) — nedostajuće/null polje baca `ValueError` pri `get()`, nepostojeća verzija isto (bez silent fallback-a). `ab_control/v1.yaml` provjeren ručno (koordinator čitao fajl) — ne sadrži nijedan CampaignRole naziv, namjerna dizajn granica ispoštovana. `MockAdapter` implementira svih 5 modova (deterministic/error/invalid-schema/rate-limit/telemetry), bez network poziva, bez business logike. `ports/ai_registry.py`/`ai_registry/` netaknuti (potvrđeno `git status`). Proširio `tests/architecture/test_import_boundaries.py` za `infrastructure/ai/` (eksplicitno dozvoljeno acceptance stavkom, isti pattern kao ACS-GUI-001 za `presentation_webview/`) — jedina izmjena van `allowed_paths`. Koordinator nezavisno reprodukovao pytest (362 u izolovanom worktree-u, 370 na `main` post-merge)/ruff/mypy/import-boundaries (16), pročitao sva 4 core fajla + svih 5 YAML promptova (skriptom provjerio da svih 8 polja postoje u sve 5 fajla). MEDIUM risk → Claude-only review → odmah merge po §29. Čist merge, bez konflikta sa ACS-F1-007. Worktree uklonjen (clean). |
| ACS-GUI-002 | **DONE — merged u main** | MiniMax | Claude (MEDIUM) | Merge commit `af6723d`-predecessor (`--no-ff` u `2aed9fe`, branch `task/ACS-GUI-002-remaining-sidebar-screens` @ `99f3502`). Preostala 4 sidebar ekrana (Brend/Kampanje/Kalendar/Podešavanja) zamijenila ACS-GUI-001 placeholder sadržaj realnim, fixture-driven `render_body()` — isti pattern kao Početna (frozen dataclass fixtures + `html.escape()`). Koordinator uporedio string-po-string protiv `docs/gui-v3/screens/{02,03,06,09}_*/index.html` — Brend markup je bajt-za-bajt identičan referenci; Kampanje ispravno pretvorio SVA tri "Otvori" dugmeta (uključujući referenci-in jedini pravi `<a href="../04_opis_kampanje/...">`) u `data-action="toast"` stub (ekran ne postoji u `presentation_webview`); Kalendar ispravno izostavio `?campaign=` banner/stepper (`data-campaign-only` blokovi u referenci) — samo globalni pogled portovan; Podešavanja bajt-za-bajt identičan. Nijedan `<a href>` ka nepostojećem ekranu, nema remote asset referenci (CSP `default-src 'self'` netaknut), `shell/`/`screens/__init__.py`/`_static_pages.py`/`pocetna/`/`static/`/`__main__.py` svi netaknuti (git diff potvrdio). 55 novih testova (fixture-driven invariant, XSS escaping, CSS klase, no-`<a href>`, no-remote-asset po ekranu). Očekivani test failure (`test_write_all_pages_placeholder_screens_carry_only_their_label`, van implementer-ovog `allowed_paths`) reprodukovan i popravljen od koordinatora nakon merge-a (`af6723d`) — preimenovan u `test_write_all_pages_screens_carry_real_content`, sada provjerava stvaran sadržaj (`BrightSmile Oral Care`/`Proljetna kolekcija`/`queue/retry`/`AI provajderi`) umjesto uklonjenog `"ACS-GUI-002"` placeholder markera. Koordinator nezavisno reprodukovao pytest (393 u izolovanom worktree-u minus gate-report subprocess artefakt, 425 na `main` post-merge)/ruff/mypy/import-boundaries. Live pywebview launch NIJE ponovljen za ovaj task pri merge-u (implementer je test-env bez display/webview modula; prethodni ACS-GUI-001 live-test je tada bio jedina live-launch evidencija). **Praznina zatvorena naknadno (2026-09-02, isti dan): Human Owner je live-pokrenuo aplikaciju i podijelio screenshot-e svih 5 ekrana — koordinator ih uporedio protiv `DEFAULT_FIXTURE`, sve tačno, stilizovano, bez grešaka** (vidi entry na vrhu fajla). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-009 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `4a7d643` (`--no-ff` u `5134b4c`, branch `task/ACS-F1-009-campaign-brief-plan-generation`). A9 — `CreateCampaign` (validira `CampaignBriefInput` → `map_campaign_brief` → atomic persist brief+DRAFT campaign) + `GenerateCampaignPlan` (učitava Campaign/BrandSnapshot/CampaignBrief → `LEAD_GENERATION_V1` template → `PromptRepositoryPort.get("campaign_plan","1")` → `AIRequest` → `TextGenerationPort.generate` → `validate_campaign_plan_output` + deterministička domain validacija (bez duplikata tema, min. 2 distinktne role kad ima ≥2 itema, implementer dokumentovao prag) → atomic persist plan + `Campaign.status→PLAN_GENERATED`). Oba use-case-a zavise samo od portova + lokalnog `_UnitOfWork` Protocol-a (isti obrazac kao ACS-F1-007). Dodao TAČNO jednu aditivnu metodu `CampaignRepositoryPort.get_brief()` + SQLite implementaciju (`_brief_from_row`) — koordinator line-by-line diff-ovao `ports/repositories.py`, potvrđeno da nijedna postojeća metoda nije dirana. Integration test `test_end_to_end_fixture_to_plan` lanči `LoadBrandFixture` → `CreateCampaign` → `GenerateCampaignPlan` zajedno na pravoj SQLite bazi — prvi pravi cross-task end-to-end dokaz. Atomicity za oba use-case-a testirana mid-failure na pravoj bazi (`save_campaign` failuje nakon uspješnog `save_plan`/`save_brief` → sve rollback-uje). Koordinator nezavisno reprodukovao pytest (439 u izolovanom worktree-u, 452 na `main` post-merge)/mypy/import-boundaries (16) čisti; whole-repo `ruff check .` i `generate_phase0_gate_report.py` trenutno kontaminirani MiniMax-ovim necommit-ovanim scratch fajlovima (van scope-a ovog taska — vidi napomena na vrhu fajla), `ruff check src tests scripts` (tracked-only) čist. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-010 | **DONE — merged u main** | Claude | Codex (HIGH) | Merge commit `1de7423` (`--no-ff` u `faaa5d7`, branch `task/ACS-F1-010-social-post-payload-persistence`). Aditivno `ContentPiece.payload: SocialPostPayload \| None = None` (jedno trailing polje) + prva `ALTER TABLE` migracija u projektu (`resources/migrations/0003_content_payload.sql` — `content_pieces.payload_json TEXT`, nullable) + `SqliteContentRepository` read/write proširen. Zatvara persistence gap dokumentovan u ACS-F1-006 (ContentPiece nije imao mjesto za stvaran generisan post) koji bi inače blokirao ACS-F1-011. **Netipičan implementer**: Claude (Human Owner odluka) — pošto je Claude i koordinator i implementer na ovom tasku, review NIJE mogao biti "Claude-only" (Implementer != reviewer) — umjesto toga Codex je uradio jedinu review rundu, `PASS_WITH_NOTES`, bez blocking findings, plus SVOJA nezavisna adversarial provjera (scratch DB samo sa 0000-0002, potvrda da `payload_json` ne postoji, pa primjena 0003, potvrda da se pojavljuje, pa `payload=None` vs namjerno prazan `SocialPostPayload` — oba ostaju semantički različita nakon round-trip-a). Finalni decision packet: `agent_reports/2026-09-02-ACS-F1-010-final-decision-packet.md`. Human Owner odobrenje: "Odobravam". Post-merge gate: 455 testova (scoped `ruff check src tests scripts` čist — whole-repo `ruff`/gate-report i dalje kontaminirani MiniMax-ovim necommit-ovanim scratch fajlovima, nepovezano sa ovim taskom), mypy čist, boundaries (16) čisti. Worktree uklonjen (clean). |
| ACS-F1-011 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `1c28789` (`--no-ff` u `13d5b3a`, branch `task/ACS-F1-011-allowed-facts-post-generation`). A11 — `select_allowed_facts` (deterministički, samo `is_fact_usable` fact-ovi, case-insensitive lexical substring matching protiv `facts_needed`, prazan `facts_needed` → prazan set, nije greška) + `claim_validator` (plan sekcija 35 TAČNO, ne 36 — FACT claim treba postojeći+usable+dozvoljen fact_id → `VERIFIED_BY_FACT`, inače `UNSUPPORTED` sa reason code-om `missing-fact-id`/`fact-not-found`/`fact-not-approved`/`fact-not-offered`; CTA/OPINION/CREATIVE → uvijek `NON_FACTUAL`) + `GenerateSocialPost` (učitava Campaign/Plan/CampaignItem in-memory pretragom kroz `plan.items`/BrandSnapshot/facts → `post_generation` prompt → `AIRequest` → AI poziv → `SocialPostGenerationOutput.model_validate` (Pydantic greška PRIJE perzistencije) → claim-po-claim validacija → interim `ContentStatus` pravilo TAČNO kako je kontrakt specificirao (bilo koji `UNSUPPORTED` → `NEEDS_REVIEW`, inače `GENERATING`, NIKAD `DRAFT`) → atomic persist `ContentPiece` sa `payload`-om iz ACS-F1-010). Zavisi samo od portova + lokalnog `_UnitOfWork` Protocol-a — koordinator potvrdio bez `channels`/`ai_registry` importa (`grep` sweep). Integration test lanči `LoadBrandFixture` → `CreateCampaign` → (ručno sastavljen plan, plan generation već pokriven ACS-F1-009) → `GenerateSocialPost` na pravoj SQLite bazi sa pravim fact-om iz `brightsmile.json`, PLUS bonus atomicity test (mid-persist failure na `save_content_piece` ostavlja `content_pieces` praznim — nije bio formalno tražen acceptance kriterijum za single-write use-case, implementer ga ipak dodao). Koordinator nezavisno reprodukovao pytest (458 u izolovanom worktree-u, 471 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (3 core fajla + 4 test fajla) i git status scope (sve novo, ništa van `application/posts/`+testovi). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). **A11 gotov — campaign plan I social post generation sad oba postoje end-to-end nad mock AI adapterom, isti obrazac spreman za A8 (live provider) kad god se odluči da ide.** |
| ACS-F1-012 | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `a4baeed` (`--no-ff` u `4218750`, branch `task/ACS-F1-012-claim-linter-status`). "A12 dio 1" — `claim_linter.py` (data-driven pravila iz `resources/claim_rules/default_v1.yaml`) primijenjen na SVAKI claim bez obzira na trenutni status: prohibited/riskantan termin (case-insensitive substring) → `PROHIBITED` + `prohibited-claim` reason (nadjačava ČAK i `VERIFIED_BY_FACT` — riskantan jezik ostaje riskantan i kad je fact-backed); numeric signal (cijena/postotak/trajanje/datum/goli broj, provjereno tim redoslijedom) na claim koji NIJE već `VERIFIED_BY_FACT` → `UNSUPPORTED` sa odgovarajućim reason code-om. `derive_content_status.py` (čista funkcija) — bilo koji `PROHIBITED`/`UNSUPPORTED` → `NEEDS_REVIEW`, inače `DRAFT`, nikad `APPROVED`. Prežicao `GenerateSocialPost` (ACS-F1-011) — zamijenio interim `GENERATING`/`NEEDS_REVIEW` logiku ovom finalnom; ažurirao POSTOJEĆE ACS-F1-011 testove (happy path `GENERATING`→`DRAFT`, nije ih oslabio/obrisao) + dodao novi regression test (`test_prohibited_claim_yields_needs_review`) koji dokazuje da `PROHIBITED` stvarno nadjačava fact-backed claim end-to-end kroz cijeli use-case, ne samo u izolovanom linter unit testu. Sekcija 38 (Content revisions) namjerno van scope-a — ide u budući ACS-F1-013. Koordinator nezavisno reprodukovao pytest (472 u izolovanom worktree-u, 485 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (linter, status derivacija, rewiring diff, oba nova + oba ažurirana test fajla) i git status scope (`select_allowed_facts.py`/`claim_validator.py`/`domain/` potvrđeno netaknuti). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-014 | **DONE — merged u main** | Crush | Claude (MEDIUM) | Merge commit `f230db0` (`--no-ff` u `6aec5ca`, branch `task/ACS-F1-014-campaign-plan-editing`). "A10" (plan-numeracija, ne task-ID ACS-F1-010) — `EditCampaignPlan` (pozivalac šalje cijelu novu listu itema; stari DRAFT→SUPERSEDED, novi→DRAFT `version+1`, atomično; editovanje APPROVED/SUPERSEDED odbijeno) + `ReorderCampaignItem` (validira permutaciju, `order→1..N`, delegira na `EditCampaignPlan` — DRY potvrđen čitanjem) + `ApproveCampaignPlan` (`CampaignPlan→APPROVED` + `Campaign→PLAN_APPROVED` atomično). Implementer dizajn odluka: svaki item nove verzije dobija SVJEŽ id (`campaign_items.id` je globalni PRIMARY KEY, stari SUPERSEDED plan drži stare id-e — reuse bi pucao na constraint) — dobro uočeno, jasno dokumentovano, koordinator nezavisno potvrdio protiv migracije. `generate_social_post.py` NIJE diran (poznat gap, namjerno van scope-a da se izbjegne konflikt sa ACS-F1-012). Koordinator nezavisno reprodukovao pytest (499 u izolovanom worktree-u, 512 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod (3 use-case fajla + 5 test fajlova, uključujući 2 prava atomicity testa na SQLite bazi). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| FLOW-1000 — Plan-approved guard u GenerateSocialPost | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `92d2b0c` (`--no-ff` u `1e16b1a`, branch `task/FLOW-1000-plan-approved-guard`). Prvi task pod novom `FLOW-NNNN` šemom (§31). Jedna guard klauzula: `GenerateSocialPost.execute()` odbija plan koji nije `APPROVED` (`InvariantViolation`, prije `campaign_item` pretrage/AI poziva/perzistencije) — zatvara poznat gap iz ACS-F1-014. Postojeći happy-path testovi ažurirani na `APPROVED` fixture (nisu oslabljeni); novi negativni testovi dokazuju `ai_port.calls == []` za DRAFT/SUPERSEDED plan (unit) + nula persistovanih `content_pieces` (integration, prava SQLite baza). Koordinator nezavisno reprodukovao pytest (502 u izolovanom worktree-u, 516 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao cio diff. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| FLOW-1001 — Content revisions (ReviseContentPiece) | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit `01be5c9` (`--no-ff` u `0d2630b`, branch `task/FLOW-1001-content-revisions`). Poslednji dio A12 plan-grupe (plan sekcija 38). `RevisionType` (10 vrijednosti, aditivno u `domain/content/revisions.py`) + `ReviseContentPiece` — partial-field revizija preko `RevisionOutput.changed_fields` (podskup dozvoljene mape po `revision_type`, inače `InvariantViolation` PRIJE perzistencije), claims ponovo lintovane ne regenerisane, `APPROVED` post uvijek → `NEEDS_REVIEW` (kodifikuje `ContentPiece` docstring invarijantu), `NEW_VISUAL_DIRECTION` odbijen bez AI poziva. Implementer preskočio eksplicitan `null` na promijenjenom polju umjesto da postavi `None` na tipiziran `str` field — spriječio type-violation koju bi doslovan kontrakt pseudokod izazvao. Prva stvarna upotreba `RevisionRepositoryPort`/`SqliteRevisionRepository` (ACS-F1-006, do sad nekorišteni). Koordinator nezavisno reprodukovao pytest (515 u izolovanom worktree-u, 529 na `main` post-merge)/ruff/mypy/import-boundaries (16) čisti, pročitao sav kod. MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). |
| ACS-F1-015 — Provider config + model selection persistence (A8, dio 1) | **DONE — merged u main** | Pi | Claude (MEDIUM) | Merge commit (`--no-ff` u `bb13f53`) + re-export commit `cabe1c6`, branch `task/ACS-F1-015-provider-config-persistence`. `ProviderConfig`/`ModelSelection` dataclass-e + `ProviderConfigRepositoryPort`/`ModelSelectionRepositoryPort` (`@runtime_checkable`) + `SqliteProviderConfigRepository`/`SqliteModelSelectionRepository` nad VEĆ POSTOJEĆIM P0 tabelama (`provider_configs`/`model_selections`, nema nove migracije, nula koda ih koristilo do sad). `credential_ref` striktno string referenca, potvrđeno bez `ports/secrets.py`/`infrastructure/secrets/` importa. `bool` kolone stvarno round-trip-uju kao `bool`. Koordinator nezavisno reprodukovao pytest (529 u izolovanom worktree-u, 543 na `main` post-merge)/ruff/mypy/import-boundaries (16)/`check_no_secrets.py` čisti, pročitao sav kod, dodao re-export u `repositories/__init__.py` (van implementer `allowed_paths`, isti obrazac kao ACS-F1-006). MEDIUM risk → Claude-only review → odmah merge po §29. Worktree uklonjen (clean). **ACS-F1-016 (OpenAI adapter, HIGH) je sad UNBLOCKED.** |
| ACS-HOTFIX-001 | **DONE — merged u main** | MiniMax | Codex, Claude (HIGH) | Merge commit `bcec979` (`--no-ff`, branch `hotfix/ACS-HOTFIX-001-job-event-ordering` @ `56a67d2`). Fix: `threading.Lock()` → `RLock()`, `CREATED` emit pomjeren unutar `submit()`-ovog lock bloka, `_emit()` sad drži lock kroz cio callback dispatch. Novi deterministički test (slow-callback adversarial probe) — dokazano da je probabilistički pristup propustio bug tri runde zaredom. Koordinator i Codex NEZAVISNO otkrili isti nalaz: fix ima redundantnu zaštitu (bilo koja dva od tri elementa su samostalno dovoljna) — ne defekt. Codex `PASS_WITH_NOTES`, bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-HOTFIX-001-final-decision-packet.md`. Human Owner approval: "Odobravam". Post-merge gate PASS na `main` (171 testova, ruff, mypy, health-check, 20x targeted loop čist) — **nakon ručnog ispravljanja `.pth`-a** koji je prvo pokazivao na uklonjeni worktree (vidi napomenu iznad). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-001 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `def4ea1` (`--no-ff`, task branch `task/ACS-P0-001-repo-foundation` @ `949d18c`). Reviews: Claude PASS, Codex PASS_WITH_NOTES (no blocking findings). Human Owner approval: "Odobravam". Post-merge gate PASS. Worktree uklonjen. |
| ACS-P0-002 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e187a56` (`--no-ff`, task branch `task/ACS-P0-002-config-boundaries` @ `d6dc783`). 5 review rundi: Codex REJECT×4 (BF-1: boundary-checker bypassi pa lexical/class-scope resolution bugovi), svaki fix nezavisno re-verifikovan od koordinatora (kombinovana adversarial reprodukcija do 11 bypass/scope oblika u finalnoj rundi), round 5 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-002-final-decision-packet.md` (READY FOR HUMAN APPROVAL, R1–R6 reziduelni rizici). Human Owner approval: "Slažem se". Post-merge gate PASS na `main` (43 testa, ruff, mypy, health-check, Python 3.14.1). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni, bez sadržajnog gubitka). |
| ACS-P0-003 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `e8c0a54` (`--no-ff`, task branch `task/ACS-P0-003-localization` @ `7df75c3`). 2 review runde: Codex REJECT×1 (BF-1..3: neuhvaćen `ValueError` na malformed template, non-string katalog vrijednost ruši translator, neuhvaćen `JSONDecodeError` u validatoru), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings (uključujući mixed valid/invalid-JSON edge case). Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-003-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (91 test, ruff, mypy, validate_resources, health-check). Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni). |
| ACS-P0-004 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `5ecf43f` (`--no-ff`, task branch `task/ACS-P0-004-channel-registry` @ `be3767a`). 3 review runde: Codex REJECT×2 (BF-1..3 pa BF-4, 4 stvarna nalaza — TypeError umjesto RegistryError, mutable "frozen" model, duplicate reference, `or []` falsy-scalar zamka), svaki fix nezavisno re-verifikovan od koordinatora, round 3 `PASS_WITH_NOTES` bez blocking findings. Crush nije predao nijedan self-report kroz cio task — sva evidence rekonstruisana od koordinatora. Finalni decision packet: `agent_reports/2026-08-31-ACS-P0-004-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (65 testova, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-005 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `c76eb9b` (`--no-ff`, task branch `task/ACS-P0-005-ai-registry-secrets` @ `2ff5f4e`). 2 review runde: Codex REJECT×1 (BF-1..3: secret leak kroz exception `__cause__`, env-var collision za nekanonska imena, modeli za nepoznatog providera), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-005-final-decision-packet.md`. Human Owner approval: "Odobravam". Trivijalan add/add merge konflikt na `infrastructure/__init__.py` (obje 005 i 006 kontrakte su nezavisno listale isti fajl — moja greška u allowed_paths disjoint provjeri za taj par) — riješen ručno, samo docstring razlika. Post-merge gate PASS na `main`. Worktree uklonjen (`--force`, samo Pi-jevi već-inkorporirani raw report fajlovi izgubljeni). |
| ACS-P0-006 | **DONE — merged u main** | Crush | Codex, Claude | Merge commit `298bbd3` (`--no-ff`, task branch `task/ACS-P0-006-sqlite-foundation` @ `8d45167`). 2 review runde: Codex REJECT×1 (BF-1/2: UoW re-use nakon commit-a onemogući rollback, migration runner rollback-uje caller-owned transakciju kad BEGIN padne), fix nezavisno re-verifikovan od koordinatora, round 2 `PASS_WITH_NOTES` bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-006-final-decision-packet.md`. Human Owner approval: "odobravam". Post-merge gate PASS na `main` (104 testa, ruff, mypy, health-check). Worktree uklonjen (clean, bez force-a). Usput: `.codex_tmp/` scratch fajl Codex-a je nakratko interferisao sa `ruff check .` (nije gitignored) — nestao je sam prije nego što je trebalo trajno rješenje, nije naš kod. |
| ACS-P0-007 | **DONE — merged u main** | Pi | Codex, Claude | Merge commit `1071eff` (`--no-ff`, task branch `task/ACS-P0-007-jobs-presentation-bootstrap` @ `c553379`). Scope: P0.20–P0.23 (Jobs + Presentation contracts + Bootstrap wiring). Tri Codex REJECT/REJECT/PASS_WITH_NOTES runde: BF-1 (submit-after-shutdown orphan job), BF-2 (dynamic-import guard bypass), R2-BF-1 (queued job trajno PENDING nakon shutdown-cancellation) — sva tri nalaza nezavisno reprodukovana od koordinatora PRIJE svake fix-runde I nezavisno reverifikovana POSLIJE (uključujući reprodukciju Codex-ovog 100-job concurrent submit/shutdown stress probe-a). Codex round 3: PASS_WITH_NOTES, bez blocking findings. Finalni decision packet: `agent_reports/2026-09-01-ACS-P0-007-final-decision-packet.md`. Human Owner approval: "Odobravam". Post-merge gate PASS na `main` (170 testova, ruff, mypy, oba health-check entrypointa, Python 3.14.1). Čist merge, bez konflikta. Jedan prihvaćen non-blocking rezidual (double-indirection dynamic-import bypass u presentation guardu, eksplicitno van scope-a po Codex-ovoj preporuci). Worktree uklonjen (clean, bez force-a). |
| ACS-P0-008 | **DONE — merged u main — POSLJEDNJI P0 TASK, P0-GATE = PASS** | MiniMax | Codex, Claude (HIGH) | Merge commit `aef1b0d` (`--no-ff`, task branch `task/ACS-P0-008-validators-ci-security-gate` @ `5774303`). Tok: Codex round 1 REJECT (BF-1 scanner self-poisoning, BF-2 raw-value leak) → fix round 1 → Codex round 2 `PASS_WITH_NOTES` → BF-3 (secret scanner provider-coverage gap, Google/OpenRouter propust, flagovano iz eksterne analize, empirijski potvrđeno) + `_KEY_VALUE` character-class bug (MiniMax sam otkrio) → Codex round 3 `PASS_WITH_NOTES`, bez blocking findings. Svaki nalaz kroz sve tri runde nezavisno potvrđen od koordinatora DRUGAČIJOM probom od implementera/Codex-a. Finalni decision packet: `agent_reports/2026-09-02-ACS-P0-008-final-decision-packet.md`. Human Owner approval: "Merdžuj, komituj i pušuj na github". Post-merge gate PASS na `main` (217 testova, ruff, mypy, validate_resources, check_no_secrets, health-check, 10x race-stress loop čist) — `.pth` provjeren prije verifikacije (lekcija iz ACS-HOTFIX-001). Gate report regenerisan protiv stvarnog merge-ovanog main-a: `status: PASS`, svih 17 checkova `true`. Worktree uklonjen (`--force`, samo LF/CRLF whitespace artifact, bez sadržajnog gubitka). |

## Paralelizacija — trenutna provjera

Drugi paralelni par (ACS-P0-005 + ACS-P0-006, pokrenut 2026-09-01) je uspješno završen — oba
merged (006 prvo, pa 005), sa jednim trivijalnim add/add merge konfliktom na
`infrastructure/__init__.py` (obje kontrakte su nezavisno listale isti `__init__.py` u
`allowed_paths` — propust u disjoint provjeri za ovaj par, upisan kao lekcija za naredne
paralelne parove: provjeriti i package `__init__.py` fajlove, ne samo "glavne" module fajlove).
ACS-P0-007 je sada jedini kandidat — nema drugog unblocked P0 taska za paralelizam trenutno.

## Poznati blokatori

- **PROCES-GREŠKA (koordinator, 2026-09-02): CI status na task branch push-ovima
  nije bio redovno provjeravan tokom review ciklusa, pa je slomljen `ci.yml` prošao
  nezapaženo kroz cijeli ACS-P0-008 review (Claude, Codex x3 runde) i merge.**
  Uzrok: ACS-P0-008 je proširio `ci.yml` health-check korakom koji je koristio bash
  heredoc (`python - <<'PY' ... PY`) UNUTAR uvučenog YAML block scalar-a
  (`run: |`). Heredoc terminator linija je naslijedila YAML uvlačenje, pa nikad nije
  tačno odgovarala bash-ovom zahtjevu da `<<'PY'` terminator bude na početku linije
  bez uvlačenja — GitHub Actions je odbijao da parsira CIJELI workflow fajl (0 job-ova,
  "likely failed because of a workflow file issue") na SVAKOM push-u od trenutka kad
  je ta izmjena landovala (task branch, ACS-HOTFIX-001 merge, ACS-P0-008 merge — svi
  crveni, svi neprimijećeni). Otkriveno tek nakon P0-008 merge-a kad je koordinator
  eksplicitno provjerio `gh run list` post-merge. Popravljeno (`95a799f`): uklonjena
  fragilna heredoc/env-var mašinerija, zamijenjena postojećim, već testiranim
  `python -m ai_campaign_studio.main --health-check` entrypoint-om (GitHub Actions
  runner je svježa, jednokratna VM — default `platformdirs.user_data_dir` je
  bezbjedan za pisanje, temp-dir override nikad nije bio stvarno potreban u CI-ju).
  Dodan `.gitattributes` (`text eol=lf` za `.github/workflows/*.yml` i `*.sh`) kao
  dodatna zaštita, iako CRLF nije bio stvaran uzrok ovog konkretnog problema (commit-ovan
  blob je već bio LF — autocrlf je uticao samo na lokalno radno stablo).
  **Lekcija za ubuduće**: nakon SVAKOG push-a na task branch ili main, provjeriti
  `gh run list --branch <branch> --limit 1` kao dio standardne verifikacije — ne
  samo na "značajnim" merge-ovima. Heredoc unutar YAML `run: |` bloka je generalno
  fragilan obrazac — izbjegavati ga, koristiti zaseban script fajl ili `python -c`
  jednolinijski poziv umjesto toga.
- **GitHub push protection hvata secret-shaped demo vrijednosti u evidence reportima.**
  Kad `agent_reports/*.md` dokumentuje "before" reprodukciju secret-scanner nalaza
  (npr. `check_no_secrets.py` fix-round evidence), literal poput
  `sk-abcdefghijklmnopqrstuvwxyz123456` je dovoljno key-shaped da GitHub-ov vlastiti
  secret scanning push protection blokira push, iako je fajl van scope-a našeg
  `check_no_secrets.py` (koji isključuje `*.md`). Rješenje: u evidence reportima
  koristiti eksplicitno EXAMPLE-markirane placeholder vrijednosti
  (`sk-EXAMPLE-abcdefghijklmnopqrstuvwxyz`) umjesto punih key-shaped literala, čak i
  kad demonstriraš da je fix "prije" hvatao takav string. Otkriveno na ACS-P0-008
  BF-3 fix rundi (2026-09-01) — push odbijen, ispravljeno squash-ovanjem commit-a sa
  ispravljenim tekstom prije ponovnog push-a.
- Proces-learning iz ACS-P0-002: Claude-ov arhitekturni review dao je PASS na
  `test_import_boundaries.py` provjeravajući samo direktne/alias/uslovne import oblike; Codex je
  istim testom otkrio da relative import, dynamic `importlib`/`__import__` sa literal stringom, i
  case-sensitivity bug (`Flask` vs `flask`) prolaze neopaženo. Za buduće boundary/invariant reviewe
  (ACS-P0-003+): Claude mora eksplicitno probati relative importe, dynamic import pozive, i
  case/naming varijante stvarnih modula, ne samo "direct import + alias + conditional" obrazac.
- Ova (koordinator) sesija nema direktan CLI pristup pravim Codex/Crush/Pi alatima — koordinator
  priprema worktree, branch i eksplicitna uputstva (Task Contract); Human Owner pokreće
  implementer/reviewer agente eksterno i javlja rezultat/diff nazad koordinatoru. Za ACS-P0-001 je
  ovaj obrazac funkcionisao (Codex review dobijen i verifikovan).
- `.agent/GITNEXUS_PROTOCOL.md` §9 i workflow §19 referenciraju `npx gitnexus check --cycles --repo .`
  — ta komanda ne postoji u instaliranoj GitNexus CLI verziji (`unknown command 'check'`; stvarne
  komande vidi `npx gitnexus --help`). Cycle-check korak je preskočen post-merge gate-u za ACS-P0-001
  (nebitno za 3 fajla bez međuzavisnosti). Treba ažurirati protokol dokument na stvarne CLI komande
  prije nego što cycle-check postane bitan (ACS-P0-002+, kad se uvode moduli sa međuzavisnostima).
- `scripts/coordination.py` (claim/status/release) još ne postoji. Do sada nije bio problem (uvijek
  samo jedan unblocked task). Postaje relevantno ako se 003–006 pokrenu paralelno.
- GitNexus `detect-changes`/`context`/`impact` binduju se na registrovani glavni checkout, ne na
  linked worktree (`--repo .` iz worktree-a vraća "Repository not found"; iz glavnog checkout-a
  vraća diff glavnog radnog stabla, ne task branch-a). Potvrđeno i od implementera (Pi, ACS-P0-002)
  i od koordinatora — nije izolovan slučaj. `gitnexus_impact` se za MEDIUM/HIGH taskove trenutno
  mora tretirati kao `UNKNOWN` i kompenzovati ručnim diff/file review-om (kao za ACS-P0-002), ne kao
  "nema impacta". Riješiti prije nego što broj paralelnih worktree-ova poraste (ACS-P0-003..006).
- Nekomitovane Performance/Analytics dopune (`AGENTS.md`, `CLAUDE.md`, `.agent/PROJECT_MAP.md`,
  `.agent/TASK_ROUTING.md`, dva nova plan dokumenta) postoje u radnom stablu, dodane iz druge
  sesije — nisu commit-ovane od strane koordinatora, ostavljene netaknute.

## Verification baseline

Uspostavljen na `main` poslije merge-a ACS-P0-008 — **P0-GATE = PASS** (2026-09-02, root `.venv`,
Python 3.14.1, `.pth` ručno provjeren/vraćen na main checkout — vidi napomenu iznad):

```text
import ai_campaign_studio          → OK (0.1.0)
python -m pytest -q                → 217 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 51 source files
python scripts/validate_resources.py → All resources are valid
python scripts/check_no_secrets.py   → NO CONFIRMED SECRET IN TRACKED FILES
python -m ai_campaign_studio.main --health-check → exit 0
python scripts/generate_phase0_gate_report.py → status: PASS, svih 17 checkova true
10x loop -k "event_sequence or event_ordering_under_slow" → 10/10 čisto
```

**Osvježeno na `main @ af6723d`** poslije merge-a ACS-F1-007 + ACS-F1-008 + ACS-GUI-002
(2026-09-02, isti `.venv`, `.pth` provjeren):

```text
python -m pytest -q                → 425 passed
python -m ruff check .             → All checks passed!
python -m mypy src                 → Success: no issues found in 108 source files
python scripts/validate_resources.py → All resources are valid
python scripts/check_no_secrets.py   → NO CONFIRMED SECRET IN TRACKED FILES
python -m ai_campaign_studio.main --health-check → status: ok
python scripts/generate_phase0_gate_report.py → status: PASS, svih 17 checkova true
```

## CI

`.github/workflows/ci.yml` postoji od 2026-08-31, prošireno u ACS-P0-008 (2026-09-01/02).
Pokreće `ruff check .` → `mypy src` → `pytest -q` → resource validation → no-secret scan →
health-check (izolovan temp data dir preko `AppPaths(data_dir_override=...)`, bez keyring/GUI/
network) na `push`/`pull_request` ka `main`, GitHub-ov Python 3.12 runner (donja granica iz
`requires-python`). Merge commit ACS-HOTFIX-001 (`bcec979`) i ACS-P0-008 (`aef1b0d`) oba zelena
na GitHub Actions. Ovo NE zamjenjuje ručnu post-merge gate provjeru koordinatora — i dalje ručno
pokretati pun set prije/poslije merge-a, CI je dodatna, ne jedina zaštita (npr. ne pokriva
`generate_phase0_gate_report.py` niti GitNexus korake).

## Repo na GitHub-u

`origin` = `https://github.com/Rade69/AI-Campaing-Studio` (javan repo). `main` i svi task branch-evi
(`task/ACS-P0-001..004`) se guraju poslije svake značajnije izmjene. Historija provjerena na
secrete prije prvog push-a (2026-08-31) — čisto.

## GitNexus index status

Reindeksirano poslije merge-a ACS-F1-007 + ACS-F1-008 + ACS-GUI-002:

```text
Indexed commit: af6723d (= trenutni main HEAD)
Status: up-to-date
6456 nodes | 8584 edges | 167 clusters | 71 flows
```

`mcp__gitnexus__*` MCP alati su dostupni u koordinator sesiji (pored CLI), ali dijele istu
worktree-binding limitaciju — vidi blokatore. Prije narednog pre-impact-a, ako main odmakne,
ponovo pokrenuti `npx gitnexus analyze --skip-agents-md` pa `npx gitnexus status`.

## Sljedeći task

**Cijeli campaign application-layer pipeline JE SAD U POTPUNOSTI GOTOV** — uključujući reviziju
posta, poslednji preostali komad plana za Faza 1 Vertical Slice: domain sloj (ACS-F1-001/002),
boundary schemas (ACS-F1-003/004), business persistence (ACS-F1-005/006), fixture load
(ACS-F1-007), prompt repository + AI port + mock adapter (ACS-F1-008), CreateCampaign +
GenerateCampaignPlan (ACS-F1-009), SocialPostPayload persistence (ACS-F1-010, HIGH),
GenerateSocialPost (ACS-F1-011), claim linter + status derivation (ACS-F1-012), plan editing/
versioning/approval (ACS-F1-014), plan-approved guard (FLOW-1000), content revisions
(**FLOW-1001**) svi merged u main (2026-09-02/03), 529 testova, sve zeleno. GUI paralelno: svih 5
sidebar ekrana takođe merged i **live-verifikovano od Human Owner-a**.

Tok: LoadBrandFixture → CreateCampaign → GenerateCampaignPlan → EditCampaignPlan/
ReorderCampaignItem/ApproveCampaignPlan → GenerateSocialPost (odbija ne-APPROVED plan) →
claim_linter/derive_content_status → finalan `ContentStatus` → **ReviseContentPiece** (partial
revizija, ponovo lintuje, `APPROVED`→uvijek `NEEDS_REVIEW`). Svaki korak atomičan, nezavisno
testiran, lančano integration-testiran preko pravih SQLite baza. Nema poznatih otvorenih gap-ova
u ovom pipeline-u. **A12 plan-grupa (Claim validator + linter + revisions) je time u potpunosti
gotova** — sekcije 35/36-37/38 sve implementirane preko tri odvojena taska.

**A8 dio 1 (ACS-F1-015) je GOTOV — ACS-F1-016 (OpenAI adapter, HIGH) je sad UNBLOCKED,
implementer TBD.** To je jedini trenutno spreman-za-rad kontrakt. Ostali kandidati, bez
kontrakta: **A13 — Visual System** (plan sekcije 39-41, `CampaignVisualSystem`/`LayoutSpec` —
otvorilo bi i `NEW_VISUAL_DIRECTION` revision tip koji FLOW-1001 namjerno odbija), **A15+ — ZIP
export/telemetry summary/A16 eval harness** (dalje niz plana). GUI dizajn iteracija (vidi ispod)
je paralelan, nezavisan trak — čeka MiniMax-ov trenutni popravak (u toku, dira `shared/`,
`screens/_static_pages.py`, `shell/__init__.py`, `static/`, novi `brand-logo.png` asset, Codex-ove
scratch probe skripte u root-u — koordinator i dalje ne dira ništa od toga dok se ne javi da je
gotovo). **ACS-GUI-003** (campaign workflow ekrani) sad ima kompletan application-layer pipeline
da ga stvarno poziva — realan kandidat čim GUI dizajn iteracija završi.

**VAŽNO za MiniMax/Codex (2026-09-03)**: `static/app.css` je upravo promijenjen u main-u kroz
ACS-GUI-004 merge (vidi "Zadnje ažurirano" gore) — sadrži NOVI density/spacing rewrite (odobren od
Human Owner-a). Vaš necommit-ovani `app.css` diff (isti tip density prepravke, ali drugačiji
brojevi) je superseded — kad nastavite rad, **pull-ujte main PRIJE nego što nastavite na
`app.css`** i rebase-ujte preko nove verzije, ne obrnuto. Vaš `.brand`/`.brand-logo` blok je već
ručno prenesen u merge-ovanu verziju (aditivan, nije se sudarao) — ne treba ga ponovo dodavati.
Ostali vaši necommit-ovani fajlovi (`shell/__init__.py`, `__main__.py`, `_static_pages.py`,
`docs/gui-v3/*`, `test_static_pages_generator.py`) nisu dirani i ostaju kako jesu.

## GUI dizajn — otvoreno pitanje (Human Owner feedback, 2026-09-02)

Human Owner nije zadovoljan trenutnim izgledom uprkos tome što je live-verifikacija (screenshot-i,
vidi gore) potvrdila da render radi ispravno: **paneli su nekonzistentni, pojavljuje se skrol
(cilj je "jedan pogled" bez skrolovanja), blizu smo mokapa ali ne na zamišljenom nivou.**
Dogovoreni pristup: **prvo iterirati na `docs/gui-v3` mokapima** (brzo, vizuelno, bez re-wiring
troška), tek onda prenijeti odobreni dizajn u `presentation_webview/`. **Trenutno na čekanju:**
MiniMax radi necommit-ovane popravke direktno u `presentation_webview/__main__.py` (window-state
persistencija, van formalnog task-sistema — vidi napomena na vrhu fajla) — koordinator čeka da
MiniMax završi prije nego što dirne bilo šta u `docs/gui-v3`/`presentation_webview/`, po
eksplicitnom zahtjevu Human Owner-a. Target veličina prozora za "bez skrola" cilj NIJE utvrđena
(pitanje ostalo otvoreno kad je razgovor skrenuo na "sačekajmo MiniMax-a").

Paralelno već u toku, van formalnog Faza 1 Task Contract sistema: **SPIKE-001** (pywebview UI,
`spike/pywebview-content-studio` grana) — MiniMax radi GUI prema mokapu.

**GUI mockup rekonsolidacija RIJEŠENA (2026-09-02).** `GUI-architecture/` direktorijum
(untracked, nepoznatog porijekla) je pročitan u cjelosti, sadržaj procijenjen kao kvalitetan
i usklađen sa zaključanim arhitektonskim odlukama (minimalan sidebar scope, Analytics guard
prisutan dva puta, Quick Actions + facts + compliance u Studiju, ispravna razlika između
postojećih `PresentationFacade` metoda i onoga što tek treba F1 contracte). **Human Owner je
eksplicitno potvrdio V3 kao kanonski GUI kandidat** — `mockup_proposal`/`mockup_proposal_v2`
iz SPIKE-001 grane ostaju samo referenca/exploration, nisu više kandidat za production wiring.
Paket je premješten iz untracked `GUI-architecture/` u trackovan **`docs/gui-v3/`**
(`README.md`, `V3_PLAN.md`, `INTEGRATION.md`, `screens/01_pocetna` … `09_podesavanja`,
`shared/app.css`, `shared/app.js`; redundantne root-nivo duplikate, `.zip` i
`phase0_foundation_gate.json` kopiju sam izbacio pri premještanju — originalni
`GUI-architecture/` direktorijum obrisan).

Dva gapa nađena nezavisnom provjerom HTML-a (nisu bila u README-u) su **POPRAVLJENA
(2026-09-02, commit `9f744ac`)** direktno u `docs/gui-v3/`, prije wiring-a:
1. Stepper "done" koraci (ekrani 04–08) su sada pravi `<a class="step done">` linkovi ka
   odgovarajućem ekranu, umjesto inertnih divova — usklađeno sa `V3_PLAN.md` tvrdnjom da
   stepper omogućava povratak. Dodano `[hidden]{display:none!important}` i
   `text-decoration:none` za `.step` u `shared/app.css`.
2. `screens/06_kalendar/index.html` (dvostruka uloga: globalni Kalendar iz sidebar-a I korak 3
   campaign workflow-a) sada ima query-param-driven campaign banner (`?campaign=...` iz
   `05_plan_kampanje` linka) — breadcrumb + stepper + "Nastavi → Studio sadržaja" dugme se
   pojave samo kad se stranica otvori sa tim parametrom; direktan pristup iz sidebar-a ostaje
   nepromijenjen (čist globalni pogled). Toggle logika je čisto prezentaciona (čita URL param,
   ne poziva business logiku) u `shared/app.js`.

**Sigurnosna politika za pywebview dodana (2026-09-02): `docs/PYWEBVIEW_SECURITY.md`.** Human
Owner je tražio maksimalno bezbjedan pywebview 6.2.1 setup. Istraženo protiv zvanične
dokumentacije (bez trenutnih CVE-ova). Najkritičniji nalaz: na Windows-u pywebview bez
eksplicitnog `gui='edgechromium'` tiho pada na `mshtml` (IE/Trident, deprecated, bez zakrpa)
ako WebView2 Runtime nije instaliran — mora se forsirati `edgechromium` i eksplicitno
detektovati odsustvo Runtime-a umjesto tihog downgrade-a. Dokument pokriva i debug/DevTools,
`js_api` allowlisting, CSP, eksterne linkove, storage/private_mode, i dependency pinning.
Referenciran kao obavezan read-set u `.agent/TASK_ROUTING.md` za svaki budući task koji dira
`presentation_webview/`/`js_api`.

## G9 — UI Framework Gate: ZATVOREN (2026-09-02)

Plan (`AI_Campaign_Studio_Faza_1_v1_4_...md` sekcija 3, G9) formalno traži uporedni
`pywebview vs PySide6` spike prije zaključavanja UI frameworka; AR5 (sekcija 4) eksplicitno
zabranjuje production `presentation_webview/`/`presentation_qt/` arhitekturu prije G9. SPIKE-001
je testirao SAMO pywebview (nikad nije rađen PySide6 spike). **Human Owner je eksplicitno
odlučio (2026-09-02) zatvoriti G9 bez PySide6 poređenja** — obrazloženje: pywebview je već
dokazan kroz SPIKE-001 (BHS layout robustan, real desktop window radi, Windows nativni chrome),
i sada postoji `docs/PYWEBVIEW_SECURITY.md` hardening politika. **UI framework je zaključan:
pywebview.** `presentation_webview/` production wiring je od ovog trenutka dozvoljen (prvi
task: ACS-GUI-001, MiniMax, GUI-BASE shell). Ovo NE poništava potrebu da se
`docs/PYWEBVIEW_SECURITY.md` politika primijeni od prvog reda tog koda.

Sljedeći koraci za GUI: kad se A4+ application/use-case slojevi za Brand/Campaign pojave, otvoriti
formalni lightweight task (van Task Contract sistema, po uzoru na SPIKE-001, ili kao pravi F1
contract — odlučiti tada) za wiring `docs/gui-v3/` u `presentation_webview/` po strukturi iz
`INTEGRATION.md`.
