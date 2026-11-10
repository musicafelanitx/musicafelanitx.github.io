# Web del Conservatori de Felanitx

Web estàtica de **musicafelanitx.org**: Conservatori Municipal de Música, Escola de Música i Dansa Pare Aulí i Espai de Música de Portocolom.

Es publica sola a GitHub Pages cada vegada que es puja un canvi a la branca `main` (vegeu `.github/workflows/pages.yml`).

## Veure-la a l'ordinador

```bash
python3 tools/build.py --serve
```

i obriu <http://localhost:8770>.

## On és cada cosa

| Vull canviar… | Fitxer |
|---|---|
| Una notícia | `src/noticies/*.md` |
| El menú | `data/menu.json` |
| Les dates del curs (trimestres, tribunals, audicions) | `data/curs.json` |
| El professorat | `data/professorat.json` |
| El text d'una pàgina | `src/pages/…` (mateixa ruta que l'adreça web) |
| Capçalera i peu de pàgina | `src/layout.html` |
| Colors i tipografia | `assets/css/style.css` (variables al principi) |
| Imatges | `img/` |

## Afegir una notícia

Creau un fitxer a `src/noticies/` amb un número davant (el número més alt surt primer):

```markdown
---
titol: Concert de Nadal
categoria: Activitats
data: 2026-12-20
imatge: /img/concert-nadal.jpg
resum: Una frase que surt a la targeta de la notícia.
---
Text de la notícia. Es poden fer **negretes**, *cursives* i [enllaços](https://...).

## Un subtítol

- Una llista
- amb punts

[Inscripcions](https://forms.gle/...){.btn}
```

- `data` és opcional: si hi és, la notícia mostra la data i la marca com a passada quan ja ha arribat.
- Per retirar una notícia sense esborrar-la, afegiu `arxivada: si` a la capçalera.

## Imatges de la web antiga

`tools/baixa-imatges.py` baixa les imatges de la web de Google Sites a `img/` (només cal fer-ho una vegada):

```bash
python3 tools/baixa-imatges.py
```

## Domini

Mentre es revisa, la web es veu a `https://musicafelanitx.github.io/`. Per passar-la a **musicafelanitx.org**:

1. Creau un fitxer `CNAME` a l'arrel amb el text `www.musicafelanitx.org`.
2. A IONOS, al DNS de `musicafelanitx.org` (sense tocar els registres MX ni TXT del correu):
   - `www` → **CNAME** `musicafelanitx.github.io`
   - `@` → **A** `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
3. A GitHub → Settings → Pages, activau **Enforce HTTPS** quan estigui disponible.
4. A IONOS, redirigiu `musicafelanitx.com` cap a `https://www.musicafelanitx.org`.

Les adreces antigues de Google Sites (amb accents, com `/estudis/matrícula`) es redirigeixen automàticament a les noves des de `404.html`.
