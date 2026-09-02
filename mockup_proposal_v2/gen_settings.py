"""gen_settings.py -- generate 6 settings sub-screens from a single template.

Each screen is a static HTML file at settings/<key>/index.html with the
shared sidebar + settings sub-nav, varying only the main content.
"""

import pathlib

BASE = pathlib.Path(__file__).resolve().parent / "settings"

# Sub-nav items in order; (key, label, icon-path) per item.
SUB_NAV = [
    ("profil", "Profil", "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"),
    ("language", "Jezik", "M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"),
    ("tim", "Tim", "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"),
    ("brend", "Podešavanja brenda", "M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"),
    ("ai", "AI provajderi", "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"),
    ("integracije", "Integracije", "M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"),
    ("fakturisanje", "Fakturisanje", "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"),
    ("preferencije", "Preferencije", "M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"),
]


def sidebar(active_main: str = "Podešavanja") -> str:
    items = [
        ("Znanje o brendu", "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"),
        ("Kampanje", "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"),
        ("Studio sadržaja", "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"),
        ("Kalendar", "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"),
        ("Resursi", "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"),
        ("Analitika", "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"),
    ]
    nav_html = ""
    for label, icon in items:
        active = "font-medium text-blue-700 bg-blue-50" if label == active_main else "text-slate-600 hover:bg-slate-50"
        nav_html += f'            <a class="flex items-center gap-2.5 px-3 py-2 text-sm {active} rounded-md"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="{icon}"/></svg>{label}</a>\n'
    # Last item is "Podešavanja" -- always active here
    nav_html += '            <a class="flex items-center gap-2.5 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-md"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>Podešavanja</a>\n'
    return f"""      <aside class="w-64 bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
        <div class="px-4 py-3 border-b border-slate-100">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-[11px] font-bold">BS</div>
            <div class="min-w-0"><div class="text-sm font-semibold text-slate-900 truncate">BrightSmile</div><div class="text-[10px] text-slate-500 truncate">Oralna njega</div></div>
          </div>
        </div>
        <div class="px-4 py-2 border-b border-slate-100">
          <div class="flex items-center gap-1.5 text-[11px] font-medium text-emerald-700">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
            <span>Verifikovano i ažurno</span>
          </div>
        </div>
        <nav class="px-2 py-3 space-y-0.5 flex-1">
{nav_html}        </nav>
        <div class="p-3 border-t border-slate-100">
          <button class="w-full px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md flex items-center justify-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            <span>Izvezi paket brenda</span>
          </button>
        </div>
      </aside>"""


def sub_nav(active_key: str) -> str:
    html = ""
    for key, label, icon in SUB_NAV:
        active = "font-medium text-blue-700 bg-blue-50" if key == active_key else "text-slate-600 hover:bg-slate-50"
        html += f'            <a class="flex items-center gap-2.5 px-3 py-2 text-sm {active} rounded-md"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="{icon}"/></svg>{label}</a>\n'
    return html


HEADER = """    <header class="bg-white border-b border-slate-200 px-5 h-14 flex items-center gap-3 flex-shrink-0">
      <div class="w-7 h-7 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-[11px] font-bold">AC</div>
      <span class="text-sm font-semibold text-slate-900">AI Campaign Studio</span>
      <span class="text-[10px] text-slate-400 ml-1">v1.0</span>
      <div class="flex-1"></div>
      <div class="flex gap-1 ml-2"><div class="w-3 h-3 rounded-full bg-slate-300"></div><div class="w-3 h-3 rounded-full bg-slate-300"></div><div class="w-3 h-3 rounded-full bg-slate-300"></div></div>
    </header>"""


