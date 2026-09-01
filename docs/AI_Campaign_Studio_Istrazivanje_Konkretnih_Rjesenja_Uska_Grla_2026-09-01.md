# AI Campaign Studio — istraživanje konkretnih rješenja za moguća uska grla

**Datum:** 2026-09-01  
**Cilj:** pronaći postojeća, konkretna rješenja na GitHubu i u savremenim agentic-development platformama koja mogu smanjiti tehnički i procesni rizik AI Campaign Studija.

## 1. Sažetak

Najvažniji rezultat istraživanja nije da treba ubaciti veliki framework. Naprotiv: za većinu ključnih uskih grla postoje manja, zrela rješenja ili provjereni obrasci koje možemo ugraditi bez promjene Clean/Hexagonal arhitekture.

Najveću neposrednu vrijednost imaju:

1. **Pydantic Evals** za G10/A-B evaluacioni harness i verzionisane eval datasete.
2. **Trafilatura + extruct** za Website/Brand Ingestion.
3. **Docling** za PDF/DOCX/PPTX/XLSX i drugi document ingestion.
4. **Playwright direktno** za deterministički HTML/CSS → PNG renderer i kasniji JS-heavy website fallback.
5. **Replit Decision-Time Guidance + OpenHands/GitHub Agent Skills obrazac** za smanjenje prenatrpanog agent konteksta i review petlji.
6. **RapidFuzz** samo za uske determinističke/advisory zadatke: redundancy i pomoć pri ručnom analytics matchingu.
7. **simonw/llm plugin model** kao dobra referenca za naš provider registry, ali bez preuzimanja cijelog frameworka.

Ne preporučujem kao core dependency: LiteLLM, Firecrawl, Langfuse, Pydantic AI agent runtime, SQLAlchemy-Continuum i html2image. Razlozi su navedeni niže.

## 2. Metodologija

Pregledani su javni GitHub repozitoriji, README/licence, službena dokumentacija i tehnički izvori iz Replita, Cursora, OpenHands-a, SWE-agent-a i Aider-a.

Klasifikacija:

- **ADOPT** — direktno koristiti ili napraviti spike za ugradnju.
- **ADAPT** — koristiti dio rješenja iza našeg porta/adapera.
- **INSPIRE** — preuzeti princip, ne dependency.
- **REJECT** — ne uvoditi u sadašnju arhitekturu.

Postojanje biblioteke ili industrijskog obrasca nije dokaz da će naš Campaign Engine biti kvalitetan. **R1 ostaje HIGH do G10 PASS.**

---

# R1 — Hoće li Campaign Engine biti stvarno bolji od dobrog plain LLM prompta?

## F1. Pydantic Evals

**Status:** ADOPT za development/evaluation sloj, ne runtime core.

Linkovi:

- GitHub: https://github.com/pydantic/pydantic-ai
- Docs: https://ai.pydantic.dev/evals/
- Licenca: https://github.com/pydantic/pydantic-ai/blob/main/LICENSE

Daje `Dataset`, `Case`, expected output, metadata, code-based i custom evaluatore, LLM Judge, eksperimente i izvještaje.

To se dobro poklapa sa našim:

```text
Brand/Campaign Fixture dataset
        ↓
Control A
System B
        ↓
determinističke metrike
human/LLM advisory evaluacija
        ↓
G10 report
```

Predložena struktura:

```text
tests/evals/
    campaign_engine/
        dataset.yaml
        evaluators.py
        control_a.py
        system_b.py
```

Case metadata treba čuvati najmanje `fixture_version`, `brand_fixture_id`, `campaign_goal`, `language`, `target_platforms` i tags/difficulty.

Hard evaluatori: unsupported claim, missing fact_id, schema failure, platform/format violation, role/manifest integrity i deterministička redundancy.

Advisory: kreativnost, CTA quality, brand alignment, persuasion i tone.

**Preporuka:** dodati Pydantic Evals kao kandidat za G10 implementation spike. Ne uvoditi ga u runtime dependency prije tog taska.

## F2. Promptfoo

**Status:** ADAPT kao opciono development oruđe.

Linkovi:

