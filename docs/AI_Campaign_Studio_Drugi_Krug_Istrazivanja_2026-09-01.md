# AI Campaign Studio — drugi krug istraživanja uskih grla

**Datum:** 2026-09-01  
**Status:** dubinska tehnička provjera kandidata iz prvog kruga  
**Repo projekta:** https://github.com/Rade69/AI-Campaing-Studio

## 1. Cilj drugog kruga

Prvi krug je odgovorio na pitanje:

> Koja postojeća rješenja izgledaju relevantno za moguća uska grla AI Campaign Studija?

Drugi krug pokušava odgovoriti na teže pitanje:

> Da li su ta rješenja zaista dobar izbor za našu konkretnu Python 3.12, Windows, desktop-first, local-first arhitekturu — i gdje mogu zakazati?

Zato je fokus ovog kruga bio na:

- stvarnim dependency-jima;
- otvorenim GitHub issueima;
- Windows problemima;
- memoriji i packagingu;
- silent-data-loss failure modeovima;
- API churnu;
- integracionim granicama;
- stvarnom kodu open-source marketing sistema;
- konkretnim obrascima rada Replita, OpenHands-a i Cursora.

---

# 2. Glavni zaključak

Prvi krug je bio malo previše optimističan prema nekoliko biblioteka.

Nakon dubljeg pregleda preporuke su strože:

| Kandidat | Prvi krug | Drugi krug |
|---|---|---|
| Pydantic Evals | ADOPT | **SPIKE / ADAPT** |
| DeepEval | ADAPT | **HOLD / ne za G10** |
| Ragas | ADAPT kasnije | **HOLD do stvarnog retrievala** |
| DSPy | INSPIRE | **HOLD do kalibrisanog dataseta** |
| Trafilatura | ADOPT | **ADAPT — extractor only** |
| extruct | ADOPT | **ADAPT — optional structured extractor** |
| Docling | ADOPT uz spike | **ADAPT — docling-slim + obavezan Windows/corpus spike** |
| MarkItDown | nije bio glavni kandidat | **BENCHMARK/FALLBACK** |
| Playwright | ADOPT kroz spike | **SPIKE → vjerovatni ADOPT** |
| RapidFuzz | ADOPT usko | **ADOPT usko** |
| keyring | ADOPT | **KEEP** |
| LiteLLM | REJECT core | **REJECT core potvrđen** |
| Instructor | SPIKE po potrebi | **isto** |
| Replit/OpenHands/Cursor obrasci | ADOPT pattern | **ADOPT, još jače potvrđeno** |
| SocialFlow/TryPost | nije detaljno ocijenjeno | **REFERENCE / ANTI-PATTERN, ne donor foundation** |

Najvažnija promjena:

> Parser ili evaluator ne smije postati “izvor istine” samo zato što je popularan ili zreo.

Za ACS treba zadržati sopstvene domenske granice i koristiti biblioteke kao adaptere koji mogu zakazati.

---

# 3. R1 — Campaign Engine kvalitet

## F1 — Pydantic Evals je dobar kandidat, ali ne smije preuzeti G10

**Izvori:**

- GitHub: https://github.com/pydantic/pydantic-ai
- Evals docs: https://ai.pydantic.dev/evals/
- Dataset serialization: https://ai.pydantic.dev/evals/how-to/dataset-serialization/
- Licenca: https://github.com/pydantic/pydantic-ai/blob/main/LICENSE

### Potvrđeno

Pydantic Evals podržava:

- `Dataset`;
- `Case`;
- YAML/JSON serijalizaciju;
- automatski JSON Schema za dataset;
- custom evaluatore;
- code-based evaluatore;
- `LLMJudge`;
- više eksperimenta nad istim datasetom;
- izvještaje.

To je vrlo dobar fit za:

```text
Campaign Fixture
↓
Control A
vs
System B
↓
evaluatori
↓
G10 report
```

Ali paket nije potpuno “besplatan” dependency.

`pydantic-evals` povlači i `pydantic-ai-slim`, a ovaj ima svoje dodatne dependency-je poput `httpx`, `pydantic-graph`, OpenTelemetry API-ja i drugih pomoćnih paketa.

### Procjena

Ne treba dozvoliti:

```text
Pydantic Evals API
= G10 specifikacija
```

nego:

```text
ACS G10 contract
↓
EvalHarnessPort / test adapter
↓
Pydantic Evals
```

Ako biblioteka promijeni API, naš G10 kriterij ostaje isti.

### Odluka

**SPIKE / ADAPT.**

Prije usvajanja:

1. napraviti 3–5 Campaign cases;
2. implementirati dva deterministic evaluatora;
3. jedan advisory LLM evaluator;
4. Control A i System B run;
5. provjeriti koliko koda Pydantic Evals stvarno uklanja;
6. pinovati verziju.

Ako spike ne daje jasnu vrijednost, obični `pytest + YAML + Pydantic` harness je sasvim legitimna alternativa.

### Važno