def make_page(active_subnav: str, body: str, title: str = "Podešavanja") -> str:
    return f"""<!doctype html>
<html lang="bs">
  <head>
    <meta charset="utf-8" />
    <title>{title} — AI Campaign Studio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body {{ font-family: 'Inter', system-ui, sans-serif; -webkit-font-smoothing: antialiased; }}</style>
  </head>
  <body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col">
{HEADER}
    <div class="flex flex-1 min-h-0">
{sidebar()}
      <main class="flex-1 flex min-w-0">
        <div class="w-56 bg-white border-r border-slate-200 py-4 flex-shrink-0">
          <nav class="px-2 space-y-0.5">
{sub_nav(active_subnav)}
          </nav>
        </div>
        <div class="flex-1 p-6 max-w-[700px]">
{body}
        </div>
      </main>
    </div>
  </body>
</html>
"""


# === Profile page ===
PROFIL_BODY = """          <h1 class="text-xl font-semibold text-slate-900 mb-1">Profil</h1>
          <p class="text-sm text-slate-500 mb-5">Informacije o vama i vašem brendu.</p>

          <div class="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
            <div class="flex items-center gap-4 pb-4 border-b border-slate-100">
              <div class="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xl font-bold">BS</div>
              <div>
                <div class="text-sm font-semibold text-slate-900">BrightSmile</div>
                <div class="text-xs text-slate-500 mt-0.5">brightsmile.com · Lokalni projekat</div>
                <button class="mt-2 text-xs text-blue-600 hover:underline">Promijeni avatar</button>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Ime brenda</div>
                <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md">BrightSmile</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Domena</div>
                <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md">brightsmile.com</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Industrija</div>
                <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md">Oralna njega</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Veličina tima</div>
                <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md">1 (solo)</div>
              </div>
            </div>
          </div>

          <div class="mt-5 flex justify-end gap-2">
            <button class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg">Otkaži</button>
            <button class="px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg">Sačuvaj promjene</button>
          </div>
"""
(BASE / "profil" / "index.html").write_text(make_page("profil", PROFIL_BODY, "Profil"), encoding="utf-8")
print("OK: profil")


# === Tim page ===
TIM_BODY = """          <h1 class="text-xl font-semibold text-slate-900 mb-1">Tim</h1>
          <p class="text-sm text-slate-500 mb-5">Upravljanje članovima tima i njihovim ulogama.</p>

          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-lg">
              <div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-sm font-bold">BS</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-900">Ti (BrightSmile admin)</div>
                <div class="text-xs text-slate-500 mt-0.5">admin@brightsmile.com · Admin · Pristup svim funkcijama</div>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 rounded">Aktivan</span>
            </div>

            <div class="mt-4 p-4 border border-dashed border-slate-300 rounded-lg text-center">
              <svg class="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/></svg>
              <div class="text-sm text-slate-500">Solo radni prostor</div>
              <div class="text-xs text-slate-400 mt-1">Ovaj plan podržava jednog korisnika. Za više članova tima, kontaktirajte prodaju.</div>
            </div>
          </div>
"""
(BASE / "tim" / "index.html").write_text(make_page("tim", TIM_BODY, "Tim"), encoding="utf-8")
print("OK: tim")


