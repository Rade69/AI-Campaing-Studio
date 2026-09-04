---
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
tests: REJECT
gitnexus_impact: CONFIRMED_LOW
blocking_findings:
  - F1: "100%" prohibited term can never match again (any sentence) — regex \b cannot anchor after a trailing non-word char.
  - F2: currency/duration units glued to a digit with no space ("30KM", "50EUR", "3dana") no longer detected — digits and letters are both \w, so no boundary forms between them.
---

# CILJ

Nezavisan review ACS-F1-020 (`claim_linter.py` word-boundary fix) prema
`agent_reports/ACS-F1-020-task-contract.md`, implementacija Pi
(`agent_reports/2026-09-04-ACS-F1-020-pi.md`), branch
`task/ACS-F1-020-claim-linter-word-boundary`, worktree
`H:\ai-campaign-studio-worktrees\ACS-F1-020-claim-linter-word-boundary`.

Review focus po kontraktu: word-boundary regex ispravno hendluje multi-word
termine, non-ASCII BHS karaktere, termine sa regex-specijalnim karakterima;
nema regresije na postojeće pozitivne slučajeve; currency symbol fix je
konzistentan.

# PROVJERENO

**Scope** — `git diff --stat` na branch-u: tačno `claim_linter.py` +
`test_claim_linter.py`, oba u `allowed_paths`. Nula fajlova van dozvoljenog.
`domain/`, `claim_validator.py`, `resources/claim_rules/`, `infrastructure/`,
`ports/` — netaknuti. **PASS.**

**Diff pregledan u cijelosti**: `_contains_word(text_folded, term)` =
`re.search(rf"\b{re.escape(term.casefold())}\b", text_folded) is not None`,
zamijenjeno na sva tri mjesta (prohibited_terms, currency_symbols,
duration_units) tačno kako kontrakt traži. Pristup je isti obrazac kao
ACS-F1-017 `_COUNT_LINE_RE` — arhitektonski razuman izbor, konzistentan sa
postojećom konvencijom. **architecture: PASS.**

**Sopstveno pokrenuti testovi** (ne samo pi-jev pasted output):

```
$ PYTHONPATH=<worktree>/src python -m pytest tests/unit/application/posts/test_claim_linter.py -v
...
FAILED test_euro_symbol_price_is_still_unsupported
FAILED test_percent_prohibited_term_still_works
2 failed, 14 passed in 0.21s
```

Napomena: fajl je između pi-jevog izvještaja i ovog review-a **narastao sa
64 na 80 dodanih linija** (`git diff --stat`) — neko je (van ovog review-a,
vjerovatno korisnik ili druga sesija, dogodilo se dok sam ja nezavisno
istraživao isti problem) već dodao ova dva regresiona testa, sa komentarom
koji doslovno navodi isti uzrok koji sam ja identifikovao prije nego što sam
pogledao taj dio fajla:

```python
# "€" is a non-word symbol: \b cannot anchor around it, so it must fall
# back to a plain substring match and still flag the price.
```

Ovo NIJE moja izmjena — zatečeno je već prisutno kad sam pokrenuo testove.
Navodim kao nezavisnu potvrdu istog nalaza, ne kao dio pi-jevog rada koji se
review-uje (pi-jev izvještaj navodi "14 passed" jer ova dva testa tada nisu
postojala).

**Sopstvena adversarna reprodukcija (van postojećih testova), prije nego
sam vidio gornje testove**:

```python
# _contains_word iz claim_linter.py, testirano izolovano:
'Garantujemo uspjeh od 100% sigurno.' -> False   # treba: True (100% je prohibited term)
'Rezultat je 100%.'                  -> False   # treba: True
'Cijena je 30KM ukupno.'             -> False   # treba: True (KM je currency_symbol)
'Cijena je 30 KM ukupno.'            -> True    # ispravno (sa razmakom)
'Paket kosta 50EUR.'                 -> False   # treba: True
'Akcija traje 3dana.'                -> False   # treba: True (dan je duration unit)
```

# NALAZI (BLOCKING)

## F1 — "100%" prohibited term trajno neupotrebljiv

`resources/claim_rules/default_v1.yaml` sadrži `"100%"` kao prohibited term.
Termin se završava sa `%` (non-word karakter). `\b` zahtijeva tranziciju
word↔non-word na OBA kraja mača; pošto ništa što prirodno slijedi "100%" u
tekstu (razmak, tačka, kraj rečenice) nije word karakter, drugi `\b` NIKAD
ne postoji. Rezultat: `_contains_word(text, "100%")` vraća `False` za
SVAKU rečenicu koja prirodno sadrži "100%". Prije ove izmjene, plain
substring provjera je ovo ispravno hvatala. Ovo je **potpuna, tiha
regresija** jedne od 9 prohibited-term pravila u produkcijskoj
konfiguraciji — doslovno krši acceptance stavku "Stvaran zabranjen termin
... I DALJE postaje PROHIBITED" iz kontrakta (kontrakt je testirao samo
"Mi smo najbolji izbor", ne "100%" — pa je propust prošao kroz pi-jevu
sopstvenu verifikaciju).