R1 ostaje **HIGH** sve dok naš G10 ne prođe.

Postojanje Pydantic Evalsa ne smanjuje taj rizik samo po sebi.

---

## F2 — DeepEval je pretežak za naš prvi G10

**Izvori:**

- GitHub: https://github.com/confident-ai/deepeval
- Docs: https://deepeval.com/docs/getting-started
- Licenca: Apache-2.0

### Potvrđeno

Base dependency surface uključuje, između ostalog:

- pytest i više pytest plugina;
- OpenAI;
- aiohttp;
- OpenTelemetry;
- grpcio;
- PostHog;
- Pydantic;
- Rich;
- Typer.

Ima veoma bogate LLM/RAG metrike.

### Procjena

To je više infrastrukture nego što nam treba za:

```text
Control A vs System B
+ nekoliko provjerljivih Campaign evaluatora
```

### Odluka

**Ne koristiti za G10.**

Ponovo ga razmotriti tek ako Website Ingestion/RAG zaista napravi problem sa mjerenjem:

- faithfulness;
- context recall;
- context precision;
- retrieval relevance.

---

## F3 — Ragas i DSPy ostaju kasniji alati, ne rješenje za početak

**Ragas:** https://github.com/vibrantlabsai/ragas  
**DSPy:** https://github.com/stanfordnlp/dspy

Ragas vrijedi tek kada imamo stvaran retrieval pipeline.

DSPy vrijedi tek kada imamo:

```text
stabilan dataset
+
dobru metriku
+
human calibration
```

Bez toga DSPy samo efikasnije optimizuje pogrešan cilj.

---

# 4. Novi prijedlog: Campaign Quality Regression Dataset

Ovo je jedna od najvažnijih stvari potvrđenih drugim krugom.

G10 ne treba biti jednokratni test.

Treba postati početak trajnog dataseta:

```text
G10 Dataset v1
↓
Campaign Engine PASS
↓
stvarno korištenje
↓
čovjek potvrdi problem
↓
novi regression Case
↓
Dataset v2
↓
svaki novi prompt/model mora ponovo proći stare slučajeve
```

Primjeri caseova:

- izmišljena cijena;
- unsupported claim;
- dva CampaignItema sa praktično istom ulogom;
- ponavljanje CTA-a;
- pogrešna činjenica;
- loš platform format;
- ContentPiece ne koristi assigned CampaignItem role;
- pogrešan manifest/revision ID;
- sadržaj koristi superseded ApprovedFact.

To je mnogo vrednije od jednog generičkog:

```text
AI QUALITY SCORE = 87/100
```

---

# 5. R2 — Website Ingestion

## F4 — Trafilatura ostaje korisna, ali samo kao extractor

**Izvori:**

- GitHub: https://github.com/adbar/trafilatura
- Docs: https://trafilatura.readthedocs.io/

### Potvrđeni problemi iz stvarnih GitHub issuea

Crawler na nekim sajtovima ne otkriva linkove:

https://github.com/adbar/trafilatura/issues/680

Problemi sa listama i gubitkom strukture/sadržaja:

https://github.com/adbar/trafilatura/issues/769

`include_images=True` može promijeniti i čak skratiti izvučeni tekst:

https://github.com/adbar/trafilatura/issues/194

Postoje slučajevi nepotpune ekstrakcije članka:

https://github.com/adbar/trafilatura/issues/85

Trafilatura sama ne rješava JavaScript/captcha browser slučajeve:

https://github.com/adbar/trafilatura/issues/18

### Promjena preporuke

Ne:

```text
Trafilatura
= crawler + fetcher + extractor
```

nego:

```text
ACS Website Discovery
↓
ACS fetch
↓
raw HTML snapshot
↓
Trafilatura extractor
```

Za tekst bih inicijalno koristio:

```text
include_images=False
```

Slike/assets obrađivati zasebno.

### Odluka

**ADAPT — extraction adapter, ne crawler source-of-truth.**

---

## F5 — extruct je koristan, ali treba ostati opcioni adapter

**GitHub:** https://github.com/scrapinghub/extruct

Podržava JSON-LD, Microdata, Open Graph, RDFa i druge embedded metadata formate.

Za ACS je najvrijedniji dio mnogo uži:

```text
Organization
Product
Offer
Brand
price
currency
logo
sameAs
description
```

### Problem

extruct ima širi RDF/metadata dependency surface nego što ACS možda realno treba, a postoje i edge-case/install problemi kroz njegov issue tracker.

Primjeri:

https://github.com/scrapinghub/extruct/issues/251  
https://github.com/scrapinghub/extruct/issues/241

### Odluka

**ADAPT.**

Uvesti kroz:

```text
StructuredMetadataExtractorPort
```

Ako Windows/Python 3.12 spike ne bude čist, vlastiti uski JSON-LD/OpenGraph parser za nekoliko potrebnih Schema.org tipova može biti jednostavniji i provjerljiviji.

---

# 6. Preporučeni Website pipeline poslije drugog kruga

