# Custom MD — State Tracker

The cross-session handoff file. Every session **reads this first** and
**updates it last** (newest log entry at the top). See `AGENTS.md` for the
protocol.

**Last updated:** 2026-10-07
**Status:** v1.2.0 released (import, preview highlighting, collapsible sidebar, theme toggle, welcome.md walkthrough) · v1.1.0 released earlier · the "v1.2.1 hold" is moot — those fixes rode inside v1.2.0 (see log entry below)

## Goal

A tiny local markdown reader/editor: plain `.md` files in a folder you choose,
served by a Python stdlib server behind a vanilla-JS split editor. Notes stay
yours — portable, greppable, editable in any other tool.

## Current state

- All plan milestones (M0–M6) implemented: file tree, read/edit with live
  preview, create/rename/delete, search, polish (shortcuts + autosave), and
  v1.2's import (drag-drop + button), preview syntax highlighting
  (`highlight.js`), collapsible sidebar, `welcome.md` walkthrough.
- `v1.1.0` tagged and pushed (autosave + `RELEASING.md`). Remote:
  `github.com/imangoldfish/goldfish-md`. v1.2 changes sit in commit `4aa820f`
  (not yet tagged).
- `README.md`, `PLAN.md`, `RELEASING.md` are current; agent definitions
  describe the Python stdlib backend accurately.
- Test suite covers the file API, traversal/symlink rejection, and edge
  cases (41 tests). Run it from the repo root:

  ```sh
  python3 -m unittest discover -s app/tests -t .
  ```

## Next up

- [x] v1.2.0 tagged + released (this session, commit `03ebc6e` + follow-ups). The
      other session's "these fixes become v1.2.1" plan is moot: its fixes
      (autosave resurrection guard, rename-keeps-md, NUL 400 — in `4aa820f` /
      `eda28c4`) are ancestors of the v1.2.0 tag, so v1.2.0 already includes
      them. A v1.2.1 tag now would be a no-op — reserve v1.2.1 for NEW fixes.
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

#### 2026-10-07 — release v1.2.0 (theme toggle + review fixes)
- User asked for a theme toggle on top of the 1.2 build: toolbar ☀️/🌙/🖥️
  button cycles Light/Dark/System, persisted in `localStorage.custommd.theme`,
  applied pre-paint by an inline `<head>` script (no flash). CSS reworked so
  `data-theme` overrides `prefers-color-scheme` (light forces light, dark
  forces dark, unset/system follows the OS). Verified cycle + persistence.
- Reviewer pass on the follow-up increment: 0 blockers, 0 majors, 3 minors —
  all fixed: byte-accurate `file.size` check restored *before* `file.text()`;
  failed-save cleanup now GETs the note and deletes only if still empty (a
  write whose response was lost is never deleted); dropped folders detected
  via `webkitGetAsEntry().isDirectory` and refused with their own message
  (also catches a folder literally named `foo.md`).
- Browser test caught a real regression the reviewer missed: `importFiles`
  used `.filter(isImportableName)` which passes the *File object*, not its
  name string → every import silently refused ("Skipped 1…"). Fixed to
  `.filter((f) => isImportableName(f.name))`. Re-verified drop-import,
  `name (1).md` collision, oversize refusal, hidden-name refusal in-browser.
- highlight.js sticky-regex review came back clean (linear scan, no infinite
  loop; >64 KB blocks fall back to plain escaped text).
- Docs agent added 4 README bullets (import, theme toggle, collapsible
  sidebar, preview highlighting). `welcome.md` image is now an inline SVG.
- Suite 42/42. Tagged `v1.2.0`, pushed, GitHub release created.
- Note for the other session: your v1.2.1-hold plan is moot (details in Next
  up) — v1.2.1 is free for NEW fixes only.
- Verify: `python3 -m unittest discover -s app/tests -t .` (42 OK) ·
  `git tag` shows v1.2.0 · `gh release view v1.2.0` · drop a .md in the
  browser and watch it land in the tree.

#### 2026-10-07 — validation pass: reviewer + tester + docs (v1.2 context)
- User asked for a fresh reviewer/tester/docs pass. Reviewer found a MAJOR in
  the autosave work: a stale in-flight `openFile()` for a note being
  deleted/renamed could apply later and resurrect it on the next keystroke.
  Fixed in `app/static/app.js` with `pendingPath` + `invalidateOpenUnder()`
  (bumps `switchToken` right after confirm so the doomed path's GET is
  dropped), plus easy wins: Tab-key edits now mark the note dirty (they were
  silently lost — programmatic edits don't fire `input`), renames keep the
  `.md` extension (UI appends it; `server.py` `/api/rename` returns 400 for
  file targets without a markdown extension; folder renames unrestricted),
  and the static route rejects NUL bytes with 400 instead of a 500.
- Tester re-ran the suite and added 7 gap tests (folder-rename guards,
  recursive delete, search pruning, PUT validation) — 40/40. After my fixes
  the suite is 41/41.
- Re-review: no blockers; two minors applied (double-open `finally` guard now
  keyed on `token === switchToken`; bare-stem rename `foo.md`→`foo` becomes a
  no-op instead of a confusing 409). Deliberately kept `invalidateOpenUnder`
  early (right after confirm): moving it later reopens the resurrection
  window during `await saveChain`; its only cost is dropping an in-flight open
  when a mutation is later aborted, which is safe (user re-clicks).
- Docs agent refreshed `README.md` (rename-keeps-markdown bullet;
  `highlight.js` in the layout list). I corrected `PLAN.md`'s M6 section —
  it claimed `server.py` was untouched; it isn't (rename guard + NUL 400).
- Surprise found mid-session: a concurrent session committed `4aa820f`
  ("1.2: import, highlight, collapsible sidebar, welcome.md") and its
  `git add -A` swept my then-uncommitted fixes into it. Verified the final
  tree is correct and pushed. No tag now: the human said another agent owns
  v1.2.0 (tag/release); these fixes are held to be tagged v1.2.1 afterwards.
- Verify: `python3 -m unittest discover -s app/tests -t .` (41 OK) ·
  `git log --oneline -3` (4aa820f on top of 47bddc8).

#### 2026-10-07 — tester: fresh suite validation + gap coverage
- Ran the existing suite fresh: 33/33 OK against a throwaway temp vault (real
  server, ephemeral port; repo `notes/` untouched, left its untracked user
  files alone).
- Added 7 tests to `app/tests/test_api.py` for real coverage gaps (no
  production changes): folder rename (disk move, root-rename 400 guard,
  folder-into-itself 400 guard), recursive folder DELETE over a nested tree +
  sibling survival, DELETE /api/file on a folder → 400, search pruning
  (hidden/non-md/symlink/oversized, incl. filename-match on non-md), PUT
  missing/non-string content → 400. Suite now 40/40.
- Verify: `python3 -m unittest discover -s app/tests -t .` (Ran 40 tests, OK).

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

#### 2026-10-07 — kit restructure: template vs live split
- Moved the kit's seed materials to `template/` and made `tracker/STATE.md`
  the kit's own live tracker (its own `.gitignore`); added a project
  `AGENTS.md` for the kit; `scaffold.sh` + README + global hook footer
  updated to match.
- Why: the user wants to run sessions directly inside the kit repo — the old
  layout would have made sessions read the seed template as if it were live
  state. The kit now self-hosts: it runs the same protocol it ships.
- Verify: `~/.config/opencode/memory-template/scaffold.sh` smoke test
  (generates tracker/ + .gitignore + AGENTS.md from `template/`) ·
  `git -C opencode-memory-kit status` clean · commit `c37def0`.

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