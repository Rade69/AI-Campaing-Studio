# SPIKE-001 — pywebview UI framework validation (Content Studio screen)

**Ovo NIJE Task Contract i ne prolazi kroz punu P0 disciplinu.** Namjerno
lightweight: cilj je brza validacija odluke (UI framework), ne isporuka
production koda. Nema Codex review runde, nema HIGH-risk ciklusa.

## Zašto

Human Owner odluka (2026-09-01): prije nego što se UI framework formalno
zaključa (workflow §53 "UI spike test matrica", R6 "UI decision po
osjećaju" anti-pattern), napraviti jedan stvaran ekran u pywebview-u da se
provjeri:

1. Da li pywebview daje dovoljno kvalitetan native desktop feel za web-style
   mockup koji već postoji.
2. Da li duži BHS stringovi (dijakritici, duže riječi/rečenice nego EN)
   lome layout — konkretan, poznat rizik za regionalnu varijantu.

## Šta NIJE cilj ove runde

- Nije potrebno wire-ovati na `bootstrap.py`/`JobManager`/AI providere —
  mock/statički podaci su dovoljni.
- Nije potrebno pokrivati svih 6 ekrana iz mockup-a (Brand, Brief, Plan,
  Studio, Preview, Export) — samo Content Studio.
- Nije potrebno donijeti finalnu odluku sam — spike proizvodi dokaz,
  Human Owner donosi odluku.
- Kod se vjerovatno baca/prepravlja kad krene prava implementacija — to je
  očekivano i u redu.

## Scope

- Nova putanja: `presentation_webview/` (već rezervisana u
  `.agent/PROJECT_MAP.md` §3 kao budući kandidat, prazna do sada).
- Jedan pywebview prozor, jedan ekran: **Content Studio**.
- Sadržaj po mockup-u (Human Owner prilaže fajl/opis — vidi niže):
  - Quick Actions dugmad: Rewrite, Shorten, Improve Hook, Change Tone.
  - Glavni content/caption editing prostor.
  - Fact-first / "Claim Check" panel pri dnu ekrana.
- Sadržaj mora biti prikazan i na EN i na BHS (prebacivanje jezika ili dva
  odvojena snapshot-a — implementer bira), sa namjerno DUŽIM BHS
  demo-tekstom (ne kratak placeholder) da se stvarno testira lom layout-a.
- Stack: pywebview + HTML/CSS/JS. Tailwind CSS (CDN ili lokalni build) je
  razuman default za brzo iteriranje — nije obavezan, implementer može
  predložiti alternativu uz kratko obrazloženje.

## Acceptance (spike-level, ne production-level)

- [ ] `python presentation_webview/spike_content_studio.py` (ili sličan
      entrypoint) otvara pywebview prozor sa Content Studio ekranom.
- [ ] Ekran je vizuelno prepoznatljiv kao isti dizajn iz mockup-a (ne mora
      biti piksel-precizan).
- [ ] BHS varijanta se prikazuje bez vidljivog loma layout-a (overflow,
      obrezan tekst, preklapanje elemenata) — ili, ako SE lomi, to je
      eksplicitno dokumentovano sa screenshot-om kao nalaz, ne sakriveno.
- [ ] Kratak izvještaj (vidi ispod) sa subjektivnom ocjenom: da li pywebview
      djeluje kao dobar izbor za ostatak proizvoda.

## Evidence / report

`SPIKE_REPORT.md` u ovom worktree-u (ne `agent_reports/`, jer ovo nije dio
P0 sistema): šta je urađeno, screenshot(ovi) EN i BHS varijante, poteškoće
na koje se naišlo (packaging, native look, performance, developer
experience), i implementerova preporuka.

## Ne commituj u main

Ovaj branch (`spike/pywebview-content-studio`) se NE mergea u `main`
automatski. Human Owner pregleda rezultat i odlučuje šta dalje — možda
merge kao osnova za pravi UI rad, možda odbačen, možda modifikovan.
