# ACS-GUI-008 — fix-brief runda 2 (Codex adversarial nalazi + HOTFIX-002 rebase)

Implementer: MiniMax · Reviewer: Claude (HIGH risk, pun ciklus)
Prethodni fix: `agent_reports/2026-09-06-ACS-GUI-008-fix-brief-za-minimax.md`
(riješen -- SQL uklonjen, `plan_id` threading, PASS).
Novo: Codex adversarial review (`agent_reports/2026-09-06-ACS-GUI-008-review-codex.md`),
verdict `REJECT`, 4 blocking nalaza. BF-2 je VEĆ RIJEŠEN zasebno kao
ACS-HOTFIX-002 (mergovano u main, CRITICAL, pogađalo je cijeli bridge
ne samo ovaj task). Preostaju BF-1/BF-3/BF-4 + rebase.

## 0. OBAVEZNO PRVO: rebase na main (donosi HOTFIX-002)

```bash
git fetch origin
git rebase origin/main
```

HOTFIX-002 je promijenio `CampaignBridgeApi`-jevu unutrašnju strukturu
(`self._campaign_repo` itd. su sad property-ji čitani iz `ContextVar`-a,
svaki `js_api` poziv otvara SVOJU SQLite konekciju preko
`@_with_call_resources` dekoratora). Tvoj `generate_campaign_content`
MORA dobiti ISTI `@_with_call_resources` dekorator (isti obrazac kao
`create_campaign_and_generate_plan`/`configure_provider`) -- bez njega
će pucati identično kako je BF-2 opisao, čim se pozove sa stvarnog
pywebview worker thread-a.

**Dodaj SVOJ worker-thread regression test** za `generate_campaign_content`,
isti obrazac kao `test_js_api_methods_work_from_fresh_worker_threads`
(HOTFIX-002-ov test, `_call_on_fresh_thread` helper već postoji u istom
test fajlu -- iskoristi ga, ne piši novi).

## BF-1 — produkcijski Studio HTML nema live generate kontrolu

**Root cause**: `write_all_pages()` (ili ekvivalentna build-time SSR
generator funkcija) renderira `studio_sadrzaja` BEZ fixture-a ->
`campaign_id=None`, `plan_id=None` -> dugme se NIKAD ne emituje u
STATIČKOM HTML fajlu koji stvarno ide u produkciju. Ovo je STRUKTURNI
problem: `campaign_id`/`plan_id` se saznaju tek u RUNTIME-u (kad
korisnik otvori kampanju preko `?campaign=X&plan=Y` u URL-u), ne u
BUILD-TIME-u (kad se statički HTML generiše) -- SSR-at-build-time
pristup NE MOŽE ispravno raditi za ovo.

**Rješenje: postoji VEĆ obrazac za tačno ovaj problem u
`static/app.js`** (kraj fajla, IIFE koji čita `?campaign=` preko
`URLSearchParams(location.search)` i dinamički otkriva/sakriva
`[data-campaign-only]`/`[data-campaign-hide]` elemente + popunjava
`[data-campaign-name]` tekst -- koristi ga `kalendar` ekran već). NE
IZMIŠLJAJ nov mehanizam -- proširi ISTI IIFE (ili dodaj analogan, po
istom stilu):

1. Pročitaj i `plan` query param (`new URLSearchParams(location.search).get('plan')`).
2. `studio_sadrzaja` SSR (`_edit_card()`) MORA UVIJEK emitovati dugme +
   `data-generate-result` element u STATIČKOM HTML-u (ne uslovno na
   `fx.campaign_id`/`fx.plan_id` kao sad) -- ali sa `data-campaign-id`/
   `data-plan-id` PRAZNIM/placeholder atributima i dugme `hidden`
   po default-u (ili `disabled`).
3. Kad su `campaign`+`plan` OBA prisutna u URL-u, JS IIFE postavlja
   `data-campaign-id`/`data-plan-id` na STVARNE vrijednosti iz URL-a i
   otkriva/omogućava dugme. Bez oba parametra, dugme ostaje
   sakriveno/onemogućeno (legacy toast stub ekvivalent).
4. **Nov test koji Codex traži eksplicitno**: pokreni STVARNU
   produkcijsku generator funkciju (`write_all_pages()` ili kako se
   zove -- pronađi je, Codex-ov review je referencira) i provjeri da
   izlazni HTML SADRŽI dugme+data-atribute (čak i prazne/placeholder),
   NE samo da SSR test sa ručno-predatim fixture-om prolazi.

