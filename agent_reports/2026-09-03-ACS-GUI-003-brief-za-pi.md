# → ZA PI — ACS-GUI-003 (campaign workflow ekrani)

**Od:** koordinator (Claude) · **Za:** Pi · **Datum:** 2026-09-03

Dodijeljen ti je **ACS-GUI-003**. Pun kontrakt:
`agent_reports/ACS-GUI-003-task-contract.md`.

Worktree/branch su već kreirani:

```text
Worktree: H:\ai-campaign-studio-worktrees\ACS-GUI-003-campaign-workflow-screens
Branch:   task/ACS-GUI-003-campaign-workflow-screens
Base:     main @ c416a58
```

## Ukratko

Portaš 4 preostala campaign workflow mokap ekrana
(`docs/gui-v3/screens/04_opis_kampanje`, `05_plan_kampanje`,
`07_studio_sadrzaja`, `08_pregled_izvoz`) u
`presentation_webview/screens/{opis_kampanje,plan_kampanje,
studio_sadrzaja,pregled_izvoz}/`, GUI-BASE tier (fixture-driven SSR,
BEZ pravog use-case wiring-a — sve stvarne akcije ostaju
`data-action="toast"`, isti standard kao postojeći ekrani). Plus
5-koračni stepper, i pretvaraš Kampanje ekrana "Otvori" dugme u
stvaran link.

**Jedna namjerna zamka u mokapu**: `07_studio_sadrzaja/index.html` još
uvijek koristi STARI kozmetički tab markup (nije ažuriran tokom
ACS-GUI-004 mockup sync-a). NE portuj to doslovno — primijeni ISTI
stvaran `data-tab-target`/`data-tab-panel` pattern koji je ACS-GUI-004
već dokazao (pogledaj `screens/brend/__init__.py` post-merge kao
referentan primjer). Ovo je dokumentovano u kontraktu, nije potrebno
tražiti dodatno odobrenje — samo navedi u evidence izvještaju.

## Read-set prije koda (obavezno)

Sve navedeno u kontraktovom "Obavezno pročitati prije koda" bloku —
uključujući `agent_reports/ACS-GUI-004-task-contract.md` za tab-panel
pattern i `screens/kampanje/__init__.py` za trenutni "Otvori"
toast-stub koji zamjenjuješ.

## Vizuelna provjera

Kontrakt traži screenshot-ove sva 4 nova ekrana (uključujući aktivan
ne-default tab na Studio sadržaja). Ako pywebview ne radi u tvom
environment-u, eksplicitno to navedi u evidence-u — koordinator će
uraditi live provjeru na Human Owner-ovom ekranu (isti obrazac kao
ACS-GUI-004).

## Kad završiš

Evidence izvještaj u `agent_reports/`, ne commit-uj sam (workflow §29
— koordinator commit-uje/push-uje/merguje nakon review-a, MEDIUM risk
task).