```text
URL
↓
Domain / URL validation
↓
robots + sitemap + link discovery
↓
crawl budget
(max pages / depth / timeout / bytes)
↓
HTTP fetch
↓
da li je dokument dovoljno renderovan?
├─ DA → raw HTML
└─ NE → Playwright browser fallback
↓
SourceSnapshot
(raw source se uvijek čuva)
↓
├─ StructuredMetadataExtractor
│     └─ extruct ili uski ACS parser
│
└─ MainTextExtractor
      └─ Trafilatura
↓
ExtractionQualityReport
↓
normalize / dedupe
↓
FactCandidates
↓
Human review
↓
Approved Facts
↓
Brand Snapshot
```

Ključna promjena je `ExtractionQualityReport`.

---

# 7. D1 — Dodati ExtractionQualityReport

Ovo je novi seam koji direktno proizlazi iz stvarnih failure modeova parsera.

Parseri često ne “padnu”.

Opasniji slučaj je:

```text
parser vrati rezultat
+
rezultat izgleda validno
+
30–70% sadržaja nedostaje
```

Zato svaka ekstrakcija treba generisati tehnički izvještaj:

```text
ExtractionQualityReport
- source_snapshot_id
- parser_name
- parser_version
- input_mime
- input_size_bytes
- page_count?
- extracted_char_count
- structured_item_count
- warnings[]
- page_coverage?
- suspicious: bool
- suspicious_reasons[]
- elapsed_ms
```

Primjeri `suspicious_reasons`:

```text
VERY_LOW_TEXT_TO_INPUT_RATIO
EMPTY_EXPECTED_PAGE
PARSER_WARNING
PAGE_COUNT_MISMATCH
STRUCTURED_DATA_ONLY_NO_TEXT
ALTERNATE_PARSER_LARGE_DISAGREEMENT
TIMEOUT_PARTIAL_RESULT
```

Ovaj report ne odlučuje da je činjenica tačna.

On samo kaže:

> Da li imamo razlog sumnjati da extraction nije kompletan?

---

# 8. D2 — FactCandidate treba imati precizniji source locator

Postojeći provenance koncept je dobar, ali drugi krug pokazuje da “source document” ponekad nije dovoljno precizno.

Predlažem da `FactCandidate`/`ApprovedFact` nose locator poput:

```text
source_snapshot_id
source_locator:
    url?
    page_number?
    section?
    char_start?
    char_end?
    json_path?
    element_hint?
extractor_name
extractor_version
```

Primjer:

```text
ApprovedFact:
"Proizvod košta 89 KM"

source:
snapshot_17
page: 3
json_path: $.offers[0].price
```

ili:

```text
snapshot_42
url: /usluge
section: "Cjenovnik"
char_start: 1840
char_end: 1891
```

To čini kasniju ljudsku provjeru i audit mnogo lakšim.

---

# 9. R2b — Document Ingestion: Docling

## F6 — Docling je tehnički snažan, ali nije dovoljno siguran da postane jedini parser

**Izvori:**

- GitHub: https://github.com/docling-project/docling
- Docs: https://docling-project.github.io/docling/
- Installation: https://docling-project.github.io/docling/getting_started/installation/
- Slim packaging plan:
  https://github.com/docling-project/docling/blob/main/.plans/active/docling-slim.md

### Potvrđeno: docling-slim mijenja procjenu packaging rizika

Docling radi na Windowsu i ima novi modularniji `docling-slim` pravac sa odvojenim extras.

Njihov trenutni plan navodi približno:

```text
docling-slim base            ~50 MB
basic PDF                    ~150 MB
advanced PDF                 ~180 MB
parse + DOCX                 ~220 MB
local ML models              ~2+ GB
standard/full                ~2.8 GB
```

To znači da ne moramo povući kompletan Torch/model stack samo da bismo parsirali Office dokumente ili osnovni PDF.

Fine-grained extras uključuju odvojeno:

- PDF backend;
- DOCX;
- PPTX;
- XLSX;
- web;
- OCR engine;
- lokalne modele;
- VLM;
- Playwright HTML rendering.

### Ali stvarni issuei su važni

Vector-heavy PDF može eksplodirati u RAM-u:

https://github.com/docling-project/docling/issues/4058

Veliki dokumenti mogu imati višegigabajtni memory footprint:

https://github.com/docling-project/docling/issues/4071

DOCX textbox sadržaj može biti izgubljen:

https://github.com/docling-project/docling/issues/4034

DOCX content controls mogu izgubiti sadržaj:

https://github.com/docling-project/docling/issues/3950

Windows veliki PDF OOM / bad_alloc slučajevi:

https://github.com/docling-project/docling/issues/3671  
https://github.com/docling-project/docling/issues/3844

Windows Torch compile zahtjevi/komplikacije:

https://github.com/docling-project/docling/issues/3956

OCR problemi:

https://github.com/docling-project/docling/issues/4022  
https://github.com/docling-project/docling/issues/3839

