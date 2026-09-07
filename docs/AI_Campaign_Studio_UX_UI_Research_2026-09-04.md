# AI Campaign Studio — dubinsko UX/UI istraživanje konkurentskih alata

**Datum:** 2026-09-04  
**Fokus:** UX/UI obrasci, korisničke žalbe, pouzdanost interakcije i implikacije za AI Campaign Studio  
**Status:** istraživački dokument / preporuke, nije automatski product requirement

---

## 1. Cilj istraživanja

Cilj nije kopirati Jasper, Hootsuite, Buffer, Later, Sprout Social, Canva, Mailchimp, Metricool, SocialBee, Meta Business Suite ili HubSpot.

Cilj je pronaći:

1. na šta se korisnici tih alata najčešće žale;
2. koje UX obrasce korisnici posebno hvale;
3. gdje se pojavljuju problemi sa povjerenjem u sistem;
4. koje probleme stvara feature bloat;
5. kako AI mijenja klasična UX pravila;
6. šta AI Campaign Studio treba svjesno **izbjeći**;
7. šta možemo preuzeti kao princip bez kopiranja proizvoda.

---

## 2. Metodologija

Istraživanje je koristilo tri grupe izvora.

### 2.1 Recenzije stvarnih korisnika

Primarno:

- G2 recenzije za Jasper
- Hootsuite
- Sprout Social
- Buffer
- Later Social
- SocialBee
- Metricool
- Canva
- Mailchimp
- HubSpot Marketing Hub

G2 nije savršen izvor i dio recenzija je incentivized, pa pojedinačnu recenziju ne tretiramo kao dokaz opšteg ponašanja. Veću težinu imaju obrasci koji se ponavljaju kroz veliki broj recenzija i više proizvoda.

### 2.2 Community izvori

Reddit diskusije korištene su prvenstveno za:

- stvarne workflow frustracije;
- detaljne failure scenarije;
- slučajeve gdje UI prikazuje uspjeh, a stvarno stanje nije jasno;
- preview/publishing probleme.

Reddit se ne koristi kao statistički izvor.

### 2.3 UX/HCI izvori

Za prevođenje korisničkih žalbi u dizajn principe korišteni su:

- Nielsen Norman Group — usability heuristics i progressive disclosure
- Microsoft HAX — Guidelines for Human-AI Interaction
- Google PAIR — People + AI Guidebook
- W3C WCAG 2.2 — errors, focus, input assistance i accessibility

---

## 3. Executive summary

Najvažniji rezultat istraživanja:

> **AI Campaign Studio ne treba pobijediti konkurenciju brojem funkcija. Treba pobijediti jasnoćom, kontrolom, pouzdanošću i povjerenjem u rezultat.**

Korisnici najčešće pozitivno reaguju na proizvode koji:

- imaju čist i predvidljiv workflow;
- daju dobar vizuelni pregled kalendara;
- jasno prikazuju šta je zakazano, završeno ili pogriješilo;
- omogućavaju da se sadržaj lako prilagodi različitim platformama;
- čuvaju rad i istoriju izmjena;
- ne tjeraju korisnika da pamti gdje se nešto nalazi;
- ne zatrpavaju početnika naprednim opcijama.

Najčešće negativne teme:

- previše funkcija i “težak” interfejs;
- silent failure;
- preview koji nije vjeran finalnom rezultatu;
- status “uspjelo” kada korisnik nije siguran da je stvarno uspjelo;
- nedovoljno jasne greške;
- ograničenja platformi koja postanu vidljiva tek na kraju;
- generičan AI sadržaj;
- napredne funkcije sakrivene ili teško otkrivene;
- slaba organizacija media asseta;
- slaba verzijska istorija ili recovery;
- analytics sa puno brojeva, ali malo objašnjenja.

---

# 4. Glavni nalazi

## F1 — Feature bloat je stvarni UX problem

Hootsuite korisnici navode da je platforma moćna, ali da može djelovati “heavy”, sa mnogo sekcija i postavki i realnim learning curveom.

SocialBee dobija sličan feedback: korisnici hvale funkcionalnost, ali feature-rich početno iskustvo može biti overwhelming.

