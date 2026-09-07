---
title: "AI Campaign Studio — UX evolucija na osnovu Buffer + Later principa"
document_type: "UX/UI product design specification"
project: "AI Campaign Studio"
purpose: "Precizno opisuje kako unaprijediti sadašnji GUI bez velikog redizajna, zadržavajući jednostavnost postojećeg interfejsa i dodajući Buffer/Later principe tamo gdje stvarno donose vrijednost."
based_on: "Sadašnje ekrane Kampanje, Kalendar i Brend koje je Human Owner dostavio 2026-09-06."
status: "Design recommendation — nije automatski implementation requirement"
version: "1.0"
date: "2026-09-06"
---

# AI Campaign Studio — UX evolucija bez velikog redizajna

## 1. Osnovna odluka

Ne predlažem veliki redizajn sadašnje aplikacije.

Sadašnji vizuelni pravac je dobar:

- tamni navy sidebar;
- vrlo mali broj glavnih navigacionih stavki;
- svijetla radna površina;
- violet kao primarna akcijska boja;
- bijele kartice;
- statusne boje koje imaju značenje;
- veliki razmak između sekcija;
- bez nepotrebnog enterprise dashboard izgleda.

Najvažnija odluka je:

> **Ne praviti novi proizvod preko postojećeg GUI-ja. Nadograditi postojeći GUI tamo gdje korisniku treba više konteksta, kontrole i vizuelnog planiranja.**

Buffer nam je referenca za **jednostavnost toka**.

Later nam je referenca za **vizuelno planiranje, kalendar i preview**.

AI Campaign Studio ostaje poseban proizvod zbog:

- Approved Facts;
- provenance;
- Campaign Plan;
- Campaign Roles;
- Claim Check;
- revision history;
- AI generation;
- human approval.

---

# 2. Šta sada postoji i šta bih zadržao

Na osnovu trenutnih ekrana, globalni shell je:

```text
┌───────────────────────┬──────────────────────────────────────┐
│                       │                                      │
│   AI Campaign Studio  │          GLAVNI SADRŽAJ             │
│                       │                                      │
│   Početna             │                                      │
│   Brend               │                                      │
│   Kampanje            │                                      │
│   Kalendar            │                                      │
│                       │                                      │
│   Podešavanja         │                                      │
│                       │                                      │
│                       │                                      │
│   ● Lokalno           │                                      │
└───────────────────────┴──────────────────────────────────────┘
```

## D1 — Sidebar ostaje

Ne dodavati u sidebar:

- Studio sadržaja;
- Media Library;
- Analytics;
- Export;
- Publish;
- Team;
- Billing;
- Integrations.

Ti koncepti mogu postojati u sistemu, ali ne trebaju biti globalna navigacija dok nisu zasebni, redovno korišteni workflow-i.

Sadašnji sidebar je mnogo bliži Buffer filozofiji nego generisana ilustracija koju smo ranije napravili.

---

# 3. Vizuelni jezik koji zadržavamo

## D2 — Zadržati sadašnji design system

### Primarne površine

```text
Sidebar:        tamni navy
Canvas:         vrlo svijetla siva
Card:           bijela
Primary CTA:    violet
Positive:       emerald/mint
Warning:        amber
Error:          red
```

### Komponente koje već rade dobro

- veliki naslov ekrana;
- kratak podnaslov;
- rounded cards;
- jasni status badge-ovi;
- jedno glavno dugme po ekranu;
- jednostavni tabovi;
- dovoljno praznog prostora;
- tekstualni status uz boju.

Ne bih mijenjao osnovni vizuelni identitet samo zato što Buffer ili Later drugačije izgledaju.

---

# 4. Ekran „Kampanje“ — samo mala evolucija

## 4.1 Sadašnje stanje

Trenutno:

```text
KAMPANJA
BREND
STATUS
PLANIRANO
ZADNJA IZMJENA
[OTVORI]
```

Primjer:

```text
Proljetna kolekcija | BrightSmile | U pripremi | 6 objava | Danas 14:20 | Otvori
```

Ovaj ekran je već dobar.

Ne bih ga pretvarao u kartični dashboard.

Ne bih dodavao preview slike.

