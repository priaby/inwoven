#!/bin/sh
# Claude shell form: sh on Unix, Git Bash on Windows. Keep stdin for the hook.
script="$CLAUDE_PLUGIN_ROOT/skills/inwoven/scripts/inwoven.py"
for runtime in python3 python; do
  if command -v "$runtime" >/dev/null 2>&1 && "$runtime" -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then
    exec "$runtime" "$script" hook
  fi
done
if command -v py >/dev/null 2>&1 && py -3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' >/dev/null 2>&1; then
  exec py -3 "$script" hook
fi
printf "%s\n" "Inwoven check skipped: python3 not found" >&2
exit 0
