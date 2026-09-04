# → ZA CODEX — ACS-GUI-007 adversarial review

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

Drugi HIGH-risk bridge task (nakon ACS-GUI-005). Ovaj put secret string
ide OD JS-a U bridge (prvi put u projektu u tom smjeru — ranije je bridge
samo ČITAO secrete server-side, nikad primao od JS-a).

## Šta pregledati

```text
agent_reports/ACS-GUI-007-task-contract.md
agent_reports/2026-09-04-ACS-GUI-007-brief-za-minimax.md
agent_reports/2026-09-04-ACS-GUI-007-minimax.md
agent_reports/2026-09-04-ACS-GUI-007-review-claude.md (moj review, PASS)
docs/PYWEBVIEW_SECURITY.md (§3 direktno normativan)

src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  (nova configure_provider metoda + settings test seam u __init__)
src/ai_campaign_studio/presentation_webview/screens/podesavanja/__init__.py
src/ai_campaign_studio/presentation_webview/static/app.js
  (provider-toggle/provider-save handleri)
src/ai_campaign_studio/presentation/contracts.py
src/ai_campaign_studio/presentation/ui_models.py
  (ProviderConfigResultUiModel — NEMA api_key polje, provjeri strukturno)
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
tests/unit/presentation_webview/test_podesavanja_ssr.py
```

Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config`
Branch: `task/ACS-GUI-007-provider-config`

## Kontekst koji možda nije očigledan iz koda

- **Live-verifikovano od strane koordinatora, van test suite-a**:
  direktan poziv `CampaignBridgeApi().configure_provider(...)` sa
  PRAVOM produkcijskom default konfiguracijom (bez settings override-a)
  protiv PRAVOG OS keyring-a. Nezavisno pročitan `keyring.get_password`
  direktno (mimo aplikacije) potvrđuje da je vrijednost stvarno tamo.
  Zatim, u SVJEŽOJ instanci bridge-a (simulira novo pokretanje app-a),
  `create_campaign_and_generate_plan` je automatski pronašao taj
  provider i uspješno završio pravi Gemini poziv — prvi put da ovaj
  kraj-do-kraja tok radi bez ručnog seed-ovanja baze.
- **`settings.environment` promjena na `"production"` je izolovana**:
  koordinator nezavisno grep-ovao (`settings.environment`) i potvrdio
  TAČNO JEDNO mjesto upotrebe u cijelom kodu (`bootstrap.py:144`, bira
  secret store). Molim te nezavisno potvrdi ovo isto — ne uzimaj zdravo
  za gotovo, ovo je upravo tvoj tip nalaza koji bi trebao provjeriti.

## Posebno fokusiraj (iz task contracta, "Review focus — Codex")

- Da li BILO KOJI error path (uključujući neočekivane exception tipove)
  može procuriti `api_key` u povratnu vrijednost ili log? (Provjeri i
  `RegistryError`/`InvariantViolation` grane — da li njihov `str(exc)`
  ikad MOŽE sadržati api_key posredno, npr. ako neko izmijeni
  `ConfigureProvider` u budućnosti da uključi ulaz u poruku grešku —
  trenutno ne uključuje, ali je li ovaj bridge kod otporan na tu
  promjenu ili tiho ranjiv ako se `configure_provider.py` promijeni?)
- Da li `type="password"` input + JS `input.value=''` STVARNO sprječava
  da ključ ostane vidljiv u DOM-u nakon uspješnog/neuspješnog
  Sačuvaj-a — provjeri OBA puta (uspjeh i grešku), uključujući
  `catch` granu za thrown exception iz same `await` linije.
- Da li je moguće dvoklikom na "Sačuvaj" izazvati dva paralelna
  `ConfigureProvider` poziva za isti provider (race na
  `set_secret`/`save_provider_config`)?
- Nezavisno potvrdi da `AppSettings(environment="production")` promjena
  nema BILO KAKAV drugi efekat osim secret store izbora.

## Kad završiš

Standardan format (verdict/scope/acceptance/architecture/security/tests
YAML header + narativ). Ako PASS/PASS_WITH_NOTES bez blokirajućih
nalaza, ovo ide direktno na Human Owner odobrenje.