Excel EMF slike mogu nestati:

https://github.com/docling-project/docling/issues/3684

### Zaključak

Docling nije loš izbor.

Problem je pogrešna pretpostavka:

```text
Docling output
= kompletna istina dokumenta
```

To ne smijemo raditi.

### Nova odluka

**ADAPT iza `SourceDocumentPort`.**

Prvi spike:

```text
docling-slim
+ format-pdf
+ format-docx
+ format-xlsx
```

bez lokalnih ML modela i bez OCR-a po defaultu.

OCR/model extras uvoditi samo ako realni dokumenti to opravdaju.

---

# 10. F7 — MarkItDown kao jeftiniji secondary parser / benchmark

**Izvori:**

- GitHub: https://github.com/microsoft/markitdown
- MIT licenca
- Python 3.12 podržan

MarkItDown ima modularne extras:

```text
docx → mammoth + lxml
xlsx → pandas + openpyxl
pdf  → pdfminer.six + pdfplumber
pptx → python-pptx
```

To ga čini lakšim od punog Docling stacka.

Ali ni on nije autoritativan.

### Potvrđeni problemi

PDF može “uspješno” vratiti samo dio teksta poslije inline image problema:

https://github.com/microsoft/markitdown/issues/1870

Strikethrough semantika može nestati:

https://github.com/microsoft/markitdown/issues/2340

Malformed DOCX math može srušiti konverziju:

https://github.com/microsoft/markitdown/issues/1979

DOCX equations mogu nestati:

https://github.com/microsoft/markitdown/issues/1512

PPTX `None` text može srušiti cijelu konverziju:

https://github.com/microsoft/markitdown/issues/1808

PDF OCR nije automatski univerzalan:

https://github.com/microsoft/markitdown/issues/1601

### Odluka

Ne:

```text
Docling OR MarkItDown
```

nego:

```text
Primary parser
+
sanity checks
+
secondary parser samo kada je rezultat sumnjiv
```

Primjer:

```text
Docling output = 1.2 KB teksta
PDF = 80 stranica / 15 MB
↓
SUSPICIOUS
↓
probaj MarkItDown ili drugi parser
↓
ako se outputi dramatično razlikuju:
USER_REVIEW_REQUIRED
```

Ne treba uvijek parsirati svaki dokument dvaput.

---

# 11. D3 — Document parser architecture nakon drugog kruga

```text
SourceDocumentPort
        ↓
DocumentIngestionService
        ↓
Resource Guard
(page / bytes / time / RAM policy)
        ↓
Primary Parser Adapter
        ↓
ExtractionQualityReport
        ↓
     suspicious?
      /      \
    NO        YES
    ↓          ↓
continue   Secondary Parser
             ↓
        compare signals
             ↓
       warning/manual review
```

Najvažnije:

```text
Parser output
→ FactCandidates
NIKAD
→ direktno Approved Facts
```

Human approval ostaje sistemska zaštita.

---

# 12. R7 — Renderer: Playwright

## F8 — Playwright ostaje najbolji kandidat, ali samo uz kontrolisan runtime

**Izvori:**

- Python docs: https://playwright.dev/python/
- Screenshots: https://playwright.dev/python/docs/screenshots
- PyInstaller: https://playwright.dev/python/docs/library
- GitHub Python binding:
  https://github.com/microsoft/playwright-python

### Potvrđeno

Playwright:

- podržava PyInstaller;
- može bundlovati browser uz executable;
- može instalirati samo potreban browser/headless shell;
- daje fixed viewport;
- PNG screenshot u memoriju;
- browser context izolaciju;
- kontrolu animacija, CSS-a i browser lifecyclea.

### Potvrđeni rizici iz issue trackera

Python 3.14.0–3.14.6 sync task retention/memory problem:

https://github.com/microsoft/playwright-python/issues/3148

`context.route()` retention problem:

https://github.com/microsoft/playwright-python/issues/3121

Free-threaded 3.14 problemi:

https://github.com/microsoft/playwright-python/issues/3123  
https://github.com/microsoft/playwright-python/issues/3129

ACS trenutno cilja Python 3.12, pa ti 3.14 problemi nisu direktan blocker.

Ipak, potvrđuju važnu arhitektonsku odluku:

> Renderer worker ne treba biti vječni browser proces bez kontrole resursa.

### Preporučeni renderer

```text
LayoutSpec
↓
validator
↓
trusted local HTML/CSS template
↓
separate Renderer Worker
↓
Playwright Chromium/headless shell
- pinned version
- fixed viewport
- offline network
- trusted local assets only
- explicit fonts
- animations disabled
- await document.fonts.ready
↓
PNG
↓
artifact manifest
↓
worker recycle policy
```

### Kritična granica

Ne dijeliti isti browser context između:

```text
Creative Renderer
i
Website Ingestion
```

Renderer obrađuje trusted local input.

Website browser obrađuje untrusted internet input.

