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
| M0 | Scaffold              | Vite app + Express API wired end to end ("hello") |
| M1 | File tree             | Sidebar lists folders + `.md`; `GET /api/tree` |
| M2 | Read / edit / save    | File open, split editor + live preview, `Ctrl+S` save |
| M3 | Create / rename / delete | New file, new folder, rename, delete from the tree |
| M4 | Search                | Search box → matches across all notes |
| M5 | Polish                | Keyboard shortcuts, unsaved guard, styling |

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
