// Standalone Node reprodukcija za ACS-F1-047 BF-CODEX-3
// (Codex re-review na PR #12).
//
// Svrha: dokazati da pomjeranje postavljanja re-entrancy markera
// ``button.dataset.acsJobActive`` sa "poslije await-a" na "sinhrono
// prije prvog await-a" zaista eliminira double-submit kada dva
// klika stignu u istom event-loop ticku (prije nego IPC
// round-trip za ``generate_campaign_content`` resolveuje).
//
// Režim rada:
//   1. BEFORE-fix varijanta: marker se postavlja TEK poslije await-a
//      (stari kod iz app.js, prije BF-CODEX-3 fix-a).
//   2. AFTER-fix varijanta: marker se postavlja ODMHAH poslije
//      api-availability provjere, sinhrono prije bilo kakvog await-a
//      (novi kod, identičan app.js linijama ~311..345).
//
// Obe varijante koriste ISTI stub: ``api.generate_campaign_content``
// vraća Promise koji NEĆE biti resolve-ovan dok eksplicitno ne
// pozovemo ``drainSubmit()``. To nam daje kontrolisan prozor u kojem
// možemo dispatchati dva klika u istom microtask slotu.
//
// Rezime outputa:
//   BEFORE: submit_calls=2  (drugi klik je prošao guard)
//   AFTER:  submit_calls=1  (drugi klik je vraćen na guard-u)
//
// Bez dependencija. Pokretanje: ``node agent_reports/2026-09-07-ACS-F1-047-bf-codex-3-repro.js``.

'use strict';

const JOB_ACTIVE_ATTR = 'acsJobActive';

// ---- Stubovi ---------------------------------------------------------------

function makeButton() {
  // Samo ono što ``generateContent`` zaista koristi. ``dataset`` je
  // običan dict u Node-u; to je dovoljno za re-entrancy guard koji
  // čita ``button.dataset[JOB_ACTIVE_ATTR]``.
  const dataset = {};
  return {
    dataset,
    textContent: 'Generiši sadržaj',
    disabled: false,
    // Pomoćno: spremi originalni label tako da after-fix logika
    // može vratiti dugme u prvobitno stanje.
    _originalLabel: 'Generiši sadržaj',
  };
}

function makeStubs() {
  const submitCalls = [];
  const cancelListeners = [];
  const pollers = [];
  const pendingSubmits = [];

  // ``api.generate_campaign_content`` je jedini poziv koji zaista
  // await-amo u ``generateContent``. Svaki poziv SNIMI argument i
  // vrati Promise koji čeka na vanjski ``drainSubmit()``. To nam
  // daje kontrolisan prozor race-a: mi dispatchamo 2 klika, pa tek
  // onda resolve-amo.
  const api = {
    generate_campaign_content(args) {
      submitCalls.push(args);
      let resolveFn;
      const promise = new Promise((resolve) => { resolveFn = resolve; });
      pendingSubmits.push(() => resolveFn({ ok: true, job_id: 'job-' + submitCalls.length }));
      return promise;
    },
    get_job_status(_args) { return Promise.resolve({ status: 'RUNNING', progress_current: 0, progress_total: 4, generated_count: 0, failed_count: 0 }); },
    cancel_job(_args) { return Promise.resolve({ ok: true }); },
  };

  // Minimal ``document`` -- samo ``querySelector`` koji vraća
  // ``null`` (jer u reprodukciji ne trebamo resultNode granu).
  const document = {
    querySelector() { return null; },
  };

  // Minimal ``window.pywebview`` -- ``api`` gore, ostalo ignore.
  const window = { pywebview: { api } };

  // ``showToast`` je pomoćni helper u app.js. U reprodukciji samo
  // štampa u stdout kada se zove.
  function showToast(msg) {
    process.stdout.write('  [toast] ' + msg + '\n');
  }

  function drainSubmit() {
    if (pendingSubmits.length === 0) {
      throw new Error('drainSubmit: no pending submit');
    }
    pendingSubmits.shift()();
  }

  return { api, document, window, showToast, drainSubmit, submitCalls, cancelListeners, pollers, pendingSubmits };
}

// ---- BEFORE-fix verzija ----------------------------------------------------

