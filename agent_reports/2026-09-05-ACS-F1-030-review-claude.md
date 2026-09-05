# ACS-F1-030 — Claude review (round 1) + fix brief za Pi

**Task:** ACS-F1-030 (A13 dio 2, foundation — `layout_specs` perzistencija)
**Implementer:** Pi
**Reviewer:** Claude (MEDIUM, §29 Claude-only)
**Verdict:** PASS_WITH_NOTES — jedan fix zatražen prije merge-a (F1, REAL correctness bug, ne stilski nit-pick)

## Šta je nezavisno provjereno

Pročitao sam `git diff main` za sve izmijenjene fajlove (ne samo evidence), i
`resources/migrations/0005_layout_specs.sql` u cjelosti. Pokrenuo sam testove
nezavisno u worktree-u:

```text
$ pytest tests/unit/domain/visual/ tests/integration/database/repositories/test_sqlite_visual_repository.py tests/integration/database/test_migrations.py -v
20 passed

$ pytest -q
848 passed

$ ruff check .
All checks passed!

$ mypy src
Success: no issues found in 149 source files
```

Migracija tačno prati plan sekciju 24, `LayoutSpec` polja su stvarno
opciona (`test_layout_spec_fields_are_typed_enums` — POSTOJEĆI test —
nepromijenjen i dalje prolazi bez novih polja), `VisualRepositoryPort`
proširenje je aditivno (`save_visual_system`/`get_visual_system` netaknuti,
git diff potvrđuje), `domain/visual/entities.py`/`enums.py`/`slots.py`/
`application/`/`resources/prompts/`/migracije `0000`-`0004` nedirnuti.

## F1 — `save_layout_spec` upsert tiho prepisuje `created_at` na re-save

`LayoutSpec` nema `created_at` polje (ispravno, dokumentovano u evidence-u —
kolona je audit metapodatak, ne domain polje). Adapter ga zato GENERIŠE
IZNOVA (`utc_now()`) na SVAKOM pozivu `save_layout_spec`, uključujući i
upsert granu (`ON CONFLICT(id) DO UPDATE SET ... created_at=excluded.created_at`).

Ovo znači: bilo koji budući poziv koji ponovo snimi ISTI `layout_spec.id`
(realan slučaj za A13 dio 2b — npr. `plan_post_layout.py` prvo snimi
layout sa `validation_status="INVALID"`, pa ga kasnije re-validira i snimi
ponovo sa `validation_status="VALID"`, ISTI `id`) će TIHO PREPISATI
originalno vrijeme kreiranja na trenutni "now". Live sam reprodukovao:

```text
$ python - (dva save_layout_spec poziva, isti id, razmak 1.2s)
first created_at:  2026-09-05T06:55:02.382881+00:00
second created_at: 2026-09-05T06:55:03.593649+00:00
CHANGED: True
```

Nijedan postojeći test ovo ne hvata — `test_round_trip_layout_spec` poredi
`get_layout_spec(...) == spec`, a `LayoutSpec` (domain objekat) NEMA
`created_at` polje, pa taj `==` uopšte ne dotiče kolonu. Ovo je stvaran,
neopažen gap: kolona koja bi trebala biti "kad je red PRVI PUT nastao"
umjesto toga postaje "kad je red POSLJEDNJI PUT dotaknut" — direktno
suprotno projekt principu append-only/audit-trail (isti princip koji
opravdava zašto `revisions` tabela postoji, zašto Approved Facts imaju
provenance, itd.).

### Traženi fix

U `save_layout_spec`, NE prepisivati `created_at` na conflict — izostaviti
ga iz `SET` liste (SQLite `ON CONFLICT DO UPDATE` mijenja SAMO kolone
eksplicitno navedene u `SET`; ako `created_at` nije tamo, zadržava
POSTOJEĆU vrijednost reda, dok INSERT grana i dalje ispravno postavlja
originalnu vrijednost za nov red):

```python
"INSERT INTO layout_specs (id, content_piece_id, format,"
" payload_json, validation_status, created_at)"
" VALUES (?, ?, ?, ?, ?, ?)"
" ON CONFLICT(id) DO UPDATE SET"
" content_piece_id=excluded.content_piece_id,"
" format=excluded.format,"
" payload_json=excluded.payload_json,"
" validation_status=excluded.validation_status",
    # created_at namjerno IZOSTAVLJEN iz UPDATE seta — čuva original
```

Dodati regresioni test (isti oblik kao moja live provjera): snimiti isti
`layout_spec.id` DVA PUTA (drugi put sa drugačijim `validation_status`,
npr. simulira re-validaciju), pročitati `created_at` DIREKTNO iz baze
(`SELECT created_at FROM layout_specs WHERE id=?`, ne kroz domain objekat
jer on tu kolonu ne nosi) prije i poslije drugog snimanja, potvrditi da su
IDENTIČNI (koristiti `time.sleep` dovoljno dugačak da bi se timestamp
razlikovao AKO bug postoji — npr. 1.1s, isti pristup kao moja live
reprodukcija — ili mockovati/injektovati `utc_now` ako je to čistije;
implementer bira).

## Manja napomena (NIJE blocker)

`test_save_layout_spec_requires_identity` testira samo `id=None` granu, ne
i `content_piece_id=None`/`validation_status=None` odvojeno. Za razliku od
ACS-F1-029-ovog "brief missing" nalaza (gdje su dvije DIFERENTNE entitetske
putanje bile slučajno spojene), ovdje su sve tri provjere doslovno susjedne,
identičnog oblika (`if X is None: raise ValueError(...)`), lako vizuelno
provjerljive u par linija — rizik od skrivenog bug-a je zanemarljiv. Ne
tražim fix za ovo, samo bilježim za budući reviewer ako se ikad promijeni.

## Sljedeći korak

Pi: ukloniti `created_at` iz `ON CONFLICT DO UPDATE SET` liste u
`save_layout_spec`, dodati regresioni test za "created_at se ne mijenja na
re-save istog id-a", ponovo pokrenuti pun set komandi iz kontrakta (unit +
integration + cijeli suite + ruff + mypy), ažurirati evidence sa novom
"Fix runda (F1)" sekcijom. Mala izmjena (jedna linija SQL + jedan test),
ne treba Codex rundu — kad se potvrdi, koordinator merguje.
