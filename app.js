/* Berea — reading and study, offline-first.
 *
 * No framework, no build step. The data in /data is the whole engine; the only
 * network call at runtime is the optional "Go deeper" request, which goes
 * straight from this browser to Anthropic using a key the reader supplies.
 */

const STORE = {
  progress: "berea.progress",
  notes: "berea.notes",
  settings: "berea.settings",
};

const state = {
  manifest: null,
  book: null,          // manifest entry
  chapter: 1,
  chapters: new Map(), // "Jhn/3" -> payload
  lexicons: new Map(), // "Jhn" -> lexicon
  verse: null,         // active verse object
  tab: "words",
  word: null,          // open word index
  answers: new Map(),  // cache of AI answers this session
};

const el = (id) => document.getElementById(id);

/* --- storage ------------------------------------------------------------- */

function load(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode or full quota — the app still works, it just won't remember */
  }
}

let progress = load(STORE.progress, {});
let notes = load(STORE.notes, {});
let settings = load(STORE.settings, { theme: "system", model: "claude-opus-5", key: "" });

/* --- text helpers -------------------------------------------------------- */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

/* Minimal Markdown for model output. Escape everything first, then re-enable a
 * fixed set of inline forms — nothing from the response can introduce markup. */
function renderMarkdown(src) {
  const inline = (s) => escapeHtml(s)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");

  const out = [];
  let list = null;

  for (const rawLine of src.split("\n")) {
    const line = rawLine.trimEnd();
    const heading = line.match(/^#{1,4}\s+(.*)$/);
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);

    if (heading) {
      if (list) { out.push(`<ul>${list.join("")}</ul>`); list = null; }
      out.push(`<h3>${inline(heading[1])}</h3>`);
    } else if (bullet) {
      (list ??= []).push(`<li>${inline(bullet[1])}</li>`);
    } else if (!line) {
      if (list) { out.push(`<ul>${list.join("")}</ul>`); list = null; }
    } else {
      if (list) { out.push(`<ul>${list.join("")}</ul>`); list = null; }
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  if (list) out.push(`<ul>${list.join("")}</ul>`);
  return out.join("");
}

/* --- data loading -------------------------------------------------------- */

async function getJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

async function getChapter(abbrev, chapter) {
  const key = `${abbrev}/${chapter}`;
  if (!state.chapters.has(key)) {
    state.chapters.set(key, await getJSON(`data/books/${abbrev}/${chapter}.json`));
  }
  return state.chapters.get(key);
}

async function getLexicon(abbrev) {
  if (!state.lexicons.has(abbrev)) {
    state.lexicons.set(abbrev, await getJSON(`data/books/${abbrev}/lexicon.json`));
  }
  return state.lexicons.get(abbrev);
}

/* --- reading view -------------------------------------------------------- */

function verseKey(abbrev, chapter, verse) {
  return `${abbrev}.${chapter}.${verse}`;
}

async function renderChapter(abbrev, chapter) {
  const book = state.manifest.books.find((b) => b.abbrev === abbrev);
  if (!book) return;

  const total = book.chapters.length;
  chapter = Math.min(Math.max(1, chapter), total);
  state.book = book;
  state.chapter = chapter;

  const data = await getChapter(abbrev, chapter);
  const readKey = `${abbrev}.${chapter}`;
  const isRead = Boolean(progress[readKey]);

  const verses = data.verses.map((v) => {
    const noted = notes[verseKey(abbrev, chapter, v.v)]?.trim() ? " noted" : "";
    return `<p class="verse${noted}" data-v="${v.v}" id="v${v.v}" tabindex="0" role="button">`
      + `<span class="n">${v.v}</span>${escapeHtml(v.text)}</p>`;
  }).join("");

  el("reader").innerHTML = `
    <div class="chapter-head">
      <div class="book">${escapeHtml(book.name)}</div>
      <h1 class="num">${chapter}</h1>
    </div>
    ${verses}
    <nav class="chapter-nav">
      <button id="nav-prev" ${chapter === 1 ? "disabled" : ""}>← ${chapter - 1 || ""}</button>
      <button id="nav-next" ${chapter === total ? "disabled" : ""}>${chapter + 1 <= total ? chapter + 1 : ""} →</button>
      <label class="mark-read spacer">
        <input type="checkbox" id="chk-read" ${isRead ? "checked" : ""}>
        read
      </label>
    </nav>`;

  el("bar-ref").textContent = `${book.name} ${chapter}`;
  document.title = `${book.name} ${chapter} · Berea`;

  el("reader").querySelectorAll(".verse").forEach((node) => {
    const open = () => openVerse(Number(node.dataset.v));
    node.addEventListener("click", open);
    node.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
  });

  el("nav-prev").addEventListener("click", () => go(abbrev, chapter - 1));
  el("nav-next").addEventListener("click", () => go(abbrev, chapter + 1));
  el("chk-read").addEventListener("change", (e) => {
    if (e.target.checked) progress[readKey] = Date.now();
    else delete progress[readKey];
    save(STORE.progress, progress);
  });

  window.scrollTo({ top: 0, behavior: "instant" });
}

function go(abbrev, chapter, verse) {
  location.hash = `#/${abbrev}/${chapter}${verse ? `/${verse}` : ""}`;
}

/* --- drawer -------------------------------------------------------------- */

function openDrawer() {
  el("drawer").classList.add("open");
  el("scrim").classList.add("open");
  document.body.classList.add("panel-open");
}

function closeDrawer() {
  el("drawer").classList.remove("open");
  el("scrim").classList.remove("open");
  document.body.classList.remove("panel-open");
  document.querySelectorAll(".verse.active").forEach((n) => n.classList.remove("active"));
  state.verse = null;
}

async function openVerse(vnum) {
  const data = await getChapter(state.book.abbrev, state.chapter);
  const verse = data.verses.find((v) => v.v === vnum);
  if (!verse) return;

  state.verse = verse;
  state.word = null;

  document.querySelectorAll(".verse.active").forEach((n) => n.classList.remove("active"));
  document.querySelector(`.verse[data-v="${vnum}"]`)?.classList.add("active");

  el("drawer-ref").textContent = `${state.book.name} ${state.chapter}:${vnum}`;
  openDrawer();
  renderPanel();
}

function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll('.tabs [role="tab"]').forEach((b) => {
    b.setAttribute("aria-selected", String(b.dataset.tab === tab));
  });
  renderPanel();
}

async function renderPanel() {
  const verse = state.verse;
  if (!verse) return;

  const panel = el("panel");
  const head = `<div class="panel-verse">${escapeHtml(verse.text)}</div>`;

  if (state.tab === "words") panel.innerHTML = head + await renderWords(verse);
  else if (state.tab === "xrefs") panel.innerHTML = head + renderXrefs(verse);
  else if (state.tab === "notes") { panel.innerHTML = head + renderNotes(); wireNotes(); }
  else if (state.tab === "deeper") { panel.innerHTML = head + renderDeeper(); wireDeeper(); }
}

/* --- word by word -------------------------------------------------------- */

async function renderWords(verse) {
  if (!verse.words?.length) {
    return `<p class="empty">No original-language data for this verse.</p>`;
  }

  const lexicon = await getLexicon(state.book.abbrev);
  const chips = verse.words.map((w, i) => `
    <button class="word${state.word === i ? " open" : ""}" data-w="${i}">
      <span class="g">${escapeHtml(w.g)}</span>
      <span class="e">${escapeHtml(w.e || w.lg || "")}</span>
    </button>`).join("");

  let detail = `<p class="hint" style="margin-top:0.9rem">Tap a Greek word to open its lexicon entry.</p>`;

  if (state.word !== null && verse.words[state.word]) {
    const w = verse.words[state.word];
    const entry = lexicon[w.s];
    const m = w.m;

    const notes = (m?.notes || [])
      .map((n) => `<div class="lex-note"><b>${escapeHtml(n.feature)}</b> — ${escapeHtml(n.note)}</div>`)
      .join("");

    detail = `
      <div class="lex">
        <div>
          <span class="lex-lemma">${escapeHtml(w.lemma || w.g)}</span>
          <span class="lex-translit">${escapeHtml(w.t)}</span>
          <span class="lex-strongs">${escapeHtml(w.s)}</span>
        </div>
        <p class="lex-gloss">${escapeHtml(entry?.gloss || w.lg || "")}</p>
        ${m ? `<div class="lex-morph">${escapeHtml(m.summary)}
                 <span class="code">(${escapeHtml(m.code)})</span></div>` : ""}
        ${notes}
        ${entry?.full ? `<div class="lex-full">${markNavigableRefs(entry.full)}</div>
                         <p class="lex-src">Abbott-Smith, via STEPBible (CC BY 4.0)</p>` : ""}
      </div>`;
  }

  return `<div class="words">${chips}</div>${detail}`;
}

/* Lexicon entries cite the whole canon, but only built books can be opened.
 * Mark the ones that can, so the rest don't look like dead links. */
function markNavigableRefs(html) {
  const built = new Set(state.manifest.books.map((b) => b.abbrev));
  return html.replace(/class="lex-ref" data-ref="([^"]+)"/g, (match, ref) => (
    built.has(ref.split(".")[0]) ? `class="lex-ref nav" data-ref="${ref}"` : match
  ));
}