- GitHub: https://github.com/promptfoo/promptfoo
- Docs: https://www.promptfoo.dev/docs/
- Red team: https://www.promptfoo.dev/docs/red-team/

Licenca: MIT.

Koristan je za prompt/model matrice, CI eval, provider poređenja i red teaming. Posebno:

```text
Prompt v12 + GPT
vs
Prompt v13 + Claude
vs
Prompt v13 + Gemini
```

Naš G10 ipak ostaje source of truth. Promptfoo je dodatni dev alat, ne core.

## F3. DeepEval

**Status:** ADAPT kasnije.

- GitHub: https://github.com/confident-ai/deepeval
- Docs: https://deepeval.com/docs/getting-started
- Apache 2.0: https://github.com/confident-ai/deepeval/blob/master/LICENSE.md

Python-native eval framework sa G-Eval, faithfulness, contextual precision/recall, hallucination i custom metrics. Vjerovatno korisniji kasnije za Website/Brand retrieval nego za početni G10.

## F4. Ragas

**Status:** INSPIRE / ADAPT tek kada retrieval postane stvaran problem.

- GitHub: https://github.com/vibrantlabsai/ragas
- Docs: https://docs.ragas.io/

Koristan za faithfulness, context precision/recall, retrieval quality i generisanje testnog dataseta. Ne uvoditi prije Website Ingestion + retrieval faze.

## F5. DSPy

**Status:** INSPIRE sada, EXPERIMENT kasnije.

- GitHub: https://github.com/stanfordnlp/dspy
- Docs: https://dspy.ai/

DSPy može optimizovati promptove/demonstracije prema metrici i datasetu. Vrijedi tek nakon:

```text
G10 dataset
→ stabilne metrike
→ human calibration
→ DSPy eksperiment
```

Ne smije postati core arhitektura.

---

# R2 — Brand Intelligence, grounding i Website/Document Ingestion

## F6. Trafilatura

**Status:** ADOPT.

- GitHub: https://github.com/adbar/trafilatura
- Docs: https://trafilatura.readthedocs.io/
- Apache 2.0 za aktuelne verzije.

Daje main-content extraction, boilerplate removal, metadata, sitemap/feed discovery, URL filtering/dedup i Markdown/JSON output.

Koristiti prvenstveno kao extraction komponentu:

```text
ACS Fetch/Budget Layer
        ↓
raw HTML
        ↓
Trafilatura
        ↓
clean main text + metadata
```

Tako zadržavamo naša pravila za max pages, depth, same-domain, timeout, size limit i provenance.

## F7. extruct

**Status:** ADOPT.

- GitHub: https://github.com/scrapinghub/extruct
- Licenca: https://github.com/scrapinghub/extruct/blob/master/LICENSE

Podržava JSON-LD, Schema.org Microdata, Open Graph, Microformats, RDFa i Dublin Core.

Za web-shop ili poslovni sajt ovo može deterministički izvući `Organization`, `Product`, `Offer`, price/currency, brand, logo, sameAs i description kada su prisutni.

Bolji pipeline:

```text
HTML
 ├── extruct → structured candidates
 └── Trafilatura → clean text candidates
                 ↓
         FactCandidate normalization
                 ↓
            Human approval
```

Ovo bih stvarno ugradio u Website Ingestion plan.

## F8. Docling

**Status:** ADOPT uz packaging/performance spike.

- GitHub: https://github.com/docling-project/docling
- Docs: https://docling-project.github.io/docling/
- MIT.

Podržava lokalno PDF, DOCX, PPTX, XLSX, HTML, slike, email, OCR i napredno razumijevanje PDF layouta/tabela/redoslijeda čitanja.

Predložena granica:

```text
SourceDocumentPort
        ↓
Docling adapter
        ↓
NormalizedDocument
        ↓
chunks / FactCandidates
```

Prije usvajanja napraviti spike: Windows packaging, 5 realnih PDF-ova, 2 DOCX, 1 XLSX, vrijeme, RAM, kvalitet tabela i veličina distributivnog paketa.

## F9. Crawl4AI

**Status:** INSPIRE / selektivni ADAPT, ne wholesale dependency.

