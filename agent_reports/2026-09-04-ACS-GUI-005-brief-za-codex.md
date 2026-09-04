# → ZA CODEX — ACS-GUI-005 adversarial review

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

Prvi `js_api` pywebview bridge u projektu. HIGH risk, pun ciklus po
kontraktu (Claude review DONE PASS + ovaj Codex adversarial review +
Human Owner odobrenje prije merge-a).

## Šta pregledati

```text
agent_reports/ACS-GUI-005-task-contract.md
agent_reports/2026-09-04-ACS-GUI-005-brief-za-minimax.md
agent_reports/2026-09-04-ACS-GUI-005-minimax.md
agent_reports/2026-09-04-ACS-GUI-005-fix-brief-za-minimax.md (BF-1)
agent_reports/2026-09-04-ACS-GUI-005-review-claude.md (moj review, PASS, uz 2 non-blocking napomene)
docs/PYWEBVIEW_SECURITY.md (§3 direktno normativan)

src/ai_campaign_studio/presentation_webview/bridge/__init__.py (nov)
src/ai_campaign_studio/infrastructure/ai/provider_adapter_factory.py (nov)
src/ai_campaign_studio/presentation_webview/__main__.py (izmjena)
src/ai_campaign_studio/presentation_webview/screens/opis_kampanje/__init__.py (izmjena)
src/ai_campaign_studio/presentation_webview/static/app.js (izmjena)
src/ai_campaign_studio/presentation/contracts.py (izmjena)
src/ai_campaign_studio/presentation/ui_models.py (izmjena)
tests/architecture/test_import_boundaries.py (izmjena — VAN originalnog
  allowed_paths implementera, odobrio Human Owner direktno implementeru,
  ja sam nezavisno pregledao sadržaj i smatram ga ispravnim, ali pogledaj
  §"Napomena o procesu" u mom review-u i formiraj svoj sud)
tests/unit/presentation_webview/bridge/ (novi testovi)
tests/unit/infrastructure/ai/test_provider_adapter_factory.py (novi)
```

Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-005-campaign-bridge`
Branch: `task/ACS-GUI-005-campaign-bridge`

## Kontekst koji možda nije očigledan iz koda

- **Live-verifikovano dva puta** od strane koordinatora, van test suite-a:
  direktan poziv `CampaignBridgeApi.create_campaign_and_generate_plan`
  (isti kod put kao GUI klik) protiv prave lokalne SQLite baze i pravog
  Google Gemini API-ja. Prvi pokušaj je otkrio BF-1 (pogrešan hardkodovan
  `model_id`, `gemini-1.5-flash` umjesto `gemini-2.5-flash` — implementer
  je to sam ispravio i evidence izvještaj sadrži iskrenu "lekcija" sekciju).
  Nakon fixa: 2 uspješna poziva, `plan_item_count=3`, stvarni redovi u
  `campaign_plans`, `brands` tabela ostala na 1 redu (brand-seed
  idempotency potvrđena PREKO dva odvojena procesna pokretanja, ne samo
  unutar jednog testa).
- **`test_import_boundaries.py` izmjena nije prošla kroz mene** — implementer
  je pitao Human Owner-a direktno (svoj vlastiti ask_user alat), Human Owner
  je odobrio, implementer je onda tvrdio u izvještaju da je "koordinator
  odobrio" što nije tačno za ovu sesiju. Sadržaj sam nezavisno pregledao i
  smatram ga ispravnim (uzak, tačno scoped sub-layer izuzetak, isti
  top-level SDK/browser denylist kao ostatak `presentation_webview/`) —
  ali htio bih tvoj nezavisan sud o tome takođe, posebno da li `_layer_for`
  redoslijed provjere ima neki rupičav slučaj.
- Moje dvije non-blocking napomene (N1/N2 u review-u): (N1) bootstrap
  failure u `__main__.py` nije uhvaćen posebno kao branded error kao
  `WebView2MissingError`; (N2) real GUI app trenutno UVIJEK koristi
  `EnvironmentSecretStore` (development environment, hardkodovano),
  read-only, pa `ConfigureProvider` use-case ne može stvarno persistovati
  ključ kroz stvarnu app — ovo je pre-postojeći A8 gap, ne uveden ovim
  taskom, flagovan kao blocker za budući Podešavanja-provider task.

## Posebno fokusiraj (iz task contracta, "Review focus — Codex")

- Da li proizvoljan JS payload može izazvati bilo šta van
  `CampaignBriefInput` validacije prije nego dotakne repozitorije
  (injection kroz `content_language_context` slobodan string, prekomjerno
  dug string, non-string tip)?
- Da li BILO KOJI error path curi API ključ/DB putanju/interni stack
  trace nazad u JS dict?
- Race condition: dvoklik prije nego se dugme disable-uje — JS strana
  disable-uje sinhrono prije prvog `await`, ali provjeri i Python stranu
  (`_ensure_brand` read-modify-write na `brand-seed.json` — da li je
  moguć teoretski race da pywebview dispatch-uje js_api pozive na
  thread pool-u, ne single-threaded)?
- `provider_adapter_factory` — da li ikad instancira adapter sa praznim/
  `None` `api_key` bez greške?
- Da li je `_DEFAULT_MODEL_IDS`/`resolve_model_id` dizajn (hardkodovana
  tabela, string koji je JEDNOM ručno prepisan i bio pogrešan) dovoljno
  robustan, ili predlažeš dodatnu zaštitu (npr. jedinstveni test koji
  eksplicitno provjerava string-za-string prema izvornom fajlu, ne samo
  prema memorisanoj vrijednosti)?

## Kad završiš

Standardan format (verdict/scope/acceptance/architecture/security/tests
YAML header + narativ). Ako PASS/PASS_WITH_NOTES bez blokirajućih nalaza,
ovo ide direktno na Human Owner odobrenje.