To su dva različita trust boundary-ja, iako oba mogu koristiti Playwright.

### Odluka

**SPIKE → vjerovatni ADOPT.**

Spike mora izmjeriti:

- Windows installer size;
- cold start;
- warm render time;
- RAM;
- 100 uzastopnih rendera;
- font fidelity;
- 1080×1350;
- 1080×1080;
- overflow;
- worker recycle;
- offline guarantee.

---

# 13. R6 — Provider abstraction

## F9 — Drugi krug snažnije potvrđuje da treba zadržati naš registry

Dodatno je pregledan:

https://github.com/andrewyng/aisuite

To je zanimljiv lightweight multi-provider projekat, ali njegovi otvoreni issuei pokazuju upravo probleme koje je naš plan već eksplicitno adresirao.

### Konkretni issuei

API-key UX i Test Connection:

https://github.com/andrewyng/aisuite/issues/337

Generic provider/model konfiguracija i custom OpenAI-compatible endpointi:

https://github.com/andrewyng/aisuite/issues/328

Model listing/discovery, OpenRouter, LM Studio:

https://github.com/andrewyng/aisuite/issues/106

Gemini provider-specific tool behavior:

https://github.com/andrewyng/aisuite/issues/321

### Zaključak

“Jedinstven chat completion API” nije dovoljan abstraction.

Nama trebaju odvojeno:

```text
ProviderDefinition
ModelDefinition
ModelSource
Capabilities
ConnectionStatus
Discovery
Adapter
SecretStore
```

To je jači model.

---

# 14. D4 — Test Connection treba preferirati model discovery, ne paid generation

Ovo je konkretna nadogradnja.

Potvrđeni API endpointi:

OpenAI:

https://platform.openai.com/docs/api-reference/models

```text
GET /v1/models
```

Anthropic:

https://docs.anthropic.com/en/api/models-list

ima List Models API.

Gemini:

https://ai.google.dev/api/models

```text
GET /v1beta/models
```

OpenRouter:

https://openrouter.ai/docs/api/api-reference/models/get-models

```text
GET /api/v1/models
```

OpenRouter vraća i korisne capability podatke poput:

- input/output modalities;
- context length;
- supported parameters;
- `tools`;
- `structured_outputs`;
- pricing.

### Predloženi flow

```text
Save API key
↓
Test Connection
↓
provider supports authenticated model listing?
├─ YES → list models
│         ↓
│       CONNECTED
│
└─ NO → cheapest safe provider-specific validation
↓
map discovered models
↓
local registry normalization / overrides
```

Za Custom OpenAI-compatible:

```text
probaj /models
↓
ako endpoint nema model discovery:
manual model ID
```

Ne smijemo pretpostaviti da svi OpenAI-compatible serveri podržavaju identičan `/models`.

---

# 15. R3 — Content Quality Gate: stvarni open-source marketing kod

Pregledan je konkretan open-source projekat:

https://github.com/inbharatai/SocialFlow

Njegov backend zaista ima odvojene agente:

```text
Scout
Planner
Creator
Reviewer
Publisher
Analyst
```

Reviewer kod:

https://github.com/inbharatai/SocialFlow/blob/main/backend/agents/reviewer.py

### Potvrđeno u kodu

Reviewer koristi:

- regex za credential leak;
- regex za internal metadata leak;
- regex za moguće fabricated claims;
- regex za brand-voice fraze;
- platform length limit;
- status `approved/review/blocked`.

To potvrđuje da je:

```text
hard deterministic checks
+
manual review
```

praktičan obrazac.

Ali pokazuje i zašto je naš Approved Facts pristup jači.

SocialFlow npr. upozorava na “95% improvement” regexom.

ACS može:

```text
claim.fact_id
↓
ApprovedFact postoji?
↓
nije superseded?
↓
vrijednost zaista odgovara?
```

To je mnogo provjerljivije.

### Važan anti-pattern

Njihov Planner hardkodira platform constraints u Python:

https://github.com/inbharatai/SocialFlow/blob/main/backend/agents/planner.py

ACS već ide boljim putem sa YAML data-driven registryjem.

To ne treba mijenjati.

---

# 16. R5 — Analytics: SocialFlow potvrđuje zašto naš model treba ostati jači

SocialFlow analytics:

https://github.com/inbharatai/SocialFlow/blob/main/backend/analytics_store.py

koristi model približno:

```text
post_ref
platform
content_type
campaign
metrics...
```

To je jednostavno, ali `post_ref` je previše slab identitet za ono što mi želimo.

Naš:

```text
CampaignItem
→ ContentPiece
→ ContentRevision
→ DistributionInstance
→ PerformanceSnapshot
```

je arhitektonski jači.

### Odluka

Ne kopirati SocialFlow analytics model.

---

# 17. D5 — analytics_match_key bez nove biblioteke

Za ovaj problem drugi krug nije pronašao razlog da uvodimo framework.

Možemo koristiti samo Python standardnu biblioteku.

Jedna opcija:

```python
uuid.uuid5(ACS_ANALYTICS_NAMESPACE_V1, canonical_input)
```

gdje je:

```text
canonical_input =
content_revision_id
+ channel_code
+ platform_code
+ format_code
```

Ali važno:

```text
key se generiše jednom
↓
PERSISTIRA se
↓
nikada se retroaktivno ne preračunava
```

Ako formula/namespace ikad promijeni značenje:

```text
algorithm_version = 2
manifest schema_version bump
```

UUIDv5 koristi SHA-1 interno, ali ovdje se ne koristi za sigurnost nego za deterministički identitet.

Alternativa je `hashlib.blake2s`.

**Ne treba treći dependency.**

---

# 18. R9 — Agent workflow: Replit nalaz je važniji nego u prvom krugu

## F10 — Decision-Time Guidance direktno pogađa naš problem

Izvor:

https://replit.com/blog/decision-time-guidance

Replit eksplicitno navodi problem:

- duge agent trajectories;
- static prompt rules mogu početi zagađivati kontekst;
- previše reminders daje diminishing ili negativan efekat;
- umjesto toga koriste kratku situacionu guidance neposredno prije odluke.

Kod doom-loopa:

```text
stuck agent
↓
external agent
↓
fresh context
↓
different model
↓
new plan
```

To je veoma blizu situaciji koju smo imali kada je P0-002 otišao u više Codex/fix rundi.

### Procjena za ACS

Naš read-order je dobar kao source-of-truth sistem, ali ne znači da svaka riječ mora biti učitana u svaki task.

---

# 19. D6 — Agent context podijeliti na Core i On-demand

Predloženi novi princip:

## Always loaded

```text
AGENTS.md — kratak router + nepovrediva pravila
Current Task Contract
relevant CURRENT_STATE
```

## On-demand

```text
.agent/skills/gitnexus/SKILL.md
.agent/skills/migrations/SKILL.md
.agent/skills/provider-adapter/SKILL.md
.agent/skills/localization/SKILL.md
.agent/skills/renderer/SKILL.md
.agent/skills/performance/SKILL.md
.agent/skills/security/SKILL.md
```

OpenHands koristi vrlo sličan model progressive disclosure:

https://docs.openhands.dev/overview/skills  
https://docs.openhands.dev/sdk/guides/skill

Agent u početku vidi samo:

```text
name
description
location
```

a puni skill otvara kada je potreban.

### Odluka

**ADOPT pattern**, ali postepeno.

Ne treba sada pretvarati P0 u projekat “izgradnje skill frameworka”.

Dovoljno je reorganizovati dokumentaciju tako da detailed guides ne moraju svi biti čitani unaprijed.

---

# 20. D7 — Doom-loop escalation pravilo

Predlažem jasnu procesnu granicu:

```text
isti blocking finding
+
2 korektne fix runde
+
problem i dalje postoji
=
DOOM_LOOP_ESCALATION
```

Tada:

```text
1. stop current fix loop
2. sačuvaj evidence
3. napravi minimalan current-state packet:
   - acceptance criterion
   - current diff
   - failing test/log
   - dvije prethodne hipoteze
4. pošalji DRUGOM modelu
5. fresh context
6. traži novu root-cause hipotezu
7. tek onda nova implementacija
```

Ne treba istom agentu dodavati još deset novih instrukcija.

---

# 21. D8 — Proporcionalni review

Cursor sada eksplicitno ima:

https://prod.cursor.com/docs/agent/agent-review

dva nivoa:

```text
Quick
Deep
```

Njihova preporuka:

- Quick za male izmjene;
- Deep za complex logic, security i large refactors.

To dobro mapira na nas:

```text
LOW
→ implementer tests
→ quick independent Codex review
→ user merge

MEDIUM
→ normal Codex review
→ execution evidence
→ Claude only if architectural/integration relevance

HIGH / shared / security / migration
→ Codex deep adversarial review
→ Claude architecture/integration review
→ user merge
```

P0-002 ne smije postati default review intenzitet za svaki task.

---

# 22. D9 — Parallel preflight prije pokretanja agenata

Replit i Cursor oba rade u izolovanim kopijama/worktreeovima:

https://docs.replit.com/core-concepts/agent/task-system  
https://prod.cursor.com/docs/configuration/worktrees

Replit dodatno flaguje konflikt kada taskovi diraju isto područje.

Naš trenutni `claim/release` koncept nije dovoljan.

Prije paralelnog rada treba provjeriti:

```text
task dependencies
allowed_paths
forbidden_paths
planned files
base SHA
main current SHA
branch staleness
shared contracts
migration ownership
```

Output:

```text
SAFE_PARALLEL

SEQUENTIAL_REQUIRED

CONFLICT_REQUIRES_DECISION
```

### Dodatna zaštita

Prije nego agent krene:

```text
if task_base_sha != expected_main_base
→ STALE_TASK
→ rebase/recreate decision
```

Time direktno sprečavamo raniji problem sa task branchom koji nema najnoviji Task Contract.

