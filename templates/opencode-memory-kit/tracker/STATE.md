# <Project name> — State Tracker

The cross-session handoff file. Every session **reads this first** and
**updates it last** (newest log entry at the top). See the tracker protocol
section in `AGENTS.md` (or the global one in `~/.config/opencode/AGENTS.md`).

**Last updated:** <date>
**Status:** <e.g. In progress / blocked / released vX.Y.Z — one line>

## Goal

<one line — what this project is trying to be>

## Current state

- <what exists now: features done, versions released, docs current>
- <how to run it / test it — the exact commands>
- <anything important a stranger must know>

## Next up

- [ ] <the next actionable step>
- [ ] <...>

## Ideas backlog (not started)

- <ideas for later, so they never get lost>

## Session log

Append-only. Newest entry at the top.

```text
Format:
#### <date> — <role / what this session was for>
What happened · decisions + why · unfinished work · concrete next step.
Keep it to a few lines.
```

#### <date> — bootstrap
- Set up this tracker (edit Goal / Current state to match the real project
  before the first real session uses it).
- Add your first session-log entry here when you finish a piece of work.