---
task_id: ACS-F1-028
phase: Faza-1 (post A16)
title: "claim_linter: pokriti morfološke varijante prohibited_terms (garantovano/garantujemo gap)"
risk: LOW
coordinator: claude
implementer: TBD
reviewers: [claude]
status: "OPEN — contract written before code, čeka implementera"
created_at: 2026-09-05
dependencies: []
allowed_paths:
  - resources/claim_rules/default_v1.yaml
  - tests/unit/application/posts/test_claim_linter.py
forbidden_paths:
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/ports/
  - src/ai_campaign_studio/infrastructure/
gitnexus_required: false
adversarial_required: false
gitnexus:
  required: false
  note: >
    Čisto data-only izmjena (YAML lista + testovi), nema izmjene javnog
    potpisa/koda. GitNexus impact provjera nepotrebna.
---

# Kontekst

Otkriveno organski tokom G10/A16 live poređenja (2026-09-05): kad je MiniMax
(kodni agent, kroz A16 brief) ručno odigrao ulogu "Control A" modela i
generisao BHS tekst koji sadrži "**Garantovano** ćete dobiti...", stvaran
`lint_claim` (`application/posts/claim_linter.py`) to NIJE prepoznao kao
kršenje zabranjenog termina — `forbidden_phrase_hits=0` u izračunatim
metrikama, iako je MiniMax sâm (pogrešno) vjerovao da će biti uhvaćen.

Uzrok: `resources/claim_rules/default_v1.yaml` sadrži termin `garantujemo`
(1. lice množine, prezent), a `_contains_word` u `claim_linter.py` radi
TAČNO poređenje riječi (`\bgarantujemo\b`) — ne prepoznaje druge gramatičke
oblike istog korijena (`garantovano`, `garantovan`, `garantuje`,
`garantujem`, `garantuju`...). Ovo je isti tip generation-time
neusklađenosti kao BF-2 (ACS-F1-020) i BF-1 (ACS-F1-025), samo sada na
nivou `prohibited_terms` liste, ne numeričke provjere.

**Namjerno izabran fix je DATA-ONLY (proširiti listu u YAML-u), NE
stemming/lemmatizacija u kodu.** Razlog: `claim_linter.py` je već
data-driven po dizajnu (pravila žive u YAML-u, ne hardkodirana u Pythonu —
vidi header fajla), pa je dodavanje eksplicitnih morfoloških varijanti u
istom stilu kao postojeće termine ("100%" pored "bez rizika" itd.)
najmanja moguća izmjena koja rješava PRIJAVLJEN slučaj bez uvođenja nove
zavisnosti (BHS stemmer/lemmatizator) ili apstrakcije "za svaki slučaj" —
u skladu sa CLAUDE.md pravilom da se ne uvodi framework prije stvarne
potrebe. Ako se u budućnosti otkrije da eksplicitno nabrajanje varijanti
ne skalira (npr. desetine termina x desetine oblika), stemming postaje
zaseban, eksplicitno predložen budući task.

# Objective

Proširiti `prohibited_terms` u `resources/claim_rules/default_v1.yaml`
tako da uobičajene morfološke varijante VEĆ POSTOJEĆIH termina budu
pokrivene, počevši od potvrđenog slučaja (`garantujemo` korijen), i
dodati regresioni test koji dokazuje da je `garantovano` sada uhvaćeno.

# Implementation steps

1. U `resources/claim_rules/default_v1.yaml`, dodati uobičajene BHS
   morfološke varijante za `garantujemo` (istog korijena, "garant-"):
   - `garantovano`
   - `garantovan`
   - `garantuje`
   - `garantujem`
   - `garantuju`
   - `garancija` (imenica istog semantičkog polja — provjeriti sa
     implementerom/reviewerom da li spada u isti "garant-" obrazac ili je
     predaleko od originalnog nalaza; ako je sporno, izostaviti i
     zabilježiti kao otvoreno pitanje u review-u, ne nagađati).

   Zadržati postojeći redoslijed/format liste (jedan termin po redu,
   lowercase, bez navodnika osim gdje YAML to zahtijeva kao za `"100%"`).

2. NE dirati `claim_linter.py` — `_contains_word`/`lint_claim` već rade
   ispravno za bilo koji termin u listi; problem je bio isključivo u
   POKRIVENOSTI liste, ne u logici poređenja.

3. Test u `tests/unit/application/posts/test_claim_linter.py`:
   - Novi slučaj: claim sa tekstom koji sadrži "Garantovano ćete dobiti
     istu razinu profesionalnosti..." → `lint_claim` vraća
     `ClaimStatus.PROHIBITED` sa `"prohibited-claim"` u `reason_codes`
     (isti oblik provjere kao postojeći testovi za `garantujemo`).
   - Regresioni test da NORMALNE riječi koje dijele prefiks ali NISU
     stvarni oblik korijena i dalje NE trigguju lažno pozitivan rezultat
     (npr. "garancijski list" ako `garancija` nije dodano, ili bilo koja
     druga riječ sa istim prefiksom a različitim značenjem — implementer
     bira razuman primjer i dokumentuje ga u testu).
   - Postojeći test(ovi) za `garantujemo` i dalje prolaze nepromijenjeni
     (dokaz da stara pokrivenost nije narušena).

# Acceptance

- [ ] `resources/claim_rules/default_v1.yaml` sadrži nove morfološke
      varijante `garantujemo`-korijena (najmanje `garantovano`).
- [ ] Novi test dokazuje da "Garantovano ćete dobiti..." sada dobija
      `ClaimStatus.PROHIBITED`.
- [ ] Postojeći testovi za `garantujemo` i dalje prolaze (nema regresije).
- [ ] `claim_linter.py` NIJE mijenjan (git diff dokaz — čisto data+test
      izmjena).
- [ ] Nema izmjena van `allowed_paths`.
- [ ] `python -m pytest tests/unit/application/posts/test_claim_linter.py -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.

# Verification

```bash
python -m pytest tests/unit/application/posts/test_claim_linter.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Nova varijanta stvarno hvata prijavljen slučaj ("Garantovano ćete
  dobiti...") — provjeriti direktnim pozivom `lint_claim`, ne samo
  čitanjem test koda;
- nema lažnih pozitiva na razumnim BHS rečenicama koje dijele prefiks a
  nemaju isto značenje (npr. riječi koje slučajno sadrže "garant" kao dio
  drugog korijena — provjeriti da li takve uopšte postoje u BHS pre nego
  što se brine o lažnim pozitivima koji nisu realni);
- `claim_linter.py` zaista nedirnut (git diff);
- ako je implementer dodao `garancija` — procijeniti da li je to razuman
  domet ili predaleko od originalnog nalaza (nije striktan blocker, ali
  vrijedi komentar u review-u).

# Rollback

LOW risk — čista data+test izmjena, nema koda. §29: Claude-only review,
PASS → odmah merge, bez posebnog Human Owner odobrenja po tasku.

# Coordination

Nezavisan od svih trenutno otvorenih taskova (ne dira nijedan isti fajl).
Može ići paralelno sa bilo čim. Namjerno OSTAVLJEN implementer=TBD —
Human Owner je tražio da se ovo "otvori i odmah završi [kao kontrakt] da
ostaje za kasnije" — kontrakt je kompletan i spreman da ga bilo koji
implementer pokupi kad bude na redu, nije hitno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-028-morphological-terms
Branch:   task/ACS-F1-028-morphological-terms
Base:     main @ c4e9088
```
