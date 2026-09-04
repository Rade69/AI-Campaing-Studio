# → ZA PI — ACS-F1-020 fix runda (BF-1)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-04

Odličan posao na sva tri predviđena slučaja (prohibited terms, duration,
multi-word, non-ASCII) — tačno, čisto, dobro testirano, i adversarijalno
dokazano (prije/poslije revert). Jedna stvar te vraća u fix rundu, koju
ni kontrakt ni tvoji testovi nisu pokrili: **`€` kao currency symbol.**

## BF-1 — `\b€\b` nikad ne matchuje ništa (regres, ne samo propust)

```python
term = "€"
pattern = rf"\b{re.escape(term.casefold())}\b"
re.search(pattern, "cijena je 5€ ukupno".casefold())  # -> None
```

`€` nije `\w` karakter (nije alfanumerički), pa `\b` (word boundary) NE
MOŽE da se usidri oko njega u realnom tekstu — `\b` zahtijeva prelaz
između `\w` i ne-`\w` karaktera. Kad je i sam term ne-`\w` (simbol), i
karakter prije/poslije njega je tipično ne-`\w` (razmak, interpunkcija),
NEMA granice tu, pa `\b€\b` nikad ne matchuje.

**Ovo NIJE isti tip greške kao prohibited terms/duration units** (koji su
alfanumerički i ISPRAVNO trebaju word-boundary). Ovo je suprotan problem:
`€` kao substring NIKAD nije mogao lažno matchovati unutar veće riječi
(nema BHS/EN riječi koja sadrži `€`), pa word-boundary ovdje nije trebao —
plain substring je bio ispravan i dovoljan za simbole. Tvoj fix je
zamijenio ISPRAVNO ponašanje sa POGREŠNIM za ovaj konkretan slučaj.

**Posljedica**: prava cijena sa € simbolom (npr. "Cijena je 500€") više
NIKAD ne dobija `unsupported-price` flag — bezbjednosna mreža je OSLABLJENA
za taj simbol, ne samo popravljena za riječi. Nijedan tvoj test ne pokriva
`€` kao pozitivan slučaj (samo "KM" u `test_numeric_price_is_unsupported`)
— zato je prošlo neprimijećeno.

Nezavisno reprodukovano: `re.search(r"\b€\b", "cijena je 5€ ukupno".casefold())`
→ `None`, dok je stari `"€" in text_folded` → `True`.

## Šta uraditi

`_contains_word` treba primijeniti word-boundary SAMO na termine koji
sadrže bar jedan `\w` karakter (alfanumerički). Za termine koji su u
potpunosti sastavljeni od ne-`\w` karaktera (npr. `"€"`), vrati se na plain
substring — tu nema rizika od lažnog matcha unutar veće riječi, jer
simbol ne može biti "dio" alfanumeričke riječi.

```python
def _contains_word(text_folded: str, term: str) -> bool:
    """Whole-word check for alphanumeric terms; plain substring for
    symbol-only terms (``\\b`` cannot anchor around a non-word character
    like ``€``, and a symbol cannot appear "inside" a larger word the
    way an alphanumeric substring can, so plain substring is safe there).
    """
    folded_term = term.casefold()
    if not re.search(r"\w", folded_term):
        return folded_term in text_folded
    return re.search(rf"\b{re.escape(folded_term)}\b", text_folded) is not None
```

Prilagodi po potrebi — bitno je da `€` (i bilo koji budući čisto-simbolički
termin) i dalje radi kao plain substring, dok alfanumerički termini
zadržavaju word-boundary zaštitu koju si već ispravno napravio.

## Novi test koji tražim

Dodaj pozitivan test za `€` specifično (ne samo "KM"):

```python
def test_euro_symbol_price_is_still_unsupported() -> None:
    result = lint_claim(_claim(ClaimStatus.NON_FACTUAL, "Cijena je 500€"), _rules())
    assert result.status is ClaimStatus.UNSUPPORTED
    assert "unsupported-price" in result.reason_codes
```

Ovo mora PROĆI nakon fixa (dokaz da je regres zatvoren), i mora PASTI
protiv tvoje trenutne (BF-1) implementacije (dokaz da je nalaz stvaran —
isti adversarijalni standard kao tvoj prije/poslije test za ostala tri
slučaja).

## Van scope-a ove runde

Sva tri originalna slučaja (jedinice/jedini, danas/dan, bambus/BAM) su
već PASS, ne diraj ih. Ne širi na `claim_validator.py` ili bilo šta drugo
van `claim_linter.py`.

## Kad završiš

Evidence update (nova "Fix runda (BF-1)" sekcija, doslovan test output —
uključi i "pada prije fixa, prolazi poslije" dokaz za novi € test). Ne
commit-uj. MEDIUM risk, §29 — nakon mog review-a ide direktno na merge.
