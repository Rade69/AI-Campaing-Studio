# AI Campaign Studio — Faza 0.6
## Revidirana početna projektna osnova

**Status:** aktivni temeljni dokument projekta  
**Verzija:** 0.6  
**Tip proizvoda:** desktop-first, local-first AI alat za pripremu marketinških kampanja, sa društvenim mrežama kao prvim i prioritetnim output kanalom  
**Primarni UI kandidat:** PySide6 — nije konačno zaključan prije UI fidelity spike-a  
**Primarni cilj ove faze:** zaključati proizvodni koncept, arhitektonske granice, prvi dokaz vrijednosti, visual/layout arhitekturu i website-ingestion pristup, uz eksplicitan UI framework gate prije detaljnog MVP plana

---

# 1. Svrha dokumenta

Ovaj dokument zamjenjuje prethodnu Fazu 0 kao aktuelnu projektnu osnovu.

Glavne ideje prethodne verzije ostaju:

- desktop-first;
- local-first;
- Python desktop backend;
- PySide6 kao vodeći UI kandidat, ali ne kao unaprijed zaključan framework;
- bez obaveznog server runtime-a;
- kampanjski plan prije generisanja pojedinačnih objava;
- human-in-the-loop;
- odvojeni domain/application/infrastructure slojevi;
- AI provider apstrakcije;
- kvalitetan export;
- opcioni VPS backup.

Međutim, nekoliko bitnih dijelova je revidirano:

1. **Claim validacija prelazi na fact-first generisanje.**
2. **Prvi vertical slice više ne počinje ingestom sajta.**
3. **Prvo se dokazuje vrijednost kampanjskog sloja na ručno definisanom brand fixture-u.**
4. **Facts, Brand Profile i Brand Voice postaju verzionisani/snapshotovani.**
5. **Template sistem dobija hard layout constraints.**
6. **B/H/S jezik postaje eksplicitan tehnički rizik koji se rano mjeri.**
7. **Golden testovi se dijele na determinističke metrike i human evaluation.**
8. **Playwright integracija mora proći tehnički spike prije konačnog zaključavanja.**
9. **SQLite backup mora koristiti SQLite backup mehanizam, ne kopiranje otvorenog `.db` fajla.**
10. **AI execution budget se mjeri od prvog vertical slicea.**
11. **Vizuelni sistem prelazi sa skupa potpuno fiksnih šablona na hibridni AI Visual Direction / Layout Engine sa determinističkim rendererom.**
12. **LLM smije predlagati layout i generisati nove šablone, ali finalni render ostaje schema-validiran i deterministički.**
13. **Website scraping se definiše kao kontrolisani Website Ingestion pipeline, ne kao nasumično agentno surfanje.**
14. **Website Ingestion koristi HTTP-first pristup, Playwright fallback, crawl budget, URL ranking, boilerplate removal, deduplikaciju i source snapshotove.**
15. **Svaka činjenica izvedena iz sajta mora zadržati provenance do konkretnog SourceSnapshot/SourceChunk izvora.**
16. **Desktop-first ostaje zaključan, ali konkretan Presentation framework više nije zaključan bez vizuelnog spike-a.**
17. **PySide6 je vodeći kandidat; pywebview + HTML/CSS/JS je kontrolna alternativa za poređenje.**
18. **Prije ozbiljne izgradnje Presentation sloja mora se replicirati jedan reprezentativan Post Studio ekran i izmjeriti vizuelna vjernost, kompleksnost, scaling, packaging i integracija.**
19. **Qt/QThread donor iskustvo iz WebshopAudit-a prenosi se kao background-job/progress/cancellation obrazac, ne kao obaveza da novi GUI bude Qt.**

---

# 2. Jedna rečenica o proizvodu

**AI Campaign Studio pretvara provjerene informacije o firmi i marketinški cilj u strukturisanu, brandiranu i provjerljivu kampanju, sa društvenim mrežama kao prvim prioritetnim output kanalima, ali bez vezivanja Brand Intelligence i Campaign Enginea isključivo za social media.**

---

# 3. Šta ovaj proizvod NIJE

Aplikacija nije:

- social media scheduler;
- Hootsuite alternativa;
- unified inbox;
- DM automation platforma;
- Meta/TikTok publishing servis;
- social analytics dashboard;
- Canva klon;
- generički prompt box;
- multi-agent demonstracija bez jasne koristi.

Prva verzija treba dokazati samo jednu centralnu pretpostavku:

> **Da li strukturisani Brand → Campaign Plan → Post pipeline daje značajno bolji i konzistentniji marketinški rezultat od jednog generičkog LLM prompta?**

Ako odgovor nije jasno „da“, nema smisla graditi složen ingest, retrieval, backup, social integracije ili dodatne AI slojeve.

---

# 4. Centralna vrijednost — kampanjski sloj

Loš workflow:

```text
"Napravi mi 8 Instagram objava za implantate."
                 ↓
            jedan LLM poziv
                 ↓
        8 sličnih objava
```

Naš workflow:

```text
BRAND CONTEXT
      ↓
CAMPAIGN BRIEF
      ↓
CAMPAIGN ROLES
      ↓
CAMPAIGN PLAN
      ↓
HUMAN REVIEW
      ↓
FACT SELECTION
      ↓
POST GENERATION
      ↓
DETERMINISTIC VALIDATION
      ↓
POST REVIEW
      ↓
VISUAL RENDER
      ↓
EXPORT
```

Objava nije izolovan tekst.

Svaka objava ima:

- ulogu;
- temu;
- cilj;
- ciljanu publiku;
- skup dozvoljenih činjenica;
- CTA politiku;
- platformsku varijantu;
- status pregleda.

---

# 5. Produktne odluke

## D1 — Desktop-first

Prva verzija je **desktop aplikacija**.

To je zaključana produktna odluka.

Konkretan Presentation framework još nije konačno zaključan.

Vodeći kandidat:

```text
PySide6
```

Kontrolna alternativa za spike:

```text
pywebview + HTML/CSS/JS
```

uz lokalni Python bridge. Flask ili drugi lokalni HTTP sloj uvodi se samo ako se pokaže stvarno potrebnim.

Razlozi za desktop-first:

- lokalni dokumenti;
- lokalne slike;
- lokalni projekti;
- jednostavan export;
- nema obaveznog hostinga;
- nema centralnog auth sistema;
- nema SaaS multi-tenancy kompleksnosti;
- aplikacija može raditi i bez VPS-a.

Web/SaaS verzija nije dio početnog razvoja.

Važno:

> **desktop-first ne znači automatski Qt-first.**

Presentation framework mora proći UI fidelity spike prije ozbiljne implementacije ekrana.

## D2 — Local-first

Na korisničkom računaru ostaju:

- projekti;
- SQLite baza;
- brand podaci;
- dokumenti;
- asseti;
- kampanje;
- draftovi;
- revizije;
- vizuali;
- exporti;
- lokalni logovi.

AI provider pozivi i opcioni VPS backup su spoljne zavisnosti, ali nisu centralni runtime aplikacije.

## D3 — VPS je backup destinacija, ne runtime

Aplikacija mora nastaviti normalno raditi ako:

- VPS nije dostupan;
- backup ne uspije;
- mreža privremeno padne.

Backup je:

```text
Desktop → Snapshot → Package → VPS
```

Ne uvodimo pravi dvosmjerni sync u MVP-u.

## D4 — Human-in-the-loop

Obavezne kontrolne tačke:

1. Campaign Plan approval
2. Post review
3. Claim warning review
4. Final export

Automatski Brand Intelligence dolazi tek u kasnijem vertical sliceu; tada će i Brand Review biti obavezna tačka.

## D5 — AI je servis, ne arhitektura

Ne uvoditi autonomne agente bez mjerljive potrebe.

Primarno:

```text
Use Case
  ↓
Orchestrated Pipeline
  ↓
Provider Port
  ↓
LLM Adapter
```

## D6 — Structured outputs gdje god je moguće

LLM output koji ulazi u application/domain sloj mora biti validiran.

Primjeri:

- CampaignPlan schema
- PostDraft schema
- VisualDirection schema
- Claim mapping schema

## D7 — Provider independence

Aplikacija ne smije direktno zavisiti od jednog modela.

Portovi:

```text
TextGenerationPort
ImageGenerationPort
EmbeddingPort
```

Built-in adapteri mogu biti:

```text
OpenAIAdapter
AnthropicAdapter
GoogleAdapter
DeepSeekAdapter
OpenRouterAdapter
OpenAICompatibleAdapter
```

Dodatni provider se dodaje kroz isti registry/adapter contract, bez izmjene Campaign Enginea.


## D-LANG-1 — Dva jezika aplikacije, jedan BHS lokalni jezički sistem

Aplikacija ima samo dva UI jezika:

```text
EN
BHS
```

`BHS` predstavlja zajednički lokalni jezički sistem za bosanski/srpski/hrvatski u latinici.

Ne praviti tri skoro identična UI prevoda:

```text
bs UI
sr UI
hr UI
```

jer bi to nepotrebno utrostručilo održavanje stringova, testova i terminologije.

UI model:

```text
AppLocale
- EN
- BHS_LATIN
```

Svi korisnički UI stringovi moraju biti izvučeni iz koda i ići kroz centralni translation key sistem.

Primjer:

```text
campaign.create
post.approve
facts.used
warning.unsupported_number
```

Resource struktura:

```text
resources/i18n/
├── en.json
└── bhs.json
```

Ne hardkodovati:

```text
"Kreiraj kampanju"
"Create campaign"
```

po widgetima/viewovima.

Presentation sloj koristi:

```text
t("campaign.create")
```

ili framework-ekvivalent.

---

## D-LANG-2 — Jezik UI-a i jezik generisanog sadržaja su odvojeni koncepti

Ne miješati:

```text
AppLocale
```

sa:

```text
ContentLanguageContext
```

Korisnik može imati:

```text
UI: BHS
```

a generisati:

```text
English campaign
```

ili obrnuto.

`ContentLanguageContext`:

```text
language_family: EN | BHS
regional_variant: NEUTRAL | BS | SR | HR
script: LATIN
preferred_terms[]
forbidden_terms[]
regional_vocabulary[]
tone_examples[]
```

Za BHS:

```text
language_family = BHS
```

Regionalna varijanta određuje terminološku preferenciju:

```text
NEUTRAL
BS
SR
HR
```

To nisu četiri različita jezička engine-a.

To je jedan lokalni jezički sistem sa regionalnim terminološkim pravilima.

---

## D-LANG-3 — Latinica je MVP pismo za BHS

Za početnu verziju:

```text
script = LATIN
```

Obavezno testirati:

```text
č ć š ž đ
Č Ć Š Ž Đ
```

Ćirilica nije MVP zahtjev.

Ako kasnije postane stvarna potreba, dodaje se kao nova script varijanta, bez promjene `language_family = BHS` modela.

---

## D-LANG-4 — Regionalna varijanta utiče na terminologiju, ne na provenance

Regionalna varijanta ne smije mijenjati činjenice.

Primjer:

```text
ApprovedFact:
"Firma ima poslovnicu u Bijeljini."
```

može se stilistički realizovati različitim lokalnim terminima, ali:

```text
fact_id
source
claim provenance
```

ostaju isti.

Regionalizacija je presentation/copy pravilo, ne fact transformation.

---

## D-LANG-5 — Promptovi moraju eksplicitno primati Language Context

Svaki relevantni AI prompt dobija:

```text
ui_language        # samo ako utiče na pomoćne poruke
output_language
language_family
regional_variant
script
preferred_terms
forbidden_terms
regional_vocabulary
tone_examples
```

Za BHS primjer:

```text
output_language: BHS
language_family: BHS
regional_variant: BS
script: LATIN
```

Za engleski:

```text
output_language: English
language_family: EN
regional_variant: NEUTRAL
script: LATIN
```

Ne koristiti više tri potpuno odvojene konfiguracije tipa:

```text
Bosnian
Serbian
Croatian
```

kao da su tri nezavisna produkcijska jezička sistema.



## D-CHANNEL-1 — Društvene mreže su prioritet, ali Brand Intelligence je channel-agnostic

Brand Intelligence nije „social-media baza“.

Podaci kao što su:

- proizvodi i usluge;
- lokacije;
- cijene i ponude;
- ciljna publika;
- brand voice;
- Approved Facts;
- vizuelni identitet;
- testimonials;
- FAQ;
- restrictions;

predstavljaju opšte marketinško znanje firme.

Zato osnovni tok glasi:

```text
WEBSITE + DOCUMENTS + MANUAL INPUT
                ↓
        BRAND INTELLIGENCE
                ↓
          BRAND SNAPSHOT
                ↓
         CAMPAIGN BRIEF
                ↓
         CAMPAIGN PLAN
                ↓
        CONTENT PIECES
                ↓
         CHANNEL OUTPUT
```

Društvene mreže ostaju **prvi implementirani channel**, ali nisu granica domain modela.

Faza 1 treba dokazati social output na malom broju formata, ali platform registry od početka poznaje širi skup mreža. To ne znači da svaki format svake mreže mora odmah imati production generator.

---

## D-CHANNEL-2 — Channel → Platform → Format

Ne koristiti jedan generički string `platform`.

Model:

```text
Channel
   ↓
Platform
   ↓
Format
```

Primjeri:

```text
Channel: SOCIAL
Platform: INSTAGRAM
Format: FEED_POST
```

```text
Channel: SOCIAL
Platform: TIKTOK
Format: SHORT_VIDEO
```