- GitHub: https://github.com/unclecode/crawl4ai
- Apache 2.0: https://github.com/unclecode/crawl4ai/blob/main/LICENSE

Daje async crawl, browser pool, deep crawl, cache, resume state, URL discovery i hooks.

Recentni changelog navodi ozbiljne security popravke (SSRF, arbitrary file write, DoS, XSS). To pokazuje koliki attack surface donosi kompletan crawler/server.

**Preporuka:** uzeti crawl-budget/resume/adaptive-dispatcher ideje, ali početi sa manjim ACS fetch layerom + Trafilatura + Playwright fallback.

## F10. Firecrawl

**Status:** REJECT kao core runtime dependency; INSPIRE za API granice.

- GitHub: https://github.com/firecrawl/firecrawl
- Docs: https://docs.firecrawl.dev/
- Licenca: AGPL-3.0.

Odličan search/scrape/crawl/map sistem, ali hosted varijanta uvodi servisnu zavisnost, self-hosted je pretežak za desktop-first MVP, a AGPL traži pažljivu licencnu procjenu.


---

# R3 — Content Quality Gate i redundancy

## F11. RapidFuzz

**Status:** ADOPT usko.

- GitHub: https://github.com/rapidfuzz/RapidFuzz
- Docs: https://rapidfuzz.github.io/RapidFuzz/
- MIT.

Može dati jeftin deterministički signal za sličnost headline/CTA/caption tekstova kroz Levenshtein, token sort/set, ratio i druge distance.

Ne treba ga koristiti kao semantičkog sudiju kreativnosti.

Druga korisna primjena je analytics import: kada nema `external_content_id` ni `analytics_match_key`, korisniku se mogu ponuditi kandidati na osnovu platforme, datuma i fuzzy sličnosti naslova/captiona.

Output ostaje:

```text
SUGGESTED_MATCH
→ human confirms
```

Nikad authoritative auto-match samo na osnovu fuzzy score-a.

## F12. Pydantic Evals kao trajni Quality Regression sloj

Isti dataset model iz G10 može postati regression baza:

```text
potvrđen failure iz realnog korištenja
↓
novi Case
↓
sljedeći prompt/model update
↓
regression experiment
```

Primjeri:

- unsupported price claim;
- pogrešan CampaignItem role;
- platform constraint violation;
- ponavljanje CTA-a;
- nepotvrđena činjenica;
- manifest/revision identity problem.

Ovo je korisnije od jednog “AI quality score 0–100”.

---

# R4 — Revision / provenance

## F13. SQLAlchemy-Continuum

**Status:** REJECT za `ContentRevision`.

- GitHub: https://github.com/sqlalchemy-continuum/sqlalchemy-continuum

Može automatski verzionisati ORM insert/update/delete, ali naš `ContentRevision` ima domensku semantiku:

```text
revision_id
content_piece_id
revision_no
provider
model
prompt_version
approved_fact_ids
old/new content
created_at
revision_reason
```

Generic ORM audit ne zna šta znači početna AI generacija, natural-language revision ili approved revision.

**Odluka:** zadržati eksplicitni model:

```text
prva generacija = Revision v1
svaka izmjena = nova immutable Revision
```

---

# R5 — Analytics identity i import/matching

## F14. Ovdje nam ne treba veliki framework

Najvažniji problem nije CSV parser nego identitet:

```text
CampaignItem
→ ContentPiece
→ ContentRevision
→ DistributionInstance
→ PerformanceSnapshot
```

Za prvi import je dovoljno:

- Python `csv`;
- `openpyxl` za Excel;
- Pydantic validation;
- RapidFuzz samo za advisory candidate matching.

Matching ostaje:

```text
1. external_content_id
2. analytics_match_key
3. stable IDs
4. manual confirmation
5. fuzzy suggestion samo kao pomoć čovjeku
```

Ne koristiti LLM semantic matching kao authoritative mehanizam.

`analytics_match_key` treba generisati jednom, trajno sačuvati, staviti u manifest, ne preračunavati retroaktivno i vezati za `schema_version` / algorithm version.

---

# R6 — LLM provider abstraction

