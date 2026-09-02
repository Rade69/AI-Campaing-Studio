# AI Campaign Studio — GUI V3 plan izrade

## Status
V3 je jedini kandidat za finalni GUI dizajn. `mockup_proposal` i `mockup_proposal_v2` su samo design exploration/reference.

## Zaključani scope
Glavni sidebar: **Početna / Brend / Kampanje / Kalendar / Podešavanja**. Nema Analitike, Tima, Fakturisanja, Profila, globalnog Izvoza ni nejasnih Resursa. Brend resursi žive unutar Brend ekrana.

Campaign workflow: **Opis kampanje → Plan kampanje → Kalendar → Studio sadržaja → Pregled i izvoz**. Stepper omogućava povratak na prethodne korake.

## Tehnički cilj
V3 nije backend implementacija. To je modularni presentation paket spreman da Codex/Claude integrišu u `presentation_webview` nakon što odgovarajući application/use-case contracti postoje.

## Pravila
- pywebview smjer, ali ovaj paket radi i direktno u browseru kao statični handoff.
- Nema JS → SQLite/SecretStore/provider SDK pristupa.
- Bridge pozivi ostaju stubovi dok application sloj ne bude spreman.
- Shared shell/design system je u `shared/`; ekrani ne dupliraju production business logiku.
- Svi UI stringovi su srpski/BHS latinica.
- Demo brend je BrightSmile kroz sve ekrane.
- Analitika ostaje van UI-ja do G10 PASS i aktivacije Performance Foundation.

## Moduli
1. `01_pocetna` — stanje rada, bez performance analytics.
2. `02_brend` — osnovni podaci, odobrene činjenice, glas brenda, brend resursi, status „Provjereno i ažurno“.
3. `03_kampanje` — lista kampanja i ulaz u campaign workflow.
4. `04_opis_kampanje` — campaign brief.
5. `05_plan_kampanje` — role/topic plan.
6. `06_kalendar` — globalni planning pogled; isti podaci mogu se filtrirati na konkretnu kampanju. Nema publishinga.
7. `07_studio_sadrzaja` — merged finalni Studio: 3 kolone + tabovi + Quick Actions + facts + compliance + revision seam + preview.
8. `08_pregled_izvoz` — završna provjera i ZIP export seam.
9. `09_podesavanja` — Opšte/Jezik/AI provajderi; trenutno vizuelno razrađen AI provider dio.

## Faze implementacije u root aplikaciju
- GUI-BASE: shell, sidebar, breadcrumbs, stepper, tokens/components.
- Screen integration redom 01→09.
- Svaki ekran prvo dobija fixture/read-model adapter, zatim stvarni PresentationFacade/Application use-case.
- Production pywebview bridge mora biti uski adapter; nikakva business logika u JavaScriptu.
- Nakon svakog ekrana: vizuelni review + boundary review + test navigacije/bridge contracta.

## Acceptance za V3 handoff
- svih 9 ekrana postoje kao zasebni moduli;
- jedan shared design system;
- navigacija konzistentna;
- nema zabranjenih/premature sidebar funkcija;
- Studio sadrži Quick Actions, korištene činjenice i provjeru usklađenosti;
- Kalendar eksplicitno nije publishing;
- Podešavanja imaju šest stvarnih provider registry opcija;
- svaki ekran se može otvoriti samostalno.
