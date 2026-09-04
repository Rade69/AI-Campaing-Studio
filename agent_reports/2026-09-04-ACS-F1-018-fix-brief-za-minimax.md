# → ZA MINIMAX — ACS-F1-018 fix runda (BF-1)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Odličan posao na istraživanju i disciplini (BF-1 lekcija iz ACS-F1-016 primijenjena tačno — stvarni
pydantic tipovi u testovima, ne SimpleNamespace). Jedna stvar te vraća u fix rundu, i jedna
napomena za ubuduće.

## Napomena: radi u projektnom `.venv`-u, ne sistemskom Python-u

Otkrio sam da `anthropic` nije bio instaliran u `H:\AI Campaing Studio\.venv` — tvoje istraživanje
je bilo urađeno protiv sistemskog Python-a
(`C:\Users\38765\AppData\Local\Programs\Python\Python314\...`). Instalirao sam ga sam da nastavim
review. Ubuduće koristi `.venv\Scripts\python.exe` (ili aktiviraj venv) da se izbjegne environment
drift.

## BF-1 — koristi native `output_config`/`json_schema`, ne prompt-based JSON

Tvoje istraživanje (0.105.2: "nema `response_format`/`json_schema` parametra") je bilo TAČNO za tu
verziju u tom trenutku. Ali `pyproject.toml` ima `anthropic>=0.30` bez gornje granice — fresh
install DANAS povlači `anthropic 1.3.0`, koja IMA native structured output:

```python
message = client.messages.create(
    model=...,
    max_tokens=...,
    system=...,
    messages=[...],
    output_config={
        "format": {
            "type": "json_schema",
            "schema": request.json_schema,
        }
    },
)
```

Potvrdio sam ovo direktno protiv instaliranog paketa (`anthropic.types.output_config_param.
OutputConfigParam`, `anthropic.types.json_output_format_param.JSONOutputFormatParam` — `{'schema':
dict, 'type': 'json_schema'}`). Ovo je funkcionalno ekvivalentno OpenAI-jevom
`response_format=json_schema` — server-side enforcement, ne samo prompt-direktiva.

**Human Owner odluka: nadogradi sada, prije merge-a.** Isti razlog kao DeepSeek BF-1 iz
ACS-F1-017 — bez server-side enforcement-a, model je slobodniji da odstupi od šeme (vidjeli smo
uživo kod DeepSeek-a: 7 stavki umjesto traženih 3, bez enforced sheme).

## Šta uraditi

1. Zamijeni `_compose_system_text()` schema-in-prompt pristup sa `output_config` parametrom na
   `messages.create()`. `system_text` ostaje kakav jeste (bez schema direktive dodane) — schema
   ide isključivo kroz `output_config`.
2. Provjeri da li `output_config`/`JSONOutputFormatParam` postoji i u tvojoj lower-bound verziji
   (`anthropic>=0.30`) — ako NE postoji u starijim verzijama koje `>=0.30` dozvoljava, ili podigni
   lower bound na verziju gdje sigurno postoji, ili detektuj feature dostupnost i fallback-uj na
   prompt-based pristup (tvoj izbor, dokumentuj obrazloženje).
3. `_parse_structured()`/defensive code-fence stripping može ostati kao fallback zaštita (ne škodi),
   ali primarni put treba biti `output_config`, ne oslanjanje na to da model poštuje prompt
   instrukciju.
4. **Ažuriraj testove da odražavaju STVARAN 1.3.0 shape** — spy na `messages.create()` poziv i
   dokaži da `output_config` sadrži tačnu šemu (isti nivo dokaza kao tvoj postojeći
   `_compose_system_text` test, samo za novi mehanizam). Fake response fixture-i ostaju kako jesu
   (već stvarni pydantic tipovi).
5. **NIJE live-testirano** (Human Owner nema Anthropic ključ trenutno) — ako TI imaš pristup,
   testiraj uživo i dokumentuj stvaran nalaz (isti standard kao DeepSeek proba). Ako nemaš, jasno
   navedi da fix nije live-verifikovan.

## Van scope-a ove runde

Sve ostalo (DI seam, retry, error mapping, `discover_models`) je već PASS, ne diraj.

## Kad završiš

Evidence update (nova "Fix runda (BF-1)" sekcija). Ne commit-uj. Ide na Codex adversarial review
tek nakon ovog fixa.