## F15. simonw/llm — dobra referenca za plugin-based provider dizajn

**Status:** INSPIRE / moguće selektivni ADAPT.

- GitHub: https://github.com/simonw/llm
- Docs: https://llm.datasette.io/
- Model plugin tutorial: https://llm.datasette.io/en/stable/plugins/tutorial-model-plugin.html
- Apache 2.0.

Njihov princip:

```text
register_models(...)
        ↓
Model implementation
        ↓
stable model_id
        ↓
plugin entry point
```

Imaju odvojeno model registration, aliases, async model, key-aware model, schema capability, tools i embeddings.

Ne treba uzeti njihov CLI/runtime, nego oblik ugovora. To dodatno potvrđuje našu odluku:

```text
TextGenerationPort
→ ProviderRegistry
→ explicit adapters
```

## F16. LiteLLM

**Status:** REJECT kao core dependency sada; INSPIRE / optional backend kasnije.

- GitHub: https://github.com/BerriAI/litellm
- Docs: https://docs.litellm.ai/
- core uglavnom MIT; enterprise dio ima posebnu licencu.

Prednost: jedinstven API za 100+ providera.

Problem za ACS: veliki dependency i provider surface za aplikaciju koja u MVP-u cilja približno 5–6 providera.

Bolji početak:

```text
OpenAIAdapter
AnthropicAdapter
GeminiAdapter
DeepSeekAdapter
OpenRouterAdapter
OpenAICompatibleAdapter
```

Ako tržište kasnije stvarno traži desetine providera, LiteLLM može postati **jedan dodatni adapter**, ne temelj arhitekture.

## F17. Instructor

**Status:** INSPIRE / SPIKE samo ako structured-output retry postane bolan.

- GitHub: https://github.com/567-labs/instructor
- Docs: https://python.useinstructor.com/
- MIT.

Dobar je za Pydantic response model, validation, retry i structured output preko više providera.

Ne uvoditi automatski jer donosi sopstveni provider/SDK sloj. Naši adapteri prvo treba da probaju native structured output + Pydantic validation.

Ako retry/repair logika postane velika i duplirana, tada napraviti Instructor spike iza `TextGenerationPort`.

---

# R7 — Renderer / visual output

## F18. Playwright direktno

**Status:** ADOPT kroz renderer spike.

Linkovi:

- Python docs: https://playwright.dev/python/
- Screenshots: https://playwright.dev/python/docs/screenshots
- Browser context: https://playwright.dev/python/docs/api/class-browsercontext
- PyInstaller: https://playwright.dev/python/docs/library

Playwright daje fixed viewport, PNG buffer, izolovan non-persistent browser context, offline mode, disable animations, screenshot-only CSS i bundling browsera uz PyInstaller.

Predloženi renderer:

```text
LayoutSpec JSON
      ↓
validator
      ↓
trusted local Jinja2/HTML/CSS template
      ↓
Playwright Chromium
- fixed viewport
- offline=True
- animations disabled
- no external resources
- await document.fonts.ready
      ↓
PNG bytes
      ↓
artifact + manifest
```

Isti Playwright runtime kasnije može služiti i kao JS-heavy Website Ingestion fallback, ali adapteri ostaju odvojeni:

```text
CreativeRendererAdapter
≠
WebsiteBrowserAdapter
```

Renderer testovi:

- golden/reference screenshots;
- overflow;
- 1080×1350;
- 1080×1080;
- kasnije 1080×1920;
- kontrolisan browser/font/OS environment.

Playwright upozorava da pixel output može varirati između okruženja, pa vizuelne regression testove treba izvršavati u standardizovanom CI/runtime okruženju.

## F19. Satori

**Status:** SPIKE samo kao rezervna opcija.

- GitHub: https://github.com/vercel/satori
- Licenca: MPL-2.0.

Namjenski radi HTML/CSS-ish layout → SVG za social/Open Graph cards. Ima Flexbox/Yoga i dobar font/layout control.

Mane za ACS: Node runtime, CSS subset i dodatni SVG→PNG korak.

**Playwright je bolji prvi izbor za Python desktop aplikaciju.**

## F20. html2image

