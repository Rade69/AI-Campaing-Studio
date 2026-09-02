// app.js -- SPIKE-001 Content Studio
//
// Owns: client-side i18n lookup, language toggle, fact-list rendering,
//       quick-action click logging, character counters. No state
//       persistence (spike).
// Does not own: any wiring to JobManager / AI providers (mocked).

(function () {
  "use strict";

  const i18n = window.__I18N__ || {};
  const initialLang = window.__LANG__ || "en";

  // --- helpers --------------------------------------------------------

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // --- i18n apply -----------------------------------------------------

  function applyLang(lang) {
    const t = i18n[lang];
    if (!t) {
      console.error("[spike] unknown lang:", lang);
      return;
    }

    // 1. text content for elements with data-i18n
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (typeof t[key] === "string") {
        el.textContent = t[key];
      }
    });

    // 2. value binding for inputs / textareas
    document.querySelectorAll("[data-i18n-bind]").forEach((el) => {
      const key = el.getAttribute("data-i18n-bind");
      if (typeof t[key] === "string") {
        if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
          el.value = t[key];
        } else {
          el.textContent = t[key];
        }
      }
    });

    // 2b. placeholder binding
    document.querySelectorAll("[data-i18n-bind-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-bind-placeholder");
      if (typeof t[key] === "string") {
        el.setAttribute("placeholder", t[key]);
      }
    });

    // 3. <html lang> attribute (a11y / font hint)
    document.documentElement.setAttribute("lang", lang === "bs" ? "bs" : "en");

    // 4. <title>
    document.title = t.title + " - " + t.post_counter;

    // 5. facts list (re-render)
    renderFacts(t);

    // 6. language toggle buttons
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      const isActive = btn.getAttribute("data-lang") === lang;
      btn.classList.toggle("bg-slate-900", isActive);
      btn.classList.toggle("text-white", isActive);
      btn.classList.toggle("text-slate-700", !isActive);
      btn.classList.toggle("hover:bg-slate-200", !isActive);
    });

    // 7. refresh character counters (text may have changed)
    updateAllCounters(t);
  }

  function renderFacts(t) {
    const list = document.getElementById("facts-list");
    if (!list || !Array.isArray(t.facts)) return;
    list.innerHTML = "";
    t.facts.forEach((f) => {
      const li = document.createElement("li");
      li.className =
        "text-[11px] text-slate-700 border-l-2 border-emerald-300 pl-2 py-1 break-words leading-relaxed";
      li.innerHTML =
        '<div class="break-words">' +
        escapeHtml(f.text) +
        "</div>" +
        '<div class="text-slate-400 mt-0.5 text-[9px] uppercase tracking-wide">' +
        escapeHtml(f.source) +
        "</div>";
      list.appendChild(li);
    });
  }

  // --- character counters --------------------------------------------

  function updateAllCounters(t) {
    document.querySelectorAll("[data-counter]").forEach((el) => {
      const name = el.getAttribute("data-counter");
      const maxKey = el.getAttribute("data-counter-max");
      const max = t[maxKey] || 0;
      const counterId = name + "-counter";
      const counter = document.getElementById(counterId);
      const len = (el.value || "").length;
      if (counter) {
        counter.textContent = len + " / " + max;
        // subtle red tint when over the limit
        if (len > max) {
          counter.classList.add("text-red-500");
        } else {
          counter.classList.remove("text-red-500");
        }
      }
    });
  }

  // wire up live update on input
  document.addEventListener("input", (ev) => {
    const t = i18n[currentLang()] || {};
    if (ev.target && ev.target.matches && ev.target.matches("[data-counter]")) {
      updateAllCounters(t);
    }
  });

  function currentLang() {
    try {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("lang");
      if (q === "en" || q === "bs") return q;
    } catch (e) {
      /* file:// quirks */
    }
    return initialLang;
  }

  // --- language toggle (also handle query string) --------------------

  function setLang(lang, pushState) {
    applyLang(lang);
    if (pushState && window.history && window.history.replaceState) {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", lang);
      window.history.replaceState({}, "", url);
    }
  }

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      setLang(btn.getAttribute("data-lang"), true);
    });
  });

  // --- quick action click handlers (no AI wiring; just visual feedback)

  document.querySelectorAll(".qa-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-action");
      console.log("[spike] quick action:", action);
      btn.classList.add("opacity-60");
      setTimeout(() => btn.classList.remove("opacity-60"), 200);
    });
  });

  // --- exit / save / send buttons (log only; no real backend) --------

  function bind(id, label) {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("click", () => {
      console.log("[spike]", label, "clicked");
      if (id === "exit-btn") {
        try {
          if (window.pywebview && window.pywebview.api && window.pywebview.api.close_window) {
            window.pywebview.api.close_window();
          } else {
            window.close();
          }
        } catch (e) {
          window.close();
        }
      }
    });
  }
  bind("exit-btn", "exit");
  bind("save-draft-btn", "save-draft");
  bind("send-review-btn", "send-review");

  // --- initial render ------------------------------------------------

  setLang(currentLang(), false);
})();