Ne bih dodavao mnogo filtera dok broj kampanja ne poraste dovoljno da to postane problem.

---

## 4.2 Jedina veća korisna dopuna: „Sljedeći korak“

Predlažem novu kolonu:

```text
SLJEDEĆI KORAK
```

Primjer:

```text
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ KAMPANJA            BREND        STATUS       SLJEDEĆI KORAK      PLANIRANO   IZMJENA   │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ Proljetna kolekcija BrightSmile  U pripremi   Dovrši opis          6 objava     Danas     │
│ Lansiranje seruma   BrightSmile  Planirano    Pregledaj sadržaj    8 objava     Jučer     │
│ Novi web-sajt       BrightSmile  Odobreno     Spremno za izvoz     5 objava     30. 8.    │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

Zašto?

`STATUS` govori:

> gdje se objekat nalazi.

`SLJEDEĆI KORAK` govori:

> šta korisnik sada treba uraditi.

To je važnija UX informacija.

---

## 4.3 „Otvori“ ostaje

Ne treba dugme mijenjati u:

- Manage;
- Edit;
- Continue;
- Open campaign workspace.

Jednostavno:

```text
Otvori
```

je dovoljno.

Ako želimo dodatno pojednostavljenje, cijeli red može kasnije biti clickable, a „Otvori“ ostaje kao jasan affordance.

---

# 5. Šta se dešava nakon „Otvori“

Ovo je mjesto gdje počinje važnija UX evolucija.

Korisnik ne treba dobiti novi sidebar.

Ulazi u **workspace jedne kampanje**.

## D3 — Campaign Workspace

Header:

```text
Kampanje / Proljetna kolekcija

Proljetna kolekcija
BrightSmile

[status]
```

I ispod toga campaign workflow:

```text
Opis kampanje
      →
Plan kampanje
      →
Kalendar
      →
Studio sadržaja
      →
Pregled i izvoz
```

Vizuelno može biti horizontalni stepper/tab bar:

```text
[1 Opis] — [2 Plan] — [3 Kalendar] — [4 Studio sadržaja] — [5 Pregled i izvoz]
```

Važno:

- prethodni koraci su uvijek dostupni;
- korisnik smije ići nazad;
- nema „wizard lock-in“ ponašanja;
- trenutni korak je jasno označen;
- status kampanje ne smije zavisiti samo od toga koji je tab otvoren.

---

# 6. Opis kampanje

## Cilj

Ovo nije mjesto za AI kompleksnost.

Treba odgovoriti na:

```text
Šta želimo postići?
Šta nudimo?
Kome?
Gdje?
Koliko sadržaja?
```

---

## 6.1 Default view

```text
Naziv kampanje
Cilj kampanje
Ponuda / ključna poruka
Primarna publika
Jezik
Broj sadržaja
```

Platforme:

```text
Instagram
Facebook
LinkedIn
TikTok
...
```

ali bez tehničkih termina.

---

## 6.2 Advanced opcije

Napredne stvari ne moraju biti stalno otvorene.

```text
▸ Dodatne opcije
```

unutra:

```text
Sekundarna publika
Posebna ograničenja
Dodatne instrukcije
Regionalna varijanta
Posebni CTA zahtjevi
```

Ovo je Buffer princip:

> korisniku odmah pokaži ono što mu treba za nastavak, ne cijelu konfiguraciju sistema.

---

# 7. Plan kampanje

Plan je mjesto između ideje i sadržaja.

Ne treba ovdje uređivati čitave postove.

## 7.1 Predloženi prikaz

Jedan CampaignItem po redu/kartici:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ 01  PROBLEM                                                       │
│ Zašto potrošači teško biraju odgovarajući proizvod               │
│ Instagram · Feed 4:5                                              │
│                                                    [Otvori] [⋮]    │
├─────────────────────────────────────────────────────────────────────┤
│ 02  EDUKACIJA                                                     │
│ Kako izabrati proizvod za svakodnevnu njegu                       │
│ LinkedIn · Post                                                   │
│                                                    [Otvori] [⋮]    │
├─────────────────────────────────────────────────────────────────────┤
│ 03  DOKAZ                                                         │
│ Ključna karakteristika proizvoda                                  │
│ Instagram · Feed 4:5                                              │
└─────────────────────────────────────────────────────────────────────┘
```