HubSpot Marketing Hub dobija pohvale jer centralizuje rad, ali kompleksniji reporting, customization i workflows traže učenje.

Mailchimp pokazuje isti paradoks: početni workflow je pristupačan, a kako se aktivira više funkcija, interfejs može početniku djelovati preopterećeno.

**Zaključak:** “Više funkcija” i “bolji UX” nisu isto.

### Preporuka za ACS

Glavni sidebar MVP-a treba ostati mali:

```text
Početna
Brend
Kampanje
Kalendar
Podešavanja
```

Ne uvoditi kao top-level stavke dok nisu stvaran, aktivan workflow:

- Analitika
- Tim
- Fakturisanje
- Integracije
- globalni Izvoz
- Resursi bez jasnog use-casea

**UX princip:** Progressive disclosure.

---

## F2 — Vizuelni kalendar je jedan od najhvaljenijih dijelova social marketing alata

Later Social korisnici posebno hvale drag-and-drop calendar, vizuelno planiranje i mogućnost da vide kako sadržaj izgleda kao cjelina.

Sprout Social korisnici redovno ističu clean calendar view.

Metricool korisnici vizuelni calendar navode kao jednu od najkorisnijih stvari za organizaciju.

Buffer korisnici hvale jednostavan scheduling workflow i jasan calendar.

**Zaključak:** Kalendar nije sekundarni ukras. Za marketera je kalendar često glavni mentalni model kampanje.

### Preporuka za ACS

```text
Globalni Kalendar
→ sve kampanje i planirani sadržaji

Campaign Kalendar
→ samo sadržaji trenutne kampanje
```

Isti underlying podaci, različit scope.

---

## F3 — Preview mora biti vjerodostojan, ne dekorativan

Later korisnici posebno cijene Instagram preview jer mogu procijeniti vizuelni raspored.

Buffer korisnici prijavljuju frustraciju kada preview nije dovoljno dobar ili “seamless”.

Reddit korisnici social schedulera direktno navode frustraciju kada preview ne odgovara stvarnom cropu/izgledu na platformi.

Meta Business Suite ima slučajeve gdje preview izgleda ispravno prije publish-a, a nakon automatskog publish-a link preview izgubi sliku.

**Zaključak:** Preview koji lažno uvjerava korisnika je gori od nedostatka previewa.

### Preporuka za ACS

Preview treba biti:

- format-aware;
- aspect-ratio aware;
- platform-aware;
- jasno označen kao preview, ne kao garantovani pixel-perfect prikaz platforme ako to ne možemo dokazati.

---

## F4 — Visibility of system status je kritična

Najgori obrazac se vidi u Meta Business Suite primjerima:

```text
UI kaže:
"Post scheduled successfully"

ali:
post nije vidljiv u Planneru.
```

U nekim slučajevima post ipak bude objavljen, u drugim nije. Korisnik više ne zna da li da ponovi operaciju i rizikuje duplikat.

### Preporuka za ACS

Nikada:

```text
Sačuvano ✓
```

samo zato što je korisnik kliknuo dugme.

Radije:

```text
Čuvanje...
↓
Sačuvano
Revizija 4
21:37
```

AI job:

```text
Generisanje...
3/6 sadržaja završeno
[Otkaži]
```

Failure:

```text
Generisanje nije završeno.

Završeno: 3/6
Nije generisano: 3/6
Razlog: provider rate limit

[Pokušaj ponovo samo neuspjele]
```

**Princip:** System status mora odražavati dokazano stanje, ne namjeru.

---

## F5 — Silent failure je posebno štetan

Sprout Social korisnik opisuje da post ponekad ne ode live, a Sprout ne ukaže jasno da je nešto pošlo pogrešno.

Meta Business Suite ima prijavljene slučajeve gdje upload nestane bez error poruke i slučajeve beskonačnog “scheduling” spinnera.

### Preporuka za ACS

Svaka neuspjela operacija treba dati:

1. šta nije uspjelo;
2. šta je ostalo sačuvano;
3. zašto, ako znamo;
4. šta korisnik može uraditi.

Loše:

```text
Something went wrong.
```

Bolje:

```text
Nije moguće generisati vizual.

Tekst objave je sačuvan.
Image provider nije podešen.

[Podesi provider]
[Nastavi bez vizuala]
```

Error ne smije biti označen samo crvenom bojom.

---

## F6 — AI mora biti lako ispraviti i poništiti

Microsoft HAX posebno preporučuje:

- Support efficient invocation
- Support efficient dismissal
- Support efficient correction
- Scope services when in doubt
- Make clear why the system did what it did

Google PAIR isto naglašava feedback, kontrolu i trust calibration.

Jasper korisnici često opisuju generic/repetitive output, neprecizan context/tone, dodatno editovanje i fact checking.

To znači da naš UI mora dizajnirati AI kao **editable collaborator**, ne kao autoritet.

### Preporuka za Studio sadržaja

Quick Actions ostaju vidljive:

```text
Prepiši
Skrati
Poboljšaj uvod
Promijeni ton
Generiši varijantu
```

Svaka AI transformacija mora:

- napraviti novu revision;
- omogućiti Undo;
- ne prepisati approved sadržaj tiho;
- jasno pokazati šta je izmijenjeno.

---

## F7 — AI povjerenje ne treba graditi “AI scoreom”, nego dokazom

Google PAIR naglašava da AI proizvodi trebaju kalibrisati povjerenje: objasniti šta AI može, ograničenja i relevantno porijeklo rezultata.

Microsoft HAX preporučuje da sistem po mogućnosti objasni zašto je nešto uradio.

### ACS prednost

Naš fact-first pristup omogućava mnogo bolji trust UX od generičkog AI scorea.

### Preporuka

U Studio sadržaja:

```text
Korištene činjenice (3)
```

Klik otvara:

```text
F12 — Fluoride toothpaste, 1450 ppm
Izvor: product-page snapshot
Status: Odobreno
```

Claim Check:

```text
3 tvrdnje podržane činjenicama
0 nepodržanih tvrdnji
1 kreativna/opinion tvrdnja
```

### Ne raditi

```text
AI Confidence: 94%
```

ako taj broj nije statistički kalibrisan i validiran.

---

## F8 — Autosave, verzije i recovery nisu luksuz

Canva korisnici pominju da version history i folder organization mogu biti bolji.

AI alati povećavaju rizik jer jedno dugme može zamijeniti veliki dio teksta.

### Preporuka

Studio treba stalno imati nenametljiv status:

```text
Sačuvano prije 12 s
Revizija 7
```

i dostupnu:

```text
Istorija verzija
```

Manual edit, AI rewrite, tone change i regeneration treba da budu recoverable.

---

## F9 — Jedan sadržaj za sve platforme nije dovoljan

Later korisnici hvale mogućnost da prilagode isti sadržaj različitim platformama, a istovremeno prijavljuju platform-specific gaps: Reels music, locations, LinkedIn PDF, ratio i caption ograničenja.

Hootsuite/Sprout korisnici takođe navode tagging i publishing razlike.

### Preporuka

ACS zadržava:

```text
CHANNEL
→ PLATFORM
→ FORMAT
```

U Campaign Plan:

```text
Instagram · Feed 4:5
LinkedIn · Post
Facebook · Feed
```

U Studio editoru format-specific polja prikazivati samo kada su relevantna.

---

## F10 — Media/brand asset organizacija brzo postaje UX bottleneck

Later korisnici eksplicitno traže foldere za fotografije/video jer library postaje convoluted.

Drugi Later korisnici hvale tag-based media organization.

Canva korisnici pominju folder organization kao područje za poboljšanje.

### Preporuka za ACS

Ne praviti generički top-level “Resursi”.

Bolje:

```text
Brend
  → Brend resursi
```

Kasnije:

- logo;
- fotografije;
- product assets;
- approved visuals;
- source documents.

---

## F11 — Onboarding treba biti task-oriented

Sprout Social korisnici cijene kada junior korisnici brzo postanu produktivni.

SocialBee je koristan, ali njegov feature richness može početno overwhelmati.

Mailchimp može biti vrlo pristupačan, ali napredniji UI postaje overwhelming za početnika.

### Preporuka

Početna ne treba biti “control room” sa 25 KPI kartica.

