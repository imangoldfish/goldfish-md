## Cross-session tracker protocol

Models do not share memory between sessions. `tracker/STATE.md` is the single
source of handoff truth — how a new session picks up where the last one left
off.

- **At the start** of a session: read `tracker/STATE.md` before doing anything
  else. If it lists unfinished work, continue it (or say what you are doing
  instead).
- **At the end**: update it — add one short entry to the Session log (what you
  changed, decisions + why, what is unfinished) and refresh **Status** and
  **Next up**.
- Keep entries short and concrete: file paths, commands, exact next steps, and
  the reason behind decisions. No essays.
- The log is append-only; **newest entry at the top**. Do not delete or rewrite
  other sessions' entries.
- Commit `tracker/STATE.md` together with the code it describes so handoff
  state is versioned like everything else.