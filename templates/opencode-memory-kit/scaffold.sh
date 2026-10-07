#!/usr/bin/env bash
# Scaffold the cross-session tracker into the current directory (usually a
# fresh project repo). Creates tracker/STATE.md and an AGENTS.md with the
# tracker protocol section. Run from the project root:
#   ~/.config/opencode/memory-template/scaffold.sh
set -euo pipefail

KIT="${KIT:-$HOME/.config/opencode/memory-template}"

if [ ! -d "$KIT" ]; then
  echo "Template kit not found at $KIT" >&2
  exit 1
fi

mkdir -p tracker
cp "$KIT/tracker/STATE.md" tracker/STATE.md
echo "Created tracker/STATE.md"

if [ -f AGENTS.md ]; then
  if grep -q "Cross-session tracker protocol" AGENTS.md; then
    echo "AGENTS.md already has the protocol — left unchanged."
  else
    printf '\n' >> AGENTS.md
    cat "$KIT/AGENTS.section.md" >> AGENTS.md
    echo "Appended tracker protocol to AGENTS.md"
  fi
else
  cp "$KIT/AGENTS.section.md" AGENTS.md
  echo "Created AGENTS.md with the tracker protocol"
fi

echo
echo "Next: edit tracker/STATE.md (project name, Goal, Current state),"
echo "then commit:  git add AGENTS.md tracker/ && git commit -m \"Add tracker\""