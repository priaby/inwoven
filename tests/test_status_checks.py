"""Z325: check fails a malformed Done only on rows whose Status cell changed since git HEAD."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TREE = Path(__file__).resolve().parents[1]
SCRIPT = TREE / 'skills/inwoven/scripts/inwoven.py'
HEAD = ("# T\n\n| Item (PBI) | Core Job | Context | Status | Driver |\n| --- | --- | --- | --- | --- |\n")


def row(ident, status):
    return f'| {ident}. Title {ident} |  | ctx | {status} |  |\n'


def check(root):
    done = subprocess.run([sys.executable, '-I', str(SCRIPT), 'check', '--root', str(root)],
                          capture_output=True, text=True, encoding='utf-8')
    return done.returncode, done.stderr


def git(root, *args):
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=t', '-c', 'user.email=t@t', *args], check=True,
                   capture_output=True)


class StatusCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.file = self.root / 'backlog.md'

    def commit(self, text):
        self.file.write_text(text, encoding='utf-8')
        git(self.root, 'init', '-q') if not (self.root / '.git').exists() else None
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-qm', 'x')

    def test_unchanged_rows_pass(self):
        self.commit(HEAD + row('K417', 'Done') + row('A123', 'Complete') + row('B234', 'Done<br>Sprint: S1'))
        code, err = check(self.root)
        self.assertEqual(code, 0, err)

    def test_changed_and_new_rows_fail_with_the_fix(self):
        self.commit(HEAD + row('K417', 'In Progress') + row('A123', 'In Progress') + row('B234', 'In Progress'))
        self.file.write_text(HEAD + row('K417', 'Done') + row('A123', 'In Progress<br>Accepted: 2026-10-01 by PO')
                             + row('B234', 'done') + row('C345', 'Complete') + row('D456', 'Blocked')
                             + row('E567', 'in progress') + row('F678', 'Done<br>Accepted: 2026-10-01 by PO<br>From: Blocked'),
                             encoding='utf-8')
        code, err = check(self.root)
        self.assertEqual(code, 1)
        for text in ('K417 is Done without an `Accepted:` note', 'A123 has an `Accepted:` note but is not Done',
                     "B234 status 'done' differs only in case", "C345 status 'Complete' is not a status",
                     "E567 status 'in progress' differs only in case or spacing; write `In Progress` exactly"):
            self.assertIn(text, err)
        self.assertNotIn('D456 status', err)  # another legacy word stays allowed
        self.assertNotIn('F678', err)

    def test_from_done_is_flagged_on_a_changed_row(self):
        self.commit(HEAD + row('K417', 'In Progress'))
        self.file.write_text(HEAD + row('K417', 'Done<br>Accepted: 2026-10-01 by PO<br>From: Done'), encoding='utf-8')
        code, err = check(self.root)
        self.assertEqual(code, 1)
        self.assertIn('K417 has `From: Done`', err)

    def test_without_head_they_warn(self):
        self.file.write_text(HEAD + row('K417', 'Done'), encoding='utf-8')
        code, err = check(self.root)
        self.assertEqual(code, 0, err)
        self.assertIn('warning: K417 is Done without', err)


if __name__ == '__main__':
    unittest.main()
