# → ZA CODEX — ACS-GUI-008 rereview (runda 2)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-06

Tvoj prethodni review (`agent_reports/2026-09-06-ACS-GUI-008-review-codex.md`,
verdict `REJECT`, BF-1/BF-2/BF-3/BF-4) je doveo do fix runde. BF-2 je
zasebno riješen kao ACS-HOTFIX-002 (CRITICAL, već mergovano u main --
pogađalo je cijeli bridge, ne samo ovaj task). Implementer (MiniMax) je
rebase-ovao ovaj task na taj fix i riješio preostala tri.

## Šta pregledati

```text
agent_reports/2026-09-06-ACS-GUI-008-fix-brief-2-za-minimax.md (moj fix-brief)
agent_reports/2026-09-06-ACS-GUI-008-fix-brief-2-evidence.md (implementer evidence)
PR: https://github.com/Rade69/AI-Campaing-Studio/pull/4 (commit 897bd5c, CI zeleno)

src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  (generate_campaign_content sad @_with_call_resources + lock preko
  _lock_for(campaign_id, plan_id); explicitna SUPERSEDED provjera nakon
  approve-if-DRAFT koraka)
src/ai_campaign_studio/presentation_webview/screens/studio_sadrzaja/__init__.py
  (dugme se UVIJEK emituje, hidden po default-u, ne uslovno na fixture)
src/ai_campaign_studio/presentation_webview/static/app.js
  (boot IIFE prošireno sa ?plan= handling-om)
tests/unit/presentation_webview/test_static_pages_generator.py
  (nov test protiv STVARNOG write_all_pages())
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  (nova 4: fresh-worker-thread, concurrent-lock, superseded-rejected +
  ostali)
```

## Šta sam ja (koordinator) već nezavisno provjerio -- ne ponavljaj

- Pun suite 1042/1042 (uključujući integration testove -- implementer
  ih nije stigao pokrenuti zbog timeout-a, ja jesam), ruff/mypy čisti.
- Mutation-testirao BF-3 fix (privremeno uklonio lock, potvrdio da
  concurrent test PADA sa 4 umjesto 2 generisana -- pravi duplikat,
  vratio).
- Mutation-testirao BF-4 fix (privremeno uklonio SUPERSEDED provjeru,
  potvrdio da test PADA i da se reproducira TAČNO originalni Codex
  nalaz -- 2 propala AI poziva sa `InvariantViolation`, vratio).
- `test_write_all_pages_studio_sadrzaja_carries_live_generate_button`
  STVARNO poziva `write_all_pages()` (produkcijsku funkciju), ne samo
  `render_body()` sa ručnim fixture-om -- pročitao test kod direktno.
- GitNexus `detect_changes` (detached HEAD u glavnom checkout-u, isti
  postupak kao za ACS-F1-043) vratio `risk_level: high`, ALI ručno
  provjerio da je VEĆINA "touched" simbola (`_ensure_brand`,
  `_resolve_provider`, `ProviderConfigResultUiModel`, itd.) lažan
  pozitiv od pomaka linija (465 novih linija ranije u fajlu) --
  sadržaj tih simbola je bajt-identičan, samo pomjeren. Stvarne izmjene
  su ograničene na ono što fix-brief-2 traži + HOTFIX-002 rebase.
- CI zeleno na PR #4 za tačan commit `897bd5c`.

## Posebno fokusiraj (tvoj posao, ne moj)

- Da li `_lock_for`-ov lock ODMAH nakon boundary validacije, PRIJE bilo
  kakvog DB čitanja, STVARNO pokriva CIJELU "read-generate-write"
  sekvencu bez rupe (npr. da li `_generate_campaign_content_locked`
  negdje pušta lock pa ga ponovo hvata usred posla)?
- Da li BF-1-ov fix STVARNO radi za navigaciju koja NIJE
  `plan_kampanje→kalendar→studio_sadrzaja` (npr. direktan URL sa OBA
  parametra) -- i da li ispravno OSTAJE sakriveno kad je samo JEDAN
  parametar prisutan (test dokaz, ne pretpostavka)?
- Threading.Lock + ContextVar interakcija POD STVARNIM pywebview
  EdgeChromium dispatch-om (ne samo `threading.Thread` simulacija u
  testu) -- implementer sam priznaje (§"Preostali rizici" u evidence-u)
  da ovo NIJE end-to-end testirano protiv pravog pywebview runtime-a.
  Da li to smatraš dovoljnim za PASS, ili treba dodatan dokaz?
- Bilo šta iz originalnog review-a što OVA runda možda nije potpuno
  pokrila.

## Kad završiš

Standardan format (verdict/scope/acceptance/architecture/security/tests
YAML header + narativ). Ako PASS/PASS_WITH_NOTES, ide na Human Owner
odobrenje (HIGH risk, ne §29 skraćeni put).