**Status:** REJECT.

- GitHub: https://github.com/vgalin/html2image

To je wrapper oko headless Chrome/Chromium/Edge. I dalje zahtijeva browser, a nudi manje kontrole od direktnog Playwrighta.

Nema smisla uvoditi dodatni sloj:

```text
ACS → html2image → browser
```

ako možemo:

```text
ACS → Playwright → browser
```

---

# R8 — Desktop/local-first i secret storage

## F21. keyring

**Status:** KEEP / ADOPT već planirano.

- GitHub: https://github.com/jaraco/keyring
- Docs: https://keyring.readthedocs.io/

Podržava Windows Credential Locker, macOS Keychain i Linux Secret Service/KWallet.

Ne treba praviti vlastitu enkripciju API ključeva u SQLite-u.

P0 treba testirati:

- Windows packaging;
- backend-unavailable scenario;
- set/get/delete;
- redaction;
- health-check bez curenja secreta.


---

# R9 — Agentic development workflow

Ovo istraživanje je posebno relevantno jer je naš proces već pokazao dvije realne slabosti: previše konteksta i potencijalno previše review/fix rundi.

## F22. Replit Agent 4 — izolovani taskovi + explicit apply

**Status:** ADOPT PATTERN.

Linkovi:

- Task system: https://docs.replit.com/core-concepts/agent/task-system
- Agent 4 changes: https://replit.com/blog/whats-changed-agent3-to-agent4
- Agent 4: https://replit.com/blog/introducing-agent-4-built-for-creativity

Replitov obrazac:

```text
Task
→ isolated copy
→ execution
→ work log + tests + preview
→ Ready
→ human review
→ Apply to main
```

Taskovi mogu ići paralelno, a main ostaje netaknut dok čovjek ne odobri.

Naš sistem je već vrlo blizu:

```text
Task Contract
→ worktree
→ Pi/Crush
→ execution evidence
→ Codex/Claude review
→ Human Owner
→ merge
```

Najkorisnija dopuna je automatski **parallel preflight**:

```text
Task A allowed_paths
Task B allowed_paths
+
planned/touched paths
+
dependency relation
+
base SHA / branch staleness
        ↓
SAFE_PARALLEL
CONFLICT
SEQUENTIAL_REQUIRED
```

To je korisnije od samog `claim/release` locka.

## F23. Replit Decision-Time Guidance

**Status:** ADOPT PATTERN, visoki prioritet.

- https://replit.com/blog/decision-time-guidance

Replit je utvrdio da gomilanje statičkih pravila može smanjiti pouzdanost. Umjesto jednog ogromnog prompta koriste stabilan core plus kratke situacione micro-instructions samo kada su relevantne.

Posebno korisni obrasci:

- signal da greška postoji, a agent sam povlači relevantan log;
- kod ponovljenih neuspjeha/doom-loopa konsultuje se drugi agent;
- drugi model dobija fresh context, bez istorije propalih pokušaja;
- guidance je kratka i nestaje kada više nije potrebna.

Naš read-set:

```text
AGENTS.md
CLAUDE.md
workflow
CURRENT_STATE
PROJECT_MAP
Task Contract
TASK_ROUTING
GitNexus
veliki plan
source
tests
```

je disciplinovan, ali može biti preskup za pažnju modela.

Bolji model:

```text
ALWAYS:
- AGENTS thin router
- current Task Contract
- relevant CURRENT_STATE

ON DEMAND / BY ROUTING:
- migration guide
- provider rules
- security guide
- localization guide
- renderer guide
- analytics guide
- GitNexus special cases
```

### Doom-loop pravilo

Ako isti blocking finding preživi dvije stvarne fix runde:

```text
STOP
→ sažmi samo dokaz + trenutni diff + acceptance
→ fresh-context consult drugog modela/reviewera
→ napravi novu hipotezu
→ tek onda nova fix runda
```

Ovo direktno adresira ono što smo vidjeli na P0-002.

## F24. OpenHands / GitHub Agent Skills — progressive disclosure

**Status:** ADOPT PATTERN.

Linkovi:

- OpenHands extensions: https://github.com/OpenHands/extensions
- OpenHands docs: https://docs.openhands.dev/
- GitHub Agent Skills: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills
- Agent Skills standard: https://agentskills.io/

OpenHands i GitHub koriste kratka always-on pravila + katalog skills + `SKILL.md` koji se učitava samo kada je relevantan.

To je formalizovana verzija onoga što smo pokušali sa `TASK_ROUTING.md`.

Ne graditi novi skill framework odmah. Organizovati `.agent/` tako da može preći na progressive-disclosure model:

```text
.agent/guides/
  gitnexus/
  migrations/
  provider-adapter/
  localization/
  renderer/
  performance/
```

Svaki guide treba da ima kratak summary, kada se čita, checklistu, poznate failure modes i reference po potrebi.

## F25. Cursor Worktrees / Cloud Agents / Agent Review

**Status:** ADOPT PATTERN / potvrda.

Linkovi:

- Worktrees: https://prod.cursor.com/docs/configuration/worktrees
- Background agents: https://prod.cursor.com/help/ai-features/background-agents
- Agent Review: https://prod.cursor.com/docs/agent/agent-review

Cursor takođe koristi izolovane worktreeove/VM-ove po tasku, branch, testove i review.

Posebno korisna ideja je **Quick vs Deep Review**:

```text
LOW
→ quick independent review

MEDIUM
→ normal review + acceptance evidence

HIGH/shared/security/migration
→ deep adversarial Codex + Claude
```

To je već djelimično u našem planu, ali ga treba poštovati u praksi da P0-002 ne postane default obrazac za svaki task.

## F26. SWE-agent — Agent-Computer Interface i trajectory evidence

**Status:** ADOPT PATTERN.

Linkovi:

- GitHub: https://github.com/SWE-agent/SWE-agent
- ACI: https://github.com/SWE-agent/SWE-agent/blob/main/docs/background/aci.md
- Trajectory inspector: https://github.com/SWE-agent/SWE-agent/blob/main/docs/usage/inspector.md

Njihovi praktični nalazi uključuju lint na edit, male ciljane prikaze fajla umjesto ogromnog dumpa, sažet search output, sandbox execution i čuvanje kompletnog runa kao trajectory.

Za ACS ne treba čuvati svaki token razgovora, ali svaki task može dobiti kompaktan machine-readable artifact:

```json
{
  "task_id": "...",
  "base_sha": "...",
  "head_sha": "...",
  "files_changed": [],
  "commands_run": [],
  "tests": {},
  "known_failures": [],
  "review_round": 1
}
```

Markdown report ostaje za čovjeka, JSON za alate/koordinatora.

## F27. Aider Repo Map — mogući fallback za GitNexus context problem

**Status:** INSPIRE / SPIKE samo ako GitNexus worktree problem ostane.

Linkovi:

- GitHub: https://github.com/Aider-AI/aider
- Repo map: https://aider.chat/docs/repomap.html
- Tehnički opis: https://aider.chat/2023/10/22/repomap.html

Aider koristi tree-sitter da izvlači simbole, gradi dependency graph, rangira važne dijelove i uklapa mapu u token budget.

To je relevantno zbog trenutnog GitNexus worktree-binding problema.

Ne uvoditi Aider samo zbog ove funkcije. Ako GitNexus problem ostane, napraviti read-only spike:

```text
Aider repo-map
vs
naš PROJECT_MAP
vs
GitNexus main-checkout context
```

## F28. Replit evaluation loop

**Status:** ADOPT PATTERN.

- https://replit.com/blog/evaluating-and-improving-agent-at-scale

Replit kombinuje:

```text
offline benchmark
+
A/B test
+
production traces
+
human judgement
```

i naglašava da nijedan sloj sam nije dovoljan.

Njihov ViBench koristi natural-language PRD + behavioral test plans + running app + evaluator. Kasnije potvrđeni failure traces postaju novi regression testovi.

Naš ekvivalent:

```text
G10 fixture dataset
+
Control A / System B
+
human evaluation
+
kasnije real user edits/rejections
+
performance signals
```

Najvažnija promjena: G10 ne smije biti jednokratni gate koji poslije zaboravimo. Treba postati početak **Campaign Quality Regression Dataset-a**.