```text
Channel: SOCIAL
Platform: X
Format: TEXT_POST
```

```text
Channel: EMAIL
Platform: GENERIC_EMAIL
Format: NEWSLETTER
```

```text
Channel: WEB
Platform: GENERIC_WEB
Format: LANDING_PAGE
```

Channel je široka marketinška kategorija.

Platform je konkretna distribucijska platforma.

Format je konkretan tip sadržaja.

---

## D-CHANNEL-3 — Početni Channel registry

Početni channels:

```text
SOCIAL
EMAIL
WEB
PAID_AD
PRINT
DIRECT_MESSAGE
```

MVP implementira prvenstveno:

```text
SOCIAL
```

Ostali channels se ne implementiraju u Fazi 1, ali domain model ih ne smije onemogućiti.

---

## D-CHANNEL-4 — Social platform registry mora biti proširiv

Početni social registry:

```text
INSTAGRAM
FACEBOOK
LINKEDIN
X
TIKTOK
YOUTUBE
PINTEREST
THREADS
SNAPCHAT
```

Ne vezivati Campaign Engine za unaprijed zatvoren Python enum koji zahtijeva domain release svaki put kada se doda nova mreža.

Koristiti:

```text
SocialPlatformDefinition
- code
- display_name
- supported_formats[]
- text_constraints
- visual_constraints
- content_rules
- enabled
```

Konfiguracija:

```text
resources/platforms/
├── instagram.yaml
├── facebook.yaml
├── linkedin.yaml
├── x.yaml
├── tiktok.yaml
├── youtube.yaml
├── pinterest.yaml
├── threads.yaml
└── snapchat.yaml
```

Platform registry se može proširiti dodavanjem nove definicije, bez izmjene Campaign Engine domain logike.

---

## D-CHANNEL-5 — Platforma i format imaju različita pravila

Ne tretirati sve social mreže kao Instagram varijante.

Primjeri:

```text
Instagram
- feed post
- carousel
- story
- reel
```

```text
TikTok
- short video
- hook
- video script
- caption
```

```text
X
- text post
- thread
- image post
```

```text
YouTube
- short
- video title
- description
- community post
```

```text
Pinterest
- pin
- title
- description
```

Zato platform-specific pravila dolaze iz `PlatformDefinition` i `FormatDefinition`, ne iz hardkodovanih `if instagram` blokova po application kodu.

---

## D-CHANNEL-6 — Campaign Engine je generički, SocialPost je prvi output tip

Dugoročna domain slika:

```text
CampaignPlan
    ↓
CampaignItem
    ↓
ContentPiece
```

`ContentPiece` je generički campaign output.

Mogući kasniji tipovi:

```text
SocialPost
EmailContent
AdCreative
LandingPageCopy
PrintCreative
DirectMessageContent
```

Faza 1 ne implementira sve.

Faza 1 implementira samo social-first `ContentPiece` varijante potrebne za dokaz Campaign Enginea.

---

## D-CHANNEL-7 — Campaign Brief bira channels/platforms/formats

Campaign Brief ne smije imati samo:

```text
platforms[]
```

nego:

```text
targets[]
```

Svaki target:

```text
channel
platform_code
format_code
```

Primjer:

```json
{
  "channel": "SOCIAL",
  "platform_code": "INSTAGRAM",
  "format_code": "FEED_POST"
}
```

Isti Campaign Plan kasnije može imati više targeta.

U MVP-u se može ograničiti na mali broj targeta po kampanji, ali model ostaje generalan.

---

## D-AI-1 — Provider i model su odvojeni koncepti

API ključ pripada provideru, ne modelu.

UX:

```text
AI PROVIDERS / MODELS

[ OpenAI ]
[ Anthropic ]
[ Google Gemini ]
[ DeepSeek ]
[ OpenRouter ]
[ Custom OpenAI-compatible ]
        ↓
unesi API key
        ↓
TEST CONNECTION
        ↓
učitaj dostupne modele
        ↓
izaberi default model
```

Ako korisnik klikne konkretan model, aplikacija može automatski otvoriti pripadajući provider setup.

Ali credential se čuva jednom po provideru.

---

## D-AI-2 — Provider Registry

Application ne smije znati konkretne provider SDK detalje.

Model:

```text
AIProviderDefinition
- provider_code
- display_name
- adapter_type
- requires_api_key
- supports_model_discovery
- base_url_mode
- enabled
```

Početni provider registry:

```text
OPENAI
ANTHROPIC
GOOGLE
DEEPSEEK
OPENROUTER
OPENAI_COMPATIBLE
```

Kasnije dodavanje provider adaptera ne smije mijenjati Campaign Engine.

---

## D-AI-3 — Model Registry i capabilities

Model nije samo string.

```text
ModelProfile
- provider_code
- model_id
- display_name
- capabilities
- context_window?
- supports_temperature?
- enabled
```

Capabilities:

```text
TEXT_GENERATION
STRUCTURED_OUTPUT
VISION
IMAGE_GENERATION
TOOL_USE
```

Application use-case traži capability:

```text
"treba mi structured text generation"
```

a ne:

```text
"treba mi konkretan GPT model"
```

---

## D-AI-4 — Automatsko model discovery gdje je moguće

Nakon:

```text
provider configured
+
API key valid
```

adapter pokušava učitati dostupne modele ako provider API to pouzdano podržava.

Ako provider nema pouzdano model listing ponašanje:

- koristi održavani registry;
- dozvoli manual model ID;
- jasno označi da lista nije server-discovered.

Ne hardkodovati kompletnu listu modela kroz GUI kod.

---

## D-AI-5 — Jedan API ključ po provideru

Ne:

```text
Model A → API key
Model B → API key
```

nego:

```text
OpenAI
API key: configured

Models:
- A
- B
- C
```

Credential se čuva u OS keyringu preko `SecretStorePort`.

SQLite čuva samo:

```text
provider configured = true
selected model IDs
routing preferences
```

Ne čuva plaintext API key.

---

## D-AI-6 — Test Connection je obavezan UX korak

Provider setup mora imati:

```text
API Key
[________________]

[ TEST CONNECTION ]
```

Rezultat:

```text
✓ Connected
```

ili precizna greška:

```text
INVALID_API_KEY
NETWORK_ERROR
RATE_LIMIT
PROVIDER_ERROR
```

Tek uspješno konfigurisan provider može biti odabran kao aktivni model source.

---

## D-AI-7 — Default model + kasniji per-task routing

MVP Settings:

```text
Default text model
[ provider / model ▼ ]
```

Svi tekstualni use-caseovi ga mogu koristiti.

Arhitektura od početka dopušta kasnije:

```text
Campaign planning   → model A
Post writing        → model B
Revision            → model B
Visual direction    → model C
Image generation    → image model/provider
```

Ne implementirati kompleksan routing UI u prvom slice-u ako nije potreban.

---

## D-AI-8 — OpenAI-compatible adapter

Dodati generički adapter:

```text
OPENAI_COMPATIBLE
```

Setup:

```text
Display name
Base URL
API Key
Model ID
```

Koristi se za:

- kompatibilne cloud providere;
- self-hosted gatewaye;
- lokalne OpenAI-compatible servere.

Za poznate providere Base URL se ne prikazuje korisniku.

---

## D-AI-9 — Provider/model izbor ne smije procuriti u Campaign Engine

Campaign Engine koristi:

```text
TextGenerationPort
```

i model selection/routing policy.

Ne koristi:

```text
OpenAI client
Anthropic client
Gemini client
```

u domain/application poslovnoj logici.


## UI-GATE-1 — UI framework decision gate

Presentation framework je **provisional** dok ne prođe reprezentativni UI spike.

Ne praviti pet ekrana pa tek onda zaključiti da odabrani toolkit zahtijeva rewrite.

Spike mora implementirati isti Post Studio koncept u najmanje:

```text
A) PySide6/QSS/Qt widgets
B) pywebview + HTML/CSS/JS
```

Ne treba graditi funkcionalnu aplikaciju.

Dovoljno je dokazati:

- layout;
- rounded cards;
- facts/status chips;
- warning panel;
- preview panel;
- hover/selected states;
- tipografiju;
- light/dark styling kandidat;
- Windows high-DPI scaling;
- osnovnu interakciju sa Python state-om.

Poređenje:

```text
visual fidelity
implementation complexity
styling flexibility
high-DPI behavior
startup/runtime performance
memory use
file/clipboard/drag-drop integration
background-job integration
packaging
testability
maintenance cost
```

Odluka se dokumentuje kao rezultat spike-a.

Do tada:

```text
Desktop-first = LOCKED
PySide6 = LEADING CANDIDATE
pywebview = CONTROL CANDIDATE
Final Presentation framework = NOT YET LOCKED
```

---

# 6. Ključna promjena: fact-first generisanje

Prethodni pristup:

```text
LLM napiše post
      ↓
sistem pokušava dokazati svaku tvrdnju
```

nije dovoljno pouzdan kao MVP model.

Problem je semantička verifikacija:

- različita formulacija;
- paraphrasing;
- kombinovanje više izvora;
- isti model može proizvesti i ocjenjivati tvrdnju;
- full-text search nije dovoljan.

Zato se pipeline obrće.

---

# 7. Approved Facts

Prije generisanja posta aplikacija odabira konkretan skup činjenica koje model smije koristiti.

Primjer:

```json
{
  "facts": [
    {
      "fact_id": "fact_17_v2",
      "text": "Ordinacija se nalazi u Bijeljini.",
      "status": "APPROVED"
    },
    {
      "fact_id": "fact_42_v1",
      "text": "Ordinacija pruža usluge implantologije.",
      "status": "APPROVED"
    }
  ]
}
```

LLM dobija samo relevantni skup facts za konkretan CampaignItem.

---

# 8. Structured claim mapping

Post generation treba vratiti structured output.

Primjer:

```json
{
  "headline": "Da li je vrijeme da riješite problem nedostajućeg zuba?",
  "caption": "...",
  "claims": [
    {
      "text": "Ordinacija u Bijeljini pruža usluge implantologije.",
      "fact_ids": ["fact_17_v2", "fact_42_v1"],
      "type": "FACT"
    },
    {
      "text": "Zakažite konsultacije.",
      "fact_ids": [],
      "type": "CTA"
    }
  ]
}
```

Vrste:

```text
FACT
CTA
OPINION
CREATIVE
```

MVP validator može deterministički provjeriti:

- da li `fact_id` postoji;
- da li je Approved;
- da li je bio ponuđen modelu;
- da li je superseded;
- da li je soft-deleted;
- da li je claim označen kao FACT bez `fact_ids`.

---

# 9. Deterministički claim linter

Uz fact mapping uvodi se linter bez dodatnog LLM poziva.

Provjerava najmanje:

## Zabranjene / rizične fraze

Primjeri:

```text
najbolji
vodeći
garantujemo
100%
bez rizika
potpuno sigurno
najjeftiniji
jedini
certifikovan
X godina iskustva
```

Lista mora biti konfigurisana po industriji i brendu.

## Numeričke tvrdnje

Regex detekcija:

- cijena;
- procenata;
- godina;
- datuma;
- trajanja;
- količine;
- popusta.

Primjer:

```text
"20 godina iskustva"
```

mora imati odgovarajući Approved Fact.

## Claim status

Početni statusi:

```text
VERIFIED_BY_FACT
UNSUPPORTED
USER_APPROVED
PROHIBITED
NON_FACTUAL
```

---

# 10. Semantička verifikacija — nije MVP garancija

Kasnije se može dodati:

- NLI;
- LLM verifier;
- embedding retrieval;
- secondary model;
- source snippet comparison.

Ali to je dodatni safety sloj.

Ne smije se u dokumentaciji predstavljati kao deterministička garancija tačnosti.

---

# 11. Versioning facts

`ApprovedFact` ne smije biti mutable zapis.

Loše:

```text
fact_12.text = "novi sadržaj"
```

jer istorijski Post može tada retroaktivno referisati drugačiju činjenicu.

Ispravno:

```text
fact_12_v1
     ↓ superseded_by
fact_12_v2
```

Početni model:

```text
ApprovedFact
- id
- logical_fact_id
- version
- content
- source_ref
- status
- created_at
- superseded_by
- deleted_at
```

Brisanje je soft-delete.

---

# 12. Brand Snapshot

Campaign mora znati sa kojim stanjem brenda je nastao.

```text
Campaign
- id
- brand_id
- brand_snapshot_id
- campaign_brief_id
- created_at
```

Snapshot treba uključiti najmanje:

- Brand Profile version
- Brand Voice version
- Audience version
- Visual Identity version
- Approved Fact set/version reference
- Restrictions version

---

# 13. Revision log

Za sadržaj i bitne domain objekte pratiti:

- entity;
- entity_id;
- version;
- timestamp;
- manual / AI;
- provider;
- model;
- prompt_version;
- previous value;
- new value.

Ne praviti enterprise event sourcing.

Ali istorija mora biti dovoljna da se može odgovoriti:

> „Kako je ovaj post nastao?“

---

# 14. Novi redoslijed razvoja — Vertical Slice 1

Najvažnija promjena u odnosu na prethodni dokument:

**Prvi vertical slice NE počinje website ingestom.**

Prvi slice koristi ručno pripremljen fixture.

---

# 15. Vertical Slice 1 — Campaign Engine Proof

Ulaz:

```text
hand-written Brand Fixture
        +
Campaign Brief
```

Izlaz:

```text
Campaign Plan
      ↓
6 Post Drafts
      ↓
Fact Mapping
      ↓
Deterministic Checks
      ↓
Basic Visual Render
      ↓
ZIP Export
```

