# → ZA PI — ACS-F1-017 fix runda (BF-1)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-04

Human Owner je uradio ručnu end-to-end validaciju sa pravim DeepSeek ključem (van formalnog
review-a) i naišao na stvaran, blocking bug koji nijedan mock-ovan test (ni tvoj, ni moj) nije
mogao uhvatiti. Moj review je downgrade-ovan sa `PASS_WITH_NOTES` na `REJECT`. Pun nalaz:
`agent_reports/2026-09-04-ACS-F1-017-review-claude.md` (u worktree-u).

## BF-1 — DeepSeek odbija `response_format: json_schema`

Stvaran poziv (ne hipoteza):

```text
$ python -c "... OpenAIAdapter(api_key=..., model='deepseek-chat', base_url='https://api.deepseek.com').generate(...) ..."
openai.BadRequestError: Error code: 400 - {'error': {'message': 'This response_format type
is unavailable now', 'type': 'invalid_request_error', ...}}
```

`_generate_once()` uvijek šalje `response_format={"type": "json_schema", "json_schema": {...}}`
— OpenAI-specifičan strogi mod. DeepSeek ga NE podržava. Tvoj `OUT_OF_SCOPE_FINDINGS: Nema` je
bio tačan koliko je mock-ovan suite mogao pokazati — ali mock-ovan klijent nikad ne provjerava da
li backend stvarno prihvata `response_format`, samo da li kod ispravno GRADI zahtjev. Ovo je ista
vrsta gap-a kao F1/BF-1 iz ACS-F1-016 (httpx, finish_reason) — svi review koraci (tvoj, moj) su
prošli jer smo se svi oslonili na mock.

**Potvrđen fix (uživo testiran od koordinatora, ne teorija)**: DeepSeek prihvata stariji
`response_format={"type": "json_object"}` mod. Taj mod NE forsira šemu na serveru — šema mora ići
kao tekst u promptu, PLUS eksplicitna instrukcija da se brojčana ograničenja (npr.
`content_piece_count`) moraju tačno poštovati (prvi pokušaj bez te eksplicitne instrukcije je dao
7 stavki umjesto traženih 3 — DeepSeek manje strogo prati prozne instrukcije bez schema-enforced
dekodiranja).

## Šta uraditi

1. Dodaj mehanizam u `OpenAIAdapter` da bira između `json_schema` (OpenAI, default — ČUVA
   postojeće ponašanje, ne diraj OpenAI put) i `json_object` + schema-in-prompt (DeepSeek).
   Konkretan oblik (konstruktorski parametar, npr. `structured_output_mode`, ili nešto slično) —
   tvoj izbor, dokumentuj obrazloženje. Kad je `json_object` mod: ubaci JSON schema opis U
   `system_text` poruku (ili gdje god smatraš da je čist pattern), PLUS eksplicitnu instrukciju o
   tačnom broju stavki kad je primjenjivo.
2. `build_deepseek_adapter` u `openai_compatible_providers.py` mora koristiti `json_object` mod.
3. **OpenRouter NIJE testiran uživo — ne pretpostavljaj ništa.** Ako imaš pristup OpenRouter
   ključu, testiraj isto uživo (stvaran poziv, ne mock) i dokumentuj stvaran nalaz. Ako nemaš
   pristup, eksplicitno navedi u evidence-u da OpenRouter-ov `response_format` ponašanje ostaje
   neprovjereno i da default treba biti konzervativan (`json_object`, ne `json_schema`) dok se ne
   dokaže suprotno.
4. Generički `OPENAI_COMPATIBLE` provider (`base_url_mode: USER_CONFIGURABLE`) — po definiciji
   proizvoljan endpoint, ne može se pretpostaviti nijedan mod. Razmisli da li default treba biti
   `json_object` (širi kompatibilitet) uz mogućnost da pozivalac eksplicitno traži `json_schema`
   ako zna da njegov endpoint to podržava.
5. **Dodaj REGRESIONI test koji dokazuje schema-in-prompt embedding stvarno radi** (isti nivo
   dokaza kao tvoj postojeći provenance test — spy na messages sadržaj, ne samo da response_format
   promijenjen).
6. Ako imaš svoj DeepSeek pristup, ponovi live poziv (kao Human Owner) da nezavisno potvrdiš fix
   radi protiv stvarnog API-ja, ne samo mock-a. Ako nemaš, jasno navedi da fix nije live-verifikovan
   od tebe (koordinator već ima živu potvrdu, ali dodatna nezavisna potvrda je vrijedna).

## Van scope-a ove runde

`provider_code`/`provider_display` parametrizacija je već PASS, ne diraj. Base URL konstante su
PASS, ne diraj.

## Kad završiš

Evidence update (nova "Fix runda (BF-1)" sekcija u postojećem evidence fajlu). Ne commit-uj. Ide
na Codex adversarial review TEK nakon ovog fixa (Codex još nije ni pozvan na staru verziju —
nema smisla trošiti rundu na poznato slomljen kod).
