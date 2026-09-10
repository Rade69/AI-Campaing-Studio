"""Download the Q12 spike corpus HTML files from real BHS sites.

Throwaway spike helper. Fetches a small set of diverse, real pages (news,
blog, tourism, ecommerce landing) and saves the raw HTML into ``corpus/``.
Respects rate limit (>=1s between requests) and uses a normal browser UA.
"""
import time
from pathlib import Path

import requests

CORPUS = Path(__file__).parent / "corpus"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# (slug, url)
TARGETS = [
    ("klix.ba-article", "https://www.klix.ba/vijesti/svijet/iran-napao-bazu-sad-a-u-jordanu-osteceno-osam-borbenih-aviona-f-15-a-10-thunderbolt-ostao-bez-krila/260910008"),
    ("nezavisne.com-article", "https://www.nezavisne.com/novosti/svijet/pet-poginulih-u-pozaru-na-trajektu-na-filipinima-87-nestalih/981677"),
    ("akta.ba-article", "https://www.akta.ba/eu/politika/208011/europljani-zele-snazniju-eu-ali-vecina-smatra-da-kontinent-ide-u-pogresnom-smjeru"),
    ("oslobodjenje.ba-magazin", "https://www.oslobodjenje.ba/magazin/tehnologija/apple-je-predstavio-i-phone-18-pro-i-prvi-sklopivi-i-phone-duo/"),
]


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


for slug, url in TARGETS:
    out = CORPUS / f"{slug}.html"
    try:
        html = fetch(url)
        out.write_text(html, encoding="utf-8")
        print(f"OK  {slug}: {len(html)} chars <- {url}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERR {slug}: {type(exc).__name__} {exc}")
    time.sleep(1.2)