Bez:

- website crawlera;
- PDF parsera;
- embeddings;
- RAG-a;
- Brand Intelligence extractiona;
- VPS backupa;
- social API-ja;
- automatskog publishinga.

---

# 16. Hand-written Brand Fixture

Prvi test projekat treba imati unaprijed definisan brand.

Primjer strukture:

```json
{
  "brand": {
    "name": "Test Dental Clinic",
    "language": "bs-Latn",
    "voice": {
      "formality": "professional",
      "tone": ["calm", "clear", "friendly"]
    }
  },
  "audiences": [],
  "services": [],
  "facts": [],
  "restrictions": [],
  "visual_identity": {}
}
```

Fixture nije proizvodna funkcionalnost.

To je alat da dokažemo centralnu vrijednost prije komplikovanja sistema.

---

# 17. Vertical Slice 1 — kontrolni A/B test

Obavezno poređenje.

## Kontrola A

Jedan prompt:

```text
Evo informacija o firmi.
Napravi 6 Instagram/Facebook objava za ovu kampanju.
```

## Sistem B

```text
Brand Fixture
   ↓
Campaign Brief
   ↓
Campaign Roles
   ↓
Campaign Plan
   ↓
6 zasebnih post generation poziva
   ↓
Fact constraints
```

---

# 18. Kriteriji da kampanjski sloj ima vrijednost

Ne koristiti samo „sviđa mi se više“.

Mjeriti:

- broj različitih Campaign Roles;
- tematsku različitost;
- duplikate;
- unsupported claims;
- forbidden phrase hits;
- CTA diversity;
- layout validity;
- human rating kampanjske koherentnosti;
- human rating korisnosti;
- human rating brand voice-a.

Ako sistem B ne daje očigledno bolji rezultat od A, zaustaviti širenje scopea i revidirati koncept.

---

# 19. Vertical Slice 2 — Brand Ingest

Tek nakon uspješnog Slicea 1 uvodimo:

```text
Website
   +
PDF/DOCX/XLSX
   +
Manual Notes
        ↓
Source Parsing
        ↓
Brand Intelligence Draft
        ↓
Human Review
        ↓
Approved Brand Snapshot
        ↓
isti Campaign Engine iz Slicea 1
```

Tako ingest ne blokira dokaz centralne vrijednosti.

---

# 20. Vertical Slice 3 — Retrieval

Ako količina izvora opravda potrebu:

```text
Source Documents
      ↓
Chunking
      ↓
Index
      ↓
Relevant Fact Retrieval
      ↓
Campaign/Post Pipeline
```

Prvo:

- metadata filters;
- full-text search.

Embeddings tek kada test pokaže da su potrebni.

---

# 21. Vertical Slice 4 — VPS Backup

Nakon stabilnog lokalnog projekta:

```text
SQLite snapshot
      +
project assets
      +
manifest
      ↓
backup package
      ↓
optional VPS
```

Backup ne smije biti prerequisite za rad aplikacije.

---

# 22. Campaign Brief

Početni model:

```text
Šta promovišemo?
Cilj kampanje?
Publika?
Ponuda?
Kanali/platforme/formati?
Broj sadržajnih jedinica?
Dodatna pravila?
Output language?
Locale?
```

Primjer:

```text
Offer: Dental implants
Goal: Leads
Audience: Adults 35–65 missing one or more teeth
Channels: Instagram, Facebook
Posts: 6
Language: bs-Latn
Special instruction:
Ne isticati cijenu u prvim objavama.
```

---

# 23. Campaign Roles

Campaign Roles su domain podatak.

Početni skup:

```text
PROBLEM
EDUCATION
INSIGHT
BENEFIT
PROOF
TRUST
OBJECTION
MYTH_BUSTING
COMPARISON
BEHIND_THE_SCENES
PRODUCT
OFFER
URGENCY
ACTION
COMMUNITY
STORY
FAQ
```

Svaka uloga ima pravila.

Primjer:

```text
OBJECTION
- adresira konkretan strah ili prepreku;
- ne otvara agresivnom prodajom;
- koristi samo Approved Facts;
- CTA je blag ili nije obavezan.
```

---

# 24. Campaign Templates

Moguće sekvence:

## Lead Generation

```text
PROBLEM
EDUCATION
PROOF
OBJECTION
BENEFIT
OFFER
ACTION
```

## Product Launch

```text
TEASER
PROBLEM
INTRODUCTION
BENEFIT
DEMO
PROOF
OFFER
URGENCY
ACTION
```

## Education

```text
PROBLEM
FAQ
EDUCATION
MYTH_BUSTING
INSIGHT
PROOF
ACTION
```

Za MVP ne treba mnogo template-a.

Bitnije je dokazati da imaju stvarnu korist.

---

# 25. Campaign Plan model

```text
CampaignPlan
- id
- campaign_id
- version
- status
- created_at

CampaignItem
- id
- order
- role
- topic
- goal
- target_audience_id
- facts_needed
- status
```

---

# 26. Campaign Plan Review

Korisnik može:

- reorder;
- edit topic;
- change role;
- delete;
- duplicate;
- replace;
- add;
- regenerate individual item.

Tek nakon:

```text
APPROVE CAMPAIGN PLAN
```

postovi prelaze u generation pipeline.

---

# 27. Post Generation Pipeline

```text
Campaign Item
      ↓
Load Brand Snapshot
      ↓
Select Allowed Facts
      ↓
Apply Role Rules
      ↓
Apply Language/Locale Rules
      ↓
Apply Platform Rules
      ↓
Apply Layout Content Limits
      ↓
LLM Structured Generation
      ↓
Schema Validation
      ↓
Fact-ID Validation
      ↓
Deterministic Linter
      ↓
Post Draft
```

---

# 28. ContentPiece / SocialPost model

```text
ContentPiece
- id
- campaign_item_id
- status
- channel
- platform_code
- format_code
- brand_snapshot_id
- facts_allowed
- claims
- revisions

SocialPostPayload
- headline
- caption
- hook
- body
- cta
- hashtags
- visual_direction
```

---

# 29. Post statuses

```text
PLANNED
GENERATING
DRAFT
NEEDS_REVIEW
APPROVED
REJECTED
EXPORTED
```

---

# 30. Natural-language revisions

Korisnik mora moći promijeniti samo dio posta.

Primjeri:

```text
"Ne spominji cijenu."
"Zadrži caption, napravi kraći headline."
"Ton neka bude topliji."
"CTA neka bude manje prodajan."
```

Quick actions:

```text
SHORTER
LONGER
STRONGER_HOOK
MORE_PROFESSIONAL
MORE_FRIENDLY
LESS_PROMOTIONAL
NEW_CTA
NEW_HEADLINE
NEW_VISUAL_DIRECTION
```

Revizija ne briše prethodni sadržaj.

---

# 31. B/H/S kvalitet — T8

Nije potvrđeno koji model daje najbolji marketing copy na bosanskom/srpskom/hrvatskom.

Ne pretpostavljati.

Testirati rano.

---

# 32. Language Context

Prompt/context mora sadržati najmanje:

```text
output_language
locale
script
preferred_terms
forbidden_terms
regional_vocabulary
tone_examples
```

Primjeri:

```text
output_language: BHS
language_family: BHS
regional_variant: BS
locale: bs-BA
script: LATIN
```

ili:

```text
output_language: BHS
language_family: BHS
regional_variant: SR
locale: sr-Latn
script: LATIN
```

ili:

```text
output_language: English
language_family: EN
regional_variant: NEUTRAL
locale: en
script: LATIN
```

---

# 33. Few-shot examples na ciljnom jeziku

Ne koristiti samo engleske examples sa instrukcijom:

```text
"write in Bosnian"
```

Za brand voice test imati kvalitetne primjere na ciljnom jeziku.

---

# 34. Font test

Svi fontovi koji ulaze u `resources/fonts/` moraju biti provjereni za:

```text
č
ć
š
ž
đ
Č
Ć
Š
Ž
Đ
```

u svim potrebnim težinama:

- Regular
- Medium
- SemiBold
- Bold

Ako font nema glyph coverage, ne smije ući u podržani template set.

---

# 35. Template system — content constraints

Svaki tekstualni slot definiše:

```text
target_chars
max_chars
max_lines
preferred_case
allow_wrap
```

Primjer:

```json
{
  "slot": "headline",
  "target_chars": 35,
  "max_chars": 55,
  "max_lines": 2
}
```

Ovo se prosljeđuje generatoru.

---

# 36. Template system — physical layout constraints

`max_chars` nije dovoljan.

Renderer mora imati:

```text
bounding_box
font_family
min_font_size
max_font_size
line_height
max_lines
alignment
overflow_policy
```

---

# 37. Auto-fit

Renderer pokušava:

```text
max_font_size
      ↓
measure
      ↓
reduce size
      ↓
wrap
      ↓
validate
```

Ako tekst ne stane ni na `min_font_size`:

```text
LAYOUT_VALIDATION_FAILED
```

i headline ide na skraćivanje/regeneraciju.

---

# 38. Visual Engine — hibridni AI + deterministički renderer

Finalni vizual ne treba prepustiti image modelu kao kompletan raster sa tekstom.

Image model može generisati:

- fotografiju;
- ilustraciju;
- pozadinu;
- teksturu;
- product scene;
- edit postojeće slike.

Ali **headline, cijena, CTA, logo, brand boje i ključni tekst moraju ostati stvarni, kontrolisani grafički elementi**.

Osnovni pipeline:

```text
AI/original image
       +
Campaign Visual System
       +
LayoutSpec
       +
real text
       +
logo
       +
brand colours
       ↓
deterministički renderer
       ↓
final creative
```

---

# 39. AI Visual Direction Engine

Ne koristiti ni jednu od dvije krajnosti:

```text
A) svaki post koristi potpuno isti fiksni template
```

niti:

```text
B) LLM za svaki post generiše potpuno novi proizvoljni HTML/CSS
```

Preporučeni model je hibrid:

```text
Brand Snapshot
      ↓
Campaign Brief
      ↓
Campaign Plan
      ↓
AI Visual Director
      ↓
CampaignVisualSystem
      ↓
Post Visual Planner
      ↓
LayoutSpec JSON
      ↓
Schema + Layout Validation
      ↓
HTML/SVG Renderer
      ↓
PNG
```

LLM odlučuje **unutar dozvoljenog dizajnerskog prostora**.

Renderer garantuje da je rezultat tehnički validan.

---

# 40. CampaignVisualSystem

LLM jednom po kampanji predlaže zajednički vizuelni sistem.

Primjer:

```json
{
  "style": ["clean", "clinical", "calm"],
  "primary_layout_family": "split",
  "secondary_layout_family": "full_bleed",
  "headline_scale": "large",
  "image_treatment": "soft_cool_overlay",
  "logo_rule": "bottom_left",
  "cta_rule": "minimal_pill",
  "alignment": "left"
}
```

Svi postovi u kampanji koriste isti vizuelni jezik, ali mogu imati različite layout varijante.

Cilj:

> jedna kampanja izgleda kao jedna porodica, ali ne kao šest identičnih kopija.

---

# 41. LayoutSpec — ograničeni dizajnerski jezik

LLM ne treba vraćati proizvoljan CSS.

Treba vratiti schema-validiran LayoutSpec.

Primjer:

```json
{
  "primitive": "split",
  "image_position": "right",
  "headline_position": "top_left",
  "headline_scale": "large",
  "overlay": "soft_gradient",
  "logo_position": "bottom_left",
  "cta_style": "pill",
  "alignment": "left"
}
```

Dozvoljene primitive mogu uključiti:

```text
HERO
SPLIT
QUOTE
FEATURE
FAQ
STAT
PRODUCT
CTA
TESTIMONIAL
COMPARISON
```

Dozvoljene varijacije:

```text
image left / right
light / dark
headline top / bottom
center / left alignment
overlay / no overlay
compact / spacious
```

Ovim se dobija mnogo vizuelnih kombinacija bez potpunog gubitka kontrole.

---

# 42. Template primitives umjesto velikog broja ručnih template-a

Umjesto 50 kompletno zasebnih šablona, MVP treba početi sa 6–10 dobro testiranih layout primitives.

Primjer:

1. Hero
2. Split
3. FAQ
4. Quote/Testimonial
5. Product/Service
6. CTA
7. Stat
8. Comparison

LLM bira primitive i dozvoljene parametre.

Deterministički renderer ih pretvara u HTML/SVG.

---

# 43. LLM-generisani novi template-i — design-time funkcija

LLM može generisati novi HTML/CSS template, ali **ne kao nekontrolisani runtime korak za svaki post**.

Workflow:

```text
Brand / design brief
       ↓
LLM generiše template candidate
       ↓
render sa kratkim tekstom
       ↓
render sa maksimalnim tekstom
       ↓
B/H/S dijakritici test
       ↓
overflow test
       ↓
human design review
       ↓
approved template library
```

Tek nakon prolaska testova template postaje dostupan produkcijskom rendereru.

Ovo omogućava AI-u da ubrza izradu template biblioteke bez gubitka kontrole.

---

# 44. Layout-aware copy

Copy generator mora znati ograničenja layouta **prije** generisanja teksta.

Primjer konteksta:

```text
Headline slot:
target 28–42 chars
max 55 chars
max 2 lines
large visual hierarchy
```

Tako se izbjegava workflow:

```text
dugačak headline
      ↓
renderer otkrije da ne staje
      ↓
naknadno krpljenje
```