Primarni CTA:

```text
Nova kampanja
```

Sekundarni:

```text
Nastavi posljednju kampanju
```

Ako nema brenda:

```text
1. Dodaj podatke o brendu
2. Provjeri činjenice
3. Kreiraj prvu kampanju
```

---

## F12 — Dashboardi lako postanu dekoracija

HubSpot korisnici kažu da detailed reporting/customization može biti confusing.

Metricool korisnici hvale easy-to-read dashboard kada informacije ostanu sažete.

### Preporuka za ACS

Početna treba pokazati samo KPI-jeve koji mijenjaju akciju:

```text
Aktivne kampanje
Nacrti
Čeka pregled
Spremno za izvoz
```

Ne:

```text
AI efficiency
brand score
engagement prediction
creative confidence
tone score
```

bez stvarnog dokaza i odluke iza njih.

---

## F13 — Analytics mora odgovoriti “šta da uradim”, ne samo “šta se desilo”

Marketing alati često imaju mnogo reporting opcija, ali korisnicima treba vrijeme da razumiju custom reporting i attribution.

### Kasniji ACS Performance princip

Umjesto samo:

```text
CTR 2.73
CPM 4.2
ER 1.88
```

prikazati:

```text
Instagram EDUCATION sadržaji imaju najbolji CTR.

Uzorak:
4 objave
12.430 impresija
341 klik
```

Korisnik treba moći otvoriti dokaz.

---

## F14 — Vizuelna “modernost” ne smije smanjiti profesionalnost

Metricool korisnik eksplicitno kritikuje novi dizajn zbog fluorescentnih boja, visokog kontrasta i dekorativnih linija koje izgledaju neprofesionalno.

### ACS preporuka

Zadržati:

- neutralnu svijetlu pozadinu;
- tamni navy sidebar;
- jednu jasnu primarnu accent boju;
- zelenu/amber/crvenu samo semantički;
- malo dekorativne grafike.

Status boja treba nositi značenje.

---

## F15 — Compactness i information density moraju biti kontrolisani

SocialBee korisnik konkretno traži da dugi postovi ne budu uvijek potpuno otvoreni.

### Preporuka

List/grid view:

```text
naslov/hook
2–3 linije previewa
platforma
status
datum
```

Puni tekst tek nakon otvaranja.

---

## F16 — Performance UI-a je UX

Hootsuite korisnici prijavljuju sporije učitavanje kompleksnijih reports.

Canva korisnici pominju lag na većim projektima.

### ACS preporuka

Dugi AI poslovi idu kroz background job.

GUI mora ostati responzivan.

Ako nešto traje:

- progress;
- cancel;
- partial completion;
- retry.

Ne koristiti beskonačni spinner bez objašnjenja.

---

## F17 — Accessibility se mora ugraditi u design system

WCAG 2.2 zahtijeva, između ostalog:

- visible keyboard focus;
- tekstualno objašnjenje grešaka;
- labels/instructions za input;
- dovoljno kontrasta za UI komponente;
- predvidljivo ponašanje fokusa.

### ACS preporuka

- `:focus-visible` jasno definisan;
- status nikada samo bojom;
- icon-only dugme ima accessible label/tooltip;
- error tekst uz polje;
- keyboard navigation kroz forme;
- primary actions imaju jasan focus order.

pywebview ne ukida web accessibility odgovornost.

---

# 5. Šta pojedini konkurenti najbolje pokazuju

## Buffer

**Hvale:** jednostavnost, clean UI, scheduling, straightforward analytics.  
**Zamjeraju:** limitirane advanced mogućnosti, preview limitations, povremeni publishing failure.

**Lekcija za ACS:** jednostavnost sama po sebi može biti proizvodna prednost.

---

## Later Social

**Hvale:** visual calendar, Instagram preview, drag-and-drop planiranje, media tags, platform customization.  
**Zamjeraju:** media organization, platform feature lag, format/publishing gaps.

**Lekcija:** ACS Kalendar + Preview imaju smisla kao centralni UX elementi.

---

## Sprout Social

