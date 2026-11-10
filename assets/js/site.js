/* Conservatori de Felanitx — interactivitat */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* sense emmagatzematge */ } },
  };
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const parse = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(y, m - 1, d); };
  const DAY = 864e5;

  /* capçalera amb vora en fer scroll */
  const header = $(".site-header");
  const onScroll = () => header && header.classList.toggle("is-scrolled", scrollY > 8);
  addEventListener("scroll", onScroll, { passive: true }); onScroll();

  /* menú del mòbil */
  const nav = $("#menu"), scrim = $(".scrim"), openBtn = $("[data-menu-open]");
  const setMenu = (open) => {
    if (!nav) return;
    nav.classList.toggle("is-open", open);
    scrim.hidden = !open;
    openBtn?.setAttribute("aria-expanded", open);
    document.body.style.overflow = open ? "hidden" : "";
    document.body.classList.toggle("menu-open", open);
    if (open) nav.querySelector("a, button")?.focus();
  };
  openBtn?.addEventListener("click", () => setMenu(true));
  $$("[data-menu-close]").forEach((b) => b.addEventListener("click", () => setMenu(false)));
  addEventListener("keydown", (e) => { if (e.key === "Escape" && nav?.classList.contains("is-open")) { setMenu(false); openBtn?.focus(); } });
  $$(".sub-toggle").forEach((b) => b.addEventListener("click", () => {
    const li = b.closest("li"); const open = !li.classList.contains("is-open");
    li.classList.toggle("is-open", open); b.setAttribute("aria-expanded", open);
  }));
  // al mòbil, obre per defecte la secció activa
  $(".nav-list > li.is-active.has-sub")?.classList.add("is-open");

  /* tema clar / fosc */
  $$("[data-theme-toggle]").forEach((b) => b.addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next; store.set("tema", next);
  }));

  /* cerca global (⌘K, Ctrl+K o /) */
  const dlg = $("#cerca"), input = $("[data-search-input]"), results = $("[data-search-results]");
  let index = null, sel = 0;
  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const escHtml = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const openSearch = async () => {
    if (!dlg) return;
    dlg.showModal(); input.value = ""; render("");
    input.focus();
    if (!index) { try { index = await (await fetch("/cerca.json")).json(); } catch { index = []; } render(input.value); }
  };
  const snippet = (text, q) => {
    const n = norm(text), i = n.indexOf(q);
    if (i < 0) return escHtml(text.slice(0, 140));
    const start = Math.max(0, i - 50);
    const part = text.slice(start, i + q.length + 90);
    const off = i - start;
    return (start ? "…" : "") + escHtml(part.slice(0, off)) + "<mark>" + escHtml(part.slice(off, off + q.length)) + "</mark>" + escHtml(part.slice(off + q.length)) + "…";
  };
  function render(raw) {
    if (!results) return;
    const q = norm(raw.trim());
    if (!q) {
      results.innerHTML = '<li class="hint">Prova amb <b>matrícula</b>, <b>piano</b>, <b>proves d’accés</b> o <b>dansa</b>.</li>'; return;
    }
    if (!index) { results.innerHTML = '<li class="hint">Carregant…</li>'; return; }
    const words = q.split(/\s+/);
    const hits = index.map((p) => {
      const t = norm(p.t), x = norm(p.x);
      if (!words.every((w) => t.includes(w) || x.includes(w))) return null;
      const score = words.reduce((s, w) => s + (t.includes(w) ? 10 : 0) + (x.split(w).length - 1), 0);
      return { p, score };
    }).filter(Boolean).sort((a, b) => b.score - a.score).slice(0, 8);
    sel = 0;
    results.innerHTML = hits.length
      ? hits.map(({ p }, i) => `<li><a href="${p.u}" class="${i ? "" : "is-sel"}">${p.s ? `<small>${escHtml(p.s)}</small>` : ""}<strong>${escHtml(p.t)}</strong><p>${snippet(p.x, words[0])}</p></a></li>`).join("")
      : '<li class="hint">No hem trobat res. Prova amb una altra paraula.</li>';
  }
  input?.addEventListener("input", () => render(input.value));
  input?.addEventListener("keydown", (e) => {
    const links = $$("a", results);
    if (!links.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      links[sel]?.classList.remove("is-sel");
      sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links[sel].classList.add("is-sel"); links[sel].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") { e.preventDefault(); location.href = links[sel].href; }
  });
  dlg?.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  $$("[data-search-open]").forEach((b) => b.addEventListener("click", openSearch));
  addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
    if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) { e.preventDefault(); openSearch(); }
  });
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) $$(".search-btn kbd").forEach((k) => (k.textContent = "Ctrl K"));

  /* filtres: xips i text */
  const applyFilter = (target) => {
    const root = $(target); if (!root) return;
    const chip = $(`[data-filter-chips="${target}"] .is-on`)?.dataset.value || "";
    const text = norm($(`[data-filter-text="${target}"]`)?.value || "");
    let shown = 0;
    $$("[data-cat]", root).forEach((el) => {
      const okCat = !chip || el.dataset.cat.split(" ").includes(chip);
      const okText = !text || norm(el.dataset.text || el.textContent).includes(text);
      el.hidden = !(okCat && okText); if (!el.hidden) shown++;
    });
    $$("[data-group]", root).forEach((g) => (g.hidden = !$$("[data-cat]", g).some((el) => !el.hidden)));
    const empty = $(".empty", root) || root.parentElement.querySelector(".empty");
    if (empty) empty.hidden = shown > 0;
  };
  $$("[data-filter-chips]").forEach((box) => box.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("button", box).forEach((x) => x.classList.toggle("is-on", x === b));
    applyFilter(box.dataset.filterChips);
  }));
  $$("[data-filter-text]").forEach((inp) => inp.addEventListener("input", () => applyFilter(inp.dataset.filterText)));

  /* pestanyes */
  $$("[role=tablist]").forEach((list) => {
    const tabs = $$("[role=tab]", list);
    const select = (t) => tabs.forEach((x) => {
      const on = x === t; x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1;
      $("#" + x.getAttribute("aria-controls")).hidden = !on;
    });
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t));
      t.addEventListener("keydown", (e) => {
        const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (d) { const n = tabs[(i + d + tabs.length) % tabs.length]; select(n); n.focus(); }
      });
    });
  });

  /* dates: passat / pròxim */
  $$("[data-date]").forEach((el) => {
    const start = parse(el.dataset.date), end = el.dataset.end ? parse(el.dataset.end) : start;
    if (end < today) el.classList.add("is-past");
    else if (start <= today) el.classList.add("is-current");
  });
  $$("[data-upcoming]").forEach((list) => {
    const next = $$("[data-date]", list).find((el) => !el.classList.contains("is-past"));
    if (next) {
      next.classList.add("is-next");
      const tag = $(".tl-tag", next); const days = Math.round((parse(next.dataset.date) - today) / DAY);
      if (tag) tag.textContent = days === 0 ? "Avui" : days === 1 ? "Demà" : `Pròxima activitat · falten ${days} dies`;
    }
  });

  /* curs: progrés i estat de cada trimestre */
  $$("[data-course]").forEach((c) => {
    const s = parse(c.dataset.start), e = parse(c.dataset.end);
    const pct = Math.max(0, Math.min(100, Math.round(((today - s) / (e - s)) * 100)));
    const pctEl = $("[data-course-pct]", c); if (pctEl) pctEl.textContent = pct + "%";
    let msg = null;
    $$(".term", c).forEach((t) => {
      const ts = parse(t.dataset.date), te = parse(t.dataset.end);
      const bar = $(".term-bar span", t), state = $(".term-state", t);
      const p = today < ts ? 0 : today > te ? 100 : ((today - ts) / (te - ts)) * 100;
      requestAnimationFrame(() => setTimeout(() => (bar.style.width = p + "%"), 150));
      if (today > te) state.textContent = "Acabat";
      else if (today >= ts) {
        state.textContent = "Ara";
        const nextEv = $$(".term-events li", t).find((li) => parse(li.dataset.end) >= today);
        const name = t.querySelector(".term-n").textContent.toLowerCase();
        if (nextEv) {
          const d = Math.round((parse(nextEv.dataset.date) - today) / DAY);
          const what = nextEv.querySelector("span").textContent.toLowerCase();
          msg = d <= 0 ? `Som al ${name}: setmana de ${what}.` : `Som al ${name}. Falten ${d} dies ${what === "audicions" ? "per a les audicions" : "per als tribunals"}.`;
        } else msg = `Som al ${name}.`;
      } else if (!msg && today < ts) {
        const d = Math.round((ts - today) / DAY);
        msg = `El ${t.querySelector(".term-n").textContent.toLowerCase()} comença d’aquí a ${d} dies.`;
      }
    });
    if (today < s) msg = `El curs comença d’aquí a ${Math.round((s - today) / DAY)} dies.`;
    if (today > e) msg = "El curs ha acabat. Bon estiu!";
    if (msg) $("[data-course-now]", c).textContent = msg;
  });

  /* copiar (IBAN, correu…) */
  $$("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy); } catch { return; }
    const old = b.innerHTML; b.classList.add("is-done"); b.textContent = "Copiat ✓";
    setTimeout(() => { b.innerHTML = old; b.classList.remove("is-done"); }, 1800);
  }));

  /* ampliar imatges */
  $$("[data-zoom]").forEach((img) => img.addEventListener("click", () => {
    const d = document.createElement("dialog"); d.className = "lightbox";
    d.innerHTML = `<img src="${img.currentSrc || img.src}" alt="">`;
    d.addEventListener("click", () => d.close()); d.addEventListener("close", () => d.remove());
    document.body.append(d); d.showModal();
  }));

  /* imatges que encara no existeixen: amaga el contenidor */
  $$("img[data-optional]").forEach((img) => {
    const hide = () => (img.closest("[data-optional-wrap]") || img).remove();
    if (img.complete && !img.naturalWidth) hide(); else img.addEventListener("error", hide);
  });

  /* aparició suau */
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px" });
    $$(".reveal").forEach((el) => io.observe(el));
  } else $$(".reveal").forEach((el) => el.classList.add("is-in"));
})();