Role badge ostaje vizuelno jak:

```text
PROBLEM
EDUKACIJA
DOKAZ
PRIGOVOR
PONUDA
AKCIJA
```

---

## 7.2 Reorder

Ako domain pravila dozvoljavaju:

```text
⋮⋮
```

drag handle za promjenu redoslijeda.

Ako ne želimo odmah drag/drop:

```text
↑
↓
```

je dovoljno za MVP.

---

## 7.3 Plan nije editor

Ne treba ovdje imati:

- Rewrite;
- Shorten;
- Hashtags;
- Claim Check;
- Visual Editor.

To pripada Studiju sadržaja.

---

# 8. Globalni Kalendar — sadašnje stanje je dobra osnova

Trenutni Kalendar već radi bitnu stvar:

```text
Globalni pregled planiranih objava.
Ovo nije social publishing niti auto-posting.
```

To je ispravno.

Problem nije koncept, nego količina informacija u kartici.

---

# 9. Kalendar — Later princip bez velikog redizajna

## 9.1 Sadašnji izgled ostaje month grid

Ne mijenjati u kompleksni planner.

Zadržati:

```text
PON | UTO | SRI | ČET | PET | SUB | NED
```

---

## 9.2 Dodati kontrolu mjeseca

Trenutno postoji `Danas`.

Dodati:

```text
[‹] Septembar 2026 [›]             [Danas]
```

Opcionalno:

```text
[Mjesec] [Sedmica]
```

`List` view može doći kasnije ako se pokaže potreba.

---

## 9.3 Kartica u kalendaru treba biti malo informativnija

Sada:

```text
Proljetna kolekcija
· Problem
```

Predlažem:

```text
Instagram
10:00
Proljetna kolekcija
Problem
```

ili kompaktnije:

```text
[IG] 10:00
Proljetna kolekcija
PROBLEM
```

Vizuelni primjer:

```text
┌──────────────────┐
│ IG        10:00  │
│ Proljetna        │
│ kolekcija        │
│ PROBLEM          │
└──────────────────┘
```

Ne treba puni caption.

Ne treba velika slika.

---

## 9.4 Boja kartice ne smije biti jedini nosilac značenja

Ako violet znači `PROBLEM`, korisnik i dalje mora vidjeti tekst:

```text
PROBLEM
```

Ako emerald znači `DOKAZ`, mora pisati:

```text
DOKAZ
```

Status/role nikad samo bojom.

---

# 10. Klik na Calendar Item

Ovdje bih uveo Later-style brzi pregled.

Ne otvarati odmah cijeli Studio.

Klik na kalendarsku karticu otvara desni panel ili mali details drawer:

```text
┌──────────────────────────────────────────┐
│ Proljetna kolekcija                      │
│                                          │
│ Instagram · Feed 4:5                     │
│ 3. septembar · 10:00                     │
│                                          │
│ PROBLEM                                  │
│                                          │
│ "Kako izabrati..."                       │
│                                          │
│ Status: Planirano                        │
│                                          │
│ [Otvori u Studiju]                       │
│ [Promijeni termin]                       │
└──────────────────────────────────────────┘
```

To daje vizuelni context bez napuštanja kalendara.

---

# 11. Globalni vs Campaign Kalendar

Mora biti potpuno jasno da postoje dva pogleda.

## Globalni Kalendar

Sidebar:

```text
Kalendar
```

Pokazuje:

```text
sve kampanje
sve planirane sadržaje
```

Header:

```text
Kalendar
Globalni pregled svih planiranih sadržaja
```

---

## Campaign Kalendar

Unutar otvorene kampanje:

```text
Proljetna kolekcija
→ Kalendar
```

Pokazuje samo:

```text
Proljetna kolekcija
```

Header:

```text
Kalendar kampanje
Proljetna kolekcija
```

Ne pravimo dva sistema.

To su dva filtera nad istim podacima.

---

# 12. Brend — sadašnje stanje je dobro strukturirano

Trenutni Brend ekran ima:

```text
Osnovni podaci
Odobrene činjenice
Glas brenda
Brend resursi
```

i status:

```text
✓ Provjereno i ažurno
Posljednja provjera: ...
```

Ovo je dobar pravac.

Ne treba veliki redizajn.

---

# 13. Brend — šta bih promijenio

## D4 — Dodati „Ciljna publika“ kao zaseban tab

Trenutno je `Primarna publika` prikazana unutar `Osnovni podaci`.

Za stvarni Campaign Engine, publika je dovoljno važna da zaslužuje zaseban prostor.

Predloženi tabovi:

```text
Osnovni podaci
Odobrene činjenice
Glas brenda
Ciljna publika
Brend resursi
```

Ne mora biti implementirano odmah ako domain još nije spreman, ali je to ciljna UX struktura.

---

# 14. Osnovni podaci

Trenutni sadržaj:

```text
BrightSmile Oral Care
Opis brenda
Primarna publika
Glas brenda badge-ovi
```

Kasnije, kada se `Ciljna publika` izdvoji:

```text
Naziv brenda
Opis brenda
Web stranica
Industrija/kategorija
Primarni jezik
Regionalna varijanta
```

Glas brenda se može samo sažeto prikazati:

```text
Glas: Jasan · Pouzdan · Nenametljiv
[Otvori Glas brenda]
```

---

# 15. Odobrene činjenice — ovo treba postati jedan od najvažnijih UX ekrana

Trenutno:

```text
F-001 — Proizvod ne sadrži alkohol u formulaciji.
F-002 — Pakovanje sadrži 500 ml.
F-003 — Dostupno u tri varijante ukusa.
```

To je dobra početna forma.

Kasnije svaki Fact treba moći pokazati provenance.

---

## 15.1 Collapsed row

```text
F-002
Pakovanje sadrži 500 ml.

[ODOBRENO]                 [›]
```

---

## 15.2 Expanded row

```text
F-002
Pakovanje sadrži 500 ml.

Status: Odobreno

Izvor:
https://example.com/product-x

Provjereno:
06.09.2026.

Originalni dokaz:
"Pakovanje: 500 ml"

[Otvori izvor]
[Uredi]
[Supersede]
```

Ovo je mjesto gdje naša fact-first arhitektura postaje vidljiva korisniku.

---

# 16. „Osvježi podatke“ dobija mnogo veći smisao kada Website Ingestion postoji

Trenutno dugme:

```text
Osvježi podatke
```

je vizuelno dobro mjesto.

Kada uvedemo real Website Ingestion:

```text
Osvježi podatke
↓
provjeri sajt
↓
pronađi promjene
↓
kreiraj Fact Candidates
↓
korisnik odobrava
```

Važno:

`Osvježi podatke` ne smije automatski mijenjati Approved Facts.

---

## 16.1 Primjer promjene

```text
Pronađene 2 promjene

Cijena proizvoda
29,90 KM → 34,90 KM

[Pregledaj]
```

Tek nakon odobrenja:

```text
stari Fact → SUPERSEDED
novi Fact → APPROVED
```

---

# 17. Glas brenda — ne ostaviti ga kao nekoliko badge-ova

Trenutni ekran pravilno kaže da editor još nije dostupan.

Ciljna verzija treba razlikovati:

```text
opisne karakteristike
+
pravila
+
stvarne primjere
```

---

## 17.1 Predložena struktura

```text
Glas brenda

Osobine
[Jasan] [Pouzdan] [Nenametljiv]

Preferirani izrazi
+ "svakodnevna njega"
+ "jednostavno"

Izbjegavati
- "garantovano"
- "najbolji na tržištu"

Primjeri stvarnog sadržaja
────────────────────────────
"Naš cilj je..."
[Izvor: Instagram, 12.05.2026]

"Za svakodnevnu..."
[Izvor: Web stranica]
```

Ne uvoditi lažni:

```text
Brand Voice Score: 93%
```

---

# 18. Brend resursi — zadržati jednostavno

Trenutno:

```text
Logo
Paleta boja
Izvori
```

To je dobro.

Ne treba od toga praviti Digital Asset Management sistem.

