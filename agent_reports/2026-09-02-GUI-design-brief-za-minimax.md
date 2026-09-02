# → ZA MINIMAX — GUI dizajn brief (paneli + skrol)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-02
**Status:** čeka da završiš trenutni window-state rad prije nego što počneš ovo — ne miješati u
istu granu/commit.

---

## Kontekst

Human Owner je live-testirao aplikaciju (screenshot-i svih 5 ekrana, sve renderuje ispravno,
fixture podaci tačni) i dao feedback: **"paneli su nekonzistentni, pojavljuje se skrol a cilj je
jedan pogled bez skrolovanja, blizu smo mokapa ali ne na nivou koji sam zamislio."**

Dogovoreno sa Human Owner-om: **prvo iteriramo na `docs/gui-v3` mokapima** (brzo, direktno u
browseru, bez re-wiring troška svaki put). Tek kad Human Owner odobri novi izgled, prenosimo ga u
`presentation_webview/`.

## Nalaz — vjerovatan zajednički uzrok oba problema

Pregledao sam `docs/gui-v3/shared/app.js`:

```js
if(action==='tab') { const group=el.closest('[data-tabs]'); group.querySelectorAll('.tab').forEach(x=>x.classList.remove('active')); el.classList.add('active'); }
```

**Tab-ovi su čisto kozmetički** — klik samo mijenja `.active` klasu na label-u. Ništa se ne
sakriva/prikazuje ispod. Rezultat na **Brend** ekranu: sadržaj sva 4 taba (Osnovni podaci /
Odobrene činjenice / Glas brenda / Brend resursi) je UVIJEK vidljiv odjednom, stackovan — iako
UI sugeriše da gledaš samo jedan tab. Ovo objašnjava oba problema odjednom:

1. **Nekonzistentnost** — tab metafora obećava "gledaš jednu sekciju", a stvarno se vidi sve —
   djeluje nedovršeno/kontradiktorno.
2. **Skrol** — pošto se sve renderuje odjednom, stranica je mnogo viša nego treba.

Isti mehanizam (vertikalni tab-ovi lijevo) postoji i na **Podešavanja** ekranu, ali tamo trenutno
samo "AI provajderi" ima stvaran sadržaj (namjerno, po V3_PLAN-u) — manje hitno, ali vrijedi
uraditi isti pravi tab-switching mehanizam da bude konzistentno sa Brend ekranom.

## Šta uraditi

### 1. Pravi tab-panel switching

U `shared/app.js`, promijeni `data-action="tab"` handler da:
- svaki tab label bude povezan sa svojim panel `<div>`-om (npr. preko `data-tab-target="ID"` na
  labelu i `id="ID"` na panelu, ili preko redoslijeda/indexa unutar `[data-tabs]` grupe — biraj
  pristup, dokumentuj izbor);
- klik na tab pokaže SAMO taj panel, sakrije ostale (`hidden` atribut, već postoji
  `[hidden]{display:none!important}` u `app.css`).

Primijeni na **Brend** (4 taba → 4 odvojena panela: brand-info+facts grid ostaje pod "Osnovni
podaci"/"Odobrene činjenice" kako ti ima smisla podijeliti, "Glas brenda" i "Brend resursi"
dobijaju svoje panele). Odluči tačnu podjelu sadržaja po tabovima — trenutni mokap ima sve u
jednom bloku, tvoj posao je da ga razdvojiš na način koji ima smisla i vizuelno je čist.

Primijeni i na **Podešavanja** (3 taba) — "Opšte"/"Jezik" mogu dobiti jednostavan placeholder
panel (npr. "Dostupno u budućoj verziji"), "AI provajderi" zadržava stvaran sadržaj.

### 2. Cilj "bez skrola" — target veličina

Aplikacija se pokreće sa `--width 1440 --height 900` po defaultu
(`presentation_webview/__main__.py`). **Koristi to kao baseline**: za svaki od 5 ekrana, sa
`DEFAULT_FIXTURE` podacima, sadržaj (`.content` div) ne smije zahtijevati vertikalni skrol na
1440×900 (topbar 64px + sidebar 248px već oduzeti u postojećem CSS layout-u).

Nakon što uvedeš pravi tab-switching (korak 1), provjeri svaki ekran/tab kombinaciju u browseru
(otvori `docs/gui-v3/screens/*/index.html` direktno, resize prozor na ~1440×900 ili koristi
browser DevTools device toolbar sa custom veličinom) — nema scrollbar-a na `.content`.

Ako i dalje ne stane (npr. Kalendar sa 28 dana × 120px), stegni vertikalni ritam umjereno, ne
drastično — knobovi u `shared/app.css`:

```text
.content{padding:30px}          → probaj 24px
.page-head{margin-bottom:26px}  → probaj 20px
.section-title{margin:28px 0 12px} → probaj 20px 0 10px
.card{padding:20px}             → probaj 16px
.grid{gap:18px}                 → probaj 14px
.day{min-height:120px}          → probaj 100px (Kalendar specifično)
```

Nemoj mijenjati sve odjednom "za svaki slučaj" — mijenjaj samo ono što stvarno treba da nestane
skrol na dotičnom ekranu, i provjeri vizuelno da i dalje izgleda dobro (ne pretijesno).

### 3. Konzistentnost panela — audit checklist

Prođi kroz svih 5 ekrana i provjeri (sve već ide kroz zajedničke `.card`/`.badge`/`.btn` klase iz
`shared/app.css`, pa bi trebalo biti konzistentno — ali provjeri da nijedan ekran ne koristi
inline `style=` koji odstupa bez razloga):

- razmak između page-head i prvog sadržaja — isti na svih 5 ekrana;
- card padding/border-radius/shadow — isti (dolazi iz `.card`, provjeri da niko ne override-uje);
- heading veličine (h2/h3) — konzistentne;
- dugme stilovi (`.btn` vs `.btn.primary`) — korišteni dosljedno po semantici (primary samo za
  glavnu akciju ekrana, kao "+ Nova kampanja");
- badge boje po statusu — već izgledaju konzistentne (warn/info/ok/gray/danger), samo potvrdi.

Ako nađeš konkretnu inkonzistenciju van ove liste, zapiši je i popravi — ovo je polazna tačka, ne
kompletna lista.

## Proces

1. Radi direktno na `docs/gui-v3/` HTML/CSS/JS fajlovima (ne na `presentation_webview/` — to je
   sljedeći korak, poslije odobrenja).
2. Kad završiš, napravi screenshot-e svih 5 ekrana (i svih tabova gdje ih ima) na ~1440×900, bez
   vidljivog scrollbar-a, i pošalji Human Owner-u na odobrenje.
3. Tek nakon odobrenja — javi koordinatoru, pišem formalan Task Contract (ACS-GUI-004 ili slično)
   da se odobreni dizajn prenese u `presentation_webview/screens/*/`.

## Van scope-a ovog brief-a

- `presentation_webview/` (wired Python app) — ne diraj dok mokap nije odobren.
- Window-state persistencija u `__main__.py` — tvoj trenutni rad, završi ga prvo, odvojeno od
  ovoga.
- Campaign workflow ekrani (Opis/Plan kampanje, Studio sadržaja, Pregled i izvoz) — van scope-a,
  ACS-GUI-003 kasnije.
