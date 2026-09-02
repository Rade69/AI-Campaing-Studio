# → ZA PI — ACS-F1-011 brief

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-02

## Status — PROČITAJ PRVO

**ACS-F1-011 je BLOCKED.** Zavisi od **ACS-F1-010**, koji je implementiran (od koordinatora
samog, izuzetno — ne od tebe, ne treba te brinuti zašto) ali **još NIJE mergovan u main** — čeka
Codex review + eksplicitno Human Owner odobrenje (HIGH risk, migracija).

**Ne počinji stvaran kod dok ti koordinator ne javi da je ACS-F1-010 mergovan.** Razlog: tvoj
use-case zavisi od `ContentPiece.payload` polja koje trenutno ne postoji na `main` — ako počneš
sad, radićeš protiv zastarjelog domain modela i sav taj rad ide u otpad.

Slobodno u međuvremenu: pročitaj pun kontrakt i postojeći kod (lista ispod), isplaniraj pristup,
postavi pitanja ako nešto nije jasno — samo ne piši `application/posts/*.py` kod dok ne dobiješ
zeleno svjetlo.

Kad koordinator javi "ACS-F1-010 mergovan" — **prvo `git merge main` (ili ekvivalent) u tvoj
worktree**, PA TEK ONDA kreni na kod. Tvoj worktree je granat sa `main @ 5603030`, prije nego što
je ACS-F1-010 kontrakt/implementacija uopšte postojala.

## Gdje je pun kontrakt

`agent_reports/ACS-F1-011-task-contract.md` — pročitaj ga cijelog, ovaj brief je samo skraćeni
pregled, ne zamjena.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-011-allowed-facts-post-generation
Branch:   task/ACS-F1-011-allowed-facts-post-generation
```

## Ukratko šta radiš (A11 — Allowed Facts + Social Content Generation)

Treći generation use-case u nizu (poslije ACS-F1-009 campaign plan), isti arhitektonski obrazac:
Protocol portovi, atomic persist, fake AI port u testovima.

Tri nova fajla u `application/posts/`:

1. **`select_allowed_facts.py`** — deterministička selekcija fact-ova (bez AI, bez embeddings, bez
   vector DB). Zadrži samo `is_fact_usable()` fact-ove (već postoji u `domain/facts/policies.py`,
   ne duplirati), matchuj protiv `campaign_item.facts_needed` jednostavnim lexical
   (case-insensitive substring) matcher-om.
2. **`claim_validator.py`** — Fact-ID validator, TAČNO plan sekcija 35 (ne 36 — to je A12-ov
   posao). FACT claim mora imati fact_id koji postoji, je `APPROVED`, i bio je u dozvoljenom setu
   → `VERIFIED_BY_FACT`, inače `UNSUPPORTED`. CTA/OPINION/CREATIVE → uvijek `NON_FACTUAL`.
3. **`generate_social_post.py`** — `GenerateSocialPost` use-case, orkestrira sve (učitaj
   campaign/plan/item/snapshot/facts → build AIRequest → AI call → schema validacija → claim
   validacija → **interim ContentStatus pravilo**: bilo koji `UNSUPPORTED` claim →
   `NEEDS_REVIEW`, inače `GENERATING` — **NIKAD `DRAFT`**, taj status je rezervisan za A12-ov
   "nema upozorenja" ishod koji ovaj task ne implementira → atomic persist).

Pun tok, tačni potpisi, svi acceptance kriterijumi i test-po-test lista su u kontraktu — ovo je
samo orijentacija.

## Šta NE raditi (namjerne granice, ne propust)

- A12-ov linter (prohibited termini, numeric pattern detekcija, `claim_rules/default_v1.yaml`) —
  van scope-a.
- `ContentSlotContract` (vizuelni/layout slot pravila) — A13/A14 posao.
- `channels`/`ai_registry` registry lookup — `application/posts/` ih ne uvozi, isto kao
  `application/campaigns/`.
- Nova repository metoda — sve što ti treba (`get_campaign`, `get_plan`,
  `brand_repo.get_snapshot`, `fact_repo.list_snapshot_facts`, `content_repo.save_content_piece`)
  već postoji. `CampaignItem` po id-u nalaziš pretragom kroz `plan.items` (plan ti već nosi sve
  iteme), ne izmišljaj novi repository poziv.

## Ako naiđeš na gap kao što je koordinator naišao sa `ContentPiece.payload`

Javi, ne izmišljaj zaobilazno rješenje. Isti obrazac kao dosad (F1-007/009/010 su svi imali po
jednu malu, dokumentovanu, aditivnu izmjenu van "čistog" application-layer scope-a kad je stvaran
gap postojao).
