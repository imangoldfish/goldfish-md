# Custom MD — State Tracker

The cross-session handoff file. Every session **reads this first** and
**updates it last** (newest log entry at the top). See `AGENTS.md` for the
protocol.

**Last updated:** 2026-10-07
**Status:** Released (v1.1.0) — active development ongoing

## Goal

A tiny local markdown reader/editor: plain `.md` files in a folder you choose,
served by a Python stdlib server behind a vanilla-JS split editor. Notes stay
yours — portable, greppable, editable in any other tool.

## Current state

- All plan milestones (M0–M5) implemented: file tree, read/edit with live
  preview, create/rename/delete, search, polish (shortcuts + autosave).
- `v1.1.0` tagged and pushed (autosave + `RELEASING.md`). Remote:
  `github.com/imangoldfish/goldfish-md`.
- `README.md`, `PLAN.md`, `RELEASING.md` are current.
- Test suite covers the file API, traversal/symlink rejection, and edge
  cases. Run it from the repo root:

  ```sh
  python3 -m unittest discover -s app/tests -t .
  ```

## Next up

- [ ] Fix stale agent definitions: `.opencode/agents/tester.md` (and the
      descriptions in `reviewer.md` / `docs.md`) still say "Express backend" —
      this project is Python stdlib. Update them to match reality.
- [ ] Pick the next feature (see backlog below).

## Ideas backlog (not started)

- Upgrade the editor to CodeMirror — PLAN.md says "start simple, upgrade for
  highlighting".
- Wrap the app as a desktop app — mentioned in PLAN.md as a later step.
- Whatever you (the human) decide next.

## Session log

Append-only. Newest entry at the top.

```text
Format:
#### <date> — <role / what this session was for>
What happened · decisions + why · unfinished work · concrete next step.
Keep it to a few lines.
```

#### 2026-10-07 — bootstrap (this tracker)
- Set up the cross-session tracker protocol: `AGENTS.md` (always loaded,
  stable guidance) + `tracker/STATE.md` (volatile state, read on demand).
- Seeded this file with the current project state (v1.1.0, M0–M5 done).
- Flagged for a future session: `tester.md` agent definition still says
  "Express backend"; it should describe the Python stdlib server.