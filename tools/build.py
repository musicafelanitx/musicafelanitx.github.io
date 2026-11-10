#!/usr/bin/env python3
"""Genera la web estàtica a _site/.

    python3 tools/build.py          # genera _site/
    python3 tools/build.py --serve  # genera i obre un servidor a http://localhost:8770

Estructura:
    src/layout.html        plantilla comuna (capçalera, menú, peu)
    src/pages/**.html      una pàgina per fitxer (ruta = camí del fitxer)
    src/noticies/*.md      notícies (text senzill, vegeu README.md)
    data/*.json            menú, professorat, calendari del curs
    assets/, img/          es copien tal qual
"""
import hashlib
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, DATA, OUT = ROOT / "src", ROOT / "data", ROOT / "_site"
SITE_URL = "https://www.musicafelanitx.org"
# Mentre no hi hagi fitxer CNAME (domain definitiu), la web és una vista prèvia: no s'indexa a Google.
LIVE = (ROOT / "CNAME").exists()
MESOS = ["gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost",
         "setembre", "octubre", "novembre", "desembre"]

esc = html.escape


# ---------------------------------------------------------------- utilitats

def front_matter(text):
    """Separa la capçalera `--- clau: valor ---` del contingut."""
    meta = {}
    if text.startswith("---"):
        _, head, text = text.split("---", 2)
        for line in head.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, text.strip()


def inline_md(s):
    s = esc(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: link(m.group(2), m.group(1)), s)
    s = re.sub(r"(?<![\"'>=])\b(https?://[^\s<]+[^\s<.,;:)])", lambda m: link(m.group(1), pretty_url(m.group(1))), s)
    return s


def pretty_url(u):
    return re.sub(r"^https?://(www\.)?", "", u)


def link(url, text):
    ext = url.startswith("http")
    attrs = ' target="_blank" rel="noopener"' if ext else ""
    return f'<a href="{url}"{attrs}>{text}</a>'


