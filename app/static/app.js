/* Custom MD - front-end logic (vanilla JS, no build step) */
"use strict";

/* ------------------------------- API client ------------------------------- */

const api = {
  async request(method, url, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    const text = await response.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch { data = { error: text }; }
    }
    if (!response.ok) {
      throw new Error((data && data.error) || `Request failed (${response.status})`);
    }
    return data;
  },

  tree() { return this.request("GET", "/api/tree"); },
  file(path) { return this.request("GET", `/api/file?path=${encodeURIComponent(path)}`); },
  save(path, content) { return this.request("PUT", `/api/file?path=${encodeURIComponent(path)}`, { content }); },
  createFile(path) { return this.request("POST", `/api/file?path=${encodeURIComponent(path)}`); },
  createFolder(path) { return this.request("POST", `/api/folder?path=${encodeURIComponent(path)}`); },
  rename(from, to) { return this.request("POST", "/api/rename", { from, to }); },
  removeFile(path) { return this.request("DELETE", `/api/file?path=${encodeURIComponent(path)}`); },
  removeFolder(path, recursive) {
    const suffix = recursive ? "&recursive=true" : "";
    return this.request("DELETE", `/api/folder?path=${encodeURIComponent(path)}${suffix}`);
  },
  search(q) { return this.request("GET", `/api/search?q=${encodeURIComponent(q)}`); },
};

/* --------------------------------- State ---------------------------------- */

const els = {
  tree: document.getElementById("tree"),
  search: document.getElementById("search"),
  results: document.getElementById("search-results"),
  editor: document.getElementById("editor"),
  preview: document.getElementById("preview"),
  currentPath: document.getElementById("current-path"),
  dirty: document.getElementById("dirty"),
  save: document.getElementById("save"),
  workspace: document.getElementById("workspace"),
};

const state = {
  currentPath: null,   // open file, relative to the vault
  activeDir: "",       // folder new items are created in
  dirty: false,
};

/* -------------------------------- Helpers --------------------------------- */

const joinPath = (dir, name) => (dir ? `${dir}/${name}` : name);
const parentDir = (p) => (p.includes("/") ? p.slice(0, p.lastIndexOf("/")) : "");
const hasMarkdownExt = (name) => /\.(md|markdown)$/i.test(name);
const escapeHtml = (s) => s.replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ------------------------------ File tree UI ------------------------------ */

function renderTree(children, container) {
  const ul = document.createElement("ul");
  for (const node of children) {
    const li = document.createElement("li");
    const row = document.createElement("div");
    row.className = "row";
    row.dataset.path = node.path;
    row.dataset.type = node.type;

    const twisty = document.createElement("span");
    twisty.className = "twisty";
    twisty.textContent = node.type === "dir" ? "▸" : "";
    row.appendChild(twisty);

    const label = document.createElement("span");
    label.className = "label";
    label.textContent = node.name;
    row.appendChild(label);

    const actions = document.createElement("span");
    actions.className = "row-actions";
    actions.innerHTML =
      '<button class="act rename" title="Rename">✎</button>' +
      '<button class="act delete" title="Delete">✕</button>';
    row.appendChild(actions);

    li.appendChild(row);

    if (node.type === "dir") {
      const nested = document.createElement("ul");
      nested.className = "children";
      renderTree(node.children, nested);
      li.appendChild(nested);

      row.addEventListener("click", (event) => {
        if (event.target.closest(".act")) return;
        nested.hidden = !nested.hidden;
        li.classList.toggle("collapsed", nested.hidden);
        state.activeDir = node.path;
        highlightSelection();
      });
    } else {
      row.addEventListener("click", (event) => {
        if (event.target.closest(".act")) return;
        state.activeDir = parentDir(node.path);
        openFile(node.path);
      });
    }

    ul.appendChild(li);
  }
  container.appendChild(ul);
}

function highlightSelection() {
  for (const row of document.querySelectorAll(".row")) {
    row.classList.toggle("selected", row.dataset.path === state.currentPath);
  }
}

async function refreshTree() {
  try {
    const data = await api.tree();
    els.tree.innerHTML = "";
    renderTree(data.children, els.tree);
    highlightSelection();
  } catch (error) {
    els.tree.innerHTML = `<p class="empty">Could not load notes: ${escapeHtml(error.message)}</p>`;
  }
}

/* ------------------------------- Open / save ------------------------------ */

// Autosave writes the open note after a short pause in typing, and flushes any
// pending edit before switching notes. Switching never prompts to discard.
const AUTOSAVE_DELAY = 1000; // ms of inactivity before an autosave fires

let autosaveTimer = null;
let switchToken = 0;    // bumps on every openFile() so stale loads are ignored
let saveChain = Promise.resolve();
let queuedSave = null;  // { path, content, silent, done } of the latest write
let pendingDelete = new Set(); // paths being deleted; autosaves to them are refused
let pendingRename = new Set(); // old paths being renamed; autosaves to them are refused

function frozenPath(p) {
  for (const set of [pendingDelete, pendingRename]) {
    for (const root of set) {
      if (p === root || p.startsWith(root + "/")) return true;
    }
  }
  return false;
}