/* --- cross references ---------------------------------------------------- */

function renderXrefs(verse) {
  if (!verse.xrefs?.length) {
    return `<p class="empty">No cross-references recorded for this verse.</p>`;
  }

  const built = new Map(state.manifest.books.map((b) => [b.name, b.abbrev]));

  return verse.xrefs.map((x) => {
    const m = x.ref.match(/^(.*) (\d+):(\d+)/);
    const abbrev = m ? built.get(m[1]) : null;
    const nav = abbrev ? ` data-go="${abbrev}/${m[2]}/${m[3]}"` : "";
    return `
      <button class="xref"${nav}${abbrev ? "" : " disabled"}>
        <span class="xref-ref">${escapeHtml(x.ref)}
          <span class="xref-votes">${x.votes}</span></span>
        <span class="xref-text">${escapeHtml(x.text)}</span>
      </button>`;
  }).join("")
    + `<p class="hint">Weighted by reader votes at OpenBible.info. Higher numbers mean
       more people found the connection meaningful.</p>`;
}

/* --- notes --------------------------------------------------------------- */

function renderNotes() {
  const key = verseKey(state.book.abbrev, state.chapter, state.verse.v);
  return `
    <textarea id="note-box" placeholder="What is this saying? What do you want to remember?">${escapeHtml(notes[key] || "")}</textarea>
    <p class="hint">Saved in this browser as you type.</p>`;
}