**Hvale:** clean calendar, reporting, centralization, onboarding novih korisnika.  
**Zamjeraju:** publishing ponekad ne uspije bez dovoljno jasnog statusa; platform-specific limits; learning curve.

**Lekcija:** centralizacija je vrijedna samo ako sistem jasno pokazuje stanje.

---

## Hootsuite

**Hvale:** jedan workspace za mnogo mreža, scheduling, reporting.  
**Zamjeraju:** heavy UI, learning curve, bulk workflows manje intuitivni, platform limitations.

**Lekcija:** ne pretvoriti glavnu navigaciju u katalog mogućnosti.

---

## SocialBee

**Hvale:** dobra organizacija, categories, content approval, planiranje unaprijed.  
**Zamjeraju:** feature-rich početak, dugi postovi zauzimaju previše prostora, occasional glitches.

**Lekcija:** structured workflow je dobar, ali list view mora ostati kompaktan.

---

## Metricool

**Hvale:** jednostavan dashboard, calendar, jasna analytics prezentacija.  
**Zamjeraju:** platform ograničenja i kod dijela korisnika novi vizuelni stil.

**Lekcija:** redesign ne smije razbiti profesionalni karakter proizvoda.

---

## Jasper

**Hvale:** templates, brzo kreiranje, easy setup, brand/tone koncept.  
**Zamjeraju:** generic/repetitive output, superficial output na kompleksnim temama, dodatno editovanje i fact checking.

**Lekcija:** najveća prijetnja ACS-u nije UX bug nego da složen workflow na kraju da generičan rezultat.

---

## Canva

**Hvale:** drag-and-drop, templates, reusable brand assets, brz output.  
**Zamjeraju:** hidden advanced features, lag, collaboration complexity, version history i folder organization.

**Lekcija:** critical trust funkcije ne smiju biti toliko skrivene da ih korisnik nikad ne vidi.

---

## Mailchimp

**Hvale:** low barrier to entry, onboarding, drag-and-drop, campaign creation.  
**Zamjeraju:** napredni UI može biti overwhelming; flexible template editor clunky; automation builder rigidniji za kompleksne use-caseove.

**Lekcija:** prvi campaign mora biti jednostavan.

---

## Meta Business Suite

Najvažnija lekcija:

> **korisnik ne vjeruje stanju koje UI prikazuje.**

To je anti-pattern broj 1 za ACS.

---

# 6. Human-AI UX principi za ACS

## A1 — Jasno reći šta AI radi

Ne:

```text
✨ Poboljšaj
```

Bolje:

```text
Poboljšaj uvod
Skrati tekst
Promijeni ton
Generiši drugu varijantu
```

## A2 — AI output je prijedlog

```text
AI generiše
Korisnik odlučuje
```

## A3 — Correction mora biti lakša od regenerationa

Ako korisnik želi promijeniti CTA, ne smije morati regenerisati cijelu objavu.

## A4 — Dismiss/Undo mora biti očigledan

AI akcija bez Undo je rizična.

## A5 — Explain “why” gdje imamo stvarni dokaz

```text
Zašto je ova tvrdnja označena?
→ Nije pronađen FactId koji je podržava.
```

## A6 — Ne izmišljati sigurnost

```text
Nedostaje potvrđena činjenica.
```

je bolji rezultat od uvjerljivog nagađanja.

---

# 7. Preporučeni finalni UX model za 9 ACS ekrana

## Screen 1 — Početna

**Primarni cilj:** šta trenutno zahtijeva moju pažnju?

Prikazati:

- Nova kampanja;
- Nastavi posljednju kampanju;
- Aktivne kampanje;
- Čeka pregled;
- Nacrti;
- Spremno za izvoz;
- posljednje aktivnosti.

Ne prikazivati provider/model selekciju ni pseudo-AI metrike.

---

## Screen 2 — Brend

**Primarni cilj:** mogu li vjerovati podacima koje će AI koristiti?

Header:

```text
BrightSmile Oral Care
Provjereno i ažurno
Provjereno: 04.09.2026.
```

Sekcije:

- Osnovni podaci;
- Odobrene činjenice;
- Glas brenda;
- Ciljna publika;
- Brend resursi.

Facts: status, source, version, freshness.

---

## Screen 3 — Kampanje