def markdown(md):
    """Markdown mínim: paràgrafs, ## títols, - llistes, > avís, [botó](url){.btn}."""
    out, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            out.append("<p>" + "<br>".join(inline_md(x) for x in para) + "</p>")
        if items:
            out.append("<ul>" + "".join(f"<li>{inline_md(x)}</li>" for x in items) + "</ul>")
        para, items = [], []

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        m = re.match(r"^(#{2,4})\s+(.*)", line)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline_md(m.group(2))}</h{n}>")
        elif re.match(r"^\s*[-•]\s+", line):
            if para:
                flush()
            items.append(re.sub(r"^\s*[-•]\s+", "", line))
        elif line.startswith("> "):
            flush()
            out.append(f'<p class="callout">{inline_md(line[2:])}</p>')
        elif m := re.match(r"^\[([^\]]+)\]\(([^)]+)\)\{\.btn\}$", line.strip()):
            flush()
            ext = m.group(2).startswith("http")
            out.append(f'<p><a class="btn" href="{m.group(2)}"{" target=_blank rel=noopener" if ext else ""}>{esc(m.group(1))}</a></p>')
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def data_llarga(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {'d’' if MESOS[m-1][0] in 'aeiou' else 'de '}{MESOS[m-1]} de {y}"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- notícies

def load_news():
    news = []
    for f in sorted((SRC / "noticies").glob("*.md")):
        meta, body = front_matter(f.read_text(encoding="utf-8"))
        meta["slug"] = f.stem.split("-", 1)[1] if re.match(r"^\d+-", f.stem) else f.stem
        meta["ordre"] = int(f.stem.split("-", 1)[0]) if re.match(r"^\d+-", f.stem) else 0
        meta["html"] = markdown(body)
        meta["text"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", meta["html"])).strip()
        if meta.get("arxivada", "no") == "si":
            continue
        news.append(meta)
    news.sort(key=lambda n: -n["ordre"])
    return news


def news_card(n, big=False):
    img = n.get("imatge", "")
    quan = f'<span class="chip chip-date" data-date="{n["data"]}">{esc(data_llarga(n["data"]))}</span>' if n.get("data") else ""
    return f"""<article class="card news-card{' news-card--big' if big else ''}" data-cat="{esc(n.get('categoria','').lower())}">
  <a class="card-media" href="/actualitat/{n['slug']}/" tabindex="-1" aria-hidden="true">{f'<img src="{img}" alt="" loading="lazy">' if img else ''}</a>
  <div class="card-body">
    <div class="card-meta"><span class="chip">{esc(n.get('categoria',''))}</span>{quan}</div>
    <h3><a href="/actualitat/{n['slug']}/">{esc(n['titol'])}</a></h3>
    <p>{esc(n.get('resum',''))}</p>
    <a class="more" href="/actualitat/{n['slug']}/">Llegir més <span aria-hidden="true">→</span></a>
  </div>
</article>"""


def news_page(n, all_news):
    img = n.get("imatge", "")
    others = [x for x in all_news if x["slug"] != n["slug"]][:3]
    quan = f'<span class="chip chip-date" data-date="{n["data"]}">{esc(data_llarga(n["data"]))}</span>' if n.get("data") else ""
    return f"""<article class="article">
  <a class="back" href="/actualitat/">← Totes les notícies</a>
  <div class="card-meta"><span class="chip">{esc(n.get('categoria',''))}</span>{quan}</div>
  <h1>{esc(n['titol'])}</h1>
  {f'<p class="lead">{esc(n["resum"])}</p>' if n.get('resum') else ''}
  <div class="article-grid">
    {f'<figure class="article-figure"><img src="{img}" alt="" data-zoom></figure>' if img else ''}
    <div class="prose">{n['html']}</div>
  </div>
</article>
<section class="section">
  <h2 class="section-title">Altres notícies</h2>
  <div class="grid grid-3">{''.join(news_card(o) for o in others)}</div>
</section>"""


# ---------------------------------------------------------------- blocs de dades

def render_professorat():
    people = load("professorat.json")
    groups = [("direccio", "Equip directiu"), ("docent", "Equip docent"), ("pas", "Personal no docent")]
    fams = sorted({p.get("familia") for p in people if p.get("familia")})
    noms = {"vent": "Vent", "corda": "Corda", "tecla": "Piano", "guitarra": "Guitarra",
            "percussio": "Percussió", "veu": "Cant", "teoria": "Teoria", "dansa": "Dansa"}
    out = ['<div class="toolbar"><label class="search-field"><span class="sr-only">Cerca professorat</span>'
           '<input type="search" placeholder="Cerca per nom o instrument…" data-filter-text="#professorat"></label>'
           '<div class="chips" data-filter-chips="#professorat"><button class="chip is-on" data-value="">Tots</button>'
           + "".join(f'<button class="chip" data-value="{f}">{noms.get(f, f)}</button>' for f in fams)
           + '</div></div><div id="professorat">']
    for key, title in groups:
        members = [p for p in people if p["grup"] == key]
        out.append(f'<section class="people-group" data-group><h2>{title}</h2><div class="grid grid-people">')
        for p in members:
            ini = "".join(w[0] for w in p["nom"].split()[:2]).upper()
            mail = f'<a class="person-mail" href="mailto:{p["email"]}" aria-label="Escriu a {esc(p["nom"])}">✉</a>' if p.get("email") else ""
            out.append(f'<div class="person" data-cat="{p.get("familia","")}" data-text="{esc((p["nom"]+" "+p["rol"]).lower())}">'
                       f'<span class="avatar" aria-hidden="true">{ini}</span><div><strong>{esc(p["nom"])}</strong>'
                       f'<span>{esc(p["rol"])}</span></div>{mail}</div>')
        out.append("</div></section>")
    out.append('<p class="empty" hidden>No hi ha cap resultat.</p></div>')
    return "\n".join(out)


def render_curs(compact=False):
    c = load("curs.json")
    rows = []
    for t in c["trimestres"]:
        evs = "".join(
            f'<li data-date="{e["inici"]}" data-end="{e["fi"]}"><span>{esc(e["nom"])}</span>'
            f'<time>{esc(e["text"])}</time></li>' for e in t["fites"])
        rows.append(f'<li class="term" data-date="{t["inici"]}" data-end="{t["fi"]}">'
                    f'<div class="term-head"><span class="term-n">{esc(t["nom"])}</span>'
                    f'<span class="term-dates">{esc(t["text"])}</span><span class="term-state"></span></div>'
                    f'<div class="term-bar"><span></span></div><ul class="term-events">{evs}</ul></li>')
    return (f'<div class="course" data-course data-start="{c["inici"]}" data-end="{c["fi"]}">'
            f'<div class="course-head"><div><span class="eyebrow">Curs {esc(c["curs"])}</span>'
            f'<p class="course-now" data-course-now>Del {esc(c["text"])}</p></div>'
            f'<div class="course-progress"><span data-course-pct>0%</span><small>del curs</small></div></div>'
            f'<ol class="terms">{"".join(rows)}</ol></div>')


# ---------------------------------------------------------------- menú

def render_nav(menu, current):
    items = []
    for it in menu["principal"]:
        active = current == it["url"] or current.startswith(it["url"]) and it["url"] != "/"
        cls = ' class="is-active"' if active else ""
        if it.get("fills"):
            sub = "".join(f'<li><a href="{c["url"]}"{" aria-current=page" if current == c["url"] else ""}>'
                          f'<strong>{esc(c["titol"])}</strong><span>{esc(c.get("desc",""))}</span></a></li>' for c in it["fills"])
            items.append(f'<li class="has-sub"{cls}><a href="{it["url"]}">{esc(it["titol"])}</a>'
                         f'<button class="sub-toggle" aria-expanded="false" aria-label="Obre {esc(it["titol"])}">'
                         f'<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5 6 7.5 9 4.5"/></svg></button>'
                         f'<ul class="sub">{sub}</ul></li>')
        else:
            items.append(f'<li{cls}><a href="{it["url"]}"{" aria-current=page" if current == it["url"] else ""}>{esc(it["titol"])}</a></li>')
    return "\n".join(items)


def render_breadcrumb(menu, current):
    if current in ("/",):
        return ""
    crumbs = []
    for it in menu["principal"]:
        if current.startswith(it["url"]) and it["url"] != "/":
            crumbs.append((it["titol"], it["url"]))
            for c in it.get("fills", []):
                if current.startswith(c["url"]) and c["url"] != it["url"]:
                    crumbs.append((c["titol"], c["url"]))
    if len(crumbs) < 2:
        return ""
    parts = [f'<a href="{u}">{esc(t)}</a>' for t, u in crumbs[:-1]]
    return '<nav class="crumbs" aria-label="Ruta">' + " <span>/</span> ".join(parts) + "</nav>"


# ---------------------------------------------------------------- construcció

def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for d in ("assets", "img"):
        if (ROOT / d).exists():
            shutil.copytree(ROOT / d, OUT / d)

    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    # versió dels fitxers estàtics: força els navegadors a descarregar-los de nou quan canvien
    for asset in ("assets/css/style.css", "assets/js/site.js"):
        ver = hashlib.md5((ROOT / asset).read_bytes()).hexdigest()[:8]
        layout = layout.replace(f'"/{asset}"', f'"/{asset}?v={ver}"')
    menu = load("menu.json")
    news = load_news()
    search = []

    blocks = {
        "noticies": lambda arg: "".join(news_card(n, big=(i == 0 and arg == "destacades")) for i, n in enumerate(news[: int(arg) if arg.isdigit() else (4 if arg == "destacades" else None)])),
        "filtres-noticies": lambda arg: '<div class="chips" data-filter-chips="#noticies"><button class="chip is-on" data-value="">Totes</button>'
            + "".join(f'<button class="chip" data-value="{c.lower()}">{esc(c)}</button>' for c in dict.fromkeys(n.get("categoria", "") for n in news) if c)
            + "</div>",
        "professorat": lambda arg: render_professorat(),
        "curs": lambda arg: render_curs(),
        "any": lambda arg: "2026",
    }

    def render_page(route, meta, content):
        content = re.sub(r"\{\{\s*(\w[\w-]*)\s*([^}]*)\}\}", lambda m: blocks[m.group(1)](m.group(2).strip()), content)
        title = meta.get("title", "")
        full_title = f"{title} · Conservatori de Felanitx" if title and route != "/" else "Conservatori de Felanitx · Música i Dansa"
        page = (layout
                .replace("{{title}}", esc(full_title))
                .replace("{{description}}", esc(meta.get("description", "Conservatori Municipal de Música, Escola de Música i Dansa Pare Aulí i Espai de Música de Portocolom.")))
                .replace("{{canonical}}", SITE_URL + route)
                .replace("{{body_class}}", meta.get("class", ""))
                .replace("{{nav}}", render_nav(menu, route))
                .replace("{{crumbs}}", render_breadcrumb(menu, route))
                .replace("{{any}}", str(date.today().year))
                .replace("{{robots}}", "" if LIVE else '<meta name="robots" content="noindex, nofollow">')
                .replace("{{content}}", content))
        if route == "/404/":
            dest = OUT / "404.html"
        else:
            dest = OUT / route.strip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding="utf-8")
        if route != "/404/" and not meta.get("nocerca"):
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.S)))
            search.append({"t": title or "Inici", "u": route, "s": meta.get("section", ""), "x": html.unescape(text).strip()[:4000]})

    for f in sorted((SRC / "pages").rglob("*.html")):
        rel = f.relative_to(SRC / "pages").with_suffix("")
        route = "/" if str(rel) == "index" else "/" + str(rel).removesuffix("/index") + "/"
        meta, content = front_matter(f.read_text(encoding="utf-8"))
        render_page(route, meta, content)

    for n in news:
        render_page(f"/actualitat/{n['slug']}/", {"title": n["titol"], "description": n.get("resum", ""), "section": "Actualitat"}, news_page(n, news))

    (OUT / "cerca.json").write_text(json.dumps(search, ensure_ascii=False), encoding="utf-8")
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", OUT / "CNAME")
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text("User-agent: *\n" + ("Allow: /\n" if LIVE else "Disallow: /\n"))
    print(f"✓ {len(search)} pàgines generades a {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server
        import functools
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Servint a http://localhost:8770 (Ctrl+C per aturar)")
        http.server.ThreadingHTTPServer(("", 8770), handler).serve_forever()