function wireNotes() {
  const key = verseKey(state.book.abbrev, state.chapter, state.verse.v);
  const box = el("note-box");
  let timer;
  box.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const text = box.value;
      if (text.trim()) notes[key] = text;
      else delete notes[key];
      save(STORE.notes, notes);
      const node = document.querySelector(`.verse[data-v="${state.verse.v}"]`);
      node?.classList.toggle("noted", Boolean(text.trim()));
    }, 400);
  });
}

/* --- go deeper (Anthropic API, reader's own key) ------------------------- */

const ASKS = [
  ["Historical setting", "What would a first-century reader have known here that I don't? Cover the cultural, religious, and political setting."],
  ["Key words", "Take the two or three most theologically loaded words in this verse and explain what they carry in the Greek that English flattens."],
  ["How it's read", "How has this verse been understood across the tradition, and where do careful readers genuinely disagree?"],
  ["Where it sits", "How does this verse function in the argument of the surrounding passage and the book as a whole?"],
];

const SYSTEM = `You are helping a thoughtful lay reader study the Bible closely. They are reading the Berean Standard Bible with the tagged Greek text beside it.

Write for someone who wants substance, not reassurance. Be concrete and specific: name places, dates, customs, and sources. When scholars genuinely disagree, say so and say why, rather than flattening it into one view. Where the Greek matters, quote it with a transliteration.

Distinguish clearly between what the text says, what the historical record shows, and what is interpretation. If something is uncertain or contested, say that plainly instead of smoothing it over.

Keep it to a few hundred words. Use short Markdown headings and prose paragraphs; avoid long bullet lists. Do not open with a preamble or restate the question — begin with the substance.`;

function renderDeeper() {
  if (!settings.key) {
    return `<p class="empty">Add an Anthropic API key in Settings to ask open-ended
      questions about the passage.<br><br>Everything else in Berea works without it.</p>`;
  }

  const cached = state.answers.get(askKey());
  const chips = ASKS.map(([label], i) =>
    `<button class="chip" data-ask="${i}">${escapeHtml(label)}</button>`).join("");

  return `
    <div class="ask-row">${chips}</div>
    <form class="ask-form" id="ask-form">
      <input id="ask-input" placeholder="Ask anything about this verse…" autocomplete="off">
      <button class="btn" type="submit">Ask</button>
    </form>
    <div class="answer${cached ? " done" : ""}" id="answer">${cached ? renderMarkdown(cached) : ""}</div>`;
}