**Primarni cilj:** koje kampanje postoje i šta je sljedeće za svaku?

```text
Naziv
Status
Sljedeći korak
Planirano
Sadržaji
Posljednja izmjena
```

“Sljedeći korak” je često korisniji od još jednog tehničkog statusa.

---

## Screen 4 — Opis kampanje

Default:

- cilj;
- ponuda;
- publika;
- jezik;
- kanal/platforma/format.

Advanced:

- posebne instrukcije;
- dodatna ograničenja;
- sekundarni target.

---

## Screen 5 — Plan kampanje

Uloge:

```text
Problem
Edukacija
Dokaz
Prigovor
Ponuda
Akcija
```

Svaki row/card:

- role chip;
- tema;
- cilj;
- platform/format;
- status;
- reorder.

Plan je mjesto za strukturu, ne za uređivanje cijelog teksta.

---

## Screen 6 — Kalendar

Global mode: sve kampanje.  
Campaign mode: samo trenutna kampanja.

UX:

- Month;
- Week;
- filter platform/status;
- jasna razlika PLANIRANO vs ODOBRENO.

---

## Screen 7 — Studio sadržaja

Najvažniji UX ekran.

```text
LEFT
metadata / item context

CENTER
content editor
AI Quick Actions

RIGHT
live preview
facts / claim status
```

Tabs:

```text
Sadržaj
Korištene činjenice
Provjera usklađenosti
Istorija verzija
```

Facts/trust summary treba ostati vidljiv čak i kada je `Sadržaj` aktivan.

AI actions:

```text
Prepiši
Skrati
Poboljšaj uvod
Promijeni ton
Generiši varijantu
```

Permanent status:

```text
Sačuvano · Revizija 7
```

Trust summary:

```text
3 korištene činjenice
0 nepodržanih tvrdnji
```

---

## Screen 8 — Pregled i izvoz

Hard deterministic checks:

- required fields;
- unsupported factual claims = 0;
- platform/schema constraints;
- overflow;
- forbidden terms;
- output file readiness.

Advisory AI checks odvojiti:

```text
AI procjena tona
```

od:

```text
Provjera činjenica
```

---

## Screen 9 — Podešavanja / AI provajderi

MVP tabs:

```text
AI provajderi
Jezik
Opšte
```

Workflow:

```text
Provider
→ API key
→ Testiraj vezu
→ Učitaj modele
→ Izaberi model
```

Statusi:

```text
Povezano
Nevažeći API ključ
Mrežna greška
Rate limit
Provider greška
```

---

# 8. Design-system pravila koja bih zaključao

Ovo su preporuke, ne činjenice iz istraživanja.

## D1
Najviše jedan dominantni primary CTA po viewu.

## D2
Najvažniji status uvijek tekst + boja/icon, nikad samo boja.

## D3
AI akcija koja mijenja sadržaj mora imati Undo/revision recovery.

## D4
Loading mora pokazati šta se radi kada operacija nije trenutna.

## D5
Background AI posao ne blokira cijeli GUI.

## D6
Advanced opcije su sekundarne/collapsible.

## D7
Preview i editor ostaju vizuelno povezani.

## D8
Navigation label koristi korisnički jezik, ne arhitektonske termine.

## D9
Dense list prikazuje preview, ne puni sadržaj.

## D10
Nema fake success state-a.

## D11
Nema fake AI confidence procenta.

## D12
Nema automatskog prepisivanja approved sadržaja.

---

# 9. Funkcije koje NE bih sada dodavao samo zato što ih konkurenti imaju

- auto publishing;
- unified social inbox;
- social listening;
- competitor tracking;
- CRM;
- team workspace;
- billing;
- advanced analytics;
- AI chat assistant na svakom ekranu;
- SEO suite;
- full DAM;
- generic automation builder.

---

# 10. UX prioritizacija za MVP

## P0 — mora postojati

1. jasna navigacija;
2. campaign workflow;
3. visual calendar;
4. format-aware preview;
5. save status;
6. autosave/revision;
7. AI Undo/correction;
8. facts/provenance;
9. error states;
10. loading/progress/cancel;
11. deterministic quality gate;
12. accessibility basics.

