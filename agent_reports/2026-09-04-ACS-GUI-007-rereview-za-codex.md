# → ZA CODEX — ACS-GUI-007 re-review (nakon BF-1, BF-2 fixa)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-04

Oba tvoja nalaza su bila tačna, i priznajem — oba su meni promakla u
prvom review-u. MiniMax je popravio oboje.

## BF-1 fix

Nov `_provider_err(code, message)` static helper koji vraća
`ProviderConfigResultUiModel` shape (`{ok, provider_code, error_code,
error_message}`). Sva tri error mjesta u `configure_provider` sada
koriste njega umjesto dijeljenog `_err()` (koji ostaje netaknut, i dalje
služi `create_campaign_and_generate_plan`). Novi test
`test_configure_provider_error_shape_has_no_campaign_flow_keys`
provjerava TAČAN skup ključeva na SVAKOM error putu (ne samo par polja
kao prije).

## BF-2 fix

`provider-save` handler u `app.js` sada čita `apiKey` u lokalnu
promjenljivu, pa cijeli tok (uključujući "bridge nije dostupan" granu
koja je bila propust) ide unutar `try/finally` — `input.value=''` +
`el.disabled=false` su u `finally` bloku, strukturno garantovano na
SVAKOM izlazu iz handler-a (return, throw, await rejection, happy path).

**Napomena o test pokrivenosti za BF-2**: projekat nema JS test
framework (nema jsdom-a, `tests/` su Python SSR testovi koji provjeravaju
renderovani HTML, ne stvarno JS izvršavanje) — MiniMax ovo eksplicitno
priznaje kao poznato ograničenje umjesto da ga sakrije. Fix je strukturno
dokazan (`try/finally` čini scenario nemogućim), ne test-dokazan. Ako
smatraš da je ovo blocking (nedovoljna verifikacija za security-kritičan
JS kod), reci — otvorena sam za tvoju procjenu, nisam htio sam odlučiti
da je "strukturno očigledno" dovoljno bez tvoje potvrde.

## Šta pregledati

```text
agent_reports/2026-09-04-ACS-GUI-007-minimax.md (§9 "Fix runda (BF-1, BF-2)")
src/ai_campaign_studio/presentation_webview/bridge/__init__.py (_provider_err + 5 poziva)
src/ai_campaign_studio/presentation_webview/static/app.js (try/finally restructure)
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py (novi shape test)
```

Worktree: `H:\ai-campaign-studio-worktrees\ACS-GUI-007-provider-config`
Branch: `task/ACS-GUI-007-provider-config`

## Moja nezavisna re-verifikacija

```text
$ python configure_provider za {}, {"provider_code":"NOT_REAL","api_key":"x"}, None
sve tri: sorted keys = ['error_code', 'error_message', 'ok', 'provider_code']
(prije fixa: ['campaign_id', 'error_code', 'error_message', 'ok', 'plan_item_count'])

$ pytest tests -q --ignore=test_generate_phase0_gate_report.py
793 passed

$ ruff check src tests scripts / mypy src / import_boundaries / check_no_secrets
svi čisti
```

## Kad završiš

Ako PASS/PASS_WITH_NOTES bez novih blokirajućih nalaza, ovo ide direktno
na Human Owner odobrenje.
