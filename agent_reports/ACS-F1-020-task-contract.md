---
task_id: ACS-F1-020
phase: Faza-1 (post A8, post A12 dio 1)
title: "claim_linter.py: word-boundary fix za prohibited-terms/duration substring lažne pozitive"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - tests/unit/application/posts/test_claim_linter.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/posts/claim_validator.py
  - resources/claim_rules/
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/ports/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP je nedostupan (server se rekonektuje) u trenutku pisanja.
    Koordinator će pokrenuti detect-changes/impact prije merge-a. `claim_linter.py`
    je shared/cross-cutting (poziva se iz GenerateSocialPost pipeline-a za SVAKU
    generisanu tvrdnju) — nizak rizik promjene same po sebi (čista funkcija, bez
    I/O), ali visok "blast radius" ako se pokvari (utiče na svaki generisani post).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 1a84370
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Nezavisan spoljni code review (druga Claude sesija, ne ovaj koordinator)
je pregledao repo i našao stvaran bug u `claim_linter.py` — koordinator
je nezavisno reprodukovao PRIJE pisanja ovog kontrakta (nije samo
preuzeto na vjeru):

```python
c1 = ContentClaim(id="c1", type=ClaimType.FACT,
    text="Ordinacija ima tri jedinice za digitalno skeniranje zuba.",
    status=ClaimStatus.VERIFIED_BY_FACT, fact_ids=("f1",))
lint_claim(c1, rules)
# -> status=PROHIBITED, reason_codes=('prohibited-claim',)
```

```python
c2 = ContentClaim(id="c2", type=ClaimType.CTA,
    text="Posjetite nas danas, mjesto broj 1 za vas osmijeh.",
    status=ClaimStatus.NON_FACTUAL)
lint_claim(c2, rules)
# -> status=UNSUPPORTED, reason_codes=('unsupported-duration',)
```

**Uzrok**: `lint_claim`/`_numeric_reason_code` u
`src/ai_campaign_studio/application/posts/claim_linter.py` koriste plain
substring provjeru (`term.casefold() in text_folded`, `unit in
text_folded`, `symbol.casefold() in text_folded`) umjesto word-boundary
provjere. `"jedinice"` sadrži `"jedini"` (pravi zabranjen termin iz
`resources/claim_rules/default_v1.yaml`); `"danas"` sadrži `"dan"` (pravi
duration unit).

**Ovo je ISTA klasa greške kao R2-BF-1** (ACS-F1-017, DeepSeek exact-count
regex je lažno hvatao `discount`/`account_id` jer je substring `"count"`
matchovao bez granice riječi) — samo ovdje nije uhvaćena jer
`test_claim_linter.py` ne pokriva nijedan word-boundary slučaj (provjereno
prije pisanja kontrakta — nema `\b`/word-boundary testa u fajlu).

**Zašto je ovo ozbiljno**: `claim_linter` je dio jedinog mehanizma koji
štiti glavni diferencijator aplikacije (fact-grounding, live dokazano
protiv 3 provajdera u A8) — provjera zabranjenih termina radi PRIJE
provjere `VERIFIED_BY_FACT`, pa čak i tvrdnja koja je prošla PRAVU
fact-provjeru biva odbačena. Drugi slučaj (`"danas"` → lažni
`unsupported-duration`) je vjerovatno JOŠ češći u praksi — "naručite
danas"/"javite se danas" su standardne CTA fraze; ovo bi se stalno
okidalo u realnoj upotrebi i punilo "Provjera usklađenosti" panel lažnim
upozorenjima, erodirajući povjerenje u sistem koji inače radi dobar posao.

Ovo NIJE poznat/prihvaćen rizik — propust u test pokrivenosti, ne
namjeran dizajn.

# Objective