Kasnije se mogu dodati:

```text
Logo
Boje
Fontovi
Fotografije
Product visuals
Dokumenti
Izvori
```

ali samo ako Campaign Visual System stvarno koristi te resurse.

---

# 19. Najveća UX promjena: Studio sadržaja

Ovo je jedini dio gdje bih svjesno napravio veći layout.

Ne novi vizuelni identitet.

Nego novi **radni prostor**.

---

# 20. Studio sadržaja — Buffer + Later + ACS

Cilj:

> korisnik istovremeno uređuje sadržaj, vidi rezultat i zna da li sadržaju može vjerovati.

Predloženi desktop layout:

```text
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ Proljetna kolekcija / Studio sadržaja                                               │
│                                                                                     │
│ [← prethodni]   03 / 06 · DOKAZ                               [sljedeći →]           │
├──────────────────────────────┬──────────────────────────────┬────────────────────────┤
│                              │                              │                        │
│ CONTENT EDITOR               │ LIVE PREVIEW                 │ CONTENT CHECK          │
│                              │                              │                        │
│ Instagram · Feed 4:5         │   Instagram preview          │ ✓ 3 činjenice          │
│                              │                              │ ✓ 0 unsupported         │
│ Hook                         │   ┌──────────────────────┐   │                        │
│ [........................]   │   │                      │   │ Korištene činjenice    │
│                              │   │      VISUAL          │   │ F-001                  │
│ Caption                      │   │                      │   │ F-003                  │
│ [........................]   │   └──────────────────────┘   │ F-007                  │
│ [........................]   │                              │                        │
│                              │   caption...                 │ [Detalji]              │
│ CTA                          │                              │                        │
│ [........................]   │                              │                        │
│                              │                              │                        │
│ [Skrati] [Prepiši]           │                              │                        │
│ [Poboljšaj uvod]             │                              │                        │
│ [Promijeni ton]              │                              │                        │
│                              │                              │                        │
├──────────────────────────────┴──────────────────────────────┴────────────────────────┤
│ Sačuvano · Revizija 7 · prije 12 s                                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 21. Zašto tri kolone

## Lijevo — korisnik radi

```text
Editor
AI Quick Actions
metadata
```

## Sredina — korisnik vidi posljedicu

```text
platform preview
format
visual
caption
```

## Desno — korisnik vidi povjerenje

```text
facts
claims
warnings
validation
```

Ovo je mnogo jače od tab-only pristupa jer korisnik ne mora stalno skakati:

```text
Sadržaj
→ činjenice
→ nazad
→ preview
→ nazad
```

---

# 22. Ako je ekran premalen

Na užem desktopu:

```text
Editor | Preview
```

a Content Check postaje drawer:

```text
[Provjera  ✓]
```

Ne pokušavati zadržati tri uske kolone po svaku cijenu.

---

# 23. Quick Actions — AI mora djelovati konkretno

Ne:

```text
✨ Improve
```

nego:

```text
Skrati
Prepiši
Poboljšaj uvod
Promijeni ton
Generiši varijantu
```

Zašto?

Korisnik zna šta će se promijeniti.

---

# 24. AI akcija ne smije tiho prepisati sadržaj

Poslije:

```text
Poboljšaj uvod
```

sistem pravi:

```text
Revision 8
```

i UI kaže:

```text
Nova varijanta je generisana.

[Zadrži]
[Vrati prethodnu verziju]
```

---

# 25. Save status mora biti stvaran

Permanentni mali status:

```text
Sačuvano · Revizija 7
```

Tok:

```text
Uređeno
↓
Čuvanje...
↓
Sačuvano · Revizija 8
```

Nikada:

```text
Sačuvano ✓
```

samo zato što je kliknuto dugme.

---

# 26. Content Check

Desna kolona ne treba imati generički „Quality 92%“.

Treba prikazati konkretne provjere.

Primjer:

```text
Provjera sadržaja

✓ 3 korištene činjenice
✓ 0 nepodržanih tvrdnji
✓ Nema zabranjenih izraza
✓ Format odgovara Instagram Feed 4:5

AI procjena tona
  Uglavnom odgovara glasu brenda
