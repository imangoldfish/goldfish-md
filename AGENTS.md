# AGENTS.md — Custom MD

**Custom MD** is a local markdown reader/editor: a Python 3 stdlib HTTP
server with a vanilla-JS frontend, pointed at a folder of markdown notes
("the vault"). No build step, no third-party dependencies in the app.

## Where things are

- `README.md` — user-facing docs (run it, features, shortcuts, safety)
- `PLAN.md` — architecture, milestones (M0–M5), agent team workflow
- `RELEASING.md` — commit → tag → push → GitHub release checklist
- `app/server.py` — stdlib HTTP server + JSON file API
- `app/static/` — vanilla JS UI + vendored `marked` / `DOMPurify`
- `app/tests/test_api.py` — integration tests for the file API
- `notes/` — the default vault; **user data, not code**. Leave loose sample
  notes alone unless the task is about the vault itself.
- `tracker/STATE.md` — the cross-session state tracker (see protocol below)
- `templates/opencode-memory-kit/` — the reusable tracker kit (AGENTS section
  snippet + `tracker/STATE.md` seed + `scaffold.sh`); installed copy at
  `~/.config/opencode/memory-template` is a symlink to this

## Commands

- Run the app: `cd app && python3 server.py` → http://127.0.0.1:8765/
- Run tests (from repo root): `python3 -m unittest discover -s app/tests -t .`

## Non-negotiable ground rules

- **Stdlib only** for server and tests; the frontend is vanilla JS with
  `marked` + `DOMPurify` vendored. No new dependencies, no build step.
- **File-API jail:** resolve and check every path against the vault root;
  reject `..`, absolute paths, and symlink escapes. Mutating ops
  (create/rename/delete/save) refuse symlinks entirely.
- **Sanitize rendered markdown** before it enters the DOM.
- Keep `README.md` / `PLAN.md` / `RELEASING.md` current when behavior changes
  (the `docs` agent does this).

## Cross-session tracker protocol

Models do not share memory between sessions. `tracker/STATE.md` is the single
source of handoff truth — it is how a new session picks up where the last one
left off.

- **At the start** of a session: read `tracker/STATE.md` before doing anything
  else. If it says there is unfinished work, continue it (or say what you are
  doing instead).
- **At the end**: update it — add one short entry to the Session log (what you
  changed, decisions + why, what is unfinished) and refresh **Status** and
  **Next up**.
- Keep entries short and concrete: file paths, commands, exact next steps, and
  the reason behind decisions. No essays.
- The log is append-only; **newest entry at the top**. Do not delete or rewrite
  other sessions' entries.
- Commit `tracker/STATE.md` together with the code it describes so handoff
  state is versioned like everything else.

## Agent roster (from PLAN.md)

- Primary agent: does the build (that's you, when you are the main session).
- `reviewer` — read-only; reviews changes for correctness + file-API security,
  reports blocker / major / minor findings, never edits.
- `tester` — writes and runs API tests against a throwaway temp vault.
- `docs` — may only edit `README.md` and files under `docs/`.
- `explore` — read-only research when a library/API is unclear.

Hand work to subagents through the existing `.opencode/agents/*.md`
definitions, and make each task self-contained (subagents run in fresh
sessions and do not share this conversation).