Isti uzrok pogađa currency symbol `"€"` (takođe non-word) kad se pojavi bez
sljedećeg word karaktera — što je normalan slučaj (npr. "500€" na kraju
rečenice).

## F2 — currency/duration bez razmaka od broja više se ne detektuje

`"30KM"`, `"50EUR"`, `"3dana"` (broj zalijepljen za jedinicu/simbol bez
razmaka — uobičajen stil pisanja cijena u BHS marketinškom tekstu) više se
NE prepoznaju. Uzrok: cifre i slova su OBA `\w` klasa za regex, pa `\b`
(i ekvivalentna lookaround provjera koju sam probao kao alternativu) ne
pravi razliku između "broj+jedinica zalijepljeno" i "jedinica usred druge
riječi" — oba izgledaju kao "nema granice". Generička "cijela riječ"
provjera (`\b...\b` ili `(?<!\w)...(?!\w)`) strukturno ne može riješiti ovaj
slučaj bez posebne logike za "dozvoljeno prethodi cifra, ne slovo".

Nijedan postojeći test (ni prije ni poslije ovog taska) nije koristio
notaciju bez razmaka, pa je regresija prošla neopaženo kroz pi-jevu
verifikaciju.

# PREPORUKA ZA POPRAVKU (nije propisana, implementer bira)

Oba nalaza dijele isti korijen: generička `\b`-zasnovana "cijela riječ"
provjera je pogrešan alat za termine koji se sastoje od ili graniče sa
non-word karakterima. Razuman pravac (ne propisujem tačan kod):

- Za termine koji sadrže SAMO word karaktere (`[a-zA-ZčćžšđČĆŽŠĐ0-9_]+`) —
  zadržati `\b...\b` (ispravno rješava originalni jedinice/jedini,
  danas/dan slučaj).
- Za termine koji sadrže bar jedan non-word karakter (`100%`, `€`) —
  koristiti plain substring (kao prije ove izmjene) ili lookaround koji
  eksplicitno tretira digit-prije kao dozvoljen non-boundary
  (`(?<![^\W\d])term(?!\w)` za slučajeve gdje termin direktno prati broj).
- Alternativno, minimalno: zadržati plain substring SAMO za termine/simbole
  koji sadrže non-word karakter, uz eksplicitan komentar zašto (upravo
  komentar koji su novi testovi već napisali).

# ŠTA NIJE PROVJERENO

- GitNexus impact nisam ponovo pokretao — pi-jev pre-change rezultat
  (`impactedCount: 11, risk: LOW`, 2 direktna production callera) je
  vjerodostojan i logički se poklapa sa manuelnim pregledom (funkcija ne
  mijenja potpis/povratni tip). `gitnexus_impact: CONFIRMED_LOW` na osnovu
  ovoga, ne ponovnog MCP poziva.
- `python -m pytest -q` (cijeli suite) nisam ponovo pokretao u cijelosti —
  fokusiran na `test_claim_linter.py` gdje je nalaz.
- `ruff`/`mypy` nisam ponovo pokretao — nalaz nije lint/tip problem, nego
  bihevioralna regresija koju ti alati ne hvataju.

# ZAKLJUČAK

**REJECT.** Implementacija ispravno rješava DVA originalno prijavljena
false-positive bug-a (jedinice/jedini, danas/dan) i to je arhitektonski
čist, dobro strukturisan fix. Ali uvodi dvije nove, stvarne regresije
(F1 potpuna, F2 djelimična) koje direktno krše kontraktove acceptance
stavke o ne-regresiji na postojeće pozitivne slučajeve. Pošto je §29
"Claude PASS → odmah merge" za MEDIUM task, ne mogu dati PASS kad bi to
odmah pustilo u produkciju termin koji se nikad ne može uhvatiti
("100%") i tiho oslabilo currency/duration detekciju za uobičajenu
notaciju. Vraćam implementeru (Pi) sa oba nalaza i predloženim pravcem
popravke; nova iteracija treba dokazati F1+F2 kao regresione testove
koji prelaze iz FAIL u PASS (isti obrazac kao postojeći adversarni dokaz
za originalna dva bug-a).
