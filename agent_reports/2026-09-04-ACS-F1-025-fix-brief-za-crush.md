# → ZA CRUSH — ACS-F1-025 fix runda (BF-1)

**Od:** koordinator (Claude) · **Za:** Crush · **Datum:** 2026-09-04

Čist kod, tačno prema kontraktu — ali kontrakt je eksplicitno tražio da
prag (0.6) provjeriš sa "par realnih BHS primjera", ne samo sintetičkim
testovima ("a b c d"), i to je otkrilo pravi problem.

## BF-1 — `.split()` ostavlja interpunkciju zalijepljenu za riječi

```python
>>> 'Posjetite nas danas i zakažite pregled zuba.'.casefold().split()
{'nas', 'posjetite', 'i', 'zakažite', 'pregled', 'danas', 'zuba.'}
```

`"zuba."` (sa tačkom) je DRUGAČIJI token od `"zuba"` — pa dvije rečenice
koje pričaju o istoj stvari, samo sa tačkom/zarezom na drugom mjestu,
dobijaju VJEŠTAČKI niži skor sličnosti nego što bi trebale.

Testirao sam realan slučaj — plitka parafraza istog CTA-a:

```text
"Posjetite nas danas i zakažite pregled zuba."
"Zakažite pregled zuba već danas kod nas."
```

Sa trenutnom implementacijom: **0.273** (daleko ispod praga 0.6 — NE bi
bilo flagovano, iako je ovo TAČNO ono što ova provjera treba da uhvati).

Sa `re.findall(r"\w+", text.casefold())` umjesto `.casefold().split()`:
**0.556** (bliže pragu, ispravno odražava stvarnu sličnost).

Provjerio sam i da fix NE pravi lažne pozitive — dvije stvarno različite
rečenice o istoj temi (implantati) ostaju nisko (0.071) i prije i poslije
fixa.

## Fix

```python
import re

def jaccard_similarity(text_a: str, text_b: str) -> float:
    words_a = set(re.findall(r"\w+", text_a.casefold()))
    words_b = set(re.findall(r"\w+", text_b.casefold()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)
```

`\w+` u Python `re` je Unicode-aware po defaultu, pa BHS dijakritici
(č/ć/š/ž/đ) ostaju dio riječi ispravno — provjeri da tvoji novi testovi
to i dokažu (riječ sa dijakritikom se i dalje ispravno poklapa sama sa
sobom).

## Novi testovi koje tražim

- Dvije rečenice koje se razlikuju SAMO u interpunkciji na kraju
  (npr. "Naručite danas." vs "Naručite danas!") → identična sličnost kao
  bez interpunkcije (dokaz da fix radi).
- Realan BHS primjer parafraze (možeš iskoristiti moj gornji par ili
  sličan) → sličnost STVARNO odražava sadržajnu bliskost, ne artefakt
  interpunkcije.
- Postojeći sintetički testovi (a/b/c/d stil) i dalje prolaze
  nepromijenjeni — potvrdi regresiju.

## Van scope-a ove runde

`generate_social_post.py` integracija (poziv `is_too_similar_to_any`,
`list_campaign_content`) je već ispravna, ne diraj. `SIMILARITY_THRESHOLD
= 0.6` ostaje isti — ovo NIJE promjena praga, nego ispravka tokenizacije
koja utiče na sve skorove podjednako.

## Kad završiš

Evidence update (nova "Fix runda (BF-1)" sekcija u
`agent_reports/2026-09-04-ACS-F1-025-crush.md`, doslovan test output —
uključi "prije/poslije" poređenje na realnom BHS primjeru). Ne commit-uj.
