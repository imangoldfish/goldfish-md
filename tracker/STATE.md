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
- `README.md`, `PLAN.md`, `RELEASING.md` are current; agent definitions
  describe the Python stdlib backend accurately.
- Test suite covers the file API, traversal/symlink rejection, and edge
  cases. Run it from the repo root:

  ```sh
  python3 -m unittest discover -s app/tests -t .
  ```

## Next up

- [ ] Pick the next feature (see backlog below) — human is drafting V2 ideas;
      do not pick unilaterally.

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

#### 2026-10-07 — state handoff update
- Picked up "Next up": verified the stale-agent-definition item is already
  fixed — all three `.opencode/agents/*.md` describe the Python stdlib backend.
- Fixed the last stale stack reference: `PLAN.md` M0 row said "Vite app +
  Express API" → now "Python stdlib server + static UI".
- Left `notes/` user data (untracked test notes) alone, per AGENTS.md.
- Unfinished: next feature un-chosen — human is drafting V2 ideas (backlog).

#### 2026-10-07 — autosave release + handoff polish
- Added autosave to the editor (`app/static/app.js`): debounced ~1s save, flush
  on file switch (no more "unsaved?" confirm), writes serialized so an older
  save can't clobber a newer one, autosaves refused for paths mid-rename/delete
  (no ghost recreation of moved/deleted notes), hidden-tab flush.
- Reviewer ran 3 passes; round-1 majors (write ordering, rename/delete
  resurrection, typing-during-switch) and round-2 major (delete discarding
  edits before success) all fixed; final verdict: ready to merge. Tester added
  4 PUT tests (33 total, all green). Docs agent updated the README autosave
  bullet.
- Released: tagged + pushed `v1.1.0`, created the GitHub release
  (github.com/imangoldfish/goldfish-md/releases/tag/v1.1.0).
- Added `RELEASING.md` (release checklist) + README link; committed, pushed.
  User asked to learn git/GitHub — handed them the tag-vs-release model.
- Fixed the stale "Express backend" wording in `.opencode/agents/tester.md`
  (the only stale agent definition); `reviewer.md`/`docs.md` were already
  Python-stdlib.
- Unfinished: next feature not chosen yet (see backlog below).

#### 2026-10-07 — bootstrap (this tracker)
- Set up the cross-session tracker protocol: `AGENTS.md` (always loaded,
  stable guidance) + `tracker/STATE.md` (volatile state, read on demand).
- Seeded this file with the current project state (v1.1.0, M0–M5 done).
- Flagged for a future session: `tester.md` agent definition still says
  "Express backend"; it should describe the Python stdlib server.