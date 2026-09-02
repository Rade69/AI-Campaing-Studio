# Codex / Claude integration handoff

## Šta je ovo
Ovaj paket je finalni V3 GUI handoff kandidat. Ne merge-ovati stare `mockup_proposal*` foldere kao production kod. Koristiti V3 strukturu kao vizuelni/source-of-truth kandidat nakon Human Owner potvrde.

## Preporučena production struktura
```text
presentation_webview/
  shell/
  components/
  screens/
    pocetna/
    brend/
    kampanje/
    opis_kampanje/
    plan_kampanje/
    kalendar/
    studio_sadrzaja/
    pregled_izvoz/
    podesavanja/
  bridge/
  static/
```

## Granice
Browser/JS ne pristupa SQLite-u, SecretStore-u, provider registry internals ili domain entitetima direktno. JS poziva uski pywebview bridge; Python adapter mapira na framework-neutral `presentation/` contracte i Application use-caseove.

## Trenutni backend mapping
- AI provider lista može se mapirati na postojeći `PresentationFacade.list_ai_providers()`.
- Locale može ići preko `PresentationFacade.set_app_locale()`.
- Campaign/Brand metode trenutno nisu u P0 `PresentationFacade`; dodavati ih tek kroz odgovarajuće F1 task contracte, ne improvizovati u JS-u.
- Dashboard vrijednosti u V3 su fixture/read-model placeholderi, ne performance analytics.

## Studio bridge seams
`rewrite_content`, `shorten_content`, `improve_hook`, `change_tone`, `generate_variant`, `save_draft`, `submit_for_review`. Ovo su UI intenti, ne obavezan konačni naziv Python metoda. Mapirati na use-case contract kad bude definisan.

## Analytics guard
Ne dodavati `Analitika` u sidebar niti performance ekran prije potvrđenog G10 PASS.