Generation i rendering moraju dijeliti isti `ContentSlotContract`.

---

# 45. ContentSlotContract

Za svaki tekstualni slot:

```text
target_chars
max_chars
max_lines
preferred_case
allow_wrap
font_family
min_font_size
max_font_size
bounding_box
line_height
alignment
overflow_policy
```

`max_chars` je samo preliminarno ograničenje.

Finalna provjera je fizičko mjerenje teksta u rendereru.

---

# 46. Auto-fit i overflow recovery

Renderer:

```text
max_font_size
      ↓
measure
      ↓
wrap
      ↓
reduce font size
      ↓
validate
```

Ako ne stane ni na `min_font_size`:

```text
LAYOUT_VALIDATION_FAILED
```

Zatim application layer može tražiti:

```text
SHORTEN_HEADLINE
```

bez regeneracije cijelog posta.

---

# 47. Početni formati

MVP:

```text
1080 × 1350 — Instagram Feed
1080 × 1080 — Square/Facebook
1080 × 1920 — Story
```

Vertical Slice 1 može početi sa jednim ili dva formata, ali arhitektura mora omogućiti više formata iz istog sadržaja i CampaignVisualSystem-a.

---

# 48. Renderer boundary

LLM:

```text
odlučuje dizajnersku namjeru
```

Naš kod:

```text
garantuje validan layout i render
```

Ne koristiti:

```text
LLM → random HTML string → screenshot
```

kao standardni runtime pipeline.

Standardni pipeline je:

```text
LLM → LayoutSpec JSON → Validator → Renderer → PNG
```

---

# 49. Playwright — arhitektonski spike

Playwright ne vezivati za konkretan Presentation framework niti automatski smještati u glavni desktop proces.

Treba napraviti mali prototip i testirati:

## Opcija A

```text
Desktop process
  ↓
background worker/thread
  ↓
dedicated Playwright instance
```

## Opcija B

```text
Desktop process
  ↓
subprocess/process boundary
  ↓
Playwright worker
  ↓
persistent Chromium
```

Opcija B ima prednost izolacije.

Odluka o Playwright procesu je odvojena od odluke:

```text
PySide6 vs pywebview
```

Isto tako, izbor HTML/CSS renderera za social creative **ne znači automatski** da UI aplikacije mora biti HTML/pywebview.

Ali odluka se donosi tek nakon testiranja:

- stabilnost;
- packaging;
- memory use;
- speed;
- cancellation;
- crash recovery.

---

# 50. Renderer JSON protocol — kandidat

Ako se koristi process isolation:

Request:

```json
{
  "action": "render",
  "template_id": "hero_01",
  "format": "1080x1350",
  "data": {
    "headline": "...",
    "image_path": "...",
    "logo_path": "..."
  }
}
```

Response:

```json
{
  "status": "ok",
  "output_path": "...",
  "warnings": []
}
```

---

# 51. Background jobs

Presentation/UI thread ne smije raditi:

- AI pozive;
- Playwright;
- document parsing;
- image generation;
- rendering;
- backup.

Minimalni modul:

```text
jobs/
├── job_manager.py
├── worker.py
├── progress.py
├── cancellation.py
└── errors.py
```

---

# 52. SQLite

MVP baza:

```text
SQLite
```

Razlog:

- lokalna;
- jednostavna;
- dovoljna za jednog korisnika/projekat;
- backup friendly;
- nema server administracije.

---

# 53. SQLite backup

Ne raditi običan:

```text
copy campaign_studio.db backup/
```

dok je baza otvorena.

Koristiti:

```python
sqlite3.Connection.backup()
```

ili odgovarajući konzistentan snapshot mehanizam.

Pipeline:

```text
LIVE DB
   ↓
SQLite Backup API
   ↓
snapshot.sqlite
   ↓
project package
   ↓
optional VPS
```

---

# 54. Project folders

Ne koristiti naziv brenda kao identitet foldera.

Loše:

```text
projects/dentaland/
```

Ispravno:

```text
projects/
└── 8a07cb43-5118-4aa2-...
```

`project_manifest.json`:

```json
{
  "project_id": "8a07cb43-5118-4aa2-...",
  "display_name": "Dentaland"
}
```

Naziv se može promijeniti.

ID ostaje stabilan.

---

# 55. Project package

Backup mora sadržati stanje iz kojeg se rad može nastaviti.

Primjer:

```text
campaign-project.zip
├── project_manifest.json
├── database_snapshot.sqlite
├── sources/
├── assets/
├── renders/
├── exports/
└── settings/
```

---

# 56. Screenshotovi social objava

Za MVP:

- paste caption;
- originalna slika;
- ručno dodan primjer;
- label „good example“ / „bad example“.

Ne uvoditi OCR samo zbog screenshot inputa.

Vision/OCR kasnije ako se pokaže korisnim.

---



# WEBSHOPAUDIT KAO DONOR PROVJERENIH KOMPONENTI I OBRAZACA

Stari projekat `Rade69/webshop-audit` ne treba nastaviti kao osnovu nove aplikacije. Njegova vrijednost je što već sadrži provjerene tehničke obrasce koji direktno smanjuju rizik Vertical Slicea 2.

Koristimo ga kao **donor**, ne kao arhitekturu koju kopiramo 1:1.

### Granica potvrđenog

U trenutno pregledanom GitHub stanju WebshopAudit-a potvrđen je Qt/PyQt6 GUI sloj sa controllerima, viewmodelima i QThread workerima.

Nije potvrđeno da je ista GitHub codebase završila migracijom na `pywebview + Flask`.

Zato se eventualno ranije iskustvo sa takvom migracijom tretira kao **signal za rizik i razlog za spike**, ali ne kao potvrđena činjenica o trenutnom repozitoriju.

## W1 — HTTP fetch

Postojeći `audit/fetcher.py` već rješava:

- `requests.Session` po threadu;
- timeout;
- retry;
- redirect handling;
- HTTP 429 backoff;
- response metadata;
- paralelni fetch;
- progress callback;
- `stop_event`;
- Playwright fallback.

U novoj aplikaciji ovo ide iza:

```text
PageFetcherPort
├── HttpFetcherAdapter
└── PlaywrightFetcherAdapter
```

Ne vezivati application/domain sloj direktno za `requests` ili Playwright.

## W2 — Playwright se ne prenosi 1:1

Stari kod pali i gasi Chromium za svaki browser fetch. Novi cilj je:

```text
HTTP-first
   ↓
JS/incomplete content detection
   ↓
persistent Playwright worker
   ↓
reuse browser/context
```

Preferirani procesni obrazac, nezavisno od Presentation frameworka:

```text
Desktop application
  ↓
subprocess / process boundary
  ↓
Playwright Worker
  ↓
persistent Chromium
```

Ovo ostaje spike dok se ne izmjere stabilnost, brzina, memorija, cancellation i Windows packaging.

## W3 — Sitemap discovery

Postojeći `audit/sitemap.py` već ima:

```text
robots.txt
   ↓
Sitemap: entries
   +
common sitemap locations
   ↓
sitemap / sitemapindex
   ↓
recursive child sitemaps
```

Ovo je direktno korisno.

Webshop-specifični `filter_product_like_urls()` se ne prenosi kao univerzalna logika. Zamjenjuje ga `URLValueClassifier`.

## W4 — Crawl budget mora djelovati rano

Stari projekat može prikupiti veoma veliki sitemap pa tek onda primijeniti `max_urls`.

Novi sistem treba imati:

```text
discovery_budget
crawl_budget
per_sitemap_budget
max_depth
same_domain_only
```

Cilj je da se ne obrađuju desetine hiljada URL-ova da bi se na kraju izabralo 20.

## W5 — Parser kao donor

Postojeći parser već rješava:

- title;
- meta description;
- H1;
- canonical;
- robots;
- breadcrumb;
- visible text;
- image signals;
- cijene;
- description;
- feature lists;
- specification tables;
- shipping/returns signale;
- osnovni language signal;
- JS-render detection.

Ne prenositi to u jednu veliku webshop dataclass strukturu.

Razdvojiti:

```text
PageMetadataExtractor
MainContentExtractor
CommerceSignalExtractor
ImageAssetExtractor
LanguageSignalExtractor
JSRenderDetector
```

## W6 — Main content princip

Stari parser već pokušava ograničiti analizu na product/content area prije fallback-a na body.

To generalizujemo u:

```text
MainContentLocator
```

Prioritet:

```text
main
article
semantic section
schema-linked content
known content containers
body fallback
```

Time se smanjuju footer/menu/newsletter false-positive signali.

## W7 — JSON-LD structured data

Postojeći `schema_parser.py` već podržava:

- JSON-LD blokove;
- `@graph`;
- Product;
- Offer;
- name;
- description;
- SKU;
- GTIN;
- brand;
- price;
- currency;
- availability.

Za Campaign Studio proširiti na:

```text
Organization
LocalBusiness
ProfessionalService
Restaurant
MedicalBusiness
Dentist
Service
Person
FAQPage
Review
AggregateRating
PostalAddress
OpeningHoursSpecification
ContactPoint
```

Structured data je važan signal, ali ne postaje automatski Approved Fact.

## W8 — FactCandidate

Structured ili tekstualni extraction prvo pravi:

```text
FactCandidate
- id
- value/text
- type
- source_snapshot_id
- source_chunk_id / structured_path
- extraction_method
- confidence_signal
- status=PROPOSED
```

Tek human review kreira `ApprovedFact`.

## W9 — EvidenceSnapshot → SourceEvidence

WebshopAudit već ima važan princip: evidence treba koristiti stvarno extracted podatke, ne duplicirati extraction logiku i ne dumpovati cijeli HTML.

U novoj aplikaciji:

```text
SourceEvidence
- source_snapshot_id
- source_chunk_id
- url
- section_heading
- retrieved_at
- extraction_method
- source_excerpt
```

## W10 — Canonical provenance lanac

```text
Source
  ↓
SourceSnapshot
  ↓
SourceChunk / StructuredDatum
  ↓
FactCandidate
  ↓
ApprovedFact
  ↓
Campaign BrandSnapshot
  ↓
Post Claim
```

Svaki FACT claim mora moći završiti nazad na konkretan izvor.

## W11 — Deterministička Explainability filozofija

Stari `explainability.py` već koristi reason-code pristup umjesto LLM nagađanja.

To direktno prenosimo.

Primjeri reason code-ova:

```text
missing-fact-id
fact-not-approved
fact-superseded
unsupported-number
unsupported-price
unsupported-date
prohibited-claim
layout-overflow
source-stale
source-conflict
```

Human-readable poruka dolazi iz determinističkog mappinga.

## W12 — Ne koristiti LLM kada kod zna uzrok

Loše:

```text
LLM: objasni zašto je cijena možda nepouzdana
```

Dobro:

```text
reason_code = unsupported-price
value = 99 KM

→ "Cijena 99 KM nije povezana ni sa jednom odobrenom činjenicom."
```

LLM generiše i revidira sadržaj; sistemske greške objašnjava kod.

## W13 — Shared pipeline princip

WebshopAudit ima jedan authoritative pipeline koji koriste CLI i GUI.

Princip zadržavamo, ali novi projekat razdvaja use-caseove:

```text
GenerateCampaignPlanUseCase
GeneratePostUseCase
WebsiteIngestionUseCase
BuildBrandIntelligenceUseCase
RenderPostUseCase
BackupProjectUseCase
```

Ne praviti jedan gigantski `pipeline.py`.

## W14 — Background jobs

Iz starog projekta zadržavamo:

```text
phase_changed
progress_updated
log_message
completed
failed
stop/cancel
```

Novi standardni job contract:

```text
Job
- id
- type
- status
- progress
- phase
- cancellable
- error
- started_at
- completed_at
```

Jobovi:

```text
CampaignGenerationJob
WebsiteIngestionJob
ImageGenerationJob
RenderJob
ExportJob
BackupJob
```

Worker ne dira UI direktno. Presentation sloj dobija progress/state događaje kroz framework adapter.

Ako se izabere Qt, to mogu biti Qt signali. Ako se izabere pywebview, isti application/job događaji se prevode kroz odgovarajući bridge. Domain/application sloj ne smije zavisiti od toga.

## W15 — Checkpoint / Resume

WebshopAudit već čuva fetch checkpoint.

Website ingest treba čuvati:

```text
IngestionCheckpoint
- discovered_urls
- selected_urls
- fetched_urls
- failed_urls
- parsed_snapshots
- pending_urls
```

Ako aplikacija stane:

```text
RESUME INGESTION
```

ne mora početi od početka.

## W16 — Human Review Queue

Stari review workflow je koristan kao prethodnik.

Fact statusi:

```text
PROPOSED
APPROVED
REJECTED
SUPERSEDED
```

Post statusi:

```text
DRAFT
NEEDS_REVIEW
APPROVED
REJECTED
EXPORTED
```

Brand Intelligence:

```text
DRAFT
REVIEWED
APPROVED
```

Review mora imati status, note, timestamp, reason/evidence i manual override.

## W17 — Shortlist princip

Korisnik ne treba ručno provjeravati svaki banalni signal.

Brand Intelligence review može grupisati:

```text
HIGH_CONFIDENCE
AMBIGUOUS
CONFLICTING
```

Ali `HIGH_CONFIDENCE` ne znači automatski `ApprovedFact` bez eksplicitnog pravila/odobrenja.

## W18 — Run-to-run diff → SourceSnapshot diff

Stari `run_diff.py` već ima normalized URL matching i razlikuje new/removed/changed stanje.