---

# 3. Preporučena selekcija

## ADOPT

| Rješenje | Namjena | Kada |
|---|---|---|
| Pydantic Evals | G10 + regression dataset | Faza 1 / G10 spike |
| Trafilatura | HTML main-text extraction | Website Ingestion |
| extruct | JSON-LD/OpenGraph/Microdata | Website Ingestion |
| Docling | PDF/DOCX/XLSX/PPTX normalization | Document Ingestion spike |
| Playwright | deterministic renderer + JS fallback | Renderer spike / Website Ingestion |
| RapidFuzz | redundancy + advisory analytics matching | Content Quality / Performance |
| keyring | secrets | P0, već planirano |
| progressive-disclosure task guides | agent context | agent workflow |
| fresh-context doom-loop escalation | review/fix reliability | agent workflow |
| task isolation + explicit human merge | parallel coding | već koristimo |

## ADAPT / INSPIRE

| Rješenje | Zašto |
|---|---|
| Promptfoo | posebne prompt/model matrice i red-team |
| DeepEval | kasniji RAG/content eval |
| Ragas | retrieval evaluation poslije Website Ingestion |
| DSPy | offline prompt optimization tek kad imamo dobar dataset |
| simonw/llm | provider/plugin architecture reference |
| Instructor | structured-output retry/validation ako adapteri postanu duplirani |
| Crawl4AI | crawl/resume/budget ideje, ne cijeli dependency |
| Satori | rezervni renderer spike |
| Aider Repo Map | fallback inspiracija ako GitNexus worktree problem ostane |
| SWE-agent trajectories/ACI | compact evidence + task tools |
| Cursor Quick/Deep Review | proporcionalni review nivo |

## REJECT za sada

| Rješenje | Razlog |
|---|---|
| LiteLLM kao core | prevelik dependency/provider surface za 5–6 providera |
| Firecrawl kao core | hosted/server težina + AGPL |
| Langfuse kao app runtime | pretežak observability/server stack za desktop-first |
| Pydantic AI agent runtime | naš pipeline treba ostati deterministički |
| SQLAlchemy-Continuum za ContentRevision | generic audit ne odgovara domenskoj reviziji |
| html2image | manje kontrole od direktnog Playwrighta |

---

# 4. Predložene izmjene plana nakon istraživanja

## D1 — G10 dataset postaje trajan

Ne:

```text
G10 PASS
→ arhiviraj test
```

nego:

```text
G10 Dataset v1
→ PASS
→ real usage failures
→ Dataset v2
→ prompt/model change
→ regression experiment
→ Dataset v3...
```

Pydantic Evals je trenutno najbolji kandidat za tehničku osnovu.

## D2 — Website Ingestion dobija konkretan stack

```text
URL
↓
ACS validation / robots / sitemap / budget
↓
HTTP fetch
↓
ako HTML nije dovoljno renderovan:
    Playwright fallback
↓
raw SourceSnapshot
↓
├─ extruct → structured metadata
└─ Trafilatura → clean main content
↓
normalize / dedupe
↓
FactCandidates
↓
Human review
↓
Approved Facts / Brand Snapshot
```

## D3 — Document Ingestion ne praviti od nule

```text
PDF/DOCX/PPTX/XLSX/image
↓
Docling
↓
NormalizedDocument
↓
FactCandidates
```

Prije usvajanja obavezan packaging/performance spike.

## D4 — Renderer favorizuje Playwright

```text
LayoutSpec
→ trusted HTML/CSS
→ Playwright offline isolated context
→ fixed viewport/fonts
→ PNG
```

Ako Playwright packaging/startup/memory ne prođe acceptance, tek onda Satori ili drugo rješenje.

## D5 — Content Quality bez AI hard-gatea za ukus

```text
HARD:
facts/schema/platform/layout/deterministic redundancy

SOFT:
brand/CTA/audience/creativity/tone AI advice

FINAL:
human approval
```

## D6 — Provider registry ostaje naš

Nema LiteLLM core-a. Referenca ostaje plugin/capability separacija iz `simonw/llm`.