Zamijeniti sve substring provjere u `claim_linter.py` (prohibited_terms,
duration units, currency symbols) sa word-boundary regexom, po istom
obrascu koji je već primijenjen u `openai_adapter.py`
(`_COUNT_LINE_RE`, ACS-F1-017 R2-BF-1 fix) — `re.search(rf"\b{re.escape(term)}\b",
text_folded)` ili ekvivalentno.

# Implementation steps

1. U `lint_claim`, zamijeni `if term.casefold() in text_folded:` sa
   word-boundary provjerom. Pazi na `re.escape(term)` jer termini mogu
   sadržati specijalne regex karaktere (npr. `"100%"` je već u listi —
   `%` nije regex-specijalan ali navika `re.escape` je ispravna
   disciplina).
2. U `_numeric_reason_code`, zamijeni `if unit in text_folded and
   has_digit:` sa word-boundary provjerom za `unit`.
3. **Takođe** primijeni isti fix na `if symbol.casefold() in text_folded
   and has_digit:` (currency symbols) — spoljni review nije eksplicitno
   testirao ovaj slučaj, ali ima IDENTIČNU strukturnu manu (npr. `"KM"`
   kao substring unutar neke riječi bi teoretski isto lažno okinulo).
   Uradi isti fix ovdje radi konzistentnosti, sa bar jednim regresionim
   testom koji dokazuje da je prije bio moguć false-positive.
4. Multi-word termini (npr. `"bez rizika"`, `"potpuno sigurno"`) MORAJU
   i dalje raditi ispravno sa word-boundary regexom — `\b` radi na
   početku/kraju cijelog fraze-stringa, ne po riječi unutar fraze, pa
   `r"\bbez rizika\b"` i dalje matchuje frazu kao cjelinu. Dodaj
   eksplicitan test za ovo da dokažeš da fix ne kvari multi-word slučaj.
5. Testovi — dodaj REGRESIONE testove za oba nalaza iz ovog kontrakta
   (word koji sadrži zabranjen termin kao substring, i dalje ne smije
   biti PROHIBITED; "danas" ne smije okinuti unsupported-duration), plus
   potvrdi da postojeći pozitivni slučajevi (stvaran zabranjen termin kao
   cijela riječ, stvaran duration signal) i dalje rade.

# Acceptance

- [ ] `lint_claim(claim sa "jedinice", VERIFIED_BY_FACT)` NE postaje
      `PROHIBITED`.
- [ ] `lint_claim(claim sa "danas ... broj 1", NON_FACTUAL)` NE dobija
      `unsupported-duration` reason code samo zbog "danas".
- [ ] Stvaran zabranjen termin kao cijela riječ (npr. "Mi smo najbolji
      izbor.") I DALJE postaje `PROHIBITED`.
- [ ] Multi-word termin ("bez rizika", "potpuno sigurno") i dalje radi.
- [ ] Stvaran duration signal (npr. "Ponuda traje 3 dana.") i dalje
      postaje `unsupported-duration`.
- [ ] Currency symbol substring fix ima bar jedan regresioni test.
- [ ] `python -m pytest tests/unit/application/posts/ -v` prolazi, sa
      novim testovima za oba nalaza + currency slučaj.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/posts/test_claim_linter.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- word-boundary regex ispravno hendluje multi-word termine, non-ASCII
  BHS karaktere (č/ć/š/ž/đ), i termine sa regex-specijalnim karakterima;
- nema regresije na postojeće pozitivne (istinski prohibited/duration)
  slučajeve;
- currency symbol fix je konzistentan sa ostatkom.

# Rollback

MEDIUM risk (shared cross-cutting funkcija, ali čista/bez I/O, lako
testabilna). Fix na istoj branch bez proširenja scope-a. §29: Claude-only
review, PASS -> odmah merge.

# Coordination

Nezavisno od ACS-GUI-005 (u review-u, čeka Codex re-verifikaciju) —
potpuno disjoint fajlovi, može ići paralelno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-020-claim-linter-word-boundary
Branch:   task/ACS-F1-020-claim-linter-word-boundary
Base:     main @ 1a84370
```
