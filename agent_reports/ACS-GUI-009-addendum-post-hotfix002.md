# ACS-GUI-009 — addendum nakon HOTFIX-002/GUI-008 (2026-09-07)

Za implementera koji nastavlja ACS-GUI-009 (worktree
`H:\ai-campaign-studio-worktrees\ACS-GUI-009-pregled-izvoz-export` --
i dalje na starom, necommit-ovanom stanju baziranom na `a758408`,
PRIJE HOTFIX-002 i PRIJE GUI-008).

## Zašto addendum, ne samo "rebase"

Main se od `a758408` promijenio strukturno u `bridge/__init__.py`:

1. **ACS-HOTFIX-002**: `self._campaign_repo` itd. VIŠE NISU instance
   atributi postavljeni jednom u `__init__` -- sad su `@property`
   getter-i koji čitaju iz `ContextVar`-om vezanog `_CallResources`
   objekta, postavljenog svježe po pozivu preko `@_with_call_resources`
   dekoratora + `_resource_scope()` context managera. Svaki javni
   `js_api` metod MORA imati `@_with_call_resources`.
2. **ACS-GUI-008**: `create_campaign_and_generate_plan` sad vraća
   `plan_id` direktno u `CampaignPlanResultUiModel` (novo polje);
   `app.js`-ov `saveAndPlan` ga prosljeđuje dalje kroz `&plan=` query
   string; resource-lifecycle greške se mapiraju preko
   `_LIFECYCLE_ERROR_MAPPERS`/`_LIFECYCLE_ERROR_MESSAGES` dict-a (po
   imenu metode), ne hardkodovanog if/elif-a; produkcijski static HTML
   MORA uvijek emitovati live dugme (hidden po default-u) jer
   `write_all_pages()` ne prosljeđuje fixture sa runtime id-evima --
   `app.js`-ov boot IIFE (koji čita `?campaign=`/`?plan=`) ga otkriva.

Zbog ovoga, git rebase tvog postojećeg diff-a bi udario u konflikte
kroz SKORO CIJELU `CampaignBridgeApi` klasu (mijenja se oblik
pristupa repo-ovima na svakom mjestu). **Ne pokušavati automatski
rebase.** Umjesto toga:

## Šta raditi

1. Napraviti NOV worktree/branch od TRENUTNOG main-a
   (`task/ACS-GUI-009-pregled-izvoz-export-v2` ili slično).
2. Tvoj POSTOJEĆI necommit-ovan `export_campaign_package` je DOBAR
   materijal za PONOVNU UPOTREBU (ne baciti) -- struktura koraka
   (učitaj plan → idempotentan visual system → per-post layout petlja
   sa partial-failure toleracijom → `ExportCampaign` poziv) ostaje
   ISPRAVNA. Samo se MEHANIKA pristupa repo-ovima/greškama mijenja.
   Kopiraj logiku ručno u novi fajl, prilagodi na novi obrazac ispod.
3. **Ukloniti `campaign-routes.json`/`_record_campaign_plan`/
   `_get_campaign_plan` u potpunosti.** Više nije potrebno -- GUI-008
   je već riješio "kako export zna koji je plan kampanje" na čist
   način: `create_campaign_and_generate_plan` VEĆ vraća `plan_id`,
   `app.js` ga VEĆ prosljeđuje kroz URL. `export_campaign_package`
   treba primiti `plan_id` DIREKTNO u payload-u (isti obrazac kao
   `generate_campaign_content`), NE ga tražiti preko cache fajla.
4. **Visual-system idempotentnost** (`_get_cached_visual_system`/
   `_record_campaign_visual_system`) -- `VisualRepositoryPort` NEMA
   "get by plan_id" upit (samo `get_visual_system(visual_system_id)`
   po sopstvenom id-u), pa NEKI mehanizam i dalje treba. Zamijeni JSON
   fajl sa MALIM in-process dict-om na bridge instanci (isti stil kao
   GUI-008-ov `self._generation_locks`):
   ```python
   self._visual_system_by_plan: dict[str, str] = {}
   ```
   Dvoklik koji bi (u teoriji) napravio DRUGI `CampaignVisualSystem`
   za isti plan je prihvatljiv, niskog rizika edge-case (osirotjeli
   neiskorišten red, NE duplirani izvezeni sadržaj kao kod
   `ContentPiece`-ova) -- ne treba puna DB-backed zaštita kao BF-3 za
   `generate_campaign_content`. Dokumentuj ovu odluku u kodu.
5. **Primijeniti `@_with_call_resources`** na `export_campaign_package`
   + dodati `visual_repo`/`performance_repo` u `_CallResources`
   (`content_repo`/`revision_repo` VEĆ postoje od GUI-008) + property
   getter-e za njih.
6. **Dodati u `_LIFECYCLE_ERROR_MAPPERS`**: `"export_campaign_package":
   "_export_err"` + odgovarajuću poruku u `_LIFECYCLE_ERROR_MESSAGES`.
7. **BF-1 ekvivalent (OBAVEZNO, isti uzrok kao GUI-008)**:
   `pregled_izvoz`-ov "Izvezi" dugme MORA biti UVIJEK emitovano u
   statičkom HTML-u (hidden po default-u, prazni `data-campaign-id`/
   `data-plan-id`), NE uslovno na fixture. Proširi ISTI `app.js` boot
   IIFE (koji već čita `?campaign=`/`?plan=` za `studio_sadrzaja`
   dugme) da otkrije i OVO dugme kad su oba parametra prisutna. Napiši
   test protiv STVARNOG `write_all_pages()`, isti obrazac kao
   `test_write_all_pages_studio_sadrzaja_carries_live_generate_button`.
8. **BF-4 ekvivalent**: eksplicitno odbiti plan koji nije `APPROVED`
   (tvoj postojeći kod već ima `if plan.status is not
   CampaignPlanStatus.APPROVED: return err` -- provjeri da pokriva i
   `SUPERSEDED`, ne samo generičrepresentation, i test to dokazuje).
9. Provjeri da tvoj `ExportCampaign(...)` poziv i dalje ima TAČNIH 7
   parametara (uključujući `performance_repo`) -- provjeri
   `application/export/export_campaign.py` DIREKTNO prije pisanja
   poziva, ne po sjećanju iz starog koda.

## Proces

Ovo ostaje HIGH risk (prvi GUI poziv `GenerateVisualSystem`/
`PlanPostLayout`/`ExportCampaign`, stvaran AI + fajl I/O). Pun ciklus:
implementacija → Claude review → Codex adversarial → Human Owner
odobrenje. Isti obrazac kao GUI-008 (koje je prošlo kroz tri runde
prije PASS-a -- ne iznenaditi se ako i ovo treba više od jedne runde).

Kad završiš: evidence fajl + `git push` + `gh pr create` (implementer
NE merguje sam).

Stari worktree (`ACS-GUI-009-pregled-izvoz-export`, necommit-ovan)
OSTAJE netaknut kao referenca dok se novi branch ne pokaže dovoljnim
-- ne brisati ga dok koordinator to ne potvrdi.
