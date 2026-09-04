# → ZA MINIMAX — ACS-F1-022, mala dopuna 2 (prije merge-a)

**Od:** koordinator (Claude) · **Za:** MiniMax · **Datum:** 2026-09-04

Odličan rad na role_sequence provjeri — sve prolazi, dizajn odluke dobro
obrazložene. Prije nego mergujem, nedostaje jedna stvar iz ranije poslate
dopune ([agent_reports/2026-09-04-ACS-F1-022-addendum-za-minimax.md](agent_reports/2026-09-04-ACS-F1-022-addendum-za-minimax.md)) —
možda je stigla poslije nego što si već bio duboko u implementaciji, pa
je propuštena.

## Šta nedostaje

Duplicate-topics provjera i dalje poredi teme TAČNIM string poređenjem:
```python
topics = [item.topic for item in output.items]
if len(topics) != len(set(topics)):
```
"Zdravlje zuba" i "zdravlje zuba." prolaze kao "različite" teme.

## Fix (isto kao u originalnoj dopuni)

```python
topics = [item.topic.casefold().strip() for item in output.items]
```
(samo za poređenje — `item.topic` koji se stvarno perzistuje ostaje
nepromijenjen).

Dodaj jedan test: dvije teme koje se razlikuju samo u velikom slovu/
razmaku/tački na kraju → i dalje tretirane kao duplikat.

## Sve ostalo

Ostaje kako jeste — role_sequence dio je gotov i odobren, ovo je samo
mala dopuna u istoj funkciji.

## Kad završiš

Ažuriraj evidence (`agent_reports/2026-09-04-ACS-F1-022-minimax.md`, nova
kratka sekcija). Ne commit-uj — javi mi kad je gotovo, ovo je zadnja
stvar prije merge-a.
