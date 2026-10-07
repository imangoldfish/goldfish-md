# Custom MD — Project Plan

A personal markdown reader/editor: a small, local-first IDE for `.md` files.
Write, read, browse, and search a folder of markdown notes from a clean web UI.

## Goal

A local web app that behaves like a mini IDE for markdown:

- Sidebar file tree with **folders** and `.md` files
- Click a note to **read/edit** it with a **live preview** beside the editor
- **Create / rename / delete** files and folders
- **Search** across all notes
- Everything stored as **plain `.md` files on disk** (no lock-in)

## Architecture

```
Browser (vanilla JS UI)  <--HTTP-->  Python server  <-->  notes/ folder on disk
```

A browser cannot freely read/write arbitrary folders, so a tiny local server
owns the notes directory and exposes safe file operations. This also gives us
real search and a clean path to wrapping the app as a desktop app later.

### Stack

| Layer     | Choice                          | Why |
|-----------|---------------------------------|-----|
| Frontend  | Vanilla HTML / CSS / JS         | No build step, no dependencies to learn |
| Backend   | Python 3 stdlib `http.server`   | Already installed; zero third-party packages |
| Markdown  | `marked` + `DOMPurify` (vendored) | Render + sanitize (a note must never inject scripts) |
| Editor    | `<textarea>` → CodeMirror (later) | Start simple, upgrade for highlighting |
| Search    | Backend recursive scan          | No index needed at this scale |

## Security rules (non-negotiable)

- The API only ever touches paths **inside** the notes root.
- Every user-supplied path is resolved and checked; reject traversal (`..`),
  absolute paths, and symlinks escaping the root.
- Mutating operations (create/rename/delete/save) refuse symlinks entirely:
  an in-vault symlink must not redirect a write or delete to the wrong file.
- Server binds to `127.0.0.1` only.
- Rendered markdown is sanitized before insertion into the DOM.

## Milestones

| #  | Milestone             | Outcome |
|----|-----------------------|---------|
| M0 | Scaffold              | Python stdlib server + static UI wired end to end ("hello") |
| M1 | File tree             | Sidebar lists folders + `.md`; `GET /api/tree` |
| M2 | Read / edit / save    | File open, split editor + live preview, `Ctrl+S` save |
| M3 | Create / rename / delete | New file, new folder, rename, delete from the tree |
| M4 | Search                | Search box → matches across all notes |
| M5 | Polish                | Keyboard shortcuts, unsaved guard, styling |
| M6 | Import & highlight (1.2) | Import `.md` from the device (drag-drop + button), preview syntax highlighting, collapsible sidebar, theme toggle, editor polish |

## Release 1.2 — Milestone M6

Scope decided with the human (2026-10-07); implemented in commit `4aa820f`
(v1.2). Mostly frontend, plus two small `server.py` guards that landed with
it: `/api/rename` rejects file renames that drop a markdown extension (400),
and the static route rejects NUL-embedded paths with 400 instead of a 500.

- **Import into the vault**: drag & drop `.md` files anywhere on the window, or
  use the "Open from device" button. Files are copied into the active folder
  via the existing API. On a name collision, auto-suffix `name (1).md` (never
  overwrite an existing note). Non-markdown and hidden (dot-prefixed) files are
  refused with a message; a failed write cleans up its empty partial note.
- **Syntax highlighting in the preview**: a hand-rolled, dependency-free
  tokenizer in `app/static/highlight.js` (no new vendor files) highlights
  fenced code blocks for js/ts, python, html, css, json, bash, sql. Runs on the
  already-sanitized DOM; output only ever contains escaped text + token spans.
  Sticky regexes keep scanning linear; blocks over 64 KB fall back to plain
  text so the preview never stalls on a huge block.
- **Collapsible sidebar**: a ☰ toggle in the toolbar hides/shows the file
  tree; preference persisted in `localStorage`.
- **Theme toggle**: a ☀️ / 🌙 / 🖥️ toolbar button cycles light, dark, and
  system (auto-follow OS); persisted in `localStorage` and applied before
  first paint to avoid a flash. Previously the app only followed the OS.
- **Editor polish**: JotBird-style layout refinement (typography + spacing) —
  the split editor + live preview already exist.
- **`welcome.md`**: rewritten as a walkthrough with an example for every
  markdown feature, ending with 3 sample notes.

Not in scope (future): importing whole folders via drag-drop, in-editor
highlighting (textarea → CodeMirror), highlight languages beyond the seven
above.

## Agent team

The **primary agent** (`build`) orchestrates and does the main implementation.
Subagents run in **fresh child sessions** and receive self-contained tasks.

| Agent      | Mode     | Responsibility |
|------------|----------|----------------|
| `reviewer` | subagent | Read-only review of diffs for correctness + file-API security |
| `tester`   | subagent | Writes and runs tests against the file API |
| `docs`     | subagent | Maintains `README.md` and user documentation |
| `explore`  | builtin  | Read-only research when a library/API is unclear |

### Workflow

```
plan a milestone  ->  build it (primary)  ->  reviewer  ->  tester  ->  docs
```

Subagents do **not** share the conversation, so every task handed to one must
be self-contained and name the concrete paths/scopes it should inspect.

## Repo layout

```
custom MD/
├── .opencode/agents/   # reviewer.md, tester.md, docs.md
├── PLAN.md             # this file
├── README.md
├── notes/              # the markdown vault (sample notes)
└── app/
    ├── server.py       # Python stdlib file API + static server
    └── static/         # index.html, styles.css, app.js, vendor/
```
