# → ZA PI — ACS-F1-020 fix runda 2 (BF-2)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-04

Nezavisna paralelna review sesija (druga Claude instanca, radila
istovremeno dok si ti radio BF-1) je pronašla dodatni nalaz. Dobra vijest
prvo: tvoj BF-1 fix (100%/€ oba pravilno rade preko "oba kraja moraju biti
`\w`" logike) je nezavisno potvrđen ispravan i od mene i od te druge
sesije — F1 nalaz iz njihovog izvještaja odnosio se na verziju PRIJE tvog
BF-1, ne na tvoj stvaran fix. **Ovo NIJE otvoreno ponovo.**

Ono što JESTE otvoreno: **F2** — brojevi zalijepljeni direktno za
jedinicu/simbol bez razmaka.

## BF-2 — "30KM", "50EUR", "3dana" se više ne prepoznaju specifično

```python
'Cijena je 30KM ukupno.'  -> UNSUPPORTED('unsupported-number')   # bilo: unsupported-price
'Akcija traje 3dana.'     -> UNSUPPORTED('unsupported-number')   # bilo: unsupported-duration
```

Nezavisno reprodukovano protiv trenutnog main-a (tvoj BF-1 fix, već
mergovan). Status ostaje `UNSUPPORTED` (claim se i dalje hvata, NEEDS_REVIEW
i dalje radi ispravno — ovo NIJE bezbjednosni regres kao € slučaj), ali
reason_code je pogrešan/generički umjesto specifičnog. Uzrok: cifre i
slova su OBA `\w` klasa za `\b`, pa `\bdana\b` NE MOŽE napraviti razliku
između "3dana" (broj zalijepljen za jedinicu — treba matchovati) i
"nedana" (jedinica usred druge riječi — ne treba matchovati) — oba
izgledaju kao "nema granice" iz `\b`-ove perspektive.

**Bitna razlika od originalnog jedinice/jedini problema**: kod
`prohibited_terms` (jedini, vodeći, itd.) STROGO `\b...\b` ponašanje je i
dalje ispravno — ne diraj tu granu. Problem je SAMO kod
`currency_symbols`/`duration_units` u `_numeric_reason_code`, gdje
zalijepljen broj ISPRED termina treba biti DOZVOLJEN (to je legitiman
signal, ne lažna pozitiva), dok slovo ispred/iza i dalje treba biti
zabranjeno (bambus/BAM ostaje ne-match).

## Fix

Dodaj parametar `allow_digit_adjacent` na `_contains_word`, `False` po
defaultu (prohibited_terms ponašanje nepromijenjeno):

```python
def _contains_word(
    text_folded: str, term: str, *, allow_digit_adjacent: bool = False
) -> bool:
    folded_term = term.casefold()
    starts_word = re.match(r"\w", folded_term) is not None
    ends_word = re.search(r"\w$", folded_term) is not None
    if not (starts_word and ends_word):
        return folded_term in text_folded
    if allow_digit_adjacent:
        # A digit immediately before/after the term is a legitimate signal
        # ("3dana", "30KM"), not a false-positive collision (unlike a
        # letter, which would mean the term is glued inside a larger
        # word, e.g. "bambus"/"BAM"). ``[^\W\d]`` = a word character that
        # is NOT a digit (i.e. a letter/underscore) -- the lookaround
        # blocks only that, not a digit.
        pattern = rf"(?<![^\W\d]){re.escape(folded_term)}(?![^\W\d])"
        return re.search(pattern, text_folded) is not None
    return re.search(rf"\b{re.escape(folded_term)}\b", text_folded) is not None
```

Pozivni sajtovi:
- `lint_claim` (prohibited_terms): `_contains_word(text_folded, term)` —
  BEZ izmjene, default `False`.
- `_numeric_reason_code` (currency_symbols): `_contains_word(text_folded,
  symbol, allow_digit_adjacent=True)`.
- `_numeric_reason_code` (duration_units): `_contains_word(text_folded,
  unit, allow_digit_adjacent=True)`.

Provjerio sam ovaj dizajn ručno protiv svih poznatih slučajeva
(jedinice/jedini, danas/dan, bambus/BAM, 3dana, 30KM, 100%, €) — svi
ispravno prolaze. Ne moraš ponovo dizajnirati od nule, ali VERIFIKUJ sam
prije nego predaš (isti standard kao do sada).

## Novi testovi koje tražim

- `"Cijena je 30KM ukupno."` → `unsupported-price` (ne generički
  `unsupported-number`).
- `"Akcija traje 3dana."` → `unsupported-duration`.
- Regresija: `"bambus"` i dalje NE daje `unsupported-price`; `"danas ...
  broj 1"` i dalje NE daje `unsupported-duration` (već postojeći testovi,
  potvrdi da i dalje prolaze).
- Regresija: `"jedinice"` i dalje NE daje `PROHIBITED`; `"100%"`/`"€"`
  i dalje rade (već postojeći testovi iz BF-1, potvrdi da i dalje prolaze
  NEPROMIJENJENI).

## Van scope-a ove runde

`prohibited_terms` grana (poziv bez `allow_digit_adjacent`) — ne diraj,
već ispravna.

## Gdje raditi

ACS-F1-020 je već mergovan na main, pa je za ovaj fix kreiran nov
worktree (ne stari, taj je already merged):

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-F1-020-bf2-glued-numbers
Branch:   task/ACS-F1-020-bf2-glued-numbers
Base:     main @ e483a87
```

```bash
python -m pip install -e . --no-deps -q
```

## Kad završiš

Evidence izvještaj: `agent_reports/2026-09-04-ACS-F1-020-bf2-pi.md` (ne
commit-uj, ostavi u worktree-u, javi mi putanju).
