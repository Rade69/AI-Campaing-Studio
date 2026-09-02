# Mockup prijedlog — AI Campaign Studio (BHS)

Ovaj direktorijum sadrži **prijedlog mockup-a** za AI Campaign Studio u BHS
varijanti, na osnovu inputa Human Owner-a:

1. **Originalni product tour mockup** (dostavljen ranije)
2. **Tri inputa** dana naknadno:
   - Slike zuba i ostali vizuali su placeholderi → NE trebaju se prikazivati
   - Olivia Bennett avatar → nepotreban (single-user app, nema login UI)
   - Zahtjev za dizajn prijedlogom na osnovu mockup-a + inputa

## Šta je u prijedlogu

`index.html` — jedna stranica, 6 ekrana aplikacije u 3x2 gridu:

1. **Znanje o brendu** — brand library sa karticama (Profil, Publika, Ponuda,
   Ton komunikacije, Odobrene činjenice, Nedavne revizije, Boje i logo, Izvori)
2. **Brief kampanje** — definicija cilja, publike, ponude, kanala, formata
3. **Plan kampanje** — tabela sa 6 stavki (Problem → Edukacija → Dokaz →
   Podrška → Ponuda → Akcija), role badge-ovima u boji
4. **Studio sadržaja** (FOCUS) — primary use case, plavi ring oko kartice
5. **Pregled / Odobri / Izvezi** — 6 thumbnail kartica sa hook placeholder-ima
6. **Podešavanja / AI provajderi** — sub-nav (Profil/Tim/...), OpenAI
   aktivan, ostali provideri, status veze

`proposal_screenshot.png` — Edge headless screenshot cijele stranice
(generisan sa `edge --headless --screenshot=...`).

## Ključne dizajn odluke (reflektirane u prijedlogu)

1. **Bez placeholder slika.** Vizual paneli (lijeva kolona u Studiju,
   thumbnail-ovi u Pregledu) prikazuju hook tekst "[ Vizual ]" ili
   "Vizual će biti prikazan kada bude dostupan" sa dashed border-om.
   To signalizira dizajneru i korisniku da je vizual svjestan praznine,
   bez lažnog sadržaja.

2. **Bez login/avatar UI.** Sidebar ima BrightSmile brand karticu, ali
   bez korisničkog avatara. Single-user app, lokalno pokretanje — nema
   potrebe za profile/login UI.

3. **Sidebar na svim ekranima.** 7 navigacijskih stavki (Znanje o brendu,
   Kampanje, Studio sadržaja, Kalendar, Resursi, Analitika, Podešavanja)
   sa active state highlightom. Konvencionalan, ne mijenja layout kroz
   ekrane.

4. **Inter font.** Mockup koristi Inter (jasno po kerning/lettershape).
   Učitan preko Google Fonts-a.

5. **BHS terminologija prema originalnom mockup-u.** "Studio sadržaja",
   "Uredi/Napomene", "Brze akcije", "Provjera usklađenosti",
   "Sačuvaj nacrt", "Pošalji na reviziju" — ne izmišljana.

6. **Studio sadržaja (ekran 4) je focus ekran.** Plavi ring
   (`ring-2 ring-blue-200/60`) oko kartice označava "ovo je primary use case".

## Reprodukcija screenshot-a

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$url = "file:///" + (Resolve-Path .\index.html).Path.Replace('\','/')
& $edge --headless=new --disable-gpu --no-sandbox --hide-scrollbars `
        --window-size=1700,2000 "--screenshot=.\proposal_screenshot.png" $url
```

## Kako otvoriti

- **Browser:** dvaput klik na `index.html`, ili `start index.html` iz ovog
  direktorija. Ne treba server, sve je statičan HTML+Tailwind CDN+Inter font.
- **Screenshot:** vidi `proposal_screenshot.png` za statičan preview.

## Šta NIJE urađeno (izričito)

- Nisu renderovani pravi vizuali (slike, video) — hook tekst na njihovom mjestu
- Nema pravog logina / avatar UI-ja
- Sidebar nije collapsible (uvijek vidljiv, kao u mockup-u)
- Nema dark mode (mockup je svijetla tema)
- Nema Settings > Profil/Tim ekrana (samo AI provajderi)
- Nema Edit/Notes tab switching animacije (samo statičan "Uredi" aktivan)
- Nema Realne boje BrightSmile brenda (koriste se generičke slate/blue)

## Pitanja za Human Owner

1. Da li sidebar treba biti collapsible (samo ikone kada collapsed)?
2. Da li vizual paneli trebaju imati "Dodaj vizual" CTA (za unos novog
   slikovnog asseta) ili samo hook tekst?
3. Da li treba "Boje i logo" paleta u Brand Library da bude interaktivna
   (klik na swatch kopira hex) ili samo display?
4. Da li "Pregled kampanje" treba imati i "Vremenska linija" tab aktiviran
   u prijedlogu, ili je "Mreža" dovoljna za prvi pass?
5. Da li AI provajderi dropdown treba imati "Testiraj vezu" kao zaseban
   dijalog, ili je inline status dovoljan?
