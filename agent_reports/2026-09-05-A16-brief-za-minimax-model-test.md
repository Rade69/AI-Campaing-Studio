# → ZA MINIMAX — pomozi sa A16 poređenjem (nije coding task)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-05

Ovo NIJE task contract, nije coding zadatak — nema šta da se implementira
ili commit-uje. Ovo je molba za pomoć u live verifikaciji (A16 — A/B
evaluation harness, već izgrađen i mergovan: ACS-F1-026, ACS-F1-027).

## Kontekst

Koordinator je već uživo pokrenuo poređenje "Control A" (goli, jedan AI
poziv, bez strukture) vs "System B" (naš puni Campaign Engine pipeline —
plan, uloge, fact-selection, claim linting) protiv identičnog BrightSmile
fixture-a i brief-a, preko četiri modela: Gemini 2.5 Flash, DeepSeek-R1,
GPT-4o-mini, GPT-5.6-sol. Rezultat je dosljedan preko svih njih: System B
= 0 neosnovanih tvrdnji, Control A = 6-9 neosnovanih tvrdnji.

Human Owner želi da se doda i MiniMax-ov vlastiti model kao peti kontrolni
model — ali BEZ trošenja novca preko `api.minimax.io` naloga koji trenutno
nema balans (probali smo, dobili "insufficient_balance_error").

## Šta stvarno trebamo od tebe (dvije opcije, tvoj izbor koja je izvodljiva)

### Opcija A (preferirano ako je moguće) — daj nam radnu API putanju

Ako imaš PRISTUP MiniMax modelu preko naloga/pretplate koja NIJE ista kao
onaj pay-per-token API ključ kojem fali balans (npr. neki drugi ključ,
drugi tier, interni pristup) — javi nam:

- `api_key` (isti bezbjedan način kao i do sad — NIKAD u chat, samo preko
  keyring komande koju će koordinator dati Human Owner-u ako zatreba);
- `base_url` (ako je različit od `https://api.minimax.io/v1`);
- tačan naziv modela (npr. koji "MiniMax-M*" model tvoj pristup koristi).

Ako je to isti nalog/ključ koji smo već probali — reci to jasno, nemoj
pretpostavljati da postoji drugi.

### Opcija B (ako Opcija A nije moguća) — pokreni test SAM, u svom okruženju

Ako imaš pristup svom modelu SAMO kroz svoju vlastitu sesiju/okruženje
(ne preko API ključa koji bi koordinator mogao koristiti), onda MOLIM TE
sam odigraj ulogu oba "provider poziva" i vrati nam TAČNO sljedeće:

**"Control A" zadatak** — odigraj ulogu jednostavnog copywriter-a, JEDAN
odgovor, bez strukture:

```text
System: Ti si generički copywriting baseline. Dobiješ brend i brief,
napiši N postova direktno. Sam isplaniraj postove; ne oslanjaj se na
unaprijed zadat redoslijed uloga ili pipeline informacije. Poštuj jezički
kontekst (preferred_terms, forbidden_terms, regional_vocabulary,
tone_examples). Nikad ne koristi zabranjen termin.

## Brand snapshot
language: bs
locale: BA
script: latin
voice.formality: neformalno-profesionalno
voice.preferred_terms: pouzdanost, iskustvo, stručnost
voice.forbidden_terms: garantovano, najjeftiniji, bezbolno, jeftino
## Campaign brief
offer: Predstaviti novu liniju titanijumskih implantata uz fokus na
  provjerljive karakteristike i jednostavan CTA.
goal: Generisanje interesovanja i upita za konsultaciju
audience: Postojeći i novi pacijenti, 30-60 godina, zabrinuti za zdravlje
  zuba.
content_piece_count: 3
## Approved facts
- Ordinacija se nalazi u centru Sarajeva, lako dostupna javnim prevozom.
- Implantati su izrađeni od medicinskog titanijuma klase 4.
- Tim ima više od 12 godina iskustva u implantologiji.
```

Vrati TAČNO 3 posta, svaki sa: headline, caption, hook, body, cta,
hashtags (lista). Format nije bitan (JSON ili čitljiv tekst), samo da
sadrži svih 6 polja po postu.

**Šta koordinator radi sa tvojim odgovorom**: ručno će provući tvoj
tekst kroz POSTOJEĆI claim linter (deterministički, ne AI) da izračuna
iste metrike (`unsupported_fact_claim_count`, `numeric_claim_violations`
itd.) kao za ostala četiri modela — fer poređenje, isti mjerni instrument.

**Za System B dio ne treba da radiš ništa** — to je naš postojeći,
strukturisan pipeline (plan sa ulogama, fact-selection, itd.), koordinator
to pokreće sam kad god treba, nezavisno od koje AI modelu se poredi.

## Napomena

Ovo je čisto istraživačka/eksperimentalna provjera (dio G10 A16 evaluation
harness-a) — ne mijenja nijedan task contract niti kod. Ako ti ni Opcija
A ni B ne odgovaraju iz bilo kog razloga, slobodno reci — Human Owner
može odlučiti da li vrijedi dopuniti pravi API balans umjesto ovoga.