```

Važno:

```text
deterministička provjera
≠
AI advisory procjena
```

Vizuelno ih odvojiti.

---

# 27. Korištene činjenice

U Content Check panelu:

```text
Korištene činjenice

F-002
Pakovanje sadrži 500 ml.
[Odobreno]

F-007
Dostupno u tri varijante.
[Odobreno]
```

Klik:

```text
izvor
datum
evidence
```

To je jedan od glavnih ACS diferencijatora.

---

# 28. Preview

Preview treba pokazati:

```text
Instagram
Feed 4:5
```

ne samo generičku karticu.

Za drugi target:

```text
LinkedIn
Post
```

layout se mijenja.

Preview mora biti:

- platform-aware;
- format-aware;
- aspect-ratio aware.

Ali ne smijemo tvrditi da je pixel-perfect kopija društvene mreže ako nije.

---

# 29. Pregled i izvoz

Ovdje korisnik ne treba uređivati kampanju.

Treba odgovoriti na jedno pitanje:

> Da li je spremna?

---

## 29.1 Summary

```text
Proljetna kolekcija

6 sadržaja
3 platforme
6 vizuala
```

---

## 29.2 Hard checks

```text
✓ Svi sadržaji imaju target
✓ Sve FACT tvrdnje imaju podršku
✓ Nema prohibited termina
✓ Nema layout overflowa
✓ Svi potrebni vizuali postoje
```

Ako nešto nije prošlo:

```text
2 problema treba riješiti
```

---

## 29.3 Advisory

Odvojeno:

```text
AI procjena

Ton: uglavnom usklađen
Raznolikost CTA: dobra
```

Ne prikazivati advisory kao green deterministic gate.

---

## 29.4 Export

Jedan glavni CTA:

```text
[Izvezi kampanju]
```

Korisnički izbor:

```text
✓ slike
✓ tekst objava
✓ campaign summary
```

Tehnički manifest može biti automatski uključen.

---

# 30. Šta ne bih radio

## N1 — Ne bih redizajnirao sidebar

Sadašnji je bolji od velikog enterprise sidebara.

## N2 — Ne bih dodao „Studio sadržaja“ kao globalnu navigaciju

Studio pripada kampanji.

## N3 — Ne bih stavio Analytics sada u sidebar

Performance modul, kada stvarno dođe, treba prvo dokazati svoj workflow.

## N4 — Ne bih dodao Publish/Auto-posting sada

Kalendar ostaje planiranje.

## N5 — Ne bih pretvorio Kampanje u card gallery

Tabela je efikasnija.

## N6 — Ne bih stavljao thumbnail na svaki Campaign row

Previše vizuelnog šuma za listu kampanja.

## N7 — Ne bih napravio Brand screen kao dashboard sa skorovima

Brand je source-of-truth workspace.

## N8 — Ne bih uvodio AI chat panel na svakom ekranu

AI treba biti kontekstualna funkcija, ne stalni element.

---

# 31. Prioritet izmjena

## P0 — zadržati / popraviti sada

```text
Sidebar
Kampanje table
Brand tabs
Global calendar
```

Minimalne promjene.

---

## P1 — sljedeća UX vrijednost

1. Campaign Workspace stepper;
2. „Sljedeći korak“ u Campaigns listi;
3. bolja Calendar Item kartica;
4. Calendar details drawer;
5. month navigation;
6. jasna razlika Global / Campaign calendar.

---

## P2 — najveći UX rad

1. Studio sadržaja 3-column layout;
2. Live Preview;
3. Quick Actions;
4. Fact/Claim panel;
5. Revision status + Undo;
6. real error/loading states.

---

## P3 — Brand maturity

1. Ciljna publika tab;
2. provenance za facts;
3. Brand Voice editor;
4. real examples;
5. Website refresh / Fact Candidates;
6. source freshness.

---

# 32. Konkretne izmjene na ekranima koje si poslao

## Kampanje.png

### Zadržati

- naslov i podnaslov;
- `+ Nova kampanja`;
- tabelu;
- status badge;
- `Otvori`;
- sadašnji spacing.

### Dodati

- `Sljedeći korak`.

### Ne dodavati

- thumbnail;
- analytics;
- platform icons u ovom viewu;
- campaign preview card.

---

## Kalendar.png

### Zadržati

- month grid;
- `Danas`;
- globalni scope;
- jasnu napomenu da nije auto-posting.

### Promijeniti

Header kontrole:

```text
[‹] Septembar 2026 [›]     [Mjesec] [Sedmica]     [Danas]
```

Calendar item:

```text
[IG] 10:00
Proljetna kolekcija
PROBLEM
```

Klik:

```text
details drawer
```

### Ukloniti / doraditi

Trenutna napomena sadrži:

```text
Napomena: Napomena:
```

dupliranje treba ukloniti.

Konačno:

```text
Napomena: Kalendar prikazuje planirane termine unutar aplikacije.
AI Campaign Studio trenutno ne objavljuje automatski na društvene mreže.
```

Kraće i jasnije.

---

## Brand — Osnovni podaci

### Zadržati

- `Provjereno i ažurno`;
- datum zadnje provjere;
- tab strukturu;
- card style.

### Kasnije

- premjestiti publiku u `Ciljna publika`;
- zadržati samo summary glasa brenda.

---

## Brand — Odobrene činjenice

### Zadržati

- F-ID;
- čist list view;
- `Prikaži sve činjenice`.

### Dodati kasnije

- status;
- source;
- last checked;
- expand details;
- superseded stanje.

---

## Brand — Glas brenda

Trenutni placeholder je prihvatljiv dok funkcija nije implementirana.

Ciljna verzija:

```text
traits
preferred terms
forbidden terms
real examples
```

Ne samo adjective badge-ovi.

---

## Brand — Resursi

### Zadržati

- Logo;
- Paleta boja;
- Izvori;
- `Dodaj resurs`.

### Kasnije

Dodati samo resurse koje renderer stvarno koristi.

---

# 33. Predložena ciljna mapa aplikacije

Globalno:

```text
Početna
Brend
Kampanje
Kalendar

