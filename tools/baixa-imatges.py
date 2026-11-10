#!/usr/bin/env python3
"""Baixa les imatges de la web antiga de Google Sites a la carpeta img/.

Ús (des de la carpeta del projecte):
    python3 tools/baixa-imatges.py

Google genera enllaços d'imatge temporals cada vegada que es carrega una pàgina,
per això aquest script llegeix cada pàgina i baixa les imatges a l'acte.
Només cal executar-lo una vegada (o quan hi hagi imatges noves a Google Sites).
"""
import re
import sys
import html
import urllib.request
import urllib.parse
from pathlib import Path

BASE = "https://www.musicafelanitx.org"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
OUT = Path(__file__).resolve().parent.parent / "img"

# pàgina de Google Sites -> prefix del nom de fitxer a la web nova
PAGES = {
    "actualitat": "actualitat",
    "estudis/matrícula": "matricula",
    "estudis/documents": "documents",
    "estudis/espai-portocolom": "portocolom",
    "activitats/chopin-sessions": "piano-days",
    "activitats/chopin-sessions/masterclass": "masterclass",
    "activitats/música-al-jardí": "musica-al-jardi",
    "activitats/campus-música-creativa": "campus",
    "activitats/cor-jove": "cor-jove",
    "estudis/pla-destudis/més-info": "pla-estudis",
}
# imatges que són logotips: es guarden en PNG per conservar la transparència
PNG = {"logo", "actualitat-7", "piano-days-2", "masterclass-1", "campus-1"}


def get(url, referer=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Referer": referer} if referer else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def save(src, name, referer):
    base = re.sub(r"=[^/=]*$", "", html.unescape(src))
    png = name in PNG
    data = get(base + ("=w1600-rp" if png else "=w1600-rj"), referer)
    path = OUT / f"{name}.{'png' if png else 'jpg'}"
    path.write_bytes(data)
    print(f"  ✓ {path.name:28s} {len(data)//1024:5d} KB")


def main():
    OUT.mkdir(exist_ok=True)
    errors = 0
    for page, prefix in PAGES.items():
        url = BASE + "/" + urllib.parse.quote(page)
        print(page)
        doc = get(url).decode("utf-8")
        if prefix == "actualitat":
            logo = re.search(r'<img[^>]*src="(https://lh\d[^"]+)"', doc)
            if logo:
                save(logo.group(1), "logo", url)
        body = doc[doc.find("<section"):]
        srcs = re.findall(r'<img[^>]*src="(https://lh\d[^"]*googleusercontent[^"]+)"', body)
        for i, src in enumerate(srcs, 1):
            try:
                save(src, f"{prefix}-{i}", url)
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"  ✗ {prefix}-{i}: {e}")
    print("\nFet." if not errors else f"\nAcabat amb {errors} errors.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