---

# 23. D10 — Machine-readable execution evidence

SWE-agent i slični sistemi koriste trajectory/evidence pristup.

Za nas ne treba kompletan token-by-token log.

Dovoljno je uz Markdown report imati:

```text
agent_reports/<TASK-ID>-evidence.json
```

Primjer:

```json
{
  "task_id": "ACS-P0-005",
  "base_sha": "...",
  "head_sha": "...",
  "agent": "pi",
  "files_changed": [],
  "commands_run": [],
  "tests": {
    "pytest": "pass",
    "ruff": "pass",
    "mypy": "pass"
  },
  "review_round": 1,
  "blocking_findings": [],
  "out_of_scope_findings": []
}
```

Prednosti:

- Claude/Codex ne moraju parsirati dugački narativ;
- lakše je automatski provjeriti da dokaz postoji;
- kasnije se može praviti dashboard bez mijenjanja izvještaja.

---

# 24. Revised shortlist

## ADOPT / vjerovatni ADOPT

### 1. keyring
Za SecretStore.

https://github.com/jaraco/keyring

### 2. RapidFuzz
Samo za:

- deterministic redundancy signal;
- advisory manual analytics matching.

https://github.com/rapidfuzz/RapidFuzz

### 3. Progressive-disclosure agent guides
Koncept OpenHands/AgentSkills.

https://docs.openhands.dev/sdk/guides/skill

### 4. Replit fresh-context escalation
Procesni obrazac.

https://replit.com/blog/decision-time-guidance

### 5. Parallel preflight + isolated worktrees
Replit/Cursor obrazac.

https://docs.replit.com/core-concepts/agent/task-system  
https://prod.cursor.com/docs/configuration/worktrees

---

## SPIKE → vjerovatni ADOPT

### Pydantic Evals
Za G10 development harness, ali ACS G10 ostaje nezavisan.

https://ai.pydantic.dev/evals/

### Playwright
Za trusted local Creative Renderer.

https://playwright.dev/python/

### docling-slim
Za DocumentIngestion adapter, bez ML/OCR defaulta.

https://github.com/docling-project/docling

---

## ADAPT

### Trafilatura
Samo main text extractor.

https://github.com/adbar/trafilatura

### extruct
Structured metadata adapter.

https://github.com/scrapinghub/extruct

### MarkItDown
Secondary parser / benchmark / fallback.

https://github.com/microsoft/markitdown

### Instructor
Samo ako naši provider adapteri razviju previše duplirane structured-output retry logike.

https://github.com/567-labs/instructor

---

## HOLD

### Ragas
Do stvarnog retrieval problema.

https://github.com/vibrantlabsai/ragas

### DSPy
Do stabilnog Campaign Quality Regression Dataseta.

https://github.com/stanfordnlp/dspy

### DeepEval
Do potrebe za bogatijim RAG evalom.

https://github.com/confident-ai/deepeval

---

## REJECT kao core

### LiteLLM
Preširok dependency/provider surface za naš MVP.

https://github.com/BerriAI/litellm

### Firecrawl
Pretežak hosted/self-hosted model + AGPL za core desktop.

https://github.com/firecrawl/firecrawl

### Langfuse
Odličan observability proizvod, ali prevelik runtime/server stack za naš desktop proizvod.

https://github.com/langfuse/langfuse

### SQLAlchemy-Continuum za ContentRevision
Generic ORM audit ne odgovara našoj domenskoj revision semantici.

https://github.com/sqlalchemy-continuum/sqlalchemy-continuum

### html2image
Manje kontrole nego direktni Playwright.

https://github.com/vgalin/html2image

---

# 25. Konkretne izmjene koje bih sada ugradio u plan

## D1 — G10 ostaje ACS-owned contract

Pydantic Evals može biti adapter, ne arhitektura.

## D2 — G10 postaje permanent regression dataset

Svaki potvrđen real-world failure može postati novi case.

## D3 — Dodati `ExtractionQualityReport`

Za detekciju silent partial extractiona.

## D4 — Dodati precizni `source_locator`

Fact provenance do stranice/sekcije/span-a/JSON patha.

## D5 — Website stack

```text
ACS discovery/fetch
→ SourceSnapshot
→ extruct optional
→ Trafilatura
→ Playwright fallback
→ ExtractionQualityReport
→ FactCandidates
→ Human approval
```

## D6 — Document stack

```text
SourceDocumentPort
→ docling-slim adapter
→ quality report
→ suspicious?
→ MarkItDown/alternate parser
→ FactCandidates
```

## D7 — Resource guards za dokumente

Minimalno:

```text
max file bytes
max pages
timeout
worker memory policy
cancellation
partial result = warning, ne success
```

## D8 — Renderer

Trusted-local Playwright worker, odvojen od Internet browser workera.

## D9 — Provider Test Connection

Preferirati authenticated model listing endpoint, pa tek onda generation fallback.

## D10 — Model discovery

