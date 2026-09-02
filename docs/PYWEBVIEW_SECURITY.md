# pywebview 6.2.1 — sigurnosna politika

Status: **obavezno štivo** za svaki task koji dira `presentation_webview/`, bilo koji
pywebview `create_window`/`start` poziv, ili bilo koji `js_api` bridge. Važi bez obzira
na to da li je pywebview u datom trenutku formalno zaključan kao UI framework (vidi
CLAUDE.md "UI framework se ne zaključava prije UI spike gate-a") — ova politika obavezuje
svaku pywebview integraciju od prvog reda produkcijskog koda, uključujući GUI-BASE.

Istraženo i verifikovano nezavisno (2026-09-02) protiv zvanične pywebview dokumentacije
(pywebview.flowrl.com/api, GitHub security advisories stranice) za verziju **6.2.1**,
tačnu verziju instaliranu u projektnom `.venv`. Nema objavljenih CVE/security advisory-ja
za pywebview u trenutku pisanja — provjeriti `github.com/r0x0r/pywebview/security` prije
svakog budućeg version bump-a.

## 1. Renderer engine — najkritičniji nalaz

Na Windows-u pywebview bira renderer u redoslijedu **edgechromium → mshtml**. Ako
WebView2 Runtime nije instaliran na ciljnoj mašini, pywebview **tiho** pada nazad na
`mshtml` (Internet Explorer/Trident engine) — deprecated, bez daljeg razvoja, bez
sigurnosnih zakrpa.

**Obavezno:**
- Eksplicitno postaviti `webview.start(gui='edgechromium', ...)` (ili
  `PYWEBVIEW_GUI=edgechromium` env var) — ovo pretvara nedostatak WebView2 Runtime-a iz
  tihog downgrade-a u eksplicitnu grešku.
- Health-check / startup putanja aplikacije mora eksplicitno detektovati prisustvo
  WebView2 Runtime-a i korisniku dati jasnu poruku + link ka Microsoft Evergreen
  Bootstrapper-u ako nedostaje, umjesto da aplikacija ikad tiho radi na `mshtml`.
- Nikad ne oslanjati se na default auto-detect ponašanje u produkcijskom entry pointu.

## 2. Debug / DevTools

- `debug=False` u svakom produkcijskom pozivu `webview.start()` (eksplicitno, iako je
  to i default vrijednost — eksplicitnost sprječava slučajno nasljeđivanje `debug=True`
  iz dev/troubleshooting konfiguracije).
- `OPEN_DEVTOOLS_IN_DEBUG` je **enabled by default** kad je `debug=True` — ako se debug
  ikad uključi (npr. lokalni troubleshooting build), eksplicitno postaviti
  `webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False` ako DevTools pristup nije
  namjerno potreban toj sesiji.
- `REMOTE_DEBUGGING_PORT` ostaje **disabled** (default) u produkciji — otvara mrežni
  port sa punim DevTools protokol pristupom; nikad se ne uključuje bez eksplicitnog,
  vremenski ograničenog troubleshooting razloga.

## 3. `js_api` bridge — pravila izlaganja

- Izlagati **samo** usku, svrsi-namijenjenu bridge klasu (npr. jedan adapter objekat sa
  imenovanim metodama iz `INTEGRATION.md` — `rewrite_content`, `save_draft`, itd.) —
  nikad sirovi `PresentationFacade`, domain servis ili modul sa širim površinama.
- Svaka `js_api` metoda validira/tipizira ulaz na granici (Pydantic ili ručna provjera)
  — JS strana šalje proizvoljan JSON, ne vjerovati tipovima/rasponu bez provjere.
- Nijedna `js_api` metoda ne vraća API ključ, token ili bilo koji SecretStore sadržaj
  nazad u JS kontekst — provider pozivi ostaju potpuno na Python strani.
- Nijedna `js_api` metoda ne prima proizvoljnu fajl putanju ili shell komandu iz JS bez
  allowlist-a/sandboxing-a (path traversal / command injection površina).

## 4. Content-Security-Policy

Dodati `<meta http-equiv="Content-Security-Policy">` u shared shell template (jednom,
ne po ekranu) čim GUI-BASE počne production wiring:

- `default-src 'self'`
- `script-src 'self'` — nema remote JS-a (već ispoštovano u `docs/gui-v3/`: nijedan
  `<script src>` ne pokazuje van `shared/app.js`).
- `connect-src 'self'` — blokira JS-inicirane mrežne pozive (fetch/XHR/WebSocket) ka
  spoljnim hostovima. Svi AI/provider pozivi idu kroz Python bridge, ne kroz JS fetch —
  ovo je već arhitektonsko pravilo iz `INTEGRATION.md`, CSP ga samo tehnički provodi.
- Preferirati `window.run_js()` nad `window.evaluate_js()` sa Python strane gdje god je
  moguće — `evaluate_js` koristi `eval` i zahtijeva `unsafe-eval` u CSP-u; `run_js` ne.

## 5. Spoljni resursi / local-first

`docs/gui-v3` trenutno ima jednu spoljnu mrežnu zavisnost: Google Fonts
(`fonts.googleapis.com` / `fonts.gstatic.com`, Inter font). Preporuka za production
wiring: vendor-ovati Inter font lokalno (`static/fonts/`) — ukida spoljni network poziv
pri svakom pokretanju, pojednostavljuje CSP na čist `default-src 'self'`, i usklađeno je
sa "local-first" projektnim principom. Nije blocker za GUI-BASE, ali treba biti dio prve
production wiring iteracije, ne ostaviti trajno na CDN-u.

## 6. Eksterni linkovi i navigacija

- `OPEN_EXTERNAL_LINKS_IN_BROWSER` ostaje **enabled** (default) — svaki budući eksterni
  link u sadržaju MORA imati `target="_blank"` da iskoristi ovu zaštitu (automatski se
  otvara u OS default browseru, ne unutar pywebview prozora).
- Nikad programski navigirati sam webview prozor (`window.load_url`) na spoljni URL na
  osnovu neprovjerenog sadržaja (npr. AI-generisan tekst, buduća website ingestion) —
  to je vektor za phishing/spoofing app chrome-a.

## 7. Storage / persistence

- `private_mode` ostaje **default (ON)** — cookies/persistent objekti se ne čuvaju
  između sesija — osim ako se eksplicitno ne odluči drugačije uz Task Contract.
- Ako se ikad promijeni: `storage_path` mora biti pod `platformdirs.user_data_dir`
  (isti pattern kao SQLite/keyring), nikad proizvoljna/hardkodirana putanja.

## 8. Ostala podešavanja — ostaju na sigurnom default-u

- `ALLOW_DOWNLOADS` — disabled by default. Ne uključivati bez eksplicitne, dokumentovane
  potrebe (npr. export ZIP paket treba ići kroz Python `save_file_dialog`, ne kroz
  browser download flow).
- `ALLOW_FILE_URLS` — disabled by default. Lokalni sadržaj se učitava kroz `url=` kao
  fajl putanju (kako to već radi `SPIKE-001/presentation_webview/spike_content_studio.py`),
  ne kroz JS-inicirane `file://` navigacije.
- `IGNORE_SSL_ERRORS` — disabled by default. Nikad uključivati.

## 9. Zavisnost / supply chain

- `pywebview==6.2.1` (i `pywin32` na Windows-u) moraju biti eksplicitno pinovani u
  `pyproject.toml` **onog trenutka** kad UI spike gate formalno zaključa pywebview kao
  izabrani framework — trenutno je instaliran ručno u shared `.venv` bez deklaracije
  (vidi `pip show pywebview`), što je prihvatljivo za spike fazu ali ne za produkcijski
  dependency graf.
- Provjeriti `github.com/r0x0r/pywebview/security` prije svakog version bump-a.

## Kad se primjenjuje

- Svaki budući Task Contract koji dira `presentation_webview/`, `js_api` bridge, ili bilo
  koji `webview.create_window`/`webview.start` poziv mora u svom read-set-u navesti ovaj
  fajl (vidi `.agent/TASK_ROUTING.md` sekciju **GUI / pywebview task**).
- Acceptance kriterijumi tog Task Contracta moraju eksplicitno provjeriti tačke 1–3 i 6
  (renderer fail-loud, debug=False, js_api allowlist, external link handling) kao
  minimalni sigurnosni gate — ostatak (CSP, font vendoring, storage) prema obimu taska.