function scheduleAutosave() {
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => {
    autosaveTimer = null;
    saveFile({ silent: true });
  }, AUTOSAVE_DELAY);
}

function cancelAutosave() {
  clearTimeout(autosaveTimer);
  autosaveTimer = null;
}

async function openFile(path) {
  const token = ++switchToken;
  if (state.currentPath === path) return;
  // Autosave (rather than prompt) before leaving the current note.
  if (state.dirty) {
    const saved = await saveFile();
    if (!saved) { scheduleAutosave(); return; } // save failed: stay, re-arm autosave
    if (token !== switchToken) return;          // a newer switch superseded this one
    if (state.dirty) { scheduleAutosave(); return; } // typed during the save
  }
  try {
    const data = await api.file(path);
    if (token !== switchToken) return;
    if (state.dirty) return;            // typed while loading; keep this note
    state.currentPath = data.path;
    state.dirty = false;
    els.editor.value = data.content;
    els.currentPath.textContent = data.path;
    updateDirty();
    renderPreview();
    highlightSelection();
    els.editor.focus();
  } catch (error) {
    alert(error.message);
  }
}

// Writes are serialized through one chain so an older save can never land after
// a newer one and leave stale content on disk.
function saveFile({ silent = false } = {}) {
  cancelAutosave();
  if (!state.currentPath) return Promise.resolve(true);

  const path = state.currentPath;
  const content = els.editor.value;

  // Reuse an identical write that is already queued or in flight.
  if (queuedSave && queuedSave.path === path && queuedSave.content === content) {
    if (!silent) queuedSave.silent = false; // surface failures to an explicit save
    return queuedSave.done;
  }

  const entry = { path, content, silent };
  entry.done = saveChain.then(async () => {
    try {
      // A stale save for a file that is no longer open is a no-op.
      if (state.currentPath !== path) return true;
      // A save for a path being deleted/renamed right now is refused (not
      // "saved") so callers abort rather than dropping edits; a write here
      // would recreate the doomed/old path.
      if (frozenPath(path)) return false;
      await api.save(path, content);
      // Only clear "unsaved" when the editor still matches what we wrote —
      // the user may have typed more while the request was in flight.
      if (state.currentPath === path && els.editor.value === content) {
        state.dirty = false;
        updateDirty();
      }
      return true;
    } catch (error) {
      if (!entry.silent) alert(error.message);
      return false;
    } finally {
      if (queuedSave === entry) queuedSave = null;
    }
  });
  saveChain = entry.done.then(() => {}, () => {});
  queuedSave = entry;
  return entry.done;
}

function updateDirty() {
  state.dirty ? els.dirty.classList.remove("hidden") : els.dirty.classList.add("hidden");
  els.save.disabled = !state.currentPath;
}

function closeFile() {
  state.currentPath = null;
  state.dirty = false;
  els.editor.value = "";
  els.currentPath.textContent = "No file open";
  els.preview.innerHTML = "";
  updateDirty();
  highlightSelection();
}

/* ------------------------------- Preview ---------------------------------- */

function renderPreview() {
  const text = els.editor.value;
  if (!text.trim()) {
    els.preview.innerHTML = '<p class="empty">Nothing to preview yet.</p>';
    return;
  }
  const html = marked.parse(text, { gfm: true, breaks: false });
  els.preview.innerHTML = DOMPurify.sanitize(html);
}

/* --------------------------- Create / rename / delete --------------------- */

async function newFile() {
  let name = prompt("New note name:", "untitled.md");
  if (name === null) return;
  name = name.trim();
  if (!name) return;
  if (!hasMarkdownExt(name)) name += ".md";
  const path = joinPath(state.activeDir, name);
  try {
    await api.createFile(path);
    await refreshTree();
    await openFile(path);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  const name = prompt("New folder name:");
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) return;
  const path = joinPath(state.activeDir, trimmed);
  try {
    await api.createFolder(path);
    await refreshTree();
  } catch (error) {
    alert(error.message);
  }
}

async function renameNode(path, type) {
  const current = path.split("/").pop();
  const next = prompt("Rename to:", current);
  if (next === null) return;
  const name = next.trim();
  if (!name || name === current) return;
  const to = joinPath(parentDir(path), name);
  // Flush the open note (or a note inside the renamed folder) before the move,
  // so a queued autosave cannot recreate the pre-rename path afterwards.
  const open = state.currentPath;
  if (open && (open === path || open.startsWith(path + "/"))) {
    cancelAutosave();
    if (state.dirty && !(await saveFile())) { scheduleAutosave(); return; }
    await saveChain;
  }
  pendingRename.add(path); // refuse autosaves to the old path while it moves
  try {
    await api.rename(path, to);
    if (state.currentPath === path) {
      state.currentPath = to;
    } else if (state.currentPath && state.currentPath.startsWith(path + "/")) {
      state.currentPath = to + state.currentPath.slice(path.length);
    }
    els.currentPath.textContent = state.currentPath || "No file open";
    await refreshTree();
  } catch (error) {
    alert(error.message);
  } finally {
    pendingRename.delete(path);
    // Edits typed during the rename are still unsaved and now belong to the
    // new path — re-arm so they are saved there (or to the old path if the
    // rename failed and the note is untouched).
    if (state.dirty && state.currentPath) scheduleAutosave();
  }
}

