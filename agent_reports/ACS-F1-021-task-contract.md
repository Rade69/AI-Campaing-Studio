---
task_id: ACS-F1-021
phase: Faza-1 (post A11/A12, pre G10 analytics-ready)
title: "GenerateSocialPost: kreiraj Revision v1 za initial AI generaciju (revision_ids prazan po defaultu)"
risk: MEDIUM
coordinator: claude
implementer: crush
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-04
dependencies: []
allowed_paths:
  - src/ai_campaign_studio/application/posts/generate_social_post.py
  - tests/unit/application/posts/test_generate_social_post.py
  - tests/integration/application/posts/test_generate_social_post_integration.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/posts/revise_content_piece.py
  - src/ai_campaign_studio/application/posts/claim_linter.py
  - src/ai_campaign_studio/application/posts/derive_content_status.py
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/ports/
  - resources/migrations/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. `GenerateSocialPost.__init__` dobija
    novi obavezan constructor parametar (revision_repo) -- BREAKING CHANGE za
    postojeće pozivaoce; poznata su tačno 2 test fajla koja ga instanciraju
    (vidi allowed_paths), nema production wiring-a još (GUI bridge iz
    ACS-GUI-005 poziva samo CreateCampaign/GenerateCampaignPlan, ne
    GenerateSocialPost).
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 453d42a
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Nezavisan spoljni code review (druga Claude sesija) je pratio lanac
posljedica claim_linter bug-a (ACS-F1-020) dalje kroz kod i našao
DRUGI, nepovezan i arhitektonski značajniji nalaz. Koordinator je
nezavisno reprodukovao PRIJE pisanja ovog kontrakta:

```python
# domain/content/entities.py
revision_ids: tuple[RevisionId, ...] = ()  # default -- nikad postavljen
                                             # za initial AI generaciju
```

`GenerateSocialPost.execute()` (`application/posts/generate_social_post.py`,
linije 175-191) kreira `ContentPiece` i zove `content_repo.save_content_piece(...)`
BEZ ikad kreiranja/čuvanja `Revision` zapisa. `revision_ids` ostaje `()`.

`ReviseContentPiece.execute()` (linija 168-171):
```python
existing = self._revision_repo.list_entity_revisions("ContentPiece", str(content_piece_id))
next_version = len(existing) + 1
```
Za post koji nikad nije editovan, `existing` je prazan (`[]`), pa PRVA prava
izmjena dobija `version=1` — kao da je to prva verzija, iako je stvarna prva
verzija bila AI-jeva originalna generacija.

**Zašto je ovo arhitektonski, ne samo kozmetički problem**: `domain/content/revisions.py`
eksplicitno kaže: *"``Revision.id`` is the stable ``content_revision_id`` seam
required before G10 (Performance/Analytics) per the analytics-ready plan."*
CLAUDE.md-ova zaključana odluka: *"Faza 1 mora sačuvati stable
campaign/content/revision/target identitete... da Slice 1.5 ne zahtijeva
veliki refaktor."* Post koji nikad nije editovan — NAJČEŠĆI slučaj u praksi —
danas nema NIJEDAN `Revision` zapis, dakle nema `content_revision_id` da ga
budući export/analytics mehanizam uopšte poveže. Ovo NIJE hipotetički budući
problem: to je gap prema već-zaključanoj arhitektonskoj obavezi, otkriven
prije nego što je Slice 1.5 počeo (najbolje moguće vrijeme da se nađe).

Ovo NIJE poznat/prihvaćen rizik — propust, ne namjeran dizajn (nema komentara
u kodu koji objašnjava zašto initial generacija ne bi imala Revision).

# Objective

`GenerateSocialPost.execute()` mora kreirati i sačuvati `Revision(version=1,
origin=RevisionOrigin.AI, ...)` U ISTOJ transakciji gdje se `ContentPiece`
snima, i upisati taj `revision.id` u `content_piece.revision_ids`.
`ReviseContentPiece` se NE MIJENJA — njegova `next_version = len(existing) + 1`
logika postaje ispravna AUTOMATSKI čim initial revision postoji (prva prava
izmjena prirodno dobija `version=2`).

# Implementation steps

1. Dodaj `revision_repo: RevisionRepositoryPort` kao nov, obavezan
   constructor parametar na `GenerateSocialPost.__init__` (isti pattern kao
   `ReviseContentPiece` već koristi — vidi taj fajl za referencu, NE DIRATI
   ga, samo čitati kao primjer).
2. Nakon što se `content_piece`/`payload` izgrade (linija ~165-172), PRIJE
   `with self._unit_of_work:` bloka, kreiraj:
   ```python
   revision = Revision(
       id=RevisionId(new_id()),
       entity_type="ContentPiece",
       entity_id=str(content_piece.id),
       version=1,
       timestamp=now,
       origin=RevisionOrigin.AI,
       previous_value=json.dumps(None),
       new_value=json.dumps(asdict(payload)),
       provider=response.provider,
       model=response.model,
       prompt_version=_PROMPT_VERSION,
       instruction=None,
   )
   ```
   `previous_value=json.dumps(None)` (string `"null"`) je namjeran izbor —
   `Revision.previous_value` je `str` (NE `str | None`, provjeri
   `domain/content/revisions.py` prije koda, taj fajl je forbidden za
   izmjenu), a `resources/migrations/0002_campaign_content_visual.sql` ima
   `previous_value TEXT NOT NULL` — prazan string ili "null" su jedine
   opcije bez migracije; `json.dumps(None)` je dosljedno sa `new_value`
   koji je uvijek validan JSON string, pa svaki budući čitalac koji
   parsira `previous_value` kao JSON dobija `None`, ne parse grešku na
   praznom stringu. NE MIJENJATI `domain/content/revisions.py` da
   `previous_value` postane opcionalan — to je van `allowed_paths` i nije
   potrebno za ovaj fix.
