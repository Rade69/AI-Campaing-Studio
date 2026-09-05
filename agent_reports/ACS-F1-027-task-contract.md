---
task_id: ACS-F1-027
phase: Faza-1 (G10 — A/B evaluation harness, A16 nastavak)
title: "human_eval.py: blind A/B evaluacioni paket (§49)"
risk: MEDIUM
coordinator: claude
implementer: pi
reviewers: [claude]
status: "OPEN — contract written before code"
created_at: 2026-09-05
dependencies:
  - ACS-F1-026 (merged, main @ b000aa5) — EvaluationPost oblik, Control A/System B izlaz
allowed_paths:
  - src/ai_campaign_studio/application/evaluation/human_eval.py
  - tests/unit/application/evaluation/test_human_eval.py
forbidden_paths:
  - src/ai_campaign_studio/domain/
  - src/ai_campaign_studio/application/campaigns/
  - src/ai_campaign_studio/application/posts/
  - src/ai_campaign_studio/application/evaluation/evaluation_post.py
  - src/ai_campaign_studio/application/evaluation/run_control_a.py
  - src/ai_campaign_studio/application/evaluation/run_system_b.py
  - src/ai_campaign_studio/application/evaluation/deterministic_metrics.py
  - src/ai_campaign_studio/infrastructure/
  - src/ai_campaign_studio/ports/
gitnexus_required: true
adversarial_required: false
gitnexus:
  required: true
  note: >
    GitNexus MCP nedostupan u trenutku pisanja. Koordinator će pokrenuti
    detect-changes/impact prije merge-a. Nov modul, konzumira
    `EvaluationPost` (ACS-F1-026, nepromijenjen oblik) — nema izmjene
    postojećih potpisa.
  repository: "H:\\AI Campaing Studio"
  branch: main
  head: 3a5474c
  scope_fit: "PENDING — popuniti kad GitNexus MCP bude dostupan."
---

# Kontekst

Nastavak G10/A16 (Faza 1 v1.4 §49) — nakon `run_control_a`/`run_system_b`
(ACS-F1-026, merged), treba mehanizam koji SLIJEPO (bez da evaluator zna
koje je koje) pakuje oba izlaza za ljudsku ocjenu po fiksnoj rubrici.

**Obavezno pročitati prije koda**:

```text
AI_Campaign_Studio_Faza_1_v1_4_Agent_Workflow_Integrated.md §49
  (Human evaluation — tačan tekst, ne izmišljati novu rubriku)
src/ai_campaign_studio/application/evaluation/evaluation_post.py
  (VEĆ POSTOJI, ACS-F1-026 — EvaluationPost je ulaz ovog modula, ne
  mijenjaj taj fajl, samo ga uvezi)
```

# Objective

Čista, testabilna funkcija koja od `tuple[EvaluationPost, ...]` za
Control A i `tuple[EvaluationPost, ...]` za System B gradi:

1. **Slijep paket** — dvije "kampanje" nasumično označene "Campaign X" /
   "Campaign Y" (redoslijed nasumičan po pozivu, NE uvijek A=X/B=Y — inače
   evaluator vremenom nauči obrazac ako radi više evaluacija), sa
   sadržajem postova (headline/caption/hook/body/cta/hashtags) ALI BEZ
   ijedne oznake koje je A koje je B.
2. **Rubrika** (§49, TAČAN tekst, ne parafraziraj): Brand fit (1-5),
   Language naturalness (1-5), Campaign coherence (1-5), Post diversity
   (1-5), Usefulness (1-5), Visual consistency (1-5), Comments (slobodan
   tekst) — PO KAMPANJI (X i Y svaka dobija svoju ocjenu na svih 6
   kriterijuma), ne po pojedinačnom postu.
3. **Reveal ključ** — ODVOJENA struktura (ne dio slijepog paketa) koja
   mapira `"Campaign X"`/`"Campaign Y"` nazad na `"control_a"`/`"system_b"`
   — evaluator ovo ne smije vidjeti prije ocjenjivanja.

Plus tanka funkcija za pisanje na disk (JSON sadržaj za čitanje + CSV
prazan scoring template za popunjavanje) — §49 traži "JSON/CSV obrazac".

# Implementation steps

## 1. Dataclass-ovi

```python
@dataclass(frozen=True)
class HumanEvalPost:
    headline: str
    caption: str
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...]

@dataclass(frozen=True)
class BlindCampaign:
    label: str  # "Campaign X" ili "Campaign Y"
    posts: tuple[HumanEvalPost, ...]

RUBRIC_CRITERIA: tuple[str, ...] = (
    "Brand fit",
    "Language naturalness",
    "Campaign coherence",
    "Post diversity",
    "Usefulness",
    "Visual consistency",
)

@dataclass(frozen=True)
class HumanEvalPackage:
    campaigns: tuple[BlindCampaign, BlindCampaign]
    rubric_criteria: tuple[str, ...] = RUBRIC_CRITERIA
```

`reveal` (mapping label → "control_a"/"system_b") vraća se ODVOJENO iz
`build_human_eval_package` (npr. `tuple[HumanEvalPackage, dict[str, str]]`
povratna vrijednost) — NIKAD kao polje na `HumanEvalPackage` samom, da se
ne desi slučajno serijalizovanje reveal-a u isti fajl kao slijepi paket.

