# → ZA CODEX — ACS-GUI-008 adversarial review

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-06

Treći HIGH-risk bridge task (nakon ACS-GUI-005/007). Prvi put da GUI klik
poziva `ApproveCampaignPlan` + `GenerateSocialPost` (stvarna promjena
stanja plana + stvaran AI poziv + stvaran DB write, N puta u jednoj
petlji — ne jednom kao ranije bridge metode).

## Šta pregledati

```text
agent_reports/ACS-GUI-008-task-contract.md
agent_reports/2026-09-06-ACS-GUI-008-minimax.md (originalna implementacija)
agent_reports/2026-09-06-ACS-GUI-008-fix-brief-za-minimax.md (moj review nalaz)
agent_reports/2026-09-06-ACS-GUI-008-fix-evidence.md (implementer-ov fix)
PR: https://github.com/Rade69/AI-Campaing-Studio/pull/4

src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  (nova generate_campaign_content metoda, ~150 linija; izmijenjen
  create_campaign_and_generate_plan da vraća plan_id)
src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py
src/ai_campaign_studio/presentation_webview/static/app.js
  (generateContent handler + saveAndPlan navigacija sa &plan=)
src/ai_campaign_studio/presentation/contracts.py
src/ai_campaign_studio/presentation/ui_models.py
  (GenerateContentResultUiModel — provjeri NEMA api_key polje;
  CampaignPlanResultUiModel dobio novo plan_id polje)
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
tests/unit/presentation_webview/test_studio_sadrzaja_ssr.py
tests/unit/presentation/test_ui_models.py
tests/unit/presentation/test_contracts.py
```

Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-008-studio-sadrzaja-generate`
Branch: `task/ACS-GUI-008-studio-sadrzaja-generate`

## Kontekst koji možda nije očigledan iz koda

- **Originalna implementacija je koristila sirov SQL** u bridge-u da
  nađe "trenutni plan kampanje" (`ports/` je bio u `forbidden_paths`).
  Ja sam to odbio i tražio čist fix: `create_campaign_and_generate_plan`
  sad vraća `plan_id` (novo polje na već-mergovanom
  `CampaignPlanResultUiModel`, ACS-GUI-005), `app.js` ga pamti i
  proslijeđuje, `generate_campaign_content` sad koristi
  `CampaignRepositoryPort.get_plan(plan_id)` + cross-check
  `plan.campaign_id == campaign_id`. **Nezavisno sam mutation-testirao
  taj cross-check** (privremeno uklonio ga u kodu, potvrdio da test
  `test_generate_content_plan_id_does_not_belong_to_campaign` STVARNO
  padne sa DRUGAČIJIM error code-om, vratio kod) — molim te ipak
  nezavisno provjeri, ne uzimaj moj nalaz zdravo za gotovo.
- **GitNexus impact** (ja sam pokrenuo): `ApproveCampaignPlan`,
  `GenerateSocialPost`, `CampaignBridgeApi` — sve LOW risk, jedini
  postojeći pozivaoci su `run_system_b.py` (evaluation harness) i
  `__main__.py` (bridge konstrukcija). Nula neočekivanih.
- **Poznat, PRED-POSTOJEĆI (ne uveden ovim taskom) gap**: implementer je
  otkrio da `plan_kampanje → kalendar → studio_sadrzaja` navigacioni
  lanac NE prenosi `?campaign=`/`&plan=` query stringove kroz sve
  korake (`plan_kampanje`-ov link na `kalendar` čak koristi statičan
  fixture string, ne pravu vrijednost — vidi
  `presentation_webview/screens/plan_kampanje/__init__.py:139`). To
  znači da korisnik koji ide kroz PRIRODNU navigaciju danas NEĆE
  stići do Studio sadržaja sa `plan_id` u URL-u (dugme ostaje legacy
  toast stub). Ovo je van `allowed_paths` ovog taska (te screen fajlove
  ACS-GUI-008 ne smije dirati) i biće poseban follow-up task. NIJE
  regresija ovog taska — provjeri da li se slažeš da je ispravno
  tretirati ga kao odvojen scope, ne blocker za ovaj PR.

## Posebno fokusiraj (iz task contracta, "Review focus — Codex")

- **Partial-failure putanja ne ostavlja bazu nekonzistentnom.** Ako
  `ApproveCampaignPlan` uspije ali PRVI `GenerateSocialPost` poziv
  pukne — je li plan trajno APPROVED sa 0 pieces, i da li idempotentni
  re-click ispravno nastavlja odatle (ne re-approve, ne duplikat)?
  Provjeri i granični slučaj: šta ako se aplikacija ugasi TAČNO između
  approve-a i prve generacije (nema transakcije preko oba koraka —
  implementer je ovo sam priznao u §9 "Preostali rizici").
- **Idempotentnost pod concurrent klikovima** — da li dvoklik na
  dugme (prije nego se `button.disabled` postavi) može pokrenuti DVA
  paralelna `generate_campaign_content` poziva koja oba prođu
  `list_campaign_content` pre-check PRIJE nego ijedan upiše prvi piece
  (race na read-then-write, ne na SQL nivou)? Bridge nema
  transakciono zaključavanje oko cijele petlje.
- **Secret safety** — `test_generate_content_carries_no_api_key_in_result`
  i `test_generate_content_result_carries_no_api_key_field` postoje;
  provjeri STRUKTURNO (ne samo test-tvrdnjom) da li ijedan error-put u
  `generate_campaign_content` MOŽE uključiti `str(exc)` od AI adapter
  poziva u `error_message` (implementer tvrdi da NE — "no API key is
  u adapter's exception text" — provjeri da li je to STVARNO
  garantovano za SVE trenutno postojeće adaptere, ne pretpostavka).
- **`_targets_from_brief`/`_target_for_item` duplikacija** naspram
  `run_system_b.py:86` — pinovano jednim testom
  (`test_generate_content_round_robin_assignment_matches_run_system_b`),
  ALI taj test pokriva samo 1 target/3 iteme (mod uvijek 0). Provjeri
  ručno da li je `targets[index % len(targets)]` logika STVARNO
  identična za slučaj VIŠE targeta (npr. 2 targeta, 3 iteme → 0,1,0) —
  kod izgleda ispravno, ali test ne dokazuje taj slučaj.
- **`plan.status is CampaignPlanStatus.DRAFT` provjera prije approve —
  provjeri `SUPERSEDED` granu specifično.** `CampaignPlanStatus` ima
  TRI vrijednosti: `DRAFT`/`APPROVED`/`SUPERSEDED` (potvrđeno u
  `domain/campaign/enums.py`). Bridge kod trenutno radi: ako DRAFT →
  approve; ZA SVAKI DRUGI STATUS (uključujući `SUPERSEDED`) → tretiraj
  kao "već odobreno, samo generiši". Ali `SUPERSEDED` znači "ova verzija
  plana je zamijenjena novijom" (`edit_campaign_plan.py` postavlja
  stari plan na `SUPERSEDED` kad napravi novu verziju) — generisanje
  sadržaja za SUPERSEDED plan bi bilo generisanje za ZASTARJELU verziju
  plana, ne trenutnu. `EditCampaignPlan` NIJE danas povezan nigdje u
  GUI-ju (potvrđeno grep-om), pa je ovo TRENUTNO nedostižno u praksi —
  ALI provjeri da li bridge kod treba EKSPLICITNO odbiti `SUPERSEDED`
  (ne tiho ga tretirati kao "OK, generiši") da se ne ostavi tiha zamka
  za dan kad neko poveže plan-editing u GUI.

## Kad završiš

Standardan format (verdict/scope/acceptance/architecture/security/tests
YAML header + narativ). Ako PASS/PASS_WITH_NOTES bez blokirajućih
nalaza, ovo ide direktno na Human Owner odobrenje (HIGH risk, ne §29
skraćeni put).
