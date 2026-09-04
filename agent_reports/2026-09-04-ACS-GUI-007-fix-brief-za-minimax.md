# → ZA MINIMAX — ACS-GUI-007 fix runda (BF-1, BF-2, Codex nalazi)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Codex je vratio **FAIL** — 2 blocking nalaza. Oba su stvarna (nezavisno
sam ih reprodukovao, i priznajem — oba su mi promakla u mom review-u,
Codex je uradio bolji posao ovaj put).

## BF-1 — `configure_provider` error putevi vraćaju POGREŠAN DTO shape

`_err()` (statička metoda, dijeljena između `create_campaign_and_generate_plan`
i `configure_provider`) je hardkodovana na `CampaignPlanResultUiModel`:

```python
@staticmethod
def _err(code: str, message: str) -> dict:
    return asdict(
        CampaignPlanResultUiModel(
            ok=False,
            campaign_id=None,
            plan_item_count=None,
            error_code=code,
            error_message=message,
        )
    )
```

Znači SVAKA `configure_provider` greška (validation, unknown provider,
internal) vraća `{campaign_id, plan_item_count, ...}` umjesto
`{provider_code, ...}` — kršenje tvog vlastitog novog DTO-a
(`ProviderConfigResultUiModel`), koji se koristi SAMO na uspjeh. Nezavisno
reprodukovano — tačno kao u Codex-ovom izvještaju:

```json
{"campaign_id": null, "error_code": "VALIDATION_ERROR",
 "error_message": "api_key je obavezan (string).", "ok": false,
 "plan_item_count": null}
```

**Fix**: dodaj `_provider_err(code, message, provider_code=None)` helper
koji vraća `ProviderConfigResultUiModel` shape, i koristi ga na SVA TRI
error mjesta unutar `configure_provider` (validation, RegistryError/
InvariantViolation, generic exception). `_err()` OSTAJE nepromijenjen za
`create_campaign_and_generate_plan` — ne diraj tu putanju.

**Novi test koji tražim**: za SVAKI `configure_provider` error put,
provjeri TAČAN skup ključeva u povratnom dict-u:
`{"ok", "provider_code", "error_code", "error_message"}` — I DA NEMA
`campaign_id`/`plan_item_count`. Postojeći testovi su ovo propustili jer
su provjeravali samo `error_code`/`error_message`, ne cijeli shape —
tvoj novi test mora provjeriti cijeli shape da se ovo ne ponovi.

## BF-2 — API ključ ostaje u DOM-u ako bridge nije dostupan

U `app.js`, `provider-save` handler:

```js
if(!window.pywebview||!window.pywebview.api||typeof window.pywebview.api.configure_provider!=='function'){
  showToast('Interna greška: bridge nije dostupan. Ponovo pokreni aplikaciju.');
  return;   // <-- input.value NIJE ispražnjen ovdje
}
```

Ovaj `return` se dešava PRIJE bilo kojeg `input.value=''` (koji postoji
samo u `catch` grani i nakon uspješnog `await`). Nezavisno potvrđeno —
tačno na liniji koju je Codex naveo.

**Fix**: isprazni `input.value=''` PRIJE ovog `return`-a (isti pattern
kao ostale grane). Razmisli i o Codex-ovom prijedlogu — `try/finally`
omotan oko cijelog toka NAKON što se `apiKey` pročita, tako da
`input.value=''` bude GARANTOVAN za svaki put gdje je `apiKey` neprazan,
bez obzira gdje se desi `return`/`throw`. Tvoj izbor pristupa, ali
rezultat mora biti: NEMA nijedne putanje (nakon što je ključ pročitan iz
input-a) koja ostavlja `input.value` netaknut.

**Test**: provjerio sam — ovaj projekat nema JS test framework (nema
jsdom-a, nema `.test.js` fajlova, `tests/` su samo Python SSR testovi
koji provjeravaju RENDEROVANI HTML string, ne stvarno JS izvršavanje).
Ne izmišljaj novu test infrastrukturu za ovo — dovoljno je da fix bude
strukturalno očigledan (npr. `try/finally` čini nemoguće da se
promakne), i da to jasno navedeš u evidence izvještaju kao poznato
ograničenje (JS logika se ne može automatski testirati u ovom projektu
danas).

## Sitno, ne-blokirajuće (Codex N1)

Komentari na vrhu `bridge/__init__.py` još uvijek kažu "jedina javna
metoda" — sad ih je dvije (`create_campaign_and_generate_plan` +
`configure_provider`). Ispravi dok si već u fajlu za BF-1, nije
obavezno ako nemaš vremena.

## Van scope-a ove runde

Sve ostalo iz Codex-ovog review-a je već PASS (scope, `settings.environment`
provjera, boundary validacija, nema leak-a u logovima/povratnim
vrijednostima za druge slučajeve, double-click zaštita). Ne diraj.

## Kad završiš

Evidence update (nova "Fix runda (BF-1, BF-2)" sekcija, doslovan test
output za oba). Ne commit-uj. Ide nazad Codex-u na re-review.