Novi sistem koristi:

```text
Website Ingestion Run A
          vs
Website Ingestion Run B
```

za:

```text
new page
removed page
changed page
changed price
new service
removed offer
changed phone/address
changed structured data
```

## W19 — Stale Fact detection

Ako se izvor ApprovedFact-a promijeni:

```text
ApprovedFact
   ↓
source changed
   ↓
POTENTIALLY_STALE
```

Ne deaktivirati fact automatski.

Statusi:

```text
CURRENT
POTENTIALLY_STALE
SUPERSEDED
MANUALLY_CONFIRMED
```

Korisnik pregleda promjenu.

## W20 — URL normalizacija

Prenijeti princip normalizacije:

- tracking parametri;
- fragmenti;
- trailing slash;
- www/non-www;
- scheme normalization kada je sigurno.

Original URL, final URL i canonical URL i dalje se čuvaju odvojeno zbog provenance-a.

## W21 — CSV više nije source of truth

WebshopAudit je batch audit alat; CSV je tamo razuman.

Campaign Studio je stateful desktop aplikacija.

Zato:

```text
SQLite repositories
```

su source of truth.

CSV/JSON ostaju export, diagnostic, fixture i interoperability formati.

## W22 — Ne prenositi ProductAuditRow/scoring domain

Ne praviti novi ogromni `BrandAuditRow`.

Koristiti manje domain modele:

```text
Source
SourceSnapshot
SourceChunk
StructuredDatum
FactCandidate
ApprovedFact
VisualAsset
BrandProfile
VisualIdentity
```

Ne prenositi webshop scoring, product-only URL patterns ni hardcoded category inference.

## W23 — Language heuristika nije authoritative

Stari language detector može poslužiti samo kao jeftin signal.

Novi sistem mora imati:

```text
detected_language
requested_output_language
locale
script
preferred_terms
regional_vocabulary
```

## W24 — Multi-provider princip, ne stari provider kod

Stari hardcoded Gemini → DeepSeek fallback ne prenosimo.

Novi sistem koristi:

```text
TextGenerationPort
AIProviderRouter
```

Provider fallback/routing je application policy.

## W25 — Donor test fixture-i

Pregledati i prenijeti relevantne edge-case fixture-e iz starog repozitorija:

```text
sitemap index recursion
robots sitemap discovery
redirects
HTTP failures
European/BAM price formats
malformed JSON-LD
@graph
relative canonical
SPA/JS signals
fetch cancellation
evidence/reason mapping
URL normalization
run-to-run diff
```

Ne kopirati testove naslijepo; prenijeti scenarije koje novi domain zaista koristi.

## W26 — Donor mapa

```text
WebshopAudit                    AI Campaign Studio

audit/fetcher.py          →     HttpFetcherAdapter
                           →     PlaywrightFetcherAdapter

audit/sitemap.py          →     SitemapDiscovery
                           →     URLDiscovery

audit/parser.py           →     PageMetadataExtractor
                           →     MainContentExtractor
                           →     JSRenderDetector

audit/schema_parser.py    →     StructuredDataExtractor

audit/evidence.py         →     SourceEvidence / Provenance

audit/explainability.py   →     DeterministicReasonMapper

audit/pipeline.py         →     Use-case orchestration pattern

AuditWorker/QThread       →     background-job/progress/cancel OBRAZAC
                                   (ne prenosi se Qt zavisnost)

ReviewController          →     human-review state/workflow OBRAZAC
                                   (ne prenosi se GUI controller kod)

audit/run_diff.py         →     SourceSnapshotDiffService
```

## W27 — Šta se eksplicitno NE prenosi

```text
NO webshop scoring model
NO ProductAuditRow kao canonical schema
NO product-only URL patterns kao univerzalni filter
NO CSV kao centralni state
NO globalni use_playwright mode
NO novi Chromium za svaki URL
NO hardcoded category inference
NO hardcoded provider fallback
NO stari GUI controller model ako krši novi MVVM/Use Case dizajn
```

## W28 — Posljedica za Vertical Slice 2

Vertical Slice 2 više nije:

> napraviti crawler od nule.

Nego:

```text
adaptirati postojeće provjerene donor komponente
        +
dodati nove nedostajuće slojeve
```

Nedostajuće ključne stvari:

```text
URL value ranking
early crawl budget
boilerplate removal
cross-page deduplication
SourceSnapshot persistence
SourceChunk / StructuredDatum model
FactCandidate workflow
ApprovedFact versioning
Visual Intelligence extraction
CSS colour/font extraction
asset ranking
Brand Intelligence synthesis
SourceSnapshot diff integration
```

Ovo bitno smanjuje tehnički rizik Website Ingestion faze.

---


# WEBSITE INGESTION — Vertical Slice 2

Website ingestion je važan ulazni modul aplikacije, ali namjerno dolazi tek nakon što Vertical Slice 1 dokaže vrijednost Campaign Enginea.

Ne gradimo „AI agenta koji nasumično surfa sajtom“.

Gradimo kontrolisani ingestion pipeline sa jasnim budžetom, provenance-om i human review tačkom.

---

# Website Ingestion — cilj

Cilj nije arhivirati cijeli website.

Cilj je pronaći i strukturisati **marketinški korisne informacije**:

- čime se firma bavi;
- proizvodi/usluge;
- cijene;
- ponude;
- lokacije;
- kontakt informacije;
- dokazive činjenice;
- ciljna publika kao izvedeni prijedlog;
- FAQ;
- testimonials/case studies;
- brand boje;
- logo;
- fontovi;
- karakteristični vizuelni elementi;
- relevantne fotografije.

Output:

```text
CONTENT INTELLIGENCE
+
VISUAL INTELLIGENCE
+
SOURCE PROVENANCE
```

---

# Website Ingestion pipeline

```text
URL
 ↓
Domain validation
 ↓
robots.txt / sitemap.xml discovery
 ↓
internal link discovery
 ↓
URL ranking/classification
 ↓
crawl budget selection
 ↓
HTTP fetch
 ↓
Playwright fallback samo kada je potrebno
 ↓
content extraction
 ↓
boilerplate removal
 ↓
normalization
 ↓
deduplication
 ↓
asset extraction
 ↓
SourceSnapshot creation
 ↓
SourceChunk creation
 ↓
Brand Intelligence Draft
 ↓
Human Review
 ↓
Approved Facts / Brand Snapshot
```

---

# URL prioritization

Ne tretirati svaki URL isto.

Početne klase:

```text
HIGH VALUE
/about
/services
/products
/pricing
/offers
/case-studies
/testimonials

MEDIUM VALUE
/faq
/blog
/contact
/team
/locations

LOW VALUE / IGNORE
/privacy
/cookies
/terms
/login
/cart
/tag
/archive
/search
```

Klasifikacija može kombinovati:

- URL heuristike;
- sitemap metadata;
- page title;
- kratki content preview;
- jeftin LLM/classifier korak.

---

# HTTP-first, Playwright fallback

Playwright ne treba biti default za svaku stranicu.

Redoslijed:

```text
HTTP GET
  ↓
content present?
  ├─ YES → parse
  └─ NO / JS-heavy → Playwright
```

Prednosti:

- manje memorije;
- brže;
- manje Chromium procesa;
- jednostavnije pakovanje;
- manji rizik od browser-related failurea.

Playwright ostaje važan fallback za JavaScript-heavy sajtove.

---

# Crawl budget

Default kandidat:

```text
max_pages: 20
max_depth: 2
same_domain_only: true
page_timeout: 15s
max_page_size: 3 MB
download_images: selective
```

Korisnik može naknadno:

```text
SCAN MORE PAGES
```

Za shop sa hiljadama proizvoda ne koristiti generalni crawler kao katalog importer.

Za takve slučajeve kasnije dodati poseban product/catalog ingestion modul.

---

# Boilerplate removal

Najveći praktični problem nije skidanje HTML-a nego čišćenje.

Treba ukloniti ili de-prioritizovati:

- navigation;
- footer;
- cookie bannere;
- repeated CTA;
- related posts;
- hidden/mobile duplicate sadržaj;
- tag/archive liste;
- newsletter signup;
- boilerplate legal tekst.

Pipeline:

```text
RAW HTML
  ↓
main content extraction
  ↓
section segmentation
  ↓
boilerplate filtering
  ↓
normalization
  ↓
cross-page deduplication
```

---

# Cross-page deduplication

Isti footer ili CTA može se pojaviti desetine puta.

Koristiti:

- normalized text hashes;
- fuzzy similarity;
- repeated block frequency.

Ako se isti blok pojavljuje na velikom broju stranica, vjerovatno nije primarni brand knowledge signal.

---

# Source provenance

Nikada ne gubiti izvor.

Svaki izvučeni fragment treba znati:

```text
source_id
snapshot_id
url
page_title
section_heading
retrieved_at
content_hash
chunk_id
```

Approved Fact treba referisati konkretan source fragment.

Primjer:

```text
Fact:
"Ordinacija pruža implantologiju."

SourceSnapshot:
snapshot_2026_08_30

SourceChunk:
chunk_00421

URL:
https://example.com/implantologija
```

Time fact-first generation kasnije ima stvarni provenance lanac.

---

# Source snapshots

Website je živ izvor.

Današnji sadržaj može sutra biti promijenjen.

Zato:

```text
Source
  ↓
SourceSnapshot v1
  ↓
SourceChunks
  ↓
ApprovedFacts
```

Novi crawl:

```text
SourceSnapshot v2
```

ne mijenja v1.

Istorijska kampanja ostaje vezana za snapshot koji je postojao u trenutku generisanja.

---

# Visual Intelligence iz websitea

Website ingestion ne treba izvlačiti samo tekst.

Tražiti:

- logo;
- favicon;
- OpenGraph image;
- hero images;
- product images;
- team images;
- CSS custom properties;
- dominant colors;
- declared fonts;
- font weights;
- image style patterns.

Primjer:

```text
--primary: #183A55
--accent: #C8A96A
font-family: Montserrat
```

Ovo ulazi u **Visual Identity Draft**, koji korisnik potvrđuje.

---

# Brand Intelligence Review ekran

Nakon crawla korisnik treba vidjeti šta je pronađeno.

Primjer:

```text
18 stranica pronađeno
11 analizirano
7 preskočeno

✓ O nama
✓ Implantologija
✓ Protetika
✓ Cjenovnik
✓ Kontakt

Predložene činjenice: 34
Proizvodi/usluge: 8
Moguće publike: 3
Brand boje: 4
Logo: pronađen
Font: Montserrat
```

Zatim:

```text
[ PREGLEDAJ BRAND INTELLIGENCE ]
```

Ne koristiti misteriozni „Brand Brain“ koji nešto zaključuje bez transparentnosti.

---

# Website ingestion arhitektura

Predloženi infrastructure modul:

```text
infrastructure/
└── web_ingestion/
    ├── domain_discovery.py
    ├── robots_reader.py
    ├── sitemap_reader.py
    ├── link_discovery.py
    ├── url_normalizer.py
    ├── url_classifier.py
    ├── crawl_budget.py
    ├── http_fetcher.py
    ├── playwright_worker.py
    ├── page_metadata_extractor.py
    ├── main_content_extractor.py
    ├── structured_data_extractor.py
    ├── js_render_detector.py
    ├── boilerplate_filter.py
    ├── deduplicator.py
    ├── asset_extractor.py
    ├── visual_identity_extractor.py
    ├── snapshot_store.py
    ├── checkpoint_store.py
    └── snapshot_diff.py
```

Application pipeline:

```text
WebsiteIngestionPipeline

1. validate domain
2. normalize base URL
3. inspect robots/sitemap
4. discover candidate URLs
5. normalize/deduplicate URLs
6. rank/classify URLs
7. apply discovery + crawl budget
8. HTTP-fetch selected pages
9. detect incomplete/JS-rendered pages
10. re-fetch selected pages through persistent Playwright worker
11. extract page metadata
12. extract structured data (JSON-LD)
13. locate main content
14. clean/normalize content
15. remove boilerplate
16. cross-page deduplicate
17. extract visual assets and visual identity signals
18. create immutable SourceSnapshots
19. create SourceChunks / StructuredData records
20. create FactCandidates
21. save ingestion checkpoint/progress
22. hand off to Brand Intelligence Review
```

---

# Društvene mreže nisu isto što i website ingestion

Za MVP ne zasnivati core workflow na neovlaštenom scraping-u Instagrama/Facebooka/TikToka.

Početni input za postojeći social sadržaj:

```text
paste caption
upload original image
manual notes
import exported data
good/bad example labels
```

Zvanične API integracije mogu se istražiti kasnije ako postanu stvarna potreba.

---


# 57. Knowledge model — Vertical Slice 2+

Kada ingest uđe:

## Structured Brand Profile

Često korišteni podaci:

- overview;
- voice;
- audiences;
- products/services;
- visual identity;
- approved facts;
- restrictions.

## Source Knowledge

Originalni:

- website;
- PDF;
- DOCX;
- XLSX;
- notes;
- captions.

---

# 58. SourceChunk model

```text
SourceChunk
- id
- source_id
- source_snapshot_id
- source_type
- title
- page_or_url
- section_heading
- chunk_text
- checksum
- extraction_method
- retrieved_at
- metadata

StructuredDatum
- id
- source_snapshot_id
- schema_type
- json_path
- field_name
- normalized_value
- raw_value
- checksum
```

---

# 59. Retrieval

Ne uvoditi automatski vektorski DB.

Redoslijed:

1. structured filters;
2. full-text;
3. embeddings ako test pokaže potrebu.

Ako kasnije treba:

- local vector index;
- SQLite extension;
- pgvector tek ako aplikacija postane server/web orijentisana.

---

# 60. AI execution budget — T9

Iako finansijska isplativost nije fokus, AI execution mora biti mjerljiv.

Za svaki poziv logovati:

```text
provider
model
prompt_version
input_tokens
output_tokens
latency
retry_count
context_size
schema_valid
error_type
```

Po kampanji:

```text
number_of_calls
total_input_tokens
total_output_tokens
total_latency
schema_failure_rate
retry_rate
```

Ovo služi za:

- debugging;
- optimizaciju;
- rate limits;
- izbor modela;
- kontrolu prevelikog konteksta.

---

# 61. Prompt versioning

Promptovi ne smiju biti hard-coded kroz view/controller kod.

Struktura:

```text
prompts/
├── campaign_plan/
│   └── v1.yaml
├── post_generation/
│   └── v1.yaml
├── revision/
│   └── v1.yaml
└── visual_direction/
    └── v1.yaml
```

Metadata:

```text
name
version
input_schema
output_schema
model_preference
instructions
examples
language_support
```

---

# 62. Architecture

Preporučena osnova:

# Clean / Hexagonal Core + zamjenjivi Presentation sloj + Use Cases + Ports/Adapters

Ne koristiti klasični:

```text
View / Controller / Services
```

kao jedinu glavnu organizaciju.

MVVM je poželjan ako se izabere Qt, ali **nije domain/application arhitektonska obaveza** ako UI spike izabere HTML/pywebview Presentation.

---

# 63. Presentation

Presentation sloj mora ostati zamjenjiv dok UI framework gate nije zatvoren.

Framework-neutralna jezgra:

```text
presentation/
├── state/
├── presenters_or_viewmodels/
├── ui_models/
└── contracts/
```

Nakon spike-a dodaje se jedan konkretan adapter, npr.:

```text
presentation_qt/
```

ili:

```text
presentation_webview/
```

Presentation zna:

- šta korisnik radi;
- šta prikazati;
- progress;
- validation feedback;
- UI state.

Ne zna:

- konkretan AI provider;
- SQLite implementacione detalje;
- Playwright implementacione detalje;
- backup protokol.

Ako se izabere PySide6, mogu se koristiti ViewModel + signal obrasci.

Ako se izabere pywebview, isti application state/use-case contract ostaje, a mijenja se samo Presentation adapter.

---

# 64. Application

Use cases:

```text
application/
├── brands/
├── campaigns/
├── posts/
├── orchestration/
├── visual_direction/
├── web_ingestion/
├── rendering/
├── export/
└── backup/
```

Primjeri:

```text
CreateCampaign
GenerateCampaignPlan
ApproveCampaignPlan
GeneratePost
RevisePost
ApprovePost
RenderPost
ExportCampaign
BackupProject
```

---

# 65. Domain

```text
domain/
├── brand/
├── campaign/
├── post/
├── claims/
├── assets/
├── templates/
└── common/
```

Domain ne smije importovati:

```text
PySide6 / PyQt6
pywebview
OpenAI/provider SDK
playwright
sqlite implementation
SFTP
```

---

# 66. Ports

```text
ports/
├── ai.py
├── image_generation.py
├── repositories.py
├── rendering.py
├── sources.py
├── retrieval.py
├── storage.py
└── backup.py
```

---

# 67. Infrastructure

```text
infrastructure/
├── ai/
├── database/
├── rendering/
├── web_ingestion/
├── sources/
├── retrieval/
├── filesystem/
└── backup/
```

---

# 68. Predložena struktura repozitorija

```text
ai_campaign_studio/

├── domain/
│   ├── brand/
│   ├── campaign/
│   ├── post/
│   ├── claims/
│   ├── assets/
│   ├── templates/
│   └── common/
│
├── application/
│   ├── brands/
│   ├── campaigns/
│   ├── posts/
│   ├── orchestration/
│   ├── visual_direction/
│   ├── web_ingestion/
│   ├── rendering/
│   ├── export/
│   └── backup/
│
├── ports/
│   ├── ai.py
│   ├── image_generation.py
│   ├── repositories.py
│   ├── rendering.py
│   ├── sources.py
│   ├── retrieval.py
│   ├── storage.py
│   └── backup.py
│
├── infrastructure/
│   ├── ai/
│   ├── database/
│   ├── rendering/
│   ├── web_ingestion/
│   ├── sources/
│   ├── retrieval/
│   ├── filesystem/
│   └── backup/
│
├── presentation/
│   ├── state/
│   ├── presenters_or_viewmodels/
│   ├── ui_models/
│   └── contracts/
│
├── presentation_adapter/   # finalno ime nakon UI spike-a
│
├── jobs/
├── prompts/
├── resources/
│   ├── templates/
│   ├── fonts/
│   └── icons/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   └── fixtures/
│
├── main.py
└── pyproject.toml
```

---

# 69. Golden testovi — revidirano

Golden tests se dijele na dvije kategorije.

---

# 70. Determinističke metrike

Automatski mjeriti:

```text
unique_role_count
duplicate_topic_count
unsupported_fact_claim_count
forbidden_phrase_hits
numeric_claim_violations
missing_fact_ids
headline_overflow_count
layout_failure_count
schema_failure_count
```

---

# 71. Caption similarity

Može se mjeriti embedding similarity između captiona.

Ali prag se NE zaključava unaprijed.

Proces:

1. prikupiti stvarne dobre/loše kampanje;
2. izračunati similarity;
3. vidjeti raspodjelu;
4. tek tada definisati prag.

Npr. `0.75` može biti kandidat, ali nije odluka bez kalibracije.

---

# 72. Human evaluation

Ne glumiti da se sve može automatizovati.

Čovjek ocjenjuje:

- brand voice;
- prirodnost jezika;
- marketinšku uvjerljivost;
- campaign coherence;
- korisnost;
- repetitivnost;
- kvalitet CTA-a;
- vizuelnu konzistentnost.

Može koristiti skalu 1–5.

---

# 73. Minimalni human evaluation obrazac

Za svaku kampanju:

```text
Brand fit:              1 2 3 4 5
Language naturalness:   1 2 3 4 5
Campaign coherence:     1 2 3 4 5
Post diversity:         1 2 3 4 5
Usefulness:             1 2 3 4 5
Visual consistency:     1 2 3 4 5
```

Uz komentar.

---

# 74. Test fixtures

Početni test projekti:

```text
Dental Clinic
Restaurant
Furniture Shop
B2B Service
```

Prvi Slice može početi sa jednim kvalitetnim fixture-om.

Kasnije širiti.

---

# 75. Tehnički rizici

## T1 — Campaign layer ne daje dovoljno bolji rezultat

Najvažniji rizik.

Zato se testira prije ingest sistema.

## T2 — Fact-first constraints previše sputavaju copy

Moguće je da strogo ograničavanje facts smanji kreativnost.

Treba razlikovati:

```text
FACTUAL CLAIM
```

od:

```text
CREATIVE / OPINION / CTA
```

## T3 — Campaign diversity

Model može i uz roles ponavljati istu temu.

Mjeriti.

## T4 — Brand voice

Generički:

```text
professional, friendly
```

nije dovoljan rezultat.

Treba testirati sa stvarnim example copyjem.

## T5 — Visual consistency

Različite AI slike mogu izgledati kao različiti brendovi.

Template i asset policy trebaju čuvati konzistentnost.

## T6 — Background workload

Presentation UI mora ostati responzivan.

## T7 — Project portability

Backup/restore testirati rano.

## T8 — B/H/S jezički kvalitet

Nije potvrđeno:

- koji model je najbolji;
- koliko prirodno piše;
- da li lokalizuje marketinške fraze;
- kako radi sa regionalnim terminima.

Mora biti stvarni test, ne pretpostavka.

## T8b — BHS regionalna terminologija

Rizik:

Model može pisati gramatički ispravan lokalni tekst, ali miješati bosansku, srpsku i hrvatsku terminologiju na način koji zvuči neprirodno ciljnoj publici.

Mitigacija:

- jedan `BHS` language family;
- eksplicitan `regional_variant`;
- preferred/forbidden terms;
- regional vocabulary;
- few-shot primjeri po varijanti;
- human evaluation.

Ne tretirati ovu razliku kao tri odvojene aplikacijske lokalizacije.

## T9 — AI execution/context budget

Prevelik broj poziva i kontekst može uticati na:

- latency;
- rate limit;
- failure rate;
- debugging;
- kvalitet.

Mjeriti od Slicea 1.

## T10 — Playwright integration

Treba testirati:

- threading;
- subprocess;
- persistent Chromium;
- packaging;
- cancellation;
- crash recovery.

## T11 — Template text overflow

Obavezan layout validator.

## T12 — Brand ingest quality

Tek Slice 2.

Website extraction može pokupiti:

- menu;
- cookie tekst;
- footer;
- zastarjele informacije;
- SEO filler.

Brand Intelligence mora biti human-reviewed.

---


# Dodatni tehnički rizici nakon kasnijih revizija

## T13 — Visual Direction postaje previše slobodan

Ako LLM ima previše layout opcija, kampanja gubi konzistentnost.

Mitigacija:

- schema-validiran CampaignVisualSystem;
- ograničene layout primitive;
- dozvoljene varijante;
- human review template biblioteke.

## T14 — Visual Direction postaje previše krut

Ako je dizajnerski jezik preuzak, sve kampanje izgledaju isto.

Mitigacija:

- više layout primitives;
- campaign-level style selection;
- AI-generated design-time templates;
- odvojene visual families po brendu.

## T15 — Website crawler bira pogrešne stranice

Sitemap može sadržati hiljade nebitnih URL-ova.

Mitigacija:

- crawl budget;
- URL ranking;
- heuristike;
- human „scan more / exclude“ kontrola.

## T16 — Boilerplate postane lažna činjenica

Footer, stari CTA ili legacy page može završiti kao Brand Fact.

Mitigacija:

- cross-page dedup;
- source transparency;
- human approval;
- snapshot + URL provenance.

## T17 — Website facts zastare

Marketing informacije se mijenjaju.

Mitigacija:

- immutable SourceSnapshots;
- fact versioning;
- explicit retrieved_at;
- opcioni future recrawl/diff.


## T18 — Preveliko oslanjanje na donor kod

Stari WebshopAudit je pravljen za product audit, ne za Brand Intelligence.

Mitigacija:

- reuse kroz portove/adapters;
- ne prenositi ProductAuditRow/scoring model;
- donor modul mora imati regression test prije integracije.

## T19 — Playwright fallback postane bottleneck

Mitigacija:

- HTTP-first;
- JS confidence signal;
- selective browser fallback;
- persistent Chromium;
- ograničena browser queue.

## T20 — Structured data i vidljivi sadržaj se ne slažu

Mitigacija:

- čuvati oba izvora;
- conflict detection;
- FactCandidate status `CONFLICTING`;
- obavezni human review.

## T21 — Snapshot diff proizvodi previše šuma

Mitigacija:

- relevant-block hashes;
- field-level diff;
- ignorisati boilerplate promjene;
- stale upozorenje vezati za konkretne facts.


## T22 — Desktop UI visual fidelity / framework mismatch

Rizik:

Izabrani desktop UI toolkit može funkcionalno raditi, ali zahtijevati previše custom stylinga, painting workarounda ili specifičnih widgeta da bi Post Studio i ostali ekrani dostigli željeni vizuelni standard.

To je odvojeno od T6:

```text
T6 = responsiveness/background workload
T22 = visual fidelity + Presentation framework cost
```

Mitigacija:

prije ozbiljne izgradnje UI-a napraviti reprezentativni **Post Studio UI spike** u najmanje dvije varijante:

```text
PySide6/QSS
vs
pywebview + HTML/CSS/JS
```

Spike mora testirati:

- rounded cards;
- chips/badges;
- warning panel;
- preview;
- hover/selected states;
- tipografiju;
- spacing;
- high-DPI scaling;
- light/dark styling kandidat;
- Python state bridge;
- background progress update;
- packaging prototip.

Odluka:

```text
PASS PYSIDE6
PASS PYWEBVIEW
```

ili, ako oba imaju ozbiljan problem:

```text
REOPEN UI FRAMEWORK DECISION
```

Ne nastavljati punu implementaciju pet MVP ekrana prije ovog gate-a.


# 76. Error taxonomy

Razlikovati:

```text
NETWORK_ERROR
RATE_LIMIT
PROVIDER_ERROR
AI_SCHEMA_ERROR
MISSING_FACT
PROHIBITED_CLAIM
LAYOUT_VALIDATION_ERROR
RENDER_ERROR
DATABASE_ERROR
BACKUP_ERROR
SOURCE_PARSE_ERROR
SITEMAP_ERROR
CRAWL_BUDGET_EXCEEDED
PLAYWRIGHT_WORKER_ERROR
STRUCTURED_DATA_ERROR
SOURCE_CONFLICT
STALE_FACT_WARNING
CHECKPOINT_ERROR
UI_BRIDGE_ERROR
UI_RENDERING_ERROR
```

Ne prikazivati samo:

```text
Something went wrong
```

ako znamo stvarni problem.

---

# 77. UI — framework gate i prvi MVP ekrani

Vertical Slice 1 ne treba kompletan finalni UI.

Prije implementacije svih ekrana:

```text
POST STUDIO UI SPIKE
        ↓
PySide6 vs pywebview
        ↓
framework decision
        ↓
MVP presentation implementation
```