3. Postavi `content_piece.revision_ids=(revision.id,)` (umjesto default
   `()`) kad gradiš `ContentPiece` (linija ~175-187) — jedan revision u
   tuple-u, ne prazan.
4. U `with self._unit_of_work:` bloku (linija 189-191), sačuvaj revision
   PRIJE content piece-a (isti redoslijed kao `ReviseContentPiece`:
   revision pa content piece), atomično sa istim commit-om:
   ```python
   with self._unit_of_work:
       self._revision_repo.save_revision(revision)
       self._content_repo.save_content_piece(content_piece)
       self._unit_of_work.commit()
   ```
5. Ažuriraj OBA postojeća test fajla
   (`tests/unit/application/posts/test_generate_social_post.py`,
   `tests/integration/application/posts/test_generate_social_post_integration.py`)
   da injektuju `revision_repo` (fake u unit testu, pravi
   `SqliteRevisionRepository` u integration testu — isti pattern kao
   `test_revise_content_piece*.py` već koristi, pogledaj taj fajl kao
   referencu, NE dirati ga).
6. Dodaj nove testove:
   - `ContentPiece.revision_ids` ima tačno 1 element nakon
     `GenerateSocialPost.execute()`.
   - Taj `Revision` ima `version=1`, `origin=RevisionOrigin.AI`,
     `previous_value` je validan JSON koji parsira u `None`.
   - **Integracioni regresioni test za version-brojanje kroz obje
     use-case-e**: pozovi `GenerateSocialPost.execute()` pa
     `ReviseContentPiece.execute()` na istom postu (real SQLite,
     integration test) — potvrdi da revizija iz `ReviseContentPiece`
     dobija `version=2`, NE `version=1`. Ovo je regresioni dokaz da je
     glavni bug (prva prava izmjena krivo numerisana kao v1) zaista
     zatvoren.

# Acceptance

- [ ] `GenerateSocialPost.__init__` prima `revision_repo:
      RevisionRepositoryPort`.
- [ ] Svaki `ContentPiece` koji izađe iz `GenerateSocialPost.execute()` ima
      `len(revision_ids) == 1`.
- [ ] Taj initial `Revision` ima `version=1`, `origin=RevisionOrigin.AI`.
- [ ] `Revision` i `ContentPiece` se snimaju u ISTOJ `unit_of_work`
      transakciji (atomično — ako jedan save padne, ništa se ne commit-uje).
- [ ] Regresioni test: `GenerateSocialPost` pa `ReviseContentPiece` na istom
      postu → prva prava izmjena dobija `version=2`.
- [ ] `domain/content/revisions.py`, `revise_content_piece.py`,
      `claim_linter.py`, `derive_content_status.py` NISU DIRANI (git diff
      dokaz).
- [ ] `python -m pytest tests/unit/application/posts/ tests/integration/application/posts/ -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/posts/test_generate_social_post.py tests/integration/application/posts/test_generate_social_post_integration.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- `previous_value=json.dumps(None)` je dosljedno primijenjeno, ne prazan
  string ili neki drugi ad-hoc sentinel;
- atomičnost (revision+content_piece u istom UoW bloku);
- regresioni test za version-brojanje kroz dva use-case-a stvarno dokazuje
  da je bug zatvoren, ne samo da novi kod "izgleda ispravno";
- `ReviseContentPiece`/`domain/content/revisions.py` zaista netaknuti;
- nema promjene u ponašanju `claim_linter`/`derive_content_status`
  (ovaj task se ne bavi tim, to je ACS-F1-020, odvojen task).

# Rollback

MEDIUM risk — application-layer promjena, ne dira domain/ports/infrastructure
šemu. Fix na istoj branch bez proširenja scope-a. §29: Claude-only review,
PASS -> odmah merge.

# Coordination

Nezavisno od ACS-F1-020 (Pi, claim_linter word-boundary — u toku) i bilo
kojeg budućeg GUI taska koji bi mogao pozvati `GenerateSocialPost` (nijedan
trenutno ne postoji — ACS-GUI-005 poziva samo CreateCampaign/
GenerateCampaignPlan). Sva tri mogu ići paralelno, nema preklapanja fajlova.

Poznato, namjerno OGRANIČENJE ovog taska: postojeći `ContentPiece` redovi u
bilo kojoj već postojećoj lokalnoj bazi (npr. iz ranijih live validacija)
NEĆE biti retroaktivno backfill-ovani sa initial Revision-om — to je
prihvatljivo jer nema produkcijskih korisnika još; backfill migracija je
budući task ako/kad zatreba prije G10.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-021-initial-revision
Branch:   task/ACS-F1-021-initial-revision
Base:     main @ 453d42a
```