function askKey() {
  return verseKey(state.book.abbrev, state.chapter, state.verse.v);
}

function wireDeeper() {
  if (!settings.key) return;

  const run = (question) => askClaude(question);

  el("panel").querySelectorAll("[data-ask]").forEach((b) => {
    b.addEventListener("click", () => run(ASKS[Number(b.dataset.ask)][1]));
  });

  el("ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = el("ask-input").value.trim();
    if (q) run(q);
  });
}

function buildRequest(question) {
  const verse = state.verse;
  const ref = `${state.book.name} ${state.chapter}:${verse.v}`;

  const greek = (verse.words || [])
    .map((w) => `${w.g} (${w.t}) "${w.e}" — ${w.s} ${w.lemma}, ${w.m?.summary || ""}`)
    .join("\n");

  const context = [
    `Verse: ${ref}`,
    `English (BSB): ${verse.text}`,
    greek ? `\nTagged Greek, word by word:\n${greek}` : "",
    verse.xrefs?.length
      ? `\nCross-references: ${verse.xrefs.map((x) => x.ref).join(", ")}`
      : "",
    `\nQuestion: ${question}`,
  ].filter(Boolean).join("\n");

  const body = {
    model: settings.model,
    max_tokens: 3000,
    stream: true,
    system: SYSTEM,
    messages: [{ role: "user", content: context }],
  };

  // `effort` is supported on the Claude 5 models but rejected on Haiku 4.5.
  if (settings.model !== "claude-haiku-4-5") {
    body.output_config = { effort: "low" };
  }

  return body;
}

async function askClaude(question) {
  const target = el("answer");
  const buttons = el("panel").querySelectorAll("button");
  if (!target) return;

  buttons.forEach((b) => { b.disabled = true; });
  target.classList.remove("done");
  target.innerHTML = `<p style="color:var(--ink-faint)">Thinking…</p>`;

  let text = "";
  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": settings.key,
        "anthropic-version": "2023-06-01",
        // Required for the API to accept a request made directly from a browser.
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify(buildRequest(question)),
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err?.error?.message || detail;
      } catch { /* non-JSON error body */ }
      throw new Error(detail);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === "[DONE]") continue;

        let event;
        try { event = JSON.parse(payload); } catch { continue; }

        if (event.type === "content_block_delta" && event.delta?.type === "text_delta") {
          text += event.delta.text;
          target.innerHTML = renderMarkdown(text);
          target.scrollIntoView({ block: "nearest" });
        } else if (event.type === "error") {
          throw new Error(event.error?.message || "stream error");
        }
      }
    }

    if (!text.trim()) throw new Error("The model returned an empty response.");
    state.answers.set(askKey(), text);
    target.classList.add("done");
  } catch (err) {
    target.classList.add("done");
    target.innerHTML = `<div class="error"><strong>Couldn't reach Claude.</strong><br>
      ${escapeHtml(err.message)}</div>`;
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
  }
}

/* --- chapter index ------------------------------------------------------- */

function renderIndex() {
  const book = state.book;
  const done = book.chapters.filter((c) => progress[`${book.abbrev}.${c.chapter}`]).length;

  el("progress-line").textContent =
    `${done} of ${book.chapters.length} chapters read · ${book.verses.toLocaleString()} verses`;

  el("plan-grid").innerHTML = book.chapters.map((c) => {
    const isDone = Boolean(progress[`${book.abbrev}.${c.chapter}`]);
    const here = c.chapter === state.chapter;
    return `<button class="plan-cell${isDone ? " done" : ""}${here ? " here" : ""}"
              data-chapter="${c.chapter}">${c.chapter}</button>`;
  }).join("");

  el("plan-grid").querySelectorAll("[data-chapter]").forEach((b) => {
    b.addEventListener("click", () => {
      closeModal(el("modal-index"));
      go(book.abbrev, Number(b.dataset.chapter));
    });
  });
}

/* --- settings ------------------------------------------------------------ */

function applyTheme() {
  const root = document.documentElement;
  if (settings.theme === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", settings.theme);

  el("seg-theme").querySelectorAll("[data-theme-choice]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.themeChoice === settings.theme));
  });
}

