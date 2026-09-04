---
task_id: ACS-F1-024
phase: Faza-1 (post ACS-GUI-005)
title: "Bridge: provider fallback petlja (probaj sljedeći konfigurisan provider ako prvi nema ključ) + jači brand-seed test"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/presentation_webview/bridge/__init__.py
  - tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/presentation/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. Izmjena je izolovana na jednu
    metodu (`_resolve_provider`) u već postojećem bridge fajlu, nema novih
    importera/pozivalaca.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: e1177cc
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

MiniMax (originalni implementer ACS-GUI-005) je nakon merge-a sam
pregledao svoj rad i našao dva realna nalaza; koordinator nezavisno
potvrdio oba čitanjem trenutnog `bridge/__init__.py::_resolve_provider`
na main-u prije pisanja ovog kontrakta.

## Nalaz 1 — provider fallback ne postoji, samo prvi u prioritetu

```python
configs = list(self._provider_config_repo.list_provider_configs())
configured_codes = [c.provider_code for c in configs if c.configured]
code = pick_configured_provider(configured_codes)  # JEDAN kod
if code is None:
    return None, None
config = next((c for c in configs if c.provider_code == code), None)
...
api_key = self._bootstrap.secret_store.get_secret(config.credential_ref)
...
return code, (api_key or None)
```

Ako je npr. OPENAI konfigurisan (ima `ProviderConfig` red) ALI mu API
ključ nedostaje u SecretStore-u (npr. obrisan iz env-a), a GOOGLE je i
konfigurisan I ima stvaran ključ — `pick_configured_provider` vraća
`OPENAI` (viši prioritet), `_resolve_provider` vraća `(OPENAI, None)`,
bridge odmah javlja `PROVIDER_KEY_MISSING` i STAJE — GOOGLE nikad ne
dobija priliku, iako je potpuno spreman.

## Nalaz 2 — `test_brand_seed_reused_on_second_call` provjerava samo broj,
## ne identitet

Test provjerava `SELECT COUNT(*) FROM brands == 1` nakon dva poziva, ali
ne provjerava da je to ISTI `brand_id` koji je zapisan u
`brand-seed.json`. Teoretski prolazi i u scenariju gdje je neko obrisao
stari brend i kreirao NOV sa istim fixture-om između dva poziva — broj
ostaje 1, ali identitet se promijenio.

# Objective

1. `_resolve_provider` postaje petlja preko SVIH konfigurisanih
   provajdera po prioritetu (`_PROVIDER_PRIORITY` pa ostali po redu iz
   `configured_codes`, isti fallback redoslijed koji
   `pick_configured_provider` već implicitno definiše), ne samo prvog —
   probaj svaki dok jedan ne vrati stvaran (ne-prazan) ključ.
2. Ojačaj `test_brand_seed_reused_on_second_call` da provjerava i
   identitet (`brand_id`), ne samo broj redova.

# Implementation steps

1. U `_resolve_provider`, zamijeni logiku "uzmi jedan kod pa mu čitaj
   ključ" sa petljom: iteriraj kroz konfigurisane kodove u prioritetnom
   redoslijedu (ISTA logika kao `pick_configured_provider`, ali sad
   moraš proći kroz VIŠE kandidata, ne samo prvog — razmisli da li
   `pick_configured_provider` treba vratiti listu umjesto jednog koda,
   ili da `_resolve_provider` sam gradi prioritetni redoslijed lokalno;
   tvoj izbor, dokumentuj obrazloženje u evidence izvještaju).
2. Za svakog kandidata: pročitaj `credential_ref`, pozovi
   `secret_store.get_secret(...)`, ako je rezultat NE-prazan string,
   vrati `(code, api_key)` odmah (prvi koji uspije pobjeđuje).
3. Ako NIJEDAN konfigurisan provider nema stvaran ključ, vrati
   `(zadnji_probani_code, None)` — bridge i dalje javlja
   `PROVIDER_KEY_MISSING`, ali sad je to istinito (svi su probani, svi
   nemaju ključ), ne "prvi u redu nema ključ pa smo odustali".
4. Dodaj test: dva konfigurisana provajdera, prvi (viši prioritet) nema
   ključ u SecretStore-u, drugi ima → bridge USPIJEVA sa drugim
   (ne vraća `PROVIDER_KEY_MISSING`).
5. Dodaj test: svi konfigurisani provajderi nemaju ključ → i dalje
   `PROVIDER_KEY_MISSING`, ne beskonačna petlja/pucanje.
6. Ojačaj `test_brand_seed_reused_on_second_call`: dodaj
   `assert brand_id_from_first_call == brand_id_from_second_call` (ili
   ekvivalentno, pročitaj `brand-seed.json` sadržaj i uporedi).

# Acceptance

- [ ] Ako prvi (najviši prioritet) konfigurisan provider nema ključ, a
      drugi ima — bridge koristi drugog, ne javlja grešku.
- [ ] Ako nijedan konfigurisan provider nema ključ — `PROVIDER_KEY_MISSING`,
      bez petlje/pucanja.
- [ ] `test_brand_seed_reused_on_second_call` provjerava identitet
      (`brand_id`), ne samo broj.
- [ ] Nema regresije na postojeće `NO_PROVIDER_CONFIGURED` slučaj (nijedan
      konfigurisan uopšte).
- [ ] `ports/`, `infrastructure/`, `application/`, `domain/`,
      `presentation/` NISU DIRANI (git diff dokaz) — sve ostaje unutar
      bridge fajla.
- [ ] `python -m pytest tests/unit/presentation_webview/bridge/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/presentation_webview/bridge/test_campaign_bridge_api.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- fallback petlja stvarno probuje SVE konfigurisane, ne samo drugog pa
  odustane;
- prioritetni redoslijed (`OPENAI > ANTHROPIC > GOOGLE`, pa ostali) i
  dalje poštovan;
- brand-seed test stvarno dokazuje identitet, ne samo broj.

# Rollback

MEDIUM risk — izolovano na jednu metodu u postojećem fajlu. Fix na istoj
branch bez proširenja scope-a. §29: Claude-only review, PASS -> odmah
merge.

# Coordination

Nezavisno od ACS-GUI-006 (orphan campaign compensating delete, planiran)
— različit dio istog `bridge/__init__.py` fajla (`_resolve_provider` vs
`create_campaign_and_generate_plan`-ov error handling), ali OBA taska
mijenjaju isti fajl. Koordinator će ih sekvencirati (ne paralelno na
istom fajlu) da izbjegne merge konflikt — ovaj (ACS-F1-024) ide prvi,
manji je.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-024-provider-fallback
Branch:   task/ACS-F1-024-provider-fallback
Base:     main @ e1177cc
```