Tek nakon zatvaranja gate-a implementirati:

1. Fixture/Brand selector
2. New Campaign Brief
3. Campaign Plan
4. Campaign Board
5. Post Studio
6. Export

Brand Setup ekran dolazi u Slice 2.

Funkcionalni zahtjevi ovih ekrana moraju ostati isti bez obzira koji Presentation adapter pobijedi.

---

# 78. Campaign Brief ekran

```text
NEW CAMPAIGN

What are you promoting?
[________________________]

Goal
( ) Awareness
( ) Education
( ) Leads
( ) Sales
( ) Launch

Audience
[________________________]

Offer
[________________________]

Posts
[ 6 ]

Targets
[x] Social / Instagram / Feed Post
[x] Social / Facebook / Feed Post

Language
[ Bosnian ]

Additional rules
[________________________]

[ BUILD CAMPAIGN PLAN ]
```

---

# 79. Campaign Plan ekran

```text
01 PROBLEM
   Šta se dešava kada dugo nedostaje zub?

02 EDUCATION
   Šta je implantat?

03 OBJECTION
   Da li ugradnja boli?

...

[ reorder ]
[ edit ]
[ replace ]
[ delete ]
[ add ]

[ APPROVE PLAN ]
```

---

# 80. Campaign Board

```text
CAMPAIGN                       4 / 6 APPROVED

POST 01     POST 02     POST 03
Problem     Education   Objection
Approved    Review      Draft
```

---

# 81. Post Studio

Lijevo:

- preview

Desno:

- headline;
- caption;
- CTA;
- facts used;
- warnings;
- quick edits.

Poseban panel:

```text
FACTS USED

✓ fact_17_v2
✓ fact_42_v1
```

Warnings:

```text
⚠ Number found without Approved Fact
```

---

# 82. Export

Vertical Slice 1:

```text
ZIP
├── post-01/
│   ├── feed.png
│   └── caption.txt
├── post-02/
...
└── campaign.json
```

Kasnije:

- CSV
- PDF preview
- multiple formats

---

# 83. Referentne aplikacije

Ovo ostaje eksplicitno dokumentovano.

Ne kopiramo njihov kod niti UI.

Koristimo njihove javno vidljive workflowe kao reference.

---

# 84. Jasper

Referenca za:

- Knowledge Base;
- Brand Voice;
- Audience;
- Style Guide;
- Product knowledge;
- campaign brief;
- grounded content.

Ključna lekcija:

```text
FACTS
≠
BRAND VOICE
≠
AUDIENCE
≠
VISUAL IDENTITY
≠
CAMPAIGN
```

Naš sistem dodatno pojačava provenance kroz `fact_id`.

---

# 85. Virlya

Referenca za:

- jednostavan onboarding;
- prirodni jezik;
- campaign plan;
- human review;
- download bez obaveznog publishinga.

Ključna UX lekcija:

Korisnik može reći:

```text
"Sljedeće sedmice imamo tri slobodna termina."
```

Sistem koristi kontekst brenda i predlaže kampanju.

---

# 86. Chrombyte

Referenca za:

- website + logo + product catalog;
- content planner;
- različite načine početka kampanje.

Potencijalni UX:

```text
[ Brzo napravi kampanju ]
[ Pomozi mi da osmislimo kampanju ]
[ Imam svoj plan ]
```

Sva tri workflowa na kraju stvaraju isti `CampaignPlan`.

---

# 87. Lapis

Referenca za:

- creative iteration;
- partial regeneration;
- natural-language revisions;
- variants;
- audience-specific creative.

Ključna lekcija:

Ne imati samo:

```text
REGENERATE
```

nego:

```text
Shorter
Warmer
Stronger Hook
Different CTA
Change Headline Only
```

---

# 88. Moonya AI

Početni referentni proizvod.

Koristan za ideje:

- website → brand context;
- social content generation;
- visual generation;
- approval.

Namjerno NE preuzimamo:

- scheduler;
- publishing;
- unified inbox;
- DM automation.

Moonya služi i kao granica:

> naš proizvod nije social media management SaaS.

---

# 89. Mapa referenci

| Naš dio | Referenca |
|---|---|
| Brand Knowledge | Jasper |
| Brand Voice | Jasper |
| Simple onboarding | Virlya |
| Website → brand | Virlya + Chrombyte |
| Product catalog | Chrombyte |
| Campaign brief | Jasper |
| Campaign plan | Jasper + Chrombyte |
| Human plan review | Virlya |
| Post iteration | Lapis |
| Partial regeneration | Lapis |
| Natural-language edits | Lapis |
| Download without publishing | Virlya |
| Scope boundary | Moonya |
| Evidence/Claims | Jasper kao polazna tačka + naša fact-first verzija |

---

# 90. Šta ne graditi prije završetka Slicea 1

Eksplicitna zabrana scope creep-a:

```text
NO website crawler
NO PDF parsing
NO embeddings
NO RAG
NO VPS backup
NO social API
NO publishing
NO scheduler
NO inbox
NO analytics
NO OCR
NO video generation
NO multi-agent framework
```

osim ako je nešto minimalno potrebno samo za test harness.

---

# 91. Acceptance criteria — Vertical Slice 1

Slice 1 je gotov kada:

1. ručni Brand Fixture se učita;
2. Campaign Brief se može kreirati;
3. Campaign Plan se generiše kao validan structured object;
4. plan ima različite Campaign Roles;
5. korisnik može korigovati/reorderovati plan;
6. plan se može odobriti;
7. svaki post se generiše zasebno;
8. svaki FACT claim referiše dozvoljene `fact_id`;
9. linter detektuje bar osnovne zabranjene/numeričke tvrdnje;
10. headline dobija layout constraints;
11. renderer generiše najmanje jedan ispravan vizualni format;
12. layout overflow se detektuje;
13. kampanja se exportuje u ZIP;
14. AI telemetry se bilježi;
15. A/B kontrolni prompt i Campaign Engine output mogu se porediti;
16. Post Studio UI spike je izveden u PySide6 i pywebview kandidatu;
17. finalni Presentation framework je odabran na osnovu zabilježenih kriterija, ne unaprijed.

---

# 92. Exit criteria — prije Slicea 2

Ne prelaziti na ingest ako nije potvrđeno:

- campaign output je smisleno bolji od single-prompt kontrole;
- postovi nisu samo parafraze;
- fact-first sistem ne ubija copy;
- B/H/S output je prihvatljiv;
- template sistem može pouzdano smjestiti tekst;
- UI framework gate je zatvoren;
- odabrani Presentation framework zadovoljava vizuelni standard bez neprihvatljivog workaround troška;
- ukupni AI pipeline je tehnički stabilan.

---

# 93. Acceptance criteria — Slice 2

Tek tada:

1. website se može ingestovati;
2. PDF/DOCX/XLSX se mogu parsirati;
3. Brand Intelligence Draft se generiše;
4. svaka extracted činjenica ima source reference;
5. korisnik može odobriti/odbiti činjenice;
6. odobreni snapshot ulazi u već dokazani Campaign Engine;
7. stari campaign snapshot ostaje nepromijenjen nakon kasnijeg uređivanja brenda.

---

# 94. Sigurnost API ključeva

Ne držati ključ u plain-text settings JSON-u.

Preferirati OS keyring.

Odvojiti:

```text
local project data
AI provider payload
VPS backup payload
```

Korisnik treba znati šta napušta lokalni računar.

---

# 95. Cache

Od Slicea 2:

Cache kandidati:

- website extraction;
- PDF parse;
- source chunks;
- embeddings;
- Brand Intelligence draft;
- visual identity analysis.

Koristiti checksum.

Ne obrađivati nepromijenjen dokument ponovo bez razloga.

---

# 96. Logging

Kategorije:

```text
UI
APPLICATION
DOMAIN
AI
RENDER
DATABASE
SOURCE
BACKUP
```

Ne logovati API ključeve.

Za AI pozive logovati metadata, ne nužno puni osjetljivi sadržaj.

---

# 97. Minimalni test stack

## Unit

- domain rules;
- claim state;
- fact versioning;
- Campaign Roles;
- template constraints;
- linter;
- path/manifest.

## Integration

- Presentation contract / application bridge;
- background job events nezavisni od UI frameworka;
- SQLite repository;
- AI adapter mock;
- renderer;
- ZIP export;
- SQLite backup;
- sitemap discovery;
- HTTP fetch + retry;
- JSON-LD extraction;
- main-content extraction;
- JS-render detection;
- ingestion checkpoint/resume;
- SourceSnapshot persistence;
- SourceSnapshot diff.

## Golden

- Campaign Fixture A/B;
- deterministic metrics;
- human evaluation.

## UI framework spike tests

Za oba Presentation kandidata zabilježiti isti test paket:

- Post Studio mockup fidelity;
- 100% / 125% / 150% Windows scaling;
- resize/minimum window behavior;
- drag-and-drop lokalne slike;
- clipboard copy/paste;
- native file dialog;
- progress update iz background joba;
- cancellation;
- startup time;
- memory footprint;
- packaging/install smoke test.

Ne proglašavati pobjednika samo na osnovu screenshot izgleda.

## Donor regression fixtures

Prenijeti/reformulisati relevantne WebshopAudit scenarije za:

- sitemap index recursion;
- robots sitemap discovery;
- redirects;
- HTTP errors;
- European/BAM price formats;
- malformed JSON-LD;
- `@graph`;
- relative canonical;
- JS-render heuristics;
- cancellation;
- evidence/reason mapping;
- URL normalization;
- source diff.

---

# 98. Tehnički stack

## Desktop

- Python
- desktop-first architecture

## Presentation — provisional do UI spike-a

Kandidat A:

- PySide6
- QSS / Qt widgets / po potrebi ograničen custom painting

Kandidat B:

- pywebview
- HTML/CSS/JS
- lokalni Python bridge
- Flask samo ako spike pokaže da je potreban

Finalni izbor nije dio unaprijed zaključanog stacka.

## Internationalization

UI koristi centralni translation resource sloj:

```text
resources/i18n/en.json
resources/i18n/bhs.json
```

Ne vezivati translation sistem za Qt `tr()` ili web framework i18n biblioteku prije UI gate-a.

Framework adapter može interno mapirati centralne translation keys na konkretan toolkit.


Napomena:

```text
App UI framework
≠
social creative renderer
≠
website-ingestion browser worker
```

To su tri odvojene tehničke odluke i ne smiju se spojiti samo zato što dvije ili tri mogu koristiti HTML/Chromium.

## Validation

- Pydantic

## Database

- SQLite

## Rendering

Kandidat:

- HTML/CSS + Playwright

ali tek nakon spike-a.

## Image processing

- Pillow

## Documents — Slice 2

- PyMuPDF
- python-docx
- openpyxl

## Website — Slice 2

- `requests`/HTTP extraction prvo
- BeautifulSoup/lxml parsing
- postojeći WebshopAudit fetch/sitemap/parser kod kao donor
- Playwright persistent-worker fallback
- structured JSON-LD extraction
- checkpoint + immutable snapshot persistence

## AI

- provider adapters
- structured outputs

## Backup

- SQLite backup API
- package
- optional HTTPS/SFTP adapter

---

# 99. Trenutno zaključane i gate-ovane odluke