## P1 — veoma vrijedno nakon prvog usable slicea

1. keyboard shortcuts;
2. compact/list density controls;
3. media tag/filter;
4. richer calendar filters;
5. granular AI feedback;
6. estimated provider cost;
7. compare revisions side-by-side.

## P2 — tek poslije realnih korisničkih dokaza

1. social publishing;
2. analytics dashboards;
3. collaboration;
4. team approvals;
5. integrations marketplace;
6. advanced brand asset management.

---

# 11. UX test plan prije zaključavanja GUI-ja

## T1 — First campaign

Zadatak:

> Kreiraj kampanju za novi proizvod koristeći postojeći brend.

Mjeriti:

- da li zna gdje krenuti;
- broj pogrešnih klikova;
- gdje zastane;
- da li razumije stepper.

## T2 — AI correction

> AI je napisao dobar tekst, ali uvod je slab. Promijeni samo uvod.

Ako korisnik regeneriše cijeli sadržaj jer ne vidi Quick Action → UX nije dobar.

## T3 — Fact trust

> Provjeri odakle dolazi tvrdnja “1450 ppm fluoride”.

Ako korisnik ne može brzo do sourcea → fact-first arhitektura nije pretvorena u UX vrijednost.

## T4 — Recovery

> AI je pokvario tekst. Vrati prethodnu verziju.

Cilj: nekoliko sekundi, bez straha.

## T5 — Failure

Simulirati provider rate limit.

Korisnik mora razumjeti:

- šta je uspjelo;
- šta nije;
- šta će retry uraditi.

## T6 — Calendar

> Nađi šta ide na Instagram sljedećeg četvrtka.

Bez otvaranja 5 ekrana.

## T7 — Export readiness

> Zašto kampanja nije spremna za izvoz?

Razlog mora biti odmah vidljiv.

---

# 12. UX acceptance kriteriji koje vrijedi automatizovati gdje je moguće

- svaki form input ima label;
- svaki icon-only button ima accessible name;
- focus-visible postoji;
- status nije samo color-coded;
- error message postoji uz invalid field;
- destructive action traži potvrdu ili ima Undo;
- route/page title je konzistentan;
- sidebar ima samo odobrene MVP stavke;
- Studio sadrži Quick Actions;
- Studio pokazuje revision/save status;
- preview pokazuje target platform/format;
- hard quality checks nisu pomiješani sa AI advisory procjenama.

---

# 13. Najvažnije produktne odluke izvedene iz istraživanja

## D1 — Jednostavnost je feature

Ne pokušavamo izgledati kao enterprise suite.

## D2 — Trust UX je diferencijator

Naš najveći vizuelni razlikovni element ne treba biti gradient.

Treba biti:

```text
Korištene činjenice
Provjera tvrdnji
Izvor
Revizija
Status
```

## D3 — Kalendar ostaje

Korisnici marketing alata ga redovno smatraju jednim od najkorisnijih pogleda.

## D4 — Studio je centralni radni prostor

Ne generički AI chat.

## D5 — User control > AI automation

AI transformacije moraju biti granularne i reversible.

## D6 — Status mora biti pouzdan

Meta Business Suite je anti-pattern koji treba pamtiti.

## D7 — Preview mora biti pošten

Ne simulirati ono što ne možemo pouzdano simulirati.

## D8 — Performance kasnije mora objašnjavati odluku

Ne praviti chart wall.

---

# 14. Najveća opasnost za naš trenutni GUI

Najveća UX opasnost nije da je sidebar pogrešne nijanse.

Veća opasnost je da napravimo profesionalno izgledajući GUI koji sakriva ono po čemu bi proizvod zaista mogao biti bolji:

```text
zašto je sadržaj napravljen
koje činjenice koristi
šta je AI izmijenio
šta je sačuvano
šta je odobreno
šta nije prošlo provjeru
šta se može vratiti
```

Ako to sakrijemo iza nekoliko tabova i generičkih green checkova, naša najbolja arhitektura neće biti vidljiva korisniku.

UX zato mora biti direktna projekcija ključnih domain garancija.

---

# 15. Konačna preporuka

