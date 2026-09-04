# → ZA PI — ACS-F1-017 fix runda 2 (R2-BF-1)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-04

Codex je uradio re-review nakon tvog BF-1 fixa: `agent_reports/2026-09-04-ACS-F1-017-review-codex-rereview.md`
(u worktree-u) — **REJECT**, jedan nov nalaz (R2-BF-1). Nezavisno sam reprodukovao — stvaran bug,
ne lažna uzbuna. BF-1 (DeepSeek json_schema) ostaje zatvoren, ne diraj to.

## R2-BF-1 — exact-count regex hvata `discount`/`account_id` kao lažan "item count"

`_COUNT_LINE_RE` trenutno glasi:

```python
r"(?P<name>[A-Za-z][A-Za-z0-9_]*count[A-Za-z0-9_]*)\s*:\s*(?P<value>\d+)"
```

Ovo hvata BILO KOJI identifier koji negdje SADRŽI "count", ne samo polja koja su `*_count`. Živa
reprodukcija:

```text
>>> _count_constraints_from_text("discount: 20")
[('discount', 20)]
>>> _count_constraints_from_text("account_id: 123")
[('account_id', 123)]
```

`discount`/`account_id` su potpuno plauzibilni tekstovi u marketing brief-u (popust od 20%,
account ID 123). Trenutni kod bi modelu dao POGREŠNU instrukciju: "generiši tačno 20 stavki" /
"generiši tačno 123 stavke" — realan prompt defekt, ne teorijski.

## Fix (Codex-ov predlog, provjeren)

Zategnuti regex na stvarne count fieldove — samo imena koja se ZAVRŠAVAJU sa `_count` ili su
TAČNO `count`:

```python
r"(?P<name>(?:[A-Za-z][A-Za-z0-9_]*_count|count))\s*:\s*(?P<value>\d+)"
```

## Testovi (obavezno)

- Pozitivno: `content_piece_count: 3` MORA i dalje dodati exact-count instrukciju (regresija na
  postojeći happy path).
- Negativno: `discount: 20` NE SMIJE dodati count instrukciju.
- Negativno: `account_id: 123` NE SMIJE dodati count instrukciju.
- Negativno/prazno: schema bez array bounds + user text bez stvarnog count fielda NE SMIJE dodati
  "Exact count requirements" blok uopšte (prazan `array_constraints` + prazan `count_constraints`).

## Van scope-a ove runde

BF-1 (DeepSeek json_schema→json_object) je već zatvoren i live-verifikovan (ja sam to uradio) —
ne diraj. Nema live/API promjena u ovoj rundi.

## Kad završiš

Evidence update (nova "Fix runda 2 (R2-BF-1)" sekcija). Ne commit-uj. Ide nazad Codex-u na
re-review.