# === Podešavanja brenda page ===
BREND_BODY = """          <h1 class="text-xl font-semibold text-slate-900 mb-1">Podešavanja brenda</h1>
          <p class="text-sm text-slate-500 mb-5">Konfigurišite glas, ton i vizualni identitet vašeg brenda.</p>

          <div class="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
            <div>
              <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Primarna boja</div>
              <div class="flex items-center gap-2">
                <div class="w-10 h-10 rounded-md bg-cyan-500 border border-slate-300"></div>
                <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md font-mono">#06b6d4</div>
              </div>
            </div>
            <div>
              <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Sekundarna boja</div>
              <div class="flex items-center gap-2">
                <div class="w-10 h-10 rounded-md bg-blue-600 border border-slate-300"></div>
                <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md font-mono">#2563eb</div>
              </div>
            </div>
            <div>
              <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Font naslova</div>
              <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md">Inter (Weight 600/700)</div>
            </div>
            <div>
              <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Logo</div>
              <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-md bg-slate-50">
                <div class="w-8 h-8 rounded bg-slate-900 text-white flex items-center justify-center text-[10px] font-bold">W</div>
                <div class="flex-1">
                  <div class="text-[11px] font-bold tracking-wider text-slate-900">BRIGHTSMILE</div>
                  <div class="text-[8px] text-slate-500 tracking-wide">ORAL CARE</div>
                </div>
                <button class="text-xs text-blue-600 hover:underline">Zamijeni</button>
              </div>
            </div>
            <div>
              <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Ton komunikacije</div>
              <div class="px-3 py-2 text-sm text-slate-800 bg-white border border-slate-200 rounded-md">Prijateljski, pouzdan, stručan</div>
              <div class="text-[10px] text-slate-400 mt-1">12 tendera · Verifikovano</div>
            </div>
          </div>

          <div class="mt-5 flex justify-end gap-2">
            <button class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg">Otkaži</button>
            <button class="px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg">Sačuvaj promjene</button>
          </div>
"""
(BASE / "brend" / "index.html").write_text(make_page("brend", BREND_BODY, "Podešavanja brenda"), encoding="utf-8")
print("OK: brend")


# === Integracije page ===
INTEGRACIJE_BODY = """          <h1 class="text-xl font-semibold text-slate-900 mb-1">Integracije</h1>
          <p class="text-sm text-slate-500 mb-5">Povežite eksterne servise za objavljivanje, analitiku i upravljanje društvenim mrežama.</p>

          <div class="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
            <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-lg">
              <div class="w-10 h-10 rounded-md bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center text-white text-xs font-bold">IG</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-900">Instagram Graph API</div>
                <div class="text-xs text-slate-500 mt-0.5">Automatsko objavljivanje + učitavanje metrika</div>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 rounded">Nije povezano</span>
              <button class="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded">Poveži</button>
            </div>
            <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-lg">
              <div class="w-10 h-10 rounded-md bg-blue-600 flex items-center justify-center text-white text-xs font-bold">FB</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-900">Facebook Pages API</div>
                <div class="text-xs text-slate-500 mt-0.5">Automatsko objavljivanje + učitavanje metrika</div>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 rounded">Nije povezano</span>
              <button class="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded">Poveži</button>
            </div>
            <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-lg">
              <div class="w-10 h-10 rounded-md bg-sky-600 flex items-center justify-center text-white text-xs font-bold">LI</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-900">LinkedIn Marketing API</div>
                <div class="text-xs text-slate-500 mt-0.5">B2B objavljivanje + učitavanje metrika</div>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 rounded">Nije povezano</span>
              <button class="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded">Poveži</button>
            </div>
            <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-lg">
              <div class="w-10 h-10 rounded-md bg-slate-800 flex items-center justify-center text-white text-xs font-bold">X</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-900">X (Twitter) API v2</div>
                <div class="text-xs text-slate-500 mt-0.5">Automatsko objavljivanje + učitavanje metrika</div>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 rounded">Nije povezano</span>
              <button class="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded">Poveži</button>
            </div>
            <div class="flex items-center gap-3 p-3 border border-slate-200 rounded-lg">
              <div class="w-10 h-10 rounded-md bg-emerald-600 flex items-center justify-center text-white text-xs font-bold">GA</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-900">Google Analytics 4</div>
                <div class="text-xs text-slate-500 mt-0.5">Konverzije + praćenje korisnika</div>
              </div>
              <span class="px-2 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 rounded">Nije povezano</span>
              <button class="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded">Poveži</button>
            </div>
          </div>

          <div class="mt-5 p-4 bg-slate-100 rounded-lg">
            <div class="text-xs text-slate-600 leading-relaxed"><span class="font-semibold">Napomena:</span> Integracije sa društvenim mrežama su opcionalne. Bez njih, možete i dalje generisati sadržaj u aplikaciji, ali ćete morati ručno objaviti.</div>
          </div>
"""
(BASE / "integracije" / "index.html").write_text(make_page("integracije", INTEGRACIJE_BODY, "Integracije"), encoding="utf-8")
print("OK: integracije")


