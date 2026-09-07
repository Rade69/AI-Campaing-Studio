# → ZA CODEX — ACS-GUI-008 rereview (runda 3, samo BF-5)

**Od:** koordinator (Claude) · **Za:** Codex · **Datum:** 2026-09-07

Ti si u prošloj rundi (`agent_reports/2026-09-06-ACS-GUI-008-rereview-codex.md`)
eksplicitno rekao "provjerava samo BF-5 diff/repro" -- ostatak (BF-1/
BF-3/BF-4, scope, arhitektura, sigurnost, testovi) je već PASS i nije
diran u ovoj rundi.

## Šta pregledati

```text
agent_reports/2026-09-06-ACS-GUI-008-fix-brief-3-za-minimax.md (moj fix-brief)
agent_reports/2026-09-06-ACS-GUI-008-fix-brief-3-evidence.md (implementer evidence)
PR: https://github.com/Rade69/AI-Campaing-Studio/pull/4 (commit 67a8ae0, CI zeleno)

src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  (_LIFECYCLE_ERROR_MAPPERS + _LIFECYCLE_ERROR_MESSAGES dict-dispatch,
  zamjenjuje hardkodiran if/elif)
tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
  (test_connection_failure_never_raises_or_leaks_secret_to_js prošireno
  na sve tri metode)
```

## Šta sam ja već nezavisno provjerio

- Pročitao diff direktno -- `_LIFECYCLE_ERROR_MAPPERS` mapira sve tri
  postojeće metode eksplicitno (`configure_provider`→`_provider_err`,
  `create_campaign_and_generate_plan`→`_err`,
  `generate_campaign_content`→`_generate_err`), fallback na `_err` za
  bilo koju buduću nepoznatu metodu.
- **Mutation-testirao uživo**: privremeno uklonio
  `generate_campaign_content` unos iz mapper tabele, potvrdio da test
  STVARNO padne (`plan_id` procuri u generate-content DTO -- tačno
  originalni bug), vratio.
- Ponovio TVOJU tačnu reprodukciju (`create_connection` baca `OSError`)
  -- sad vraća `{'ok': False, 'campaign_id': None, 'generated_count': 0,
  'failed_count': 0, 'content_piece_ids': (), 'error_code':
  'INTERNAL_ERROR', 'error_message': '...'}` -- tačan DTO, bez
  `plan_id`/`plan_item_count` leaka.
- Pun suite 1042/1042, ruff/mypy čisti.
- CI zeleno na PR #4 za tačan commit `67a8ae0`.

## Tvoj posao

Samo BF-5 diff/repro, kako si sam naveo. Ako PASS, ide na Human Owner
odobrenje -- HIGH risk, nema §29 skraćeni put.
