# Custom MD

A tiny local markdown reader/editor — a Python 3 stdlib HTTP server with a vanilla-JS frontend, pointed at a folder of notes.

Custom MD serves a sidebar file tree (folders + `.md` files) and a live split preview with no build step and no dependencies. It stores everything as plain markdown files in a folder you choose ("the vault"), so your notes stay yours: portable, greppable, and editable in any other tool.

## AI disclosure

This application was made with AI assistance. It was developed through an
agent-assisted workflow using an AI coding agent (OpenCode / Big Pickle): the
primary agent wrote the implementation, while dedicated AI subagents reviewed
the code for security and correctness, wrote and ran the automated test suite,
and produced a large part of this documentation. A human directed the project,
made the product and design decisions, and reviewed the work throughout.

## Prerequisites

- **Python 3.9+** (the server uses `Path.is_relative_to`, added in 3.9)
- **Nothing else.** No pip installs — markdown rendering and sanitizing are done by `marked.min.js` and `purify.min.js` (DOMPurify), vendored in `app/static/vendor/`. The server and tests use only the standard library.

## Run it

```sh
cd app
python3 server.py
```

Then open <http://127.0.0.1:8765/>. The console prints the notes path, the URL, and `Ctrl+C` to stop.

### Options

| Flag         | Default                | What it does                     |
| ------------ | ---------------------- | -------------------------------- |
| `--notes`    | `../notes` (repo root) | Path to the notes vault          |
| `--host`     | `127.0.0.1`            | Bind address                     |
| `--port`     | `8765`                 | Port to listen on                |

Point it at another folder, e.g.:

```sh
python3 server.py --notes ~/my-notes
```

The folder is created if it doesn't exist. Everything the app can browse, edit, search, or delete lives under this root.

## Features

- **File tree** — expandable sidebar of folders and `.md`/`.markdown` notes; hidden files and symlinks are skipped.
- **Editor with live preview** — type on the left, rendered markdown (GFM) on the right. Toggle between **Split**, **Edit**, and **Preview** views.
- **Create / rename / delete** — notes and folders from the sidebar (`New note`, `New folder`, ✎, ✕ on each row). Empty folders delete directly; non-empty ones ask first.
- **Search** — case-insensitive search over note names and contents while you type (2+ characters); click a result to open it.
- **Autosave** — edits are saved to the open note about 1 second after you stop typing. Switching notes asks no questions: pending edits are saved automatically first, and hiding the tab (switching apps) flushes them too. The "● unsaved" indicator shows between a keystroke and the save; closing the tab with unsaved edits still warns.

### Keyboard shortcuts

| Key                     | Action                          |
| ----------------------- | ------------------------------- |
| `Ctrl+S` / `Cmd+S`      | Save the current note           |
| `Tab`                   | Insert two spaces (never leaves the editor) |
| `Escape` (in search)    | Clear the search box            |

## Project layout

```
custom MD/
├── app/
│   ├── server.py          # Python stdlib HTTP server + JSON file API
│   ├── static/
│   │   ├── index.html     # UI shell
│   │   ├── app.js         # front-end logic (vanilla JS, no build step)
│   │   ├── styles.css
│   │   └── vendor/        # marked (markdown -> HTML) + DOMPurify (sanitizer)
│   └── tests/
│       └── test_api.py    # integration tests for the file API
├── notes/                 # the default vault
└── README.md
```

## Tests

From the repo root:

```sh
python3 -m unittest discover -s app/tests -t .
```

The tests boot the real HTTP server on an ephemeral port against a throwaway temp folder, so your `notes/` are never touched. Standard library only.

## Releasing

Versions follow semantic versioning (a small feature bumps the minor number, e.g. `1.1.0`). See [`RELEASING.md`](RELEASING.md) for the full commit → tag → push → release checklist.

## How it stays safe

- **Local only** — binds to `127.0.0.1` by default.
- **Paths are jailed** — every API path is resolved and checked against the vault root; `..`, absolute paths, and symlink escapes are rejected.
- **Symlinks refused for edits** — create, rename, delete, and save refuse to operate on or through symlinks.
- **Markdown is sanitized** — preview HTML is run through DOMPurify after parsing, so note content can't run scripts in your page.
- **Sensible caps** — 5 MB per note and a 6 MB request body limit keep the server snappy.