async function generateContentBeforeFix(button, stubs) {
  // TAČAN stari kod (prije BF-CODEX-3 fix-a): marker se postavlja
  // TEK poslije await-a na ``api.generate_campaign_content``. Dva
  // brza klika u istom microtask slotu OBA prolaze guard na vrhu
  // (jer marker još nije setovan), OBA submit-uju, OBA pokreću
  // polling i cancel listener.
  if (button.dataset[JOB_ACTIVE_ATTR] === '1') return;
  const api = stubs.window.pywebview && stubs.window.pywebview.api;
  if (!api) return;
  const originalLabel = button._originalLabel;
  button.textContent = 'Pokrećem…';

  const submitResult = await api.generate_campaign_content({
    campaign_id: 'camp-1', plan_id: 'plan-1',
  });
  // <-- STARI marker postavlja se TEK OVDJE, poslije await-a.
  button.dataset[JOB_ACTIVE_ATTR] = '1';

  if (!submitResult || !submitResult.ok) {
    delete button.dataset[JOB_ACTIVE_ATTR];
    button.textContent = originalLabel;
    return;
  }
  // Simulacija polling/cancel wiringa (nije fokus BF-CODEX-3 ali
  // je potrebno za uvjerljivu reprodukciju "dva listenera" simptoma
  // iz Codex-ovog nalaza).
  stubs.pollers.push({ button, jobId: submitResult.job_id });
  stubs.cancelListeners.push({ button, jobId: submitResult.job_id });
  stubs.showToast('Job ' + submitResult.job_id + ' started (BEFORE)');

  // Simuliramo da poslije nekog vremena terminalni state dođe i
  // marker se obriše -- kao u pravoj ``_renderTerminal``.
  return new Promise((resolve) => {
    setImmediate(() => {
      delete button.dataset[JOB_ACTIVE_ATTR];
      button.textContent = originalLabel;
      resolve();
    });
  });
}

// ---- AFTER-fix verzija -----------------------------------------------------

async function generateContentAfterFix(button, stubs) {
  // TAČAN novi kod (BF-CODEX-3 fix, identičan app.js linijama
  // ~311..345): marker se postavlja SINHRONO, odmah poslije
  // api-availability provjere, prije bilo kakvog ``await``. Dva
  // brza klika u istom microtask slotu: prvi setuje marker i
  // awaita; drugi VIDI marker na guard-u i odmah returna.
  if (button.dataset[JOB_ACTIVE_ATTR] === '1') return;
  const api = stubs.window.pywebview && stubs.window.pywebview.api;
  if (!api) return;

  // <-- NOVO: marker se postavlja SINHRONO, prije prvog await-a.
  button.dataset[JOB_ACTIVE_ATTR] = '1';

  const originalLabel = button._originalLabel;
  button.textContent = 'Pokrećem…';

  const submitResult = await api.generate_campaign_content({
    campaign_id: 'camp-1', plan_id: 'plan-1',
  });

  if (!submitResult || !submitResult.ok) {
    // Sync-reject grana: marker se čisti jer je postavljen prije
    // submit-a. Bez ovog, failed submit (npr. SUPERSEDED plan) bi
    // trajno zaključao dugme.
    delete button.dataset[JOB_ACTIVE_ATTR];
    button.textContent = originalLabel;
    return;
  }
  stubs.pollers.push({ button, jobId: submitResult.job_id });
  stubs.cancelListeners.push({ button, jobId: submitResult.job_id });
  stubs.showToast('Job ' + submitResult.job_id + ' started (AFTER)');

  return new Promise((resolve) => {
    setImmediate(() => {
      delete button.dataset[JOB_ACTIVE_ATTR];
      button.textContent = originalLabel;
      resolve();
    });
  });
}

// ---- Test driver -----------------------------------------------------------

function assertEqual(actual, expected, label) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  process.stdout.write(
    (ok ? '  PASS  ' : '  FAIL  ') + label + ': actual=' + JSON.stringify(actual) + ' expected=' + JSON.stringify(expected) + '\n'
  );
  if (!ok) process.exitCode = 1;
}

async function runRace(label, generateContent) {
  process.stdout.write('\n=== ' + label + ' ===\n');
  const stubs = makeStubs();
  const button = makeButton();

  // Dva klika u istom microtask slotu: bez ``await`` između njih.
  // Oba poziva startaju, awaitaju ``api.generate_campaign_content``
  // (čiji Promise neće biti resolve-ovan dok ne pozovemo drain).
  const click1 = generateContent(button, stubs);
  const click2 = generateContent(button, stubs);

  // Sačekaj jedan microtask hop da se oba ``generateContent`` poziva
  // zauzmu na ``await`` granici, zatim drain-amo SVE pending submita
  // (prije fix-a ima 2, poslije fix-a ima samo 1). Pratimo
  // ``pendingSubmits`` jer ``submitCalls`` se popunjava sinhrono na
  // pozivu ``api.generate_campaign_content`` i ostaje konstantan --
  // ``drainSubmit`` samo resolve-uje Promise, ne zove ponovo submit.
  await new Promise((r) => setImmediate(r));
  while (stubs.pendingSubmits.length > 0) {
    stubs.drainSubmit();
  }

  // Čekamo da se oba ``generateContent`` poziva završe (terminal
  // setImmediate u oba).
  await Promise.all([click1, click2].filter(Boolean));

  process.stdout.write('  submit_calls=' + stubs.submitCalls.length + '\n');
  process.stdout.write('  cancel_listeners=' + stubs.cancelListeners.length + '\n');
  process.stdout.write('  pollers=' + stubs.pollers.length + '\n');
  process.stdout.write('  marker tokom submit-a: provjeravamo kroz final state -- cleared na kraju=' + (button.dataset[JOB_ACTIVE_ATTR] === undefined) + '\n');

  return stubs;
}

async function main() {
  process.stdout.write('ACS-F1-047 BF-CODEX-3 standalone reprodukcija\n');
  process.stdout.write('============================================\n');

  // BEFORE: očekujemo submit_calls=2 (race NIJE spriječen)
  const beforeStubs = await runRace('BEFORE fix (marker poslije await-a)', generateContentBeforeFix);
  assertEqual(beforeStubs.submitCalls.length, 2, 'BEFORE submit_calls');
  assertEqual(beforeStubs.cancelListeners.length, 2, 'BEFORE cancel_listeners');
  assertEqual(beforeStubs.pollers.length, 2, 'BEFORE pollers');

  // AFTER: očekujemo submit_calls=1 (drugi klik vraćen na guard-u)
  const afterStubs = await runRace('AFTER fix (marker sinhrono prije await-a)', generateContentAfterFix);
  assertEqual(afterStubs.submitCalls.length, 1, 'AFTER submit_calls');
  assertEqual(afterStubs.cancelListeners.length, 1, 'AFTER cancel_listeners');
  assertEqual(afterStubs.pollers.length, 1, 'AFTER pollers');

  // Sync-reject scenario: nakon AFTER fix-a, marker postavljen
  // sinhrono se ispravno čisti kada submit vrati ok=false.
  process.stdout.write('\n=== AFTER fix: sync-reject (SUPERSEDED plan) cisti marker ===\n');
  {
    const stubs = makeStubs();
    // Prebacimo api da vrati ok=false, ali i dalje snimi poziv.
    const origSubmit = stubs.api.generate_campaign_content;
    stubs.api.generate_campaign_content = function (args) {
      stubs.submitCalls.push(args);
      return Promise.resolve({ ok: false, error_message: 'Plan je SUPERSEDED.' });
    };
    void origSubmit; // tihi silence lint-a

    const button = makeButton();
    await generateContentAfterFix(button, stubs);
    const markerStillSet = button.dataset[JOB_ACTIVE_ATTR] === '1';
    process.stdout.write('  marker nakon sync-reject submit-a: ' + (markerStillSet ? 'POSTAVLJEN (BUG)' : 'obrisan (FIX)') + '\n');
    assertEqual(markerStillSet, false, 'AFTER sync-reject clears marker');
  }

  process.stdout.write('\n============================================\n');
  if (process.exitCode === 1) {
    process.stdout.write('REZULTAT: FAIL -- reprodukcija nije potvrdila očekivano ponašanje.\n');
  } else {
    process.stdout.write('REZULTAT: PASS -- BEFORE=2 submita, AFTER=1 submit, sync-reject cisti marker.\n');
  }
}

main().catch((err) => {
  process.stderr.write('FATAL: ' + (err && err.stack || err) + '\n');
  process.exit(2);
});
