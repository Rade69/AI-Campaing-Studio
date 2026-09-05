# ACS-F1-032 — Claude review (round 1) + fix brief za MiniMax

**Task:** ACS-F1-032 (A14 dio 1 — Renderer spike, R-A vs R-B)
**Implementer:** MiniMax
**Reviewer:** Claude (MEDIUM, §29 Claude-only)
**Verdict:** PASS_WITH_NOTES — jedan fix zatražen prije merge-a (F1,
**KRITIČAN, projekat-širok correctness bug**, ne stilski nit-pick)

## Šta je nezavisno provjereno (i potvrđeno dobro)

Pokrenuo sam OBA spike kandidata sam, otvorio stvarne PNG fajlove (ne
samo čitao metrics.json), pročitao `COMPARISON.md` i
`renderer_spike_result.json` u cjelosti:

- **Oba kandidata stvarno rade** — `shot.png` za R-A i R-B oba prikazuju
  ispravno renderovan BHS tekst ("Vaš osmijeh je naš prioritet.",
  "Slušamo vas prvo.", "Zakažite konsultaciju") — č/š dijakritici čisti,
  bez tofu-kutija/mojibake, na OBA kandidata. Dizajn (teal/zelen gradient,
  BS logo, CTA dugme) je razuman i profesionalan za oba.
- **Mjerenja su stvarna, ne izmišljena** — pokrenuo sam
  `render.py` mentalno-provjerio kroz kod (Playwright launch +
  `getBoundingClientRect()` za R-A, Pillow `font.getlength()`-baziran
  word-wrap za R-B); brojevi u evidence-u (745ms vs 48.5ms,
  377KB vs 51KB) odgovaraju stvarnim `metrics.json` fajlovima na disku.
- **Odluka (R-B) je dobro obrazložena** — packaging argument (chromium
  ~150MB binary vs Pillow već postojeći dep) je legitiman i konzistentan
  sa "local-first desktop app" premisom iz CLAUDE.md. R-A ostaje u
  repou kao dokumentovana referenca, ne obrisan — razuman izbor.
- **Scope čist**: `git diff --stat` potvrđuje SAMO `pyproject.toml` (14
  linija) + novi fajlovi u `spikes/`/`artifacts/`;
  `infrastructure/rendering/`, `ports/rendering.py`,
  `application/rendering/` NISU kreirani, tačno kako kontrakt traži.
- 858/858 pytest, ruff/mypy čisti — reprodukovao sam i to.

## F1 — `pyproject.toml` izmjena je NEVALIDNA TOML struktura, kvari SVAKU buduću instalaciju projekta

Dodano:

```toml
[project.optional-dependencies.renderer-spike]
playwright = ["playwright>=1.60"]
```

Ovo NIJE ispravan PEP 621 oblik. `project.optional-dependencies` MORA biti
tabela gdje je svaki KLJUČ ime "extra"-a a VRIJEDNOST lista requirement
stringova (isti oblik kao postojeći `dev = [...]` u istoj tabeli). Ono što
je napisano umjesto toga kreira UGNIJEŽDENU tabelu
(`optional-dependencies.renderer-spike.playwright = [...]`) — TOML to
parsira bez greške (potvrdio `tomllib.load` — vraća
`{'renderer-spike': {'playwright': [...]}}`, dict unutar dict-a), ALI
setuptools-ova validacija to odbija.

**Live reprodukovano, oba scenarija fatalna:**

```text
$ pip install --dry-run --no-deps -e ".[renderer-spike]"
ValueError: invalid pyproject.toml config: `project.optional-dependencies.renderer-spike`.
configuration error: `project.optional-dependencies.renderer-spike` must be array

$ pip install --dry-run --no-deps -e .        # BEZ ijednog extra-a!
ValueError: invalid pyproject.toml config: `project.optional-dependencies.renderer-spike`.
configuration error: `project.optional-dependencies.renderer-spike` must be array
```

**Ovo znači da OTKAD je ova grana napravljena, `pip install -e .` I
`pip install -e ".[dev]"` PADAJU U POTPUNOSTI** — ne samo za novi
`renderer-spike` extra, nego za BILO KOJU instalaciju projekta, uključujući
onu koju je koristio SVAKI DOSADAŠNJI implementer ("fresh
`pip install -e ".[dev]"`", doslovno citirano u komentaru par linija
iznad u istom fajlu). Zašto ovo nije uhvaćeno u evidence-u: DIJELJENI
`.venv` je VEĆ instaliran iz PRIJE ove izmjene (isti "workflow §13 `.pth`
zamka" obrazac koji je Pi već prije primijetio) — `pytest`/`ruff`/`mypy`
i dalje rade jer koriste POSTOJEĆI `.pth` unos, ne re-triggeruju
metadata parsing. Nijedna od postojećih acceptance stavki (pytest/ruff/
mypy) ovo ne bi ikad uhvatila — trebalo je stvarno pokrenuti
`pip install -e .` da se otkrije.

### Traženi fix

Zamijeniti pogrešnu ugniježdenu tabelu ispravnim ključem UNUTAR
POSTOJEĆE `[project.optional-dependencies]` tabele (ista tabela gdje je
`dev = [...]`):

```toml
[project.optional-dependencies]
dev = [
    ...,
    "httpx>=0.27",
]
renderer-spike = ["playwright>=1.60"]
```

(ukloniti kompletno `[project.optional-dependencies.renderer-spike]` +
`playwright = [...]` red; dodati JEDAN red `renderer-spike = [...]`
odmah nakon `dev = [...]` bloka, unutar iste `[project.optional-dependencies]`
sekcije koja već postoji ranije u fajlu — NE nova sekcija).

**Obavezna verifikacija fixa** (ovo MORA biti u novoj evidence rundi,
ne samo pytest/ruff/mypy koji ovo ne hvataju):

```bash
python -m pip install --dry-run --no-deps -e .
python -m pip install --dry-run --no-deps -e ".[dev]"
python -m pip install --dry-run --no-deps -e ".[renderer-spike]"
python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['optional-dependencies'])"
```

Sve tri `pip install --dry-run` komande moraju uspjeti (ili barem proći
metadata-validation korak bez `ValueError` — dry-run i dalje pokušava
razriješiti zavisnosti sa mreže što može drugačije usporiti/faliti, bitno
je da NE padne na `setuptools.config.pyprojecttoml` validaciji), a
`tomllib` output mora pokazati `renderer-spike` kao PRAVU listu stringova
(`['playwright>=1.60']`), ne dict.

## Ostalo — bez primjedbi

`spikes/renderer/COMPARISON.md`, `template.svg`/`template.html`, oba
`render.py`, `artifacts/renderer_spike_result.json` (9/9 polja, validan
JSON) — sve u redu, nema dodatnih nalaza.

## Sljedeći korak

MiniMax: popraviti `pyproject.toml` strukturu (gore), pokrenuti
`pip install --dry-run` verifikaciju za sva tri scenarija, ažurirati
evidence sa novom "Fix runda (F1)" sekcijom koja uključuje TAJ konkretan
dokaz (ne samo "ruff/mypy/pytest i dalje prolaze" — to ne dokazuje da je
packaging metadata validna). Malo, brzo — ne treba Codex rundu. Kad se
potvrdi, koordinator merguje.