## D7 — Agent workflow smanjuje front-loaded kontekst

Zadržati dokumente, ali detaljna pravila prebaciti u progressive-disclosure guide/skill model.

```text
Core rules
+
Task Contract
+
samo relevantni guides
```

## D8 — Doom-loop escalation

Ako isti blocker nije riješen nakon dvije korektne fix runde:

```text
STOP istog loopa
→ fresh-context drugi model
→ samo evidence + current diff + acceptance
→ nova hipoteza
```

## D9 — Parallel task preflight

Prije dva paralelna taska provjeriti:

```text
dependencies
allowed_paths
forbidden_paths
planned files
base SHA
branch staleness
```

Output: `SAFE_PARALLEL`, `SEQUENTIAL_REQUIRED` ili `CONFLICT_REQUIRES_DECISION`.

## D10 — Standardizovati execution evidence

Uz human-readable report imati:

```text
agent_reports/<task>-evidence.json
```

sa SHA, changed files, tests, commands, review round i blockerima.

---

# 5. Šta ne bih mijenjao

Istraživanje ne daje razlog da mijenjamo:

- Clean/Hexagonal core;
- fact-first model;
- Approved Facts;
- `ContentRevision v1`;
- persistent `analytics_match_key`;
- Human Approval;
- local-first;
- social-first / channel-agnostic;
- explicit provider adapters;
- SQLite kao početni persistence;
- Website Ingestion poslije G10;
- Performance runtime poslije prvih realnih kampanja.

Većina pronađenih rješenja zapravo potvrđuje da su ove granice dobro postavljene.

---

# 6. Prioritet implementacije nalaza

## Sada / P0

1. Ne uvoditi nove velike runtime dependency-je.
2. Zadržati keyring.
3. Završiti P0.
4. U agent workflow dodati samo:
   - proporcionalni review;
   - parallel preflight;
   - fresh-context escalation;
   - progressive-disclosure princip.

## Faza 1 / Campaign Engine

1. Pydantic Evals spike za postojeći G10 harness.
2. Versioned Campaign Quality Dataset.
3. Deterministic hard evaluators.
4. Human + advisory creative evaluation.
5. RapidFuzz samo za redundancy gdje je opravdan.

## Renderer

1. Playwright spike.
2. Golden screenshot test u kontrolisanom okruženju.
3. Satori samo ako Playwright ne prođe packaging/performance.

## Website/Brand Ingestion

1. extruct.
2. Trafilatura.
3. Playwright fallback.
4. SourceSnapshot/provenance ostaje obavezan.

## Document Ingestion

1. Docling packaging/performance spike.
2. Tek nakon PASS napraviti adapter.

## Performance

1. stdlib CSV + openpyxl.
2. strict IDs/match key.
3. RapidFuzz advisory samo za unmatched rows.
4. bez LLM authoritative matchinga.

---

# 7. Završni zaključak

Najbolji rezultat ovog istraživanja nije “dodaj još AI frameworka”.

Veliki dio tehničkih detalja možemo delegirati uskim, zrelim bibliotekama, dok domenska logika ostaje naša:

```text
Campaign quality:
Pydantic Evals + naš G10 + human eval

Website knowledge:
extruct + Trafilatura + Playwright fallback

Documents:
Docling

Creative rendering:
Playwright

Secrets:
keyring

Redundancy / fuzzy suggestions:
RapidFuzz

Providers:
naši adapteri
(simonw/llm kao referenca)

Agent development:
worktrees + proportional review
+ progressive disclosure
+ fresh-context escalation
+ regression evidence loop
```

Ovim ne uklanjamo R1. Ali uklanjamo veliki dio nepotrebnog tehničkog izmišljanja oko R2/R3/R6/R7/R8 i dobijamo konkretniji način da R1 mjerimo i postepeno smanjujemo.

Najvažniji nalaz iz Replitovog sistema je da **evaluation nije završni test nego trajna petlja učenja**. Svaki potvrđeni neuspjeh iz realnog korištenja treba postati novi regression case, tako da Campaign Engine vremenom postaje mjerljivo bolji umjesto da se oslanjamo na utisak.
