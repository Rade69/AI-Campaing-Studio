---
task_id: ACS-F1-025
phase: Faza-1 (post A11)
title: "GenerateSocialPost: deterministička provjera sličnosti novog posta protiv postojećih u istoj kampanji (Jaccard, bez embeddings)"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/posts/generate_social_post.py
  - src/ai_campaign_studio/application/posts/content_similarity.py
  - tests/unit/application/posts/test_content_similarity.py
  - tests/unit/application/posts/test_generate_social_post.py
  - tests/integration/application/posts/test_generate_social_post_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/application/posts/derive_content_status.py
  - src/ai_campaign_studio/application/posts/revise_content_piece.py
  - src/ai_campaign_studio/application/posts/select_allowed_facts.py
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/ports/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. Nov modul
    (`content_similarity.py`) nema postojećih pozivalaca; izmjena u
    `generate_social_post.py::execute` proširuje postojeći tok, ne mijenja
    javni potpis (isti parametri, isti povratni tip).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 2d5f368
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Human Owner je eksplicitno odobrio ovu ideju (od pet predloženih spoljnim
review-om) kao prioritet #1, prije GUI bridge nastavka — direktno gađa
originalni strah koji je pokrenuo cijeli razgovor o smislenosti
aplikacije: da AI izbaci "šest pristojnih, generičnih objava" koje sve
zvuče isto.

Trenutno postoji SAMO provjera da uloge (roles) budu različite
(`_validate_plan_domain`, na nivou PLANA — teme/uloge, ne stvaran tekst
posta) i, od ACS-F1-022, da uloge pripadaju template-u. **Ništa ne
provjerava da li je stvaran TEKST dvije objave (headline/caption) skoro
identičan.** Dvije objave mogu imati različite uloge (PROBLEM vs OFFER) a
opet zvučati skoro isto ako AI generiše plitke varijacije.

**Zašto sad, prije GUI bridge nastavka**: ovo je jeftina provjera
(stdlib, par desetina linija, bez embeddings/vektorske baze) koja
direktno testira srž vrijednosnog obećanja aplikacije — isti princip kao
fact-grounding (ne oslanjati se na "model je dobar", nego sistem koji to
garantuje deterministički).

# Objective

Nakon što se novi post generiše (`GenerateSocialPost.execute()`), uporedi
njegov tekst (headline + caption) sa TEKSTOM svih VEĆ POSTOJEĆIH objava u
ISTOJ kampanji (bilo kog statusa). Ako je Jaccard sličnost (nad skupom
riječi) sa BILO KOJOM postojećom objavom iznad praga (0.6), novi post
dobija status `NEEDS_REVIEW` (bez obzira šta su claim linter/derive_content_status
inače odredili).

**Namjerno JEDNOSMJERNO**: provjerava se SAMO novi post protiv postojećih.
Postojeće, već sačuvane objave (uključujući već `APPROVED`) se NE mijenjaju
retroaktivno — ne dirati/re-snimati tuđe redove, samo status objave koja
se upravo generiše.

**Namjerno bez perzistencije "razloga"**: ovaj task NE dodaje novo polje
na `ContentPiece` (domain je forbidden). Ako je post flagovan zbog
sličnosti, status postaje `NEEDS_REVIEW` — to je dovoljno da ga čovjek
vidi i pregleda. "Sa kojim postom je sličan i koliko" ostaje otvoreno za
budući GUI-facing task kad review ekran stvarno postoji (nema smisla
graditi prikaz "zašto" prije nego postoji GUI koji bi ga pokazao).

# Implementation steps

1. **Novi fajl `application/posts/content_similarity.py`**:
   ```python
   def jaccard_similarity(text_a: str, text_b: str) -> float:
       """Word-set Jaccard similarity, casefold-normalized. 0.0 if either
       text has zero words after normalization."""
       words_a = set(text_a.casefold().split())
       words_b = set(text_b.casefold().split())
       if not words_a or not words_b:
           return 0.0
       return len(words_a & words_b) / len(words_a | words_b)

   SIMILARITY_THRESHOLD = 0.6

   def is_too_similar_to_any(
       candidate_text: str, existing_texts: tuple[str, ...]
   ) -> bool:
       return any(
           jaccard_similarity(candidate_text, existing) >= SIMILARITY_THRESHOLD
           for existing in existing_texts
       )
   ```
   Čista, deterministička, bez I/O — isti stil kao `claim_linter.py`.
   `SIMILARITY_THRESHOLD` je modul-level konstanta (nije korisnički
   podesiva u ovom tasku — to je budući follow-up ako se pokaže potrebnim).

