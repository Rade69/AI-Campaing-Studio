# Mockup prijedlog v2 — Maksimalno blizu izvornom mockup-u

V2 prijedlog: **svaki ekran kao zaseban HTML fajl** na viewport-u 1440x900,
sa punim sidebar-om (256px), svim mockup detaljima (verifikovano badge, izvezi
paket dugme, sve navigacione stavke sa ikonama, "Prikaži sve činjenice" link,
"Pregledaj činjenice" link, "Prikaži svih 10 izvora" link, BRIGHTSMILE logo
sa bojama, character counter-i za headline i caption).

V1 prijedlog (u `mockup_proposal/`) je bio komprimiran u 3x2 grid sa 8-10px
fontovima — previše kompaktno. V2 ispravlja to sa:
- Punom širinom svakog ekrana (1440x900)
- Stvarnim sidebar-om (256px) sa svim mockup detaljima
- Većim fontovima (10-14px) bližim mockup-u
- Specifičnim dizajn elementima (boje, badge-ovi, linkovi, ikonice)
- Bez placeholder slika (samo hook tekst ili [Vizual] label)

## Struktura

```
mockup_proposal_v2/
├── brand/index.html        # 1. Znanje o brendu (8 brand library kartica)
├── brief/index.html        # 2. Brief kampanje (cilj, publika, ponuda, kanali)
├── plan/index.html         # 3. Plan kampanje (6-redna tabela sa role badge-ovima)
├── studio/index.html       # 4. Studio sadržaja (3 kolone, FOCUS)
├── pregled/index.html      # 5. Pregled (6 thumbnail kartica sa [Vizual] hook-om)
├── settings/index.html     # 6. Podešavanja / AI provajderi
├── studio/screenshot.png   # Edge headless capture 1440x900 (uspješan)
└── README.md               # ovaj fajl
```

## Ključne dizajn odluke (reflektirane u prijedlogu)

1. **Stvarni sidebar (256px)** na svakom ekranu — sa BrightSmile brand karticom,
   "Verifikovano i ažurno" zelenim badge-om, 7 navigacijskih stavki sa SVG
   ikonama (Znanje o brendu, Kampanje, Studio sadržaja, Kalendar, Resursi,
   Analitika, Podešavanja), i "Izvezi paket brenda" dugmetom na dnu.

2. **Inter font** učitan preko Google Fonts-a, weight 400/500/600/700.

3. **BHS terminologija** prema originalnom mockup-u — "Studio sadržaja",
   "Uredi/Napomene", "Brze akcije", "Provjera usklađenosti", "Sačuvaj nacrt",
   "Pošalji na reviziju", "Verifikovano i ažurno", "Pregledaj sadržaj",
   "Prikaži svih 10 izvora", "Izvezi paket brenda".

4. **Bez placeholder slika** — vizual paneli (Studio lijeva kolona, Pregled
   thumbnail-ovi) prikazuju hook tekst ("Vizual će biti prikazan kada AI
   ingestion dovede asset sa web stranice brenda") ili "[ Vizual ]" labelu
   sa svijetlo sivom pozadinom.

5. **Bez login/avatar UI** — sidebar nema korisnički avatar, nema login dropdown.
   Single-user app, lokalno pokretanje.

6. **BrightSmile boja** (cyan-500 → blue-600) korištena za brand avatar u
   sidebar-u, konzistentno kroz sve ekrane.

## Kako otvoriti

- **Browser:** otvori bilo koji `*/index.html` dvaput klikom, ili
  `start brand\index.html` iz `mockup_proposal_v2/` direktorijuma. Ne treba
  server, sve je statičan HTML+Tailwind CDN+Inter font.

- **Screenshots:** vidi `studio/screenshot.png` (uspješan). Edge headless
  prestao je generisati screenshot-ove tokom batch pokretanja — vidi
  "Poznata ograničenja" ispod.

## Reprodukcija screenshot-a (za studio, ručno)

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$url = "file:///" + (Resolve-Path studio\index.html).Path.Replace('\','/')
& $edge --headless=new --disable-gpu --hide-scrollbars `
        --window-size=1440,900 $url --screenshot=studio\screenshot.png
```

## Poznata ograničenja

- **Screenshot-ovi za 5 od 6 ekrana nisu generisani.** Edge headless
  prestao je da generiše izlaz tokom batch pokretanja (vjerovatno zbog
  akumulacije starih msedge.exe / msedgewebview2.exe procesa u pozadini).
  Studio screenshot je uspješno generisan (185KB, 1440x900). Za ostale
  ekrane, korisnik može otvoriti HTML fajlove direktno u browseru.

- **Hardcoded BrightSmile brend.** Avatar, boje, logo imaju demo-podatke
  (cyan-500 → blue-600 gradient, "BS" tekst, "W" square logo). Za
  produkciju, ovo treba biti data-driven iz brand settings.

- **Nema interaktivnosti.** Sidebar navigacija, tab switching, dropdown-ovi
  su statični (active state vizuelno, bez JS event handlera).

- **Nema dark mode.** Mockup je svijetla tema.

- **Nema multi-window modela.** Svaki ekran je zaseban HTML, ne postoji
  Settings modal ili About dijalog.

## Pitanja za Human Owner

1. **Veličina ekrana** — da li je 1440x900 odgovarajući default za review,
   ili trebam ponuditi i 1280x800 + 1920x1080 varijante?
2. **Sidebar collapsible?** — u mockup-u je uvijek vidljiv. Trebam li
   dodati collapse toggle (samo ikone)?
3. **BrightSmile brending** — da li "BS" avatar + "Oralna njega" + cyan
   gradient odgovaraju, ili treba drugačije boje/ikona?
4. **Vizual placeholder** — da li "Vizual će biti prikazan kada AI
   ingestion dovede asset..." tekst ima smisla, ili treba kraći hook
   ("Nema vizuala", "[Slika]", "Učitaj sliku")?
5. **Top bar verzija** — "v1.0" oznaka u top baru: zadržati ili ukloniti?
6. **Settings sub-nav** — da li je 7 stavki (Profil, Tim, Podešavanja
   brenda, AI provajderi, Integracije, Fakturisanje, Preferencije) dovoljno
   ili treba više/ manje?