Podešavanja
```

Kampanja:

```text
Kampanje
  └── Proljetna kolekcija
       ├── Opis kampanje
       ├── Plan kampanje
       ├── Kalendar
       ├── Studio sadržaja
       └── Pregled i izvoz
```

Brend:

```text
Brend
  ├── Osnovni podaci
  ├── Odobrene činjenice
  ├── Glas brenda
  ├── Ciljna publika
  └── Brend resursi
```

Ovo je dovoljno.

---

# 34. Mentalni model korisnika

Korisnik ne treba razumjeti internu arhitekturu.

On treba razumjeti:

```text
1. Moj brend je spreman.
2. Kreiram kampanju.
3. Pregledam plan.
4. Vidim kada sadržaj ide.
5. Uredim svaki sadržaj i odmah vidim preview.
6. Provjerim da tvrdnje imaju izvor.
7. Odobrim.
8. Izvezem.
```

Ako GUI uspije da prenese tih osam koraka, arhitektura je pravilno prevedena u proizvod.

---

# 35. Buffer + Later, precizno prevedeno na ACS

## Od Buffera uzimamo

```text
jednostavan navigation model
jasan next action
malo odluka po ekranu
brzo uređivanje sadržaja
konkretne akcije
status koji se lako razumije
```

## Od Latera uzimamo

```text
visual calendar
calendar item preview
platform/format awareness
editor + live preview
vizuelni osjećaj kampanje kroz vrijeme
```

## Ono što je samo naše

```text
Approved Facts
FactCandidate
provenance/evidence
Claim Check
Campaign Roles
immutable revisions
deterministic gates
human approval
```

---

# 36. Finalni princip dizajna

Ne treba da AI Campaign Studio izgleda kao kopija Buffera ili Latera.

Treba da korisnik osjeti:

```text
Buffer jednostavnost
+
Later vizuelno planiranje
+
ACS pouzdanost
```

Najvažniji dizajn princip:

> **Kompleksnost ostaje u sistemu; korisnik vidi samo kontekst, sljedeću akciju, rezultat i dokaz.**

To je pravac u kojem bih razvijao sadašnji GUI.

Ne bih rušio postojeću aplikaciju.

Nadogradio bih je.