## 2. `build_human_eval_package`

```python
def build_human_eval_package(
    control_a_posts: tuple[EvaluationPost, ...],
    system_b_posts: tuple[EvaluationPost, ...],
    rng: random.Random | None = None,
) -> tuple[HumanEvalPackage, dict[str, str]]:
```

- `rng` je injektovan seam za testove (deterministički); `None` default
  koristi pravi `random.Random()` u produkciji.
- Nasumično odluči da li je "Campaign X" = control_a ili system_b
  (`rng.random() < 0.5` ili `rng.choice(...)` — tvoj izbor, ali MORA
  koristiti `rng`, ne globalni `random` modul direktno, da test može
  kontrolisati ishod).
- Mapiraj `EvaluationPost` → `HumanEvalPost` (samo polja koja se
  prikazuju evaluatoru — headline/caption/hook/body/cta/hashtags; NE
  uključuj `role`/`topic`/`claims`/`platform_code` u slijepi prikaz, to
  bi moglo odati koje je koje, npr. System B ima role a Control A nema).
- Vrati `(package, reveal_dict)`.

## 3. Pisanje na disk

```python
def write_human_eval_files(
    package: HumanEvalPackage,
    reveal: dict[str, str],
    output_dir: Path,
) -> None:
```

- `output_dir/human_eval_content.json` — čitljiv sadržaj oba slijepa
  paketa (za evaluatora da čita prije ocjenjivanja).
- `output_dir/human_eval_scoring_template.csv` — prazan template, jedan
  red po kampanji (`Campaign X`, `Campaign Y`), kolone = 6 kriterijuma +
  Comments, VRIJEDNOSTI PRAZNE (evaluator popunjava ručno).
- `output_dir/human_eval_reveal.json` — SAMO reveal mapping, JASNO
  imenovan (npr. i sam sadržaj fajla ima napomenu
  `"WARNING: do not open before scoring"` kao string vrijednost ili
  komentar u strukturi) — odvojen fajl, ne miješati sa gornja dva.
- Kreiraj `output_dir` ako ne postoji (`mkdir(parents=True, exist_ok=True)`).

# Acceptance

- [ ] `build_human_eval_package` je čista funkcija (nema I/O) — testabilna
      bez diska.
- [ ] Sa fiksnim `rng` (seed), ishod (koje je X koje je Y) je
      deterministički i testom dokazan za OBA moguća ishoda (bar jedan
      seed daje X=control_a, bar jedan drugi seed daje X=system_b).
- [ ] Slijep paket NE SADRŽI `role`/`topic`/`claims`/`platform_code`
      niti bilo šta drugo što bi moglo odati identitet A ili B.
- [ ] Rubrika ima TAČNO 6 kriterijuma iz §49, tačnim redoslijedom i
      tačnim tekstom (ne parafraziran).
- [ ] `reveal` dict je ODVOJEN povratna vrijednost, nikad ugrađen u
      `HumanEvalPackage` strukturu.
- [ ] `write_human_eval_files` piše TRI odvojena fajla (content JSON,
      scoring CSV, reveal JSON) u zadati direktorij.
- [ ] CSV scoring template ima prazne vrijednosti za popunjavanje
      (ne pred-popunjene, ne placeholder brojeve).
- [ ] `evaluation_post.py`/`run_control_a.py`/`run_system_b.py`/
      `deterministic_metrics.py` NISU DIRANI (git diff dokaz).
- [ ] `python -m pytest tests/unit/application/evaluation/test_human_eval.py -v`
      prolazi.
- [ ] `python -m pytest tests -q` (cijeli suite) prolazi, 0 regresija.
- [ ] `python -m ruff check .` i `python -m mypy src` prolaze.
- [ ] Nema izmjena van `allowed_paths`.

# Verification

```bash
python -c "import ai_campaign_studio"
python -m pytest tests/unit/application/evaluation/test_human_eval.py -v
python -m pytest tests -q
python -m ruff check .
python -m mypy src
```

# Review focus — Claude

- Slijep paket stvarno ne curi identitet (role/topic/claims odsutni);
- rubrika tačno prati §49 tekst;
- `reveal` nikad nije dio serijalizovanog slijepog paketa;
- `rng` seam stvarno kontroliše nasumičnost (ne globalni `random` poziv
  koji test ne može kontrolisati).

# Rollback

MEDIUM risk — nov, izolovan modul, čista funkcija + tanak I/O. Fix na
istoj branch bez proširenja scope-a. §29: Claude-only review, PASS ->
odmah merge.

# Coordination

Nezavisno od bilo kojeg budućeg rada — ovo je posljednji poznat komad
A16 sekvence. Nakon merge-a, koordinator će ručno (u scratchpad-u)
pokrenuti pravi `run_control_a`/`run_system_b`/`build_human_eval_package`
protiv BrightSmile fixture-a sa pravim provider ključem, kao live
verifikaciju cijelog A16 lanca — to NIJE dio ovog task-contracta, radi
se nakon merge-a kao koordinatorova provjera.

```text
Worktree: ../ai-campaign-studio-worktrees/ACS-F1-027-human-eval-package
Branch:   task/ACS-F1-027-human-eval-package
Base:     main @ 3a5474c
```