2. **U `generate_social_post.py::execute()`**, nakon što se `payload`
   izgradi i `status` odredi preko `derive_content_status(claims)`, PRIJE
   nego što se `content_piece` konstruiše:
   - Pozovi `self._content_repo.list_campaign_content(campaign_id)` (VEĆ
     POSTOJI na `ContentRepositoryPort`, ne treba novi port metod).
   - Izvuci tekst za poređenje iz svake postojeće objave:
     `f"{piece.payload.headline} {piece.payload.caption}"` za one koje
     imaju `payload is not None` (preskoči one bez payload-a, ne bi
     trebalo da postoje ali defanzivno).
   - Ako `is_too_similar_to_any(f"{output.headline} {output.caption}",
     existing_texts)` — override `status = ContentStatus.NEEDS_REVIEW`
     (bez obzira šta je `derive_content_status` vratio).
3. Testovi za `content_similarity.py` (izolovano, bez use-case-a):
   - Identičan tekst → 1.0 sličnost, `is_too_similar_to_any` True.
   - Potpuno različit tekst → niska sličnost, False.
   - Granica praga (0.6) — tekst tačno na/iznad/ispod praga.
   - Prazan string na jednoj strani → 0.0 (ne dijeljenje sa nulom/ne
     exception).
4. Testovi za `generate_social_post.py` integraciju:
   - Unit: fake `content_repo.list_campaign_content` vraća postojeću
     objavu sa skoro istim headline/caption tekstom kao novi output →
     novi post dobija `NEEDS_REVIEW` iako claim linting ne bi inače to
     tražilo.
   - Unit: fake `content_repo.list_campaign_content` vraća objavu sa
     potpuno drugačijim tekstom → status ostaje šta god je
     `derive_content_status` odredio (ne prisilno mijenjan).
   - Integration: prava SQLite baza, generiši 2 objave za istu kampanju
     sa fake AI portom koji vraća skoro identičan tekst za obje → DRUGA
     objava (prva postojeća) dobija `NEEDS_REVIEW`; PRVA objava OSTAJE
     nepromijenjena (dokaz jednosmjernosti — prva se ne re-snima).

# Acceptance

- [ ] `content_similarity.py` postoji, čista funkcija bez I/O, sa
      `SIMILARITY_THRESHOLD` konstantom.
- [ ] Novi post skoro identičan postojećem u istoj kampanji → `NEEDS_REVIEW`.
- [ ] Novi post različit od postojećih → status nepromijenjen (i dalje
      određen sa `derive_content_status`).
- [ ] Postojeće objave se NE mijenjaju/re-snimaju kad se novi post
      generiše (jednosmjerno, dokazano integration testom).
- [ ] Poređenje koristi `list_campaign_content` (postojeći port metod,
      nema novog port metoda).
- [ ] Nema novog polja na `ContentPiece`/`domain/` (git diff dokaz).
- [ ] `claim_linter.py`, `derive_content_status.py`,
      `revise_content_piece.py`, `select_allowed_facts.py` NISU DIRANI.
- [ ] `python -m pytest tests/unit/application/posts/ tests/integration/application/posts/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/posts/test_content_similarity.py tests/unit/application/posts/test_generate_social_post.py tests/integration/application/posts/test_generate_social_post_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Jaccard implementacija je ispravna (uključi granični slučaj praznog
  teksta);
- provjera je STVARNO jednosmjerna — postojeće objave se ne diraju;
- `SIMILARITY_THRESHOLD = 0.6` je razuman prag — provjeriti sa par
  realnih BHS primjera (dvije stvarno slične marketinške rečenice, dvije
  stvarno različite) da li 0.6 daje intuitivno očekivan rezultat, ne samo
  da testovi prolaze;
- nema novog domain polja, nema novog port metoda.

# Rollback

MEDIUM risk — application-layer dodatak, ne dira domain/šemu/portove.
Fix na istoj branch bez proširenja scope-a. §29: Claude-only review, PASS
-> odmah merge.

# Coordination

Nezavisno od ACS-F1-020 BF-2 (Pi), ACS-F1-022 dopuna 2 (MiniMax), ACS-GUI-006
(čeka implementera) — disjoint fajlovi (ovaj task NE dira `claim_linter.py`
niti `bridge/`), može ići paralelno.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-025-content-similarity
Branch:   task/ACS-F1-025-content-similarity
Base:     main @ 2d5f368
```