# === Fakturisanje page ===
FAKTURISANJE_BODY = """          <h1 class="text-xl font-semibold text-slate-900 mb-1">Fakturisanje</h1>
          <p class="text-sm text-slate-500 mb-5">Vaš plan, fakture i način plaćanja.</p>

          <div class="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl p-5 text-white mb-4">
            <div class="text-xs opacity-80 mb-1">Trenutni plan</div>
            <div class="text-2xl font-bold">Solo</div>
            <div class="text-sm opacity-90 mt-1">Besplatan tokom beta perioda</div>
            <div class="mt-3 flex items-center gap-2 text-xs opacity-90">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
              Aktivan do 1. septembra 2026.
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <h3 class="text-sm font-semibold text-slate-900 mb-3">Historija faktura</h3>
            <div class="text-center py-6 text-sm text-slate-500">
              <svg class="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              Nema faktura. Besplatan plan tokom beta perioda.
            </div>
          </div>

          <div class="mt-4 text-center">
            <button class="text-sm text-blue-600 hover:underline">Nadogradi plan (uskoro dostupno)</button>
          </div>
"""
(BASE / "fakturisanje" / "index.html").write_text(make_page("fakturisanje", FAKTURISANJE_BODY, "Fakturisanje"), encoding="utf-8")
print("OK: fakturisanje")


# === Preferencije page ===
PREFERENCIJE_BODY = """          <h1 class="text-xl font-semibold text-slate-900 mb-1">Preferencije</h1>
          <p class="text-sm text-slate-500 mb-5">Prilagodite ponašanje aplikacije i obavještenja.</p>

          <div class="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-sm font-medium text-slate-800">Automatski sačuvaj draft svake 30 sekundi</div>
                <div class="text-xs text-slate-500 mt-0.5">Sprečava gubitak rada ako se aplikacija zatvori neočekivano</div>
              </div>
              <div class="w-9 h-5 rounded-full bg-blue-500 relative"><div class="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow"></div></div>
            </div>
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
              <div>
                <div class="text-sm font-medium text-slate-800">Prikaži "Pregledaj činjenice" link</div>
                <div class="text-xs text-slate-500 mt-0.5">Claim Check panel prikazuje link za pregled Approved Facts</div>
              </div>
              <div class="w-9 h-5 rounded-full bg-blue-500 relative"><div class="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow"></div></div>
            </div>
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
              <div>
                <div class="text-sm font-medium text-slate-800">Generiši ton komunikacije po jeziku</div>
                <div class="text-xs text-slate-500 mt-0.5">AI prilagođava ton komunikacije izabranom jeziku (ijekavica/ekavica)</div>
              </div>
              <div class="w-9 h-5 rounded-full bg-blue-500 relative"><div class="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow"></div></div>
            </div>
            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
              <div>
                <div class="text-sm font-medium text-slate-800">Slanje anonimnih metrika</div>
                <div class="text-xs text-slate-500 mt-0.5">Pomaže u poboljšanju aplikacije. Bez ličnih podataka.</div>
              </div>
              <div class="w-9 h-5 rounded-full bg-slate-200 relative"><div class="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow"></div></div>
            </div>
          </div>

          <div class="mt-5 flex justify-end gap-2">
            <button class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg">Vrati na default</button>
            <button class="px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg">Sačuvaj</button>
          </div>
"""
(BASE / "preferencije" / "index.html").write_text(make_page("preferencije", PREFERENCIJE_BODY, "Preferencije"), encoding="utf-8")
print("OK: preferencije")

print("\nAll 6 settings screens generated.")