```text
DISCOVERED
REGISTRY
MANUAL
```

ostaje dobra odluka.

## D11 — `analytics_match_key`

Koristiti stdlib deterministički algoritam + persisted value + algorithm/schema version.

## D12 — Agent progressive disclosure

AGENTS tanji; task-specific guides on-demand.

## D13 — Doom-loop escalation poslije dvije fix runde

Fresh context + drugi model.

## D14 — Proporcionalni review

LOW/Quick, MEDIUM/Normal, HIGH/Deep dual review.

## D15 — Parallel preflight + staleness guard

Prije svakog paralelnog task para.

## D16 — Machine-readable evidence JSON

Uz postojeći human report.

---

# 26. Šta još NIJE potvrđeno

Ovo je važno razlikovati od web/GitHub istraživanja.

Još nisam dokazao unutar našeg ACS repozitorija:

- da `pydantic-evals` neće napraviti dependency konflikt;
- koliko tačno MB povećava naš installer;
- da Docling radi dobro na našim realnim dokumentima;
- realni RAM Doclinga na našem Windows okruženju;
- PyInstaller + Playwright veličinu našeg finalnog paketa;
- vrijeme hladnog i toplog rendera;
- da extruct radi bez problema na našim ciljanim webshopovima;
- optimalne thresholds za `ExtractionQualityReport`;
- optimalan RapidFuzz prag za redundancy;
- da progressive-disclosure izmjena stvarno smanjuje broj review rundi u našem workflowu.

To se više ne može kvalitetno riješiti internet istraživanjem.

Sljedeći nivo dokaza su **mali, vremenski ograničeni spikeovi u našem repozitoriju**.

---

# 27. Predloženi spike paket

Ne pokretati ih sada usred P0 ako nisu potrebni.

Kada odgovarajuća faza dođe:

## SPIKE-EVAL — 0.5–1 dan

Pydantic Evals vs mali custom pytest harness.

PASS samo ako Pydantic Evals značajno smanji custom kod i ne zarobi G10 u framework.

## SPIKE-RENDER — 1 dan

Playwright + Chromium/headless shell + PyInstaller.

Mjeri:

- installer delta;
- cold start;
- 100 rendera;
- RAM;
- fonts;
- pixel stability;
- worker recycle.

## SPIKE-DOC — 1–2 dana

Corpus:

```text
5 PDF
2 DOCX
1 XLSX
1 scanned PDF
1 deliberately problematic PDF/DOCX
```

Porediti:

```text
docling-slim
vs
MarkItDown
vs
manual expected facts
```

Mjeri:

- completeness;
- tables;
- text boxes;
- OCR;
- runtime;
- RAM;
- warnings;
- silent omissions.

## SPIKE-WEB — 1 dan

5 različitih sajtova:

```text
static company site
WordPress
webshop JSON-LD
JS-heavy SPA
poor/irregular HTML
```

Pipeline:

```text
HTTP
→ extruct
→ Trafilatura
→ Playwright fallback
```

Mjeri:

- relevant fact recall;
- duplicate noise;
- assets;
- SourceLocator quality;
- time/page.

---

# 28. Konačni zaključak drugog kruga

Drugi krug je smanjio jednu vrstu rizika, ali je otkrio drugu.

Dobra vijest:

> Ne moramo izmišljati gotovo nijedan težak tehnički problem od nule.

Postoje dobra rješenja za:

- eval dataset;
- HTML extraction;
- structured metadata;
- document parsing;
- browser rendering;
- secrets;
- fuzzy matching;
- provider discovery;
- progressive agent context.

Ali pogrešan potez bi bio:

```text
našao sam dobru biblioteku
→ proglasim je source of truth
→ vežem domen za nju
```

Bolji ACS obrazac je:

```text
DOMEN
↓
PORT
↓
ADAPTER
↓
3rd-party library
↓
quality/evidence
↓
human/system gate
```

Najvažnije nove tehničke odluke iz drugog kruga su:

1. **ExtractionQualityReport** zbog silent-data-loss rizika.
2. **Precizni source_locator** za FactCandidates/ApprovedFacts.
3. **docling-slim kao adapter, ne autoritet.**
4. **Secondary parser samo za sumnjive dokumente.**
5. **Playwright trusted renderer i Website browser moraju biti odvojeni trust boundary-ji.**
6. **Provider Test Connection treba prvo koristiti model discovery kada je moguće.**
7. **G10 prerasta u trajni Campaign Quality Regression Dataset.**
8. **Agent context ide prema progressive disclosure.**
9. **Poslije dvije neuspjele fix runde fresh-context/different-model escalation.**
10. **Parallel preflight i branch staleness provjera prije pokretanja agenata.**

R1 ipak ostaje:

> **Da li naš konkretni Campaign Engine na našem fixture-u i našim promptovima stvarno pobjeđuje dobar plain LLM workflow?**

To se ne može riješiti još jednim GitHub pretraživanjem.

To će dokazati ili oboriti G10.