**D1.** Desktop-first.  
**D2.** UI framework nije konačno zaključan; PySide6 je vodeći kandidat, pywebview kontrolna alternativa do Post Studio UI spike-a.  
**D3.** Local-first.  
**D4.** SQLite MVP.  
**D5.** VPS samo kao opcioni backup.  
**D6.** Clean/Hexagonal core + zamjenjivi Presentation sloj; MVVM se koristi ako odgovara izabranom UI frameworku.  
**D7.** Use Cases + Ports/Adapters.  
**D8.** Campaign Plan prije Post Generation.  
**D9.** Human approval.  
**D10.** Fact-first content generation.  
**D11.** Immutable/versioned Approved Facts.  
**D12.** Campaign Brand Snapshot.  
**D13.** Deterministički claim checks u MVP-u.  
**D14.** Semantički verifier nije MVP garancija.  
**D15.** Vertical Slice 1 koristi ručni Brand Fixture.  
**D16.** Website/PDF ingest tek Slice 2.  
**D17.** Layout constraints su dio generation + renderer pipeline-a.  
**D18.** B/H/S kvalitet se rano mjeri.  
**D19.** Golden tests = deterministic + human evaluation.  
**D20.** Playwright integracija prolazi spike prije zaključavanja.  
**D21.** SQLite backup API, ne file copy.  
**D22.** Project folder koristi UUID.  
**D23.** OCR nije MVP zahtjev.  
**D24.** AI execution telemetry od prvog slicea.  
**D25.** Bez automatskog publishinga, schedulera, inboxa i analyticsa u MVP-u.  
**D26.** Vizuelni sistem koristi CampaignVisualSystem + LayoutSpec + deterministički renderer.  
**D27.** LLM ne generiše proizvoljan runtime HTML/CSS za svaki post kao standardni put.  
**D28.** LLM može generisati nove template kandidate u design-time workflowu uz automatske i ljudske provjere.  
**D29.** Copy generation dobija layout constraints prije generisanja teksta.  
**D30.** Website ingestion je HTTP-first sa Playwright fallbackom.  
**D31.** Website crawler koristi crawl budget i URL prioritization.  
**D32.** Svaki web-derived fact mora zadržati SourceSnapshot/SourceChunk provenance.  
**D33.** Website source snapshots su immutable.  
**D34.** Website ingestion izvlači i Content Intelligence i Visual Intelligence.  
**D35.** Social-network scraping nije core MVP zavisnost.  
**D36.** WebshopAudit se koristi kao donor, ne kao nova codebase osnova.  
**D37.** Postojeći fetch/sitemap/parser obrasci se adaptiraju iza portova/adapters granice.  
**D38.** `EvidenceSnapshot` filozofija se prenosi u SourceEvidence/Provenance model.  
**D39.** Deterministička explainability ima prednost nad LLM objašnjenjima za reason code-ove.  
**D40.** Website ingestion podržava checkpoint/resume.  
**D41.** SourceSnapshot diff se koristi za buduću detekciju potencijalno zastarjelih činjenica.  
**D42.** JSON-LD je prioritetni FactCandidate signal, ali ne postaje automatski ApprovedFact.  
**D43.** CSV/JSON su export/diagnostic formati; SQLite ostaje source of truth.  
**D44.** ProductAuditRow/scoring/category inference se ne prenose u novi domain.  
**D45.** Worker/progress/cancellation obrazac se prenosi u novi JobManager bez Qt zavisnosti u application sloju.  
**D46.** Post Studio UI fidelity spike je obavezan prije pune implementacije MVP Presentation sloja.  
**D47.** Desktop-first je zaključan, ali konkretan UI toolkit nije.  
**D48.** Donor QThread/ReviewController stavke znače prenos obrasca, ne prenos Qt GUI koda.  
**D49.** UI ima samo `EN` i `BHS` lokalizaciju.  
**D50.** `BHS` je jedan lokalni jezički sistem sa `NEUTRAL/BS/SR/HR` regionalnim varijantama za generisani sadržaj.  
**D51.** `AppLocale` i `ContentLanguageContext` su odvojeni modeli.  
**D52.** BHS MVP koristi latinicu; ćirilica nije MVP zahtjev.  
**D53.** Svi UI stringovi koriste translation keys iz `resources/i18n/`, bez hardkodovanja u viewovima.  
**D54.** Regionalna varijanta smije mijenjati terminologiju/stil, ali ne facts/provenance.  
**D55.** Brand Intelligence i Campaign Engine su channel-agnostic; društvene mreže su prvi prioritetni output.  
**D56.** Campaign target koristi `Channel → Platform → Format`.  
**D57.** Social platforme se učitavaju kroz proširivi registry, ne kroz zatvoren hardcoded enum.  
**D58.** Početni social registry uključuje Instagram, Facebook, LinkedIn, X, TikTok, YouTube, Pinterest, Threads i Snapchat.  
**D59.** `ContentPiece` je generički campaign output; SocialPost je prvi MVP payload tip.  
**D60.** API ključ pripada provideru, ne modelu.  
**D61.** Provider/model izbor ide kroz Provider Registry + Model Registry.  
**D62.** Provider setup mora imati Test Connection.  
**D63.** API ključevi se čuvaju u OS keyringu, ne SQLite/config JSON-u.  
**D64.** Model capabilities određuju kompatibilnost use-casea.  
**D65.** OpenAI-compatible adapter je podržana generička ekstenziona tačka.  
**D66.** Campaign Engine ne zavisi od konkretnog providera/modela.

---

# 100. Šta još NIJE zaključano

Ovo su otvorene tehničke odluke koje zahtijevaju test ili mjerenje:

**Q1.** Koji AI model daje najbolji B/H/S marketing copy za naš tip sadržaja?  
**Q2.** Koliko strogo fact-first ograničenje utiče na kreativnost?  
**Q3.** Koji similarity prag zaista označava preveliku repetitivnost?  
**Q4.** Playwright thread ili subprocess worker?  
**Q5.** HTML/CSS ili SVG kao primarni renderer?  
**Q6.** Kada embeddings stvarno poboljšavaju retrieval u odnosu na structured/full-text pristup?  
**Q7.** Koliko campaign roles/template-a je dovoljno za MVP?  
**Q8.** Koji skup layout primitives daje najbolji balans konzistentnosti i varijacije?  
**Q9.** Da li jedan renderer treba podržavati sve layout primitive ili je sigurnije imati mali broj renderer adaptera po primitive/family tipu?  
**Q10.** Koliko slobode LLM smije imati unutar LayoutSpec-a prije nego što kvalitet postane nestabilan?  
**Q11.** Koji URL-ranking pristup najbolje bira marketinški korisne stranice bez nepotrebnih LLM poziva?  
**Q12.** Koja biblioteka/algoritam najbolje uklanja boilerplate za naše tipične sajtove?  
**Q13.** Koliki dio starog fetcher/sitemap koda možemo prenijeti bez rewrite-a nakon uvođenja portova?  
**Q14.** Koji structured-data tipovi daju dovoljno pouzdan FactCandidate signal?  
**Q15.** Kako kalibrisati JS fallback da Playwright ne postane bottleneck?  
**Q16.** Koji nivo SourceSnapshot diff-a daje korisna stale-fact upozorenja bez šuma?  
**Q17.** Da li renderer i web-ingestion Playwright trebaju odvojene worker procese?  
**Q18.** Da li PySide6 može isporučiti Post Studio vizuelni standard uz prihvatljivu količinu custom UI koda?  
**Q19.** Da li pywebview + HTML/CSS/JS daje dovoljno bolju vizuelnu fleksibilnost da opravda dodatni bridge/packaging sloj?  
**Q20.** Koji Presentation kandidat ima bolji Windows high-DPI, drag/drop, clipboard i file-dialog behavior u našem realnom workflowu?  
**Q21.** Koliko je kvalitetan `BHS/NEUTRAL` output bez eksplicitne BS/SR/HR varijante?  
**Q22.** Koje terminološke razlike vrijedi kodirati kao regional vocabulary, a koje prepustiti few-shot primjerima?  
**Q23.** Koji social formati ulaze u prvi funkcionalni MVP nakon Campaign Engine proof-a?  
**Q24.** Da li platform registry treba dozvoliti korisničke custom platform definicije ili samo aplikacijski registry?  
**Q25.** Koji provideri pouzdano podržavaju model discovery i kako fallbackovati kada ga nema?  
**Q26.** Da li per-task model routing treba ući odmah nakon MVP-a ili tek nakon mjerenja kvaliteta/troška?  

Ove odluke se ne smiju „zaključati“ bez testa.

---

# 101. Sljedeći dokument

Nakon ove Faze 0.6 treba napraviti:

# Faza 1 — Vertical Slice 1 tehnički plan

Ne kompletan proizvod.

Samo prvi dokaz centralne pretpostavke.

Treba sadržavati:

1. tačne Pydantic/domain modele;
2. Brand Fixture schema;
3. Campaign Brief schema;
4. Campaign Role model;
5. Campaign Plan schema;
6. ApprovedFact/version model;
7. Brand Snapshot model;
8. PostDraft schema;
9. Claim mapping schema;
10. deterministic linter;
11. prompt contracts;
12. provider port;
13. prvi AI adapter;
14. CampaignPlanningPipeline;
15. PostGenerationPipeline;
16. framework-neutral Presentation contracts/state;
17. Post Studio UI fidelity spike: PySide6 vs pywebview;
18. dokumentovanu UI framework odluku;
19. minimalne ekrane u pobjedničkom Presentation frameworku;
20. renderer spike;
21. CampaignVisualSystem + LayoutSpec schema;
22. template primitive schema;
23. layout-aware copy contract;
24. ZIP export;
25. telemetry;
26. A/B evaluation harness;
27. unit/integration/golden testove;
28. acceptance criteria;
29. redoslijed implementacije.

Website Ingestion ne treba implementirati u Fazi 1, ali Faza 1 mora definisati stabilne portove/domain granice tako da se Vertical Slice 2 može priključiti bez refaktorisanja Campaign Enginea.

---

# 102. Mentalna slika Slicea 1

```text
          HAND-WRITTEN BRAND FIXTURE
                    │
                    ▼
             CAMPAIGN BRIEF
                    │
                    ▼
             CAMPAIGN PLANNER
                    │
                    ▼
              PLAN REVIEW
                    │
                    ▼
            ALLOWED FACT SET
                    │
                    ▼
             POST GENERATOR
                    │
                    ▼
             FACT-ID MAPPING
                    │
                    ▼
          DETERMINISTIC LINTER
                    │
                    ▼
              POST REVIEW
                    │
                    ▼
           TEMPLATE RENDERER
                    │
                    ▼
                 EXPORT
```

Kontrola:

```text
SAME BRAND FIXTURE
      │
      ▼
ONE GENERIC PROMPT
      │
      ▼
6 POSTS
```

Poređenje ta dva sistema je prvi pravi test projekta.

---

# 103. Mentalna slika pune aplikacije nakon kasnijih faza

```text
WEBSITE + DOCUMENTS + MANUAL INPUT
                  │
                  ▼
      CONTROLLED SOURCE INGESTION
       HTTP → Playwright fallback
                  │
                  ▼
       SOURCE SNAPSHOTS / CHUNKS
                  │
                  ▼
        BRAND INTELLIGENCE DRAFT
                  │
                  ▼
             HUMAN REVIEW
                  │
                  ▼
            BRAND SNAPSHOT
                  │
                  ▼
            CAMPAIGN BRIEF
                  │
                  ▼
            CAMPAIGN PLAN
                  │
                  ▼
             HUMAN REVIEW
                  │
                  ▼
             FACT SELECTION
                  │
                  ▼
             POST GENERATION
                  │
                  ▼
       FACT/LAYOUT VALIDATION
                  │
                  ▼
              POST STUDIO
                  │
                  ▼
        CAMPAIGN VISUAL SYSTEM
                  │
                  ▼
             LAYOUT SPEC
                  │
                  ▼
       DETERMINISTIC VISUAL RENDER
                  │
                  ▼
                EXPORT
                  │
                  ▼
           OPTIONAL BACKUP
```

---


# Faza 0.4 — konsolidovane nadogradnje

U odnosu na prethodne revizije zadržano je i dodatno korigovano:

1. donor strategija umjesto copy/paste migracije;
2. HTTP/retry/concurrency obrazac;
3. robots/sitemap discovery;
4. selective persistent Playwright fallback;
5. parser/main-content principi;
6. JSON-LD structured-data extraction;
7. SourceEvidence/provenance;
8. deterministic reason mapping;
9. use-case pipeline princip;
10. background worker/progress/cancel model;
11. ingestion checkpoint/resume;
12. human review queue;
13. URL normalization;
14. SourceSnapshot diff;
15. stale-fact workflow;
16. donor regression fixture-i;
17. eksplicitna lista webshop-specifičnih dijelova koji se ne prenose;
18. PySide6 više nije unaprijed zaključan Presentation framework;
19. uveden je Post Studio UI fidelity spike;
20. pywebview + HTML/CSS/JS uveden je kao kontrolni kandidat;
21. Presentation arhitektura je učinjena framework-neutralnom;
22. WebshopAudit QThread/ReviewController donor stavke precizirane su kao obrasci, ne Qt kod;
23. dodat je T22 — visual fidelity/framework mismatch rizik;
24. UI framework odluka postaje obavezni gate u Fazi 1.  
25. UI jezici su reducirani na `EN` i `BHS`;  
26. uveden je `ContentLanguageContext`;  
27. BHS regionalne varijante su `NEUTRAL/BS/SR/HR`;  
28. UI lokalizacija i AI output jezik su razdvojeni;  
29. uveden je framework-neutral `resources/i18n/en.json` + `bhs.json`;  
30. latinica je zaključana za BHS MVP.  
31. Brand Intelligence i Campaign Engine više nisu konceptualno ograničeni na društvene mreže;  
32. uveden je `Channel → Platform → Format` model;  
33. uveden je proširivi social platform registry;  
34. uveden je generički `ContentPiece` sa SocialPost kao prvim MVP tipom;  
35. uveden je Provider Registry;  
36. uveden je Model Registry + capabilities;  
37. API ključ se konfiguriše jednom po provideru;  
38. uveden je obavezni Test Connection UX;  
39. uveden je OpenAI-compatible adapter kao generička ekstenzija;  
40. model discovery je podržan gdje provider API to omogućava.


# Zaključak Faze 0.4

Najvažnija promjena u ovoj reviziji nije nova tehnologija.

To je **redoslijed dokazivanja**.

Ne počinjemo projekt od najkompleksnijeg dijela — ingest sistema.

Prvo dokazujemo da osnovni Campaign Engine stvara mjerljivo bolji rezultat od generičkog AI prompta.

Istovremeno, claim sistem je pomjeren sa post-hoc semantičke provjere na fact-first generisanje sa determinističkim provenance pravilima.

Time prva faza postaje:

- manja;
- testabilnija;
- brža;
- arhitektonski jasnija;
- manje zavisna od nepouzdanih AI procjena;
- bolja osnova za kasniji Brand Intelligence i retrieval.

Dodatno, desktop-first odluka je sada odvojena od izbora UI toolkit-a. PySide6 ostaje vodeći kandidat, ali Presentation framework se zaključava tek nakon reprezentativnog Post Studio spike-a protiv HTML/pywebview alternative. Time se rizik skupog GUI rewrite-a testira rano, prije nego što Presentation sloj naraste.

UI framework, HTML/SVG social renderer i Playwright website-ingestion worker ostaju tri odvojene odluke. Dijeljenje Chromium/HTML tehnologije nije dovoljan razlog da se spoje u isti runtime ili arhitektonski sloj.

**Faza 0.6 je sada aktivna projektna osnova.**