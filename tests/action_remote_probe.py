"""Capture the remote composite's actual Python result, without changing its status."""
import os
from pathlib import Path
import shlex
import sys

root = Path(os.environ['RUNNER_TEMP']) / 'inwoven-remote-probe'
root.mkdir(exist_ok=True)
log = root / 'diagnostics.log'
status = root / 'exit-code'
wrapper = root / 'python3'
wrapper.write_text('#!/bin/bash\n' +
                   shlex.quote(Path(sys.executable).as_posix()) + ' "$@" > "$INWOVEN_REMOTE_LOG" 2>&1\n' +
                   'result=$?\ncat "$INWOVEN_REMOTE_LOG"\n' +
                   'printf "%s\\n" "$result" > "$INWOVEN_REMOTE_STATUS"\nexit "$result"\n')
wrapper.chmod(0o755)
with open(os.environ['GITHUB_PATH'], 'a', encoding='utf-8') as stream:
    stream.write(str(root) + '\n')
with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as stream:
    stream.write('INWOVEN_REMOTE_LOG=' + str(log) + '\n')
    stream.write('INWOVEN_REMOTE_STATUS=' + str(status) + '\n')
