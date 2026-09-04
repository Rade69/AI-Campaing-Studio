# → ZA MINIMAX — ACS-F1-022 dopuna (mala, ista funkcija)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Prije nego što predaš evidence, dodaj JOŠ JEDNU malu stvar u
`_validate_plan_domain` — isti fajl, ista funkcija koju već diraš za
role_sequence provjeru, pa je jeftinije uraditi sad nego otvoriti novi
task za jednu liniju.

## Šta

Duplicate-topics provjera:
```python
topics = [item.topic for item in output.items]
if len(topics) != len(set(topics)):
```
poredi teme TAČNIM string poređenjem. "Zdravlje zuba" i "zdravlje zuba."
(različito veliko slovo, tačka na kraju) prolaze kao "različite" teme,
iako su suštinski ista tema. Ista vrsta popuštanja kao substring bug koji
je Pi upravo popravio u claim_linter-u (ACS-F1-020), samo niži rizik.

## Fix

Normalizuj prije poređenja:
```python
topics = [item.topic.casefold().strip() for item in output.items]
```
(samo za poređenje — NE mijenjaj `item.topic` koji se stvarno perzistuje,
originalne vrijednosti ostaju kakve jesu).

Dodaj jedan test: dvije teme koje se razlikuju samo u velikom slovu/
razmaku/tački na kraju → i dalje se tretiraju kao duplikat, baca
`InvariantViolation`.

## Ostatak

Sve iz originalnog kontrakta ([agent_reports/ACS-F1-022-task-contract.md](agent_reports/ACS-F1-022-task-contract.md))
ostaje isto — ovo je samo mala dopuna, ne mijenja risk nivo ni review put.