async function deleteNode(path, type) {
  const what = type === "dir" ? "folder" : "note";
  if (!confirm(`Delete ${what} "${path}"?`)) return;
  const open = state.currentPath;
  if (open && (open === path || open.startsWith(path + "/"))) {
    // Let in-flight writes settle, then refuse new autosaves to the doomed
    // path until the delete completes (or is cancelled/fails). The editor is
    // left untouched meanwhile, so edits are never lost prematurely.
    cancelAutosave();
    await saveChain;
    pendingDelete.add(path);
  }
  try {
    if (type === "dir") {
      try {
        await api.removeFolder(path, false);
      } catch (error) {
        if (/not empty/i.test(error.message)) {
          if (!confirm("That folder is not empty. Delete it and everything inside?")) return;
          await api.removeFolder(path, true);
        } else {
          throw error;
        }
      }
    } else {
      await api.removeFile(path);
    }
    if (state.currentPath === path ||
        (state.currentPath && state.currentPath.startsWith(path + "/"))) {
      closeFile();
    }
    await refreshTree();
  } catch (error) {
    alert(error.message);
  } finally {
    // Unfreeze the path. On a cancelled/failed delete the note is still open
    // with edits — re-arm the autosave so they are saved. On success
    // closeFile() already cleared the editor.
    pendingDelete.delete(path);
    if (state.dirty && state.currentPath) scheduleAutosave();
  }
}

/* --------------------------------- Search --------------------------------- */

let searchTimer = null;

function hideResults() {
  els.results.classList.add("hidden");
  els.tree.classList.remove("hidden");
}

function renderResults(query, results) {
  els.tree.classList.add("hidden");
  els.results.classList.remove("hidden");
  if (!results.length) {
    els.results.innerHTML = `<p class="empty">No matches for “${escapeHtml(query)}”.</p>`;
    return;
  }
  const list = document.createElement("ul");
  for (const hit of results) {
    const item = document.createElement("li");
    item.className = "result";
    const where = hit.line > 0 ? `${hit.path}:${hit.line}` : hit.path;
    item.innerHTML =
      `<div class="result-path">${escapeHtml(where)}</div>` +
      `<div class="result-line">${escapeHtml(hit.text)}</div>`;
    item.addEventListener("click", () => openFile(hit.path));
    list.appendChild(item);
  }
  els.results.innerHTML = "";
  els.results.appendChild(list);
}

async function runSearch(query) {
  try {
    const data = await api.search(query);
    renderResults(data.query, data.results);
  } catch {
    /* a failed search should not interrupt editing */
  }
}

/* --------------------------------- Wiring --------------------------------- */

els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const query = els.search.value.trim();
  if (query.length < 2) { hideResults(); return; }
  searchTimer = setTimeout(() => runSearch(query), 250);
});

els.search.addEventListener("keydown", (event) => {
  if (event.key === "Escape") { els.search.value = ""; hideResults(); }
});

let previewTimer = null;
els.editor.addEventListener("input", () => {
  if (!state.dirty) { state.dirty = true; updateDirty(); }
  clearTimeout(previewTimer);
  previewTimer = setTimeout(renderPreview, 120);
  scheduleAutosave();
});

// Tab inserts two spaces instead of moving focus.
els.editor.addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    const { selectionStart: start, selectionEnd: end, value } = els.editor;
    els.editor.value = value.slice(0, start) + "  " + value.slice(end);
    els.editor.selectionStart = els.editor.selectionEnd = start + 2;
  }
});

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    saveFile();
  }
});

document.getElementById("save").addEventListener("click", () => saveFile());
document.getElementById("new-file").addEventListener("click", newFile);
document.getElementById("new-folder").addEventListener("click", newFolder);
document.getElementById("refresh").addEventListener("click", refreshTree);

els.tree.addEventListener("click", (event) => {
  const button = event.target.closest(".act");
  if (!button) return;
  const row = button.closest(".row");
  if (button.classList.contains("rename")) renameNode(row.dataset.path, row.dataset.type);
  else if (button.classList.contains("delete")) deleteNode(row.dataset.path, row.dataset.type);
});

for (const button of document.querySelectorAll(".view-toggle button")) {
  button.addEventListener("click", () => {
    els.workspace.dataset.view = button.dataset.view;
    for (const other of document.querySelectorAll(".view-toggle button")) {
      other.classList.toggle("active", other === button);
    }
  });
}

window.addEventListener("beforeunload", (event) => {
  if (state.dirty) event.preventDefault();
});

// Flush pending edits when the tab is hidden (e.g. switching apps), so leaving
// the page for a while still saves. Beforeunload above stays as a final guard
// for an actual close.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden" && state.dirty) saveFile({ silent: true });
});

/* --------------------------------- Start ---------------------------------- */

marked.setOptions({ gfm: true, breaks: false });
refreshTree();
