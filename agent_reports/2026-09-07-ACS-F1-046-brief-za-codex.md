# → ZA CODEX — ACS-F1-046 adversarial review

PR #11: https://github.com/Rade69/AI-Campaing-Studio/pull/11
Branch: `task/ACS-F1-046-kampanje-read-path` (rebase-ovan na main
`ec7bdd1`, commit `8c62fb3`).
Implementer: Crush. Task contract:
`agent_reports/ACS-F1-046-task-contract.md` + coordinator-approved
scope proširenje: `agent_reports/ACS-F1-046-addendum-scope-decision.md`.
Claude review (PASS, bez blocking nalaza):
`agent_reports/2026-09-07-ACS-F1-046-kampanje-read-path-evidence.md`
(implementer evidence -- moj review nije bio zaseban fajl, PASS
odluka je u ovom handoff-u i u CURRENT_STATE.md).

## Šta ovaj task radi

Prvi READ js_api metod na `CampaignBridgeApi` (`list_campaigns`) --
sve tri postojeće metode (`create_campaign_and_generate_plan`,
`generate_campaign_content`, `configure_provider`) su do sad bile
write-only. Uspostavlja obrazac (bridge read metod + `app.js` DOM
hidratacija) koji budući ekrani (Brend, Kalendar, Studio sadržaja
detalj) ponavljaju kao zasebne taskove.

Tri nova ADITIVNA repo metoda (coordinator odobrio proširenje scope-a
van originalnog kontrakta, obrazloženje u addendum fajlu):
`CampaignRepositoryPort.list_campaigns()`,
`CampaignRepositoryPort.get_latest_plan_for_campaign(campaign_id)`,
`BrandRepositoryPort.get_brand(brand_id)`. `updated_at` NAMJERNO
isključen (polje ne postoji nigdje u domain modelu).

`render_body()` SSR fixture-fallback OSTAJE netaknut (git diff
potvrđuje 0 izmjena u `screens/kampanje/__init__.py`).

## Šta sam (Claude) nezavisno provjerio prije ovog brief-a

- Pun diff pročitan fajl-po-fajl (repo sloj, bridge, DTO-ovi, app.js,
  svi test fajlovi) -- ne samo evidence tekst.
- `list_campaigns` catch-all koristi `logger.exception(...)` (ne
  `.error()`) -- provjereno da je ovo KONZISTENTNO sa ostatkom
  `bridge/__init__.py`-a (10+ postojećih mjesta koriste isti obrazac za
  ne-credential putanje; SAMO `_resolve_ai_adapter`-tipa metode koje
  DIREKTNO rukuju API ključem koriste `.error()`, po ACS-GUI-007 BF-3
  presedanu). `list_campaigns`-ov poziv-lanac (`get_brief`/
  `get_latest_plan_for_campaign`/`get_brand`) NE dodiruje kredencijale
  -- nema secret-in-log rizika ovdje.
- Kolona-set u dinamičkoj `app.js` tabeli (6 kolona) razlikuje se od
  SSR fixture tabele (7 kolona, "Sljedeći korak"/"Zadnja izmjena" polja
  koja stvarni model nema) -- namjerno i opravdano, NIJE vizuelno
  provjereno uživo (nemam pywebview GUI pristup u ovom review-u).
  Preporučujem STVARAN vizuelni test prije Human Owner odobrenja ako
  je moguće.
- "Otvori" dugme i dalje vodi na statičan `../opis_kampanje/index.html`
  bez `?campaign=` parametra -- ovo je POSTOJEĆE, dokumentovano,
  namjerno ponašanje iz SSR fixture-a (GUI-BASE tier, opis_kampanje
  ekran još ne prima query param), Crush ga je VJERNO replicirao, nije
  regresija.
- Rebase na main (preko ACS-F1-045 merge-a `a7cc1ef`) je čist, bez
  konflikta -- `bridge/__init__.py` diff-ovi ne dodiruju iste linije
  (ACS-F1-045 je u `create_campaign_and_generate_plan`, ovaj task u
  novoj `list_campaigns` metodi).

## Verifikacija (moja, nakon rebase-a)

```text
python -m pytest -q          -> 1077 passed
python -m ruff check .       -> All checks passed!
python -m mypy src           -> Success: no issues found in 175 source files
```

CI na PR #11: zeleno.

## Tvoj fokus (review focus iz kontrakta)

- Prvi read-path presedan -- provjeri da NIJEDNA postojeća pretpostavka
  "bridge je write-only" nije hardkodirana negdje (grep za broj js_api
  metoda u testovima/dokumentaciji van onoga što je već ažurirano u
  `test_contracts.py`).
- XSS escape STVARNO testiran (string-assertion na `escapeHtml`, per
  kontrakt eksplicitno dozvoljeno kao alternativa headless DOM testu --
  ali provjeri da li se može naći JAČI dokaz).
- `plan_item_count` tačnost za kampanju SA planom -- integration test
  postoji (`test_list_campaigns_returns_seeded_campaign_with_plan`),
  provjeri da li pokriva VIŠE planova (SUPERSEDED + novi DRAFT) tačno
  bira najviši `version`.
- Thread-safety: `list_campaigns` ima `@_with_call_resources`, isti kao
  ostale tri metode -- provjeri da nema HOTFIX-002-klase greške.
- Adversarial: probaj naći secret/path/exception leak u `list_campaigns`
  error putanji koji ja nisam pronašao.

Kad završiš, javi rezultat (PASS/PASS_WITH_NOTES/REJECT + blocking
findings ako ih ima) -- koordinator prenosi Human Owner-u za odobrenje
prije merge-a (HIGH risk, pun ciklus).
