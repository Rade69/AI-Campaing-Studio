# AI Campaign Studio — GitNexus Protocol

**Status:** NON-NEGOTIABLE za MEDIUM/HIGH i shared-contract/refactor taskove.

GitNexus se koristi za:

- codebase context;
- caller/callee pregled;
- blast radius;
- execution-flow uticaj;
- diff-to-symbol impact;
- structural checks;
- safe refactor planning.

GitNexus ne zamjenjuje testove ili review.

---

# 1. Zaštita naših AGENTS.md / CLAUDE.md

Repo sadrži custom router fajlove.

Zato `.gitnexusrc` mora imati:

```json
{
  "defaultBranch": "main",
  "skipContextFiles": true
}
```

Pri ručnom analyze-u koristiti:

```bash
npx gitnexus analyze --skip-agents-md
```

Ne dozvoli da automatski generisan context zamijeni projektni kanonski workflow.

---

# 2. Initial setup

Ako GitNexus MCP već radi globalno:

ne pokretati setup ponovo bez potrebe.

Ako nije konfigurisan:

```bash
npx gitnexus setup
```

Nakon što ACS-P0-001 napravi početni repo skeleton:

```bash
npx gitnexus analyze --skip-agents-md
```

Provjeri:

```bash
npx gitnexus status
```

---

# 3. Obavezni identity check

Prije impact zaključka zabilježiti:

```text
Repository:
Worktree:
Branch:
HEAD:
GitNexus index status:
Index stale?:
```

Posebno kod git worktree-a ne vjerovati rezultatu ako alat analizira glavni checkout umjesto aktivnog worktree-a.

---

# 4. Pre-change protocol

Za MEDIUM/HIGH ili shared symbol:

## A. Context

```bash
npx gitnexus context <SYMBOL> --repo .
```

Cilj:

- gdje je simbol;
- ko ga koristi;
- procesi/cluster kontekst;
- relevantne veze.

## B. Upstream impact

```bash
npx gitnexus impact <SYMBOL> --direction upstream --depth 3 --include-tests --repo .
```

Pitanje:

```text
Šta zavisi od ovog simbola i šta bi moglo puknuti?
```

## C. Downstream impact kada je relevantno

```bash
npx gitnexus impact <SYMBOL> --direction downstream --depth 3 --include-tests --repo .
```

Pitanje:

```text
Od čega ovaj simbol zavisi i šta možda moramo prilagoditi?
```

## D. Structural cycles kada task dira dependency graph

```bash
npx gitnexus check --cycles --repo .
```

---

# 5. Task Contract evidence

U Task Contract upisati:

```yaml
gitnexus:
  required: true
  repository:
  worktree:
  branch:
  head:
  index_status:
  targets:
    - symbol:
      upstream_risk:
      upstream_count:
      downstream_notes:
      affected_processes:
  scope_fit: PASS|EXPAND_REQUIRED|UNKNOWN
  unknowns: []
```

Ako:

```text
scope_fit = EXPAND_REQUIRED
```

NE počinjati kod.

Redefinisati Task Contract.

Ako:

```text
UNKNOWN
```

zbog stale/partial/truncated/ambiguous rezultata, ne tretirati kao "nema impacta".

---

# 6. Pre-review detect-changes

Za MEDIUM/HIGH:

iz aktivnog worktree-a:

```bash
npx gitnexus detect-changes --scope all --repo .
```

Za poređenje cijelog task branch-a sa main:

```bash
npx gitnexus detect-changes --scope compare --base-ref main --repo .
```

Reviewer mora vidjeti ovaj output.

Ako postoje promjene, a GitNexus kaže "No changes detected":

```text
NE prihvatiti rezultat kao čist.
```

Provjeri:

- cwd/worktree;
- `--repo`;
- index freshness;
- branch binding.

---

# 7. Worktree caveat

Kod linked worktree-a postoji realan rizik da MCP/alat pogleda pogrešan checkout i vrati lažno čist rezultat.

Zato:

- izvršavaj CLI iz AKTIVNOG worktree-a;
- koristi `--repo .` ili eksplicitnu putanju aktivnog worktree-a;
- ne oslanjaj se samo na implicitni MCP repo izbor kada postoji više checkouta istog repoa.

Task evidence mora navesti worktree path.

---

# 8. Post-change reviewer questions

Reviewer koristi GitNexus da odgovori:

```text
Da li su svi depth-1 caller-i pregledani?
Da li je testiran pogođeni execution flow?
Da li je promijenjen public/shared contract?
Da li detect-changes pokazuje više procesa nego Task Contract?
Da li je risk tier i dalje ispravan?
Da li novi dependency graph uvodi cycle?
```

---

# 9. Post-merge

Na main:

```bash
npx gitnexus analyze --skip-agents-md
npx gitnexus status
npx gitnexus check --cycles --repo .
```

Ako je indeks stale:

task completion nije potpuno zatvoren.

---

# 10. Kada GitNexus nije obavezan

Samo LOW, dokazano izolovan task.

Task Contract mora eksplicitno sadržati:

```yaml
gitnexus:
  required: false
  reason: "resource-only isolated change; no shared symbol/contract"
```

Ako implementer tokom rada otkrije shared dependency:

GitNexus postaje obavezan i risk se ponovo procjenjuje.

---

# 11. GitNexus nije source of truth za ponašanje

GitNexus kaže:

```text
dependency / call / impact structure
```

Testovi i runtime evidence kažu:

```text
stvarno ponašanje
```

Oba su potrebna.

---

# 12. Zabranjeni obrasci

Ne prihvataj:

```text
"GitNexus kaže low risk pa test nije potreban"
"zero impact" iz stale indexa
impact bez vezanog repo/worktree identiteta
impact samo za jedan simbol kada diff mijenja više shared simbola
MCP rezultat iz main checkouta za feature worktree
preskakanje detect-changes prije HIGH reviewa
```