function wireSettings() {
  el("seg-theme").querySelectorAll("[data-theme-choice]").forEach((b) => {
    b.addEventListener("click", () => {
      settings.theme = b.dataset.themeChoice;
      save(STORE.settings, settings);
      applyTheme();
    });
  });

  const key = el("in-key");
  key.value = settings.key || "";
  key.addEventListener("change", () => {
    settings.key = key.value.trim();
    save(STORE.settings, settings);
    if (state.tab === "deeper") renderPanel();
  });

  const model = el("in-model");
  model.value = settings.model;
  model.addEventListener("change", () => {
    settings.model = model.value;
    save(STORE.settings, settings);
  });

  el("btn-reset-progress").addEventListener("click", () => {
    if (!confirm("Clear which chapters are marked read? Your notes are kept.")) return;
    progress = {};
    save(STORE.progress, progress);
    renderChapter(state.book.abbrev, state.chapter);
  });

  el("credits").innerHTML = `
    <p>Scripture is the <strong>Berean Standard Bible</strong>, public domain.</p>
    <p>Greek text, morphology, and lexicon from
      <a href="https://github.com/STEPBible/STEPBible-Data" target="_blank" rel="noopener">STEPBible</a>
      (CC BY 4.0), incorporating Abbott-Smith's lexicon.</p>
    <p>Cross-references from
      <a href="https://www.openbible.info/labs/cross-references/" target="_blank" rel="noopener">OpenBible.info</a>
      (CC BY).</p>`;
}

/* --- modals -------------------------------------------------------------- */

function openModal(node) { node.classList.add("open"); }
function closeModal(node) { node.classList.remove("open"); }

/* --- routing ------------------------------------------------------------- */

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const fallback = state.manifest.books[0];

  const abbrev = state.manifest.books.some((b) => b.abbrev === parts[0])
    ? parts[0]
    : fallback.abbrev;
  const chapter = Number(parts[1]) || 1;

  closeDrawer();
  await renderChapter(abbrev, chapter);

  if (parts[2]) {
    const v = Number(parts[2]);
    document.getElementById(`v${v}`)?.scrollIntoView({ block: "center" });
    openVerse(v);
  }
}

/* --- boot ---------------------------------------------------------------- */

async function main() {
  applyTheme();
  wireSettings();

  document.querySelectorAll('.tabs [role="tab"]').forEach((b) => {
    b.addEventListener("click", () => setTab(b.dataset.tab));
  });

  el("btn-close").addEventListener("click", closeDrawer);
  el("scrim").addEventListener("click", closeDrawer);

  el("btn-settings").addEventListener("click", () => openModal(el("modal-settings")));
  el("btn-index").addEventListener("click", () => { renderIndex(); openModal(el("modal-index")); });

  document.querySelectorAll("[data-close-modal]").forEach((b) => {
    b.addEventListener("click", () => closeModal(b.closest(".modal")));
  });

  document.querySelectorAll(".modal").forEach((m) => {
    m.addEventListener("click", (e) => { if (e.target === m) closeModal(m); });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal.open").forEach(closeModal);
      closeDrawer();
    }
    if (e.target.matches("input, textarea, select")) return;
    if (e.key === "ArrowRight") el("nav-next")?.click();
    if (e.key === "ArrowLeft") el("nav-prev")?.click();
  });

  // Cross-reference and lexicon links both navigate by reference.
  el("panel").addEventListener("click", (e) => {
    const word = e.target.closest("[data-w]");
    if (word) {
      const i = Number(word.dataset.w);
      state.word = state.word === i ? null : i;
      renderPanel();
      return;
    }
    const target = e.target.closest("[data-go]");
    if (target) {
      const [abbrev, chapter, verse] = target.dataset.go.split("/");
      go(abbrev, Number(chapter), Number(verse));
      return;
    }

    // Lexicon entries cite scripture as "Jhn.1.1". Follow it when that book is
    // built; otherwise leave it alone rather than pretending to navigate.
    const lexRef = e.target.closest(".lex-ref");
    if (lexRef) {
      const m = (lexRef.dataset.ref || "").match(/^(\w+)\.(\d+)\.(\d+)/);
      if (m && state.manifest.books.some((b) => b.abbrev === m[1])) {
        go(m[1], Number(m[2]), Number(m[3]));
      }
    }
  });

  state.manifest = await getJSON("data/manifest.json");
  window.addEventListener("hashchange", route);
  await route();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => { /* offline is a bonus, not a requirement */ });
  }
}

main().catch((err) => {
  el("reader").innerHTML = `<div class="error">Couldn't load Berea's data.<br>
    ${escapeHtml(err.message)}</div>`;
});