Najbolja pozicija za AI Campaign Studio nije:

> “Sve što marketaru treba u jednom alatu.”

Bolja pozicija je:

> **Od podataka o brendu do provjerene, uređive i izvozive kampanje — sa jasnim dokazom šta AI koristi i potpunom kontrolom korisnika.**

U praksi:

```text
manje opcija
+
jasniji workflow
+
bolji brand context
+
fact-first generation
+
platform-aware preview
+
revision/undo
+
transparent state
+
human approval
```

---

# 16. Izvori

## User reviews / products

- Jasper — G2  
  https://www.g2.com/products/jasper-ai/reviews

- Hootsuite — G2  
  https://www.g2.com/products/hootsuite/reviews

- Sprout Social — G2  
  https://www.g2.com/products/sprout-social/reviews

- Buffer — G2  
  https://www.g2.com/products/buffer/reviews

- Later Social — G2  
  https://www.g2.com/products/later-social/reviews

- SocialBee — G2  
  https://www.g2.com/products/socialbee/reviews

- Metricool — G2  
  https://www.g2.com/products/metricool/reviews

- Canva — G2  
  https://www.g2.com/products/canva/reviews

- Mailchimp — G2  
  https://www.g2.com/products/intuit-mailchimp-email-marketing/reviews

- HubSpot Marketing Hub — G2  
  https://www.g2.com/products/hubspot-marketing-hub/reviews

## Community failure examples

- Meta Business Suite — scheduled posts missing from Planner  
  https://www.reddit.com/r/MetaAdsHelp/comments/1rpbu2g/scheduled_posts_not_showing_in_meta_business_suite/

- Meta Business Suite — successful scheduling message but calendar state unclear  
  https://www.reddit.com/r/SocialMediaMarketing/comments/1m1cvof/meta_business_suite_scheduling_not_working/

- Meta Business Suite — upload disappears without error  
  https://www.reddit.com/r/SocialMediaManagers/comments/1r2z82e/meta_business_suite_story_upload_failing_in/

- Meta Business Suite — scheduled posts missing in Planner  
  https://www.reddit.com/r/facebook/comments/1u02fef/meta_business_suite_scheduled_posts_are_missing/

- Social scheduling UX discussion — preview mismatch / bloat  
  https://www.reddit.com/r/SocialMediaMarketing/comments/1tkbwzm/what_is_the_most_annoying_thing_about_social/

## UX/HCI guidance

- Nielsen Norman Group — 10 Usability Heuristics  
  https://www.nngroup.com/articles/ten-usability-heuristics/

- Nielsen Norman Group — heuristics for complex applications  
  https://www.nngroup.com/articles/usability-heuristics-complex-applications/

- Nielsen Norman Group — Progressive Disclosure  
  https://www.nngroup.com/articles/progressive-disclosure/

- Microsoft HAX — Guidelines for Human-AI Interaction  
  https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/

- Microsoft Research — Guidelines for Human-AI Interaction  
  https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

- Google PAIR — People + AI Guidebook  
  https://pair.withgoogle.com/guidebook-v2/

- Google PAIR — Explainability + Trust  
  https://pair.withgoogle.com/guidebook-v2/chapter/explainability-trust/

- Google PAIR — Feedback + Control  
  https://pair.withgoogle.com/guidebook-v2/chapter/feedback-controls/

- W3C — WCAG 2.2  
  https://www.w3.org/TR/WCAG22/

- W3C — Error Identification  
  https://www.w3.org/WAI/WCAG22/Understanding/error-identification

- W3C — Focus Visible  
  https://www.w3.org/WAI/WCAG22/Understanding/focus-visible

---

## Napomena o dokazima

**Potvrđeno iz izvora:** ponavljajući korisnički obrasci, konkretne recenzije i objavljene UX/HCI smjernice.

**Procjena za ACS:** screen layout, prioriteti, navigacija, acceptance kriteriji i funkcionalni izbori izvedeni su iz tih nalaza u kontekstu naše arhitekture.

**Nije dokazano:** da će bilo koji od predloženih UX obrazaca automatski povećati poslovni uspjeh ACS-a. To mora biti provjereno kroz usability testove i G10/product validation.