Napomena: navigacioni lanac (`plan_kampanje`→`kalendar`→`studio_sadrzaja`
NE prenosi `&plan=` kroz sve korake) OSTAJE poznat, odvojen follow-up --
Codex je ovo eksplicitno stavio u "NE DIRATI" listu. Ne širi scope na
te screen fajlove (van tvog `allowed_paths` ionako).

## BF-3 — konkurentna idempotentnost

Dva pywebview worker thread-a mogu OBA pročitati "prazan" `list_campaign_content`
snapshot PRIJE nego ijedan upiše prvi red -> oba upisuju za isti item,
duplikat. Rješenje (ostaje unutar tvog `allowed_paths`, NE dira bazu/
migracije): **in-process lock po (campaign_id, plan_id) paru**, isti
nivo kao svaki drugi per-instance state na bridge-u:

```python
# na CampaignBridgeApi nivou (klasa ili instanca -- instanca je dovoljna
# jer postoji SAMO JEDNA CampaignBridgeApi instanca po pokrenutoj app-i)
self._generation_locks: dict[tuple[str, str], threading.Lock] = {}
self._generation_locks_guard = threading.Lock()  # štiti sam dict

def _lock_for(self, campaign_id: str, plan_id: str) -> threading.Lock:
    key = (campaign_id, plan_id)
    with self._generation_locks_guard:
        if key not in self._generation_locks:
            self._generation_locks[key] = threading.Lock()
        return self._generation_locks[key]
```

U `generate_campaign_content`, ODMAH nakon validacije `campaign_id`/
`plan_id` (prije bilo kakvog DB čitanja), `with self._lock_for(campaign_id, plan_id):`
obuhvata CIJELU petlju (read-existing + generate + save). Drugi
konkurentan poziv za ISTI par čeka na lock, pa vidi VEĆ ažurirano
stanje -- race zatvorena. Različiti (campaign_id, plan_id) parovi se NE
blokiraju međusobno (zaseban lock po ključu).

**Nov test koji Codex traži**: dva `threading.Thread`-a koja pozivaju
`generate_campaign_content` ISTOVREMENO (ne sekvencijalno) za ISTU
kampanju/plan (koristi `threading.Barrier` da garantuješ pravo
preklapanje, isti obrazac kao HOTFIX-002-ov review) -- provjeri
DB COUNT sadržaja poslije oba poziva == broj stavki plana, NE 2x.

## BF-4 — `SUPERSEDED` plan nije eksplicitno odbijen

`CampaignPlanStatus` ima `DRAFT`/`APPROVED`/`SUPERSEDED`. Trenutni kod:
`if plan.status is DRAFT: approve; else: koristi plan kao approved`.
`SUPERSEDED` (plan zamijenjen novijom verzijom preko budućeg
`EditCampaignPlan` toka -- danas nigdje povezano u GUI, ali ne treba
tiha zamka za sutra) prolazi kroz `else` granu kao da je OK.

**Fix**: nakon approve-if-DRAFT koraka, EKSPLICITNA provjera:

```python
if approved.status is not CampaignPlanStatus.APPROVED:
    return self._generate_err(
        _ERROR_VALIDATION,
        f"Plan {plan_id} je u stanju {approved.status.value}, "
        "očekivano APPROVED. Napravi novi plan.",
    )
```

**Nov test**: plan sa `status=SUPERSEDED` (konstruiši ga direktno u
testu preko repo-a, ne kroz GUI tok koji ne postoji) ->
`generate_campaign_content` vraća `VALIDATION_ERROR`, NE pokušava
`GenerateSocialPost` uopšte (0 AI poziva, ne 2 neuspjela kako je Codex
zatekao).

## Kad završiš

Pun regression: `pytest tests/unit/presentation_webview/
tests/unit/presentation/ -v`, pun suite, ruff, mypy, secret scan. Novo
evidence sa jasnim dokazom za SVA 4 (sad 3 preostala + rebase) nalaza
pojedinačno. Ovo IDE NAZAD na Codex-a za drugu rundu (isti proces --
implementer != adversarial reviewer), pa tek onda Human Owner
odobrenje.
