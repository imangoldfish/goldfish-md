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
End with the exact command(s) that verify the claims. Keep it to a few lines.
```

#### 2026-10-07 — verified the kit improvements landed
- Reviewed the implementation against the brief: all 6 changes present.
  - Protocol text identical between global `~/.config/opencode/AGENTS.md` and
    `AGENTS.section.md` (`diff` over the section = clean).
  - Seed template Format block ends with verify-command line; compaction +
    privacy rules in template and README; `scaffold.sh` emits
    `tracker/.gitignore`.
- Committed a cosmetic trailing-newline fix to `AGENTS.section.md` (leftover
  from the interrupted edit noted below); kit repo is now clean.
- Unfinished: nothing blocking; V2 feature pick still with the human.
- Verify: `git -C ~/Programming/OpenCode/opencode-memory-kit status` (clean) ·
  protocol `diff` global/vs/section (clean) ·
  `python3 -m unittest discover -s app/tests -t .`

#### 2026-10-07 — applied the improvement brief to the kit
- Implemented the review's 6 changes in `opencode-memory-kit`:
  verify-before-claiming (grep docs when closing a "Next up" item),
  rebase-before-write (fetch + re-read before appending), "no code changes
  this session" fallback entries, verify-command lines in the Format block,
  compaction to `tracker/archive/STATE-YYYY.md`, privacy rules with untracked
  `tracker/.scratch.md`.
- Global `~/.config/opencode/AGENTS.md` wording is now identical to
  `AGENTS.section.md`; `scaffold.sh` also emits `tracker/.gitignore`.
- Only this project's Format block changed — no existing entries touched.
- One hiccup: a permission prompt timed out mid-edit (user was away), so the
  kit write was interrupted and had to be redone; the global hook had already
  updated, causing a transient section-vs-global mismatch. Lesson: do
  section + global writes sequentially, or check both after.
- Verify: `git -C opencode-memory-kit diff HEAD --stat` ·
  `~/.config/opencode/memory-template/scaffold.sh` in a temp dir ·
  global/section `diff`.

#### 2026-10-07 — review tracker system + handoff brief
- Reviewed the cross-session tracker system based on firsthand use (found
  drift: tracker claimed docs current while `PLAN.md` M0 was stale; plus
  concurrent-session clobbering risk).
- Wrote `~/Programming/OpenCode/tracker-improvements-brief.md` — a
  self-contained improvement spec (verify-before-claiming-done, rebase-before-
  write, cheap fallback entry, verify lines, compaction, privacy hygiene) for
  the implementing agent to apply to `opencode-memory-kit` + global
  `~/.config/opencode/AGENTS.md`. Saved outside this repo so the user can hand
  it to the other agent directly.
- Unfinished: kit improvements pending implementation; V2 features still
  un-chosen (human is drafting ideas).

#### 2026-10-07 — kit README (hiatus note)
- Added `README.md` to `~/Programming/OpenCode/opencode-memory-kit` — a
  welcome-back note so a future me can tell at a glance what the kit is,
  how it's installed (symlink), how to use it, and what improvements are
  available. Intentionally local/personal — no remote created, per the user.

#### 2026-10-07 — move kit out of this project → its own repo
- Moved `templates/opencode-memory-kit/` out of this repo to
  `~/Programming/OpenCode/opencode-memory-kit`, now its own git repo
  (commit 1257d0c, local identity only — no global git identity set).
- Re-pointed the `~/.config/opencode/memory-template` symlink to the new
  home; scaffolder verified working through it.
- Supersedes the earlier "keep the kit in this repo" decision: the kit is
  generic tooling, not Custom MD code, so it belongs outside the project.
- Tip for future: set `git config --global user.name/user.email` so new
  repos don't need manual identity setup.

#### 2026-10-07 — global kit + versioned template
- Promoted the tracker idea to a reusable system: a **global hook**
  (`~/.config/opencode/AGENTS.md`, auto-loaded in every workspace) plus a
  memory kit (`AGENTS.section.md`, `tracker/STATE.md` seed, `scaffold.sh`).
- Kit is versioned in this repo at `templates/opencode-memory-kit/`;
  `~/.config/opencode/memory-template` is a **symlink** to it — single source
  of truth, no drift.
- New-project setup from now on:
  `~/.config/opencode/memory-template/scaffold.sh`
- Decision: keep the kit in this repo (no dotfiles repo exists yet) — move it
  to a dotfiles repo later if one appears, re-pointing the symlink.
- Unfinished: nothing blocking; next real feature still un-chosen (human is
  drafting V2 ideas).

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