"""Public CLI behavior; stdlib only, no service imports or private files."""
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest

TREE = Path(__file__).resolve().parents[1]
SCRIPT = TREE / 'skills/inwoven/scripts/inwoven.py'
FIXTURES = TREE / 'tests/fixtures'
KINDS = ('backlog', 'goals', 'impact', 'wardley')


def run(*args, **kwargs):
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8', **kwargs)


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True, encoding='utf-8').stdout


class PublicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='inwoven space ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'product files'
        shutil.copytree(FIXTURES / 'valid', self.root)

    def test_files_and_crlf(self):
        for variant in ('valid', 'crlf', 'broken'):
            for kind in KINDS:
                with self.subTest(variant=variant, kind=kind):
                    path = FIXTURES / variant / (kind + '.md')
                    result = run('check', path)
                    self.assertEqual(result.returncode, 1 if variant == 'broken' else 0, result.stderr)
                    if variant == 'broken':
                        self.assertRegex(result.stderr, re.escape(str(path)) + r':\d+: ')
        mutations = {'backlog': ('K418', 'K417'), 'goals': ('Next', 'Now'),
                     'impact': ('    - K417', '      - K417'), 'wardley': ('| Genesis |', '| Unknown |')}
        for kind, (old, new) in mutations.items():
            path = self.root / (kind + '.md')
            before = path.read_text(encoding='utf-8')
            path.write_text(before.replace(old, new), encoding='utf-8')
            self.assertEqual(run('check', path).returncode, 1, kind)
            path.write_text(before, encoding='utf-8')
        self.assertEqual(run('check', '--root', self.root).returncode, 0)
        alternate = self.root / 'another name.md'
        shutil.copyfile(self.root / 'backlog.md', alternate)
        self.assertEqual(run('check', '--kind', 'backlog', alternate).returncode, 0)
        self.assertEqual(run('check', alternate).returncode, 1)

    def test_frontmatter(self):
        text = (TREE / 'skills/inwoven/SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\n'))
        fields = dict(line.split(':', 1) for line in text.split('---', 2)[1].strip().splitlines())
        self.assertEqual(fields['name'].strip().strip('"'), 'inwoven')
        self.assertTrue(1 <= len(fields['description'].strip().strip('"')) <= 200)
        self.assertNotIn(': ', fields['description'])
        self.assertTrue(fields['description'].strip().startswith('"'))
        self.assertLessEqual(len(text.splitlines()), 104)
        self.assertLessEqual(set(fields), {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'})

    def test_new_id_and_errors(self):
        result = run('new-id', '--count', 100, '--root', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        ids = result.stdout.splitlines()
        self.assertEqual(len(set(ids)), 100)
        used = set(re.findall(r'\b[A-Z]\d{3}\b', ''.join(p.read_text(encoding='utf-8') for p in self.root.glob('*.md'))))
        self.assertFalse(set(ids) & used)
        for ident in ids:
            self.assertRegex(ident, r'\A[ABCDEFGHJKLMNPRSTUVWXYZ][1-9][0-9]{2}\Z')
        self.assertNotEqual(run('new-id', '--count', 0, '--root', self.root).returncode, 0)

    def test_new_id_does_not_reuse_history(self):
        git(self.root, 'init')
        history = self.root / 'deleted ids.txt'
        alphabet = 'ABCDEFGHJKLMNPRSTUVWXYZ'
        history.write_text(' '.join(letter + str(n) for letter in alphabet for n in range(100, 1000)
                                    if letter + str(n) != 'Z999'), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'ids')
        history.unlink()
        result = run('new-id', '--root', self.root)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, 'Z999'), result.stderr)
        self.assertEqual(run('new-id', '--count', 2, '--root', self.root).returncode, 1)

    def test_hook_interpreter_fallbacks(self):
        command = json.loads((TREE / 'hooks/hooks.json').read_text())['hooks']['PostToolUse'][0]['hooks'][0]['command']
        bins = Path(self.tmp.name) / 'only runtimes'
        bins.mkdir()
        shell = shutil.which('bash' if os.name == 'nt' else 'sh')
        if os.name == 'nt':
            posix_bins = subprocess.check_output([shell, '-c', 'cygpath -u "$1"', 'stub-path', str(bins)], text=True).strip()
            runtime_path = posix_bins + ':/usr/bin'
        else:
            (bins / 'sh').symlink_to(shell)
            runtime_path = str(bins)
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(TREE), PATH=runtime_path)
        path = self.root / 'backlog.md'
        shutil.copyfile(FIXTURES / 'broken/backlog.md', path)
        payload = json.dumps(dict(tool_name='Write', tool_input=dict(file_path=str(path)), cwd=str(self.root)))
        for name in ('python3', 'python', 'py', None):
            with self.subTest(runtime=name):
                for binary in ('python3', 'python', 'py'):
                    target = bins / binary
                    if target.exists(): target.unlink()
                # Model a Store alias or unavailable interpreter with a nonzero probe.
                for unavailable in ('python3', 'python'):
                    if unavailable == name: break
                    target = bins / unavailable
                    target.write_text('#!/bin/sh\nexit 9009\n')
                    target.chmod(0o755)
                if name:
                    wrapper = bins / name
                    wrapper.write_text('#!/bin/sh\n' + ('shift\n' if name == 'py' else '') +
                                       'exec ' + shlex.quote(Path(sys.executable).as_posix()) + ' "$@"\n')
                    wrapper.chmod(0o755)
                result = subprocess.run([shell, '-c', command], env=env, input=payload,
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 2 if name else 0, result.stderr)
                self.assertEqual(result.stdout, '')
                if not name:
                    self.assertEqual(result.stderr, 'Inwoven check skipped: python3 not found\n')

    def test_guard_reports_stale_updated(self):
        git(self.root, 'init')
        path = self.root / 'backlog.md'
        before = path.read_text(encoding='utf-8').replace('updated: 2026-10-13', 'updated: 2000-01-01')
        path.write_text(before, encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'base')
        self.assertEqual(run('guard', '--base', 'HEAD', '--root', self.root).returncode, 0)
        path.write_text(before.replace('In Progress', 'Done'), encoding='utf-8')
        result = run('guard', '--base', 'HEAD', '--root', self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn('updated: unchanged; set updated to ', result.stdout)
        import datetime
        path.write_text(path.read_text(encoding='utf-8').replace('2000-01-01', datetime.date.today().isoformat()), encoding='utf-8')
        self.assertNotIn('updated: unchanged', run('guard', '--base', 'HEAD', '--root', self.root).stdout)

    def test_guard_without_git(self):
        result = run('guard', '--base', 'HEAD', '--root', self.root, env=dict(os.environ, PATH=''))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (2, '', 'inwoven: guard needs git on PATH\n'))

    def test_codex_apply_patch_scope(self):
        command = json.loads((TREE / 'hooks/hooks.json').read_text())['hooks']['PostToolUse'][0]['hooks'][0]['command']
        shell = shutil.which('bash' if os.name == 'nt' else 'sh')
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(TREE))
        git(self.root, 'init')
        git(self.root, 'add', '.')
        git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'base')
        def invoke(patch):
            payload = json.dumps(dict(hook_event_name='PostToolUse', tool_name='apply_patch',
                                      tool_input=dict(command=patch), cwd=str(self.root)))
            return subprocess.run([shell, '-c', command], input=payload, env=env,
                                  capture_output=True, text=True, encoding='utf-8')
        for kind in KINDS:
            with self.subTest(kind=kind):
                path = self.root / (kind + '.md')
                before = path.read_bytes()
                shutil.copyfile(FIXTURES / 'broken' / path.name, path)
                patch = '*** Begin Patch\n*** Update File: README.md\n+x\n*** Update File: ' + path.name + '\n@@\n-x\n+y\n*** End Patch'
                for event_patch in (patch, patch.replace('\n', '\r\n'), '\n' + patch, '\ufeff' + patch,
                                    patch.replace(path.name + '\n', path.name + '  \n')):
                    result = invoke(event_patch)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(path.name + ':', result.stderr)
                    self.assertEqual(result.stdout, '')
                path.write_bytes(before)
        # Requested deletion stays silent instead of suggesting init.
        (self.root / 'backlog.md').unlink()
        result = invoke('*** Begin Patch\n*** Delete File: backlog.md\n*** End Patch')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        # Moving a product file away also stays silent.
        goals = self.root / 'goals.md'
        goals.rename(self.root / 'old-goals.md')
        result = invoke('*** Begin Patch\n*** Update File: goals.md\n*** Move to: old-goals.md\n*** End Patch')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        # Foreign files with the same basename are ignored when neither text is Inwoven.
        foreign = self.root / 'another folder'
        foreign.mkdir()
        (foreign / 'backlog.md').write_text('# Foreign format')
        result = invoke('*** Begin Patch\n*** Add File: another folder/backlog.md\n+# Foreign format\n*** End Patch')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        # A move checks its destination as well as the original path.
        moved = foreign / 'goals.md'
        shutil.copyfile(FIXTURES / 'broken/goals.md', moved)
        result = invoke('*** Begin Patch\n*** Update File: README.md\n*** Move to: another folder/goals.md\n@@\n-x\n+y\n*** End Patch')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('goals.md:', result.stderr)
        # Malformed tool inputs remain non-blocking.
        self.assertEqual(invoke('not a patch').returncode, 0)

    def test_hook_without_git(self):
        path = self.root / 'backlog.md'
        shutil.copyfile(FIXTURES / 'broken/backlog.md', path)
        payload = json.dumps(dict(tool_name='Edit', tool_input=dict(file_path=str(path)), cwd=str(self.root)))
        result = run('hook', env=dict(os.environ, PATH=''), input=payload)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('updated', result.stderr)
        path.write_text('# Foreign format', encoding='utf-8')
        result = run('hook', env=dict(os.environ, PATH=''), input=payload)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))

    def test_populated_separator_width(self):
        path = self.root / 'backlog.md'
        text = path.read_text(encoding='utf-8')
        for width in (2, 7):
            path.write_text(text.replace('|---|---|---|---|---|', '|' + '---|' * width), encoding='utf-8')
            self.assertEqual(run('check', path).returncode, 0)

    def test_context(self):
        result = run('context', 'K417', '--root', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        for label in ('K417', 'Goal:', 'Measure:', 'Actor:', 'Component:'):
            self.assertIn(label, result.stdout)
        for kind in KINDS[1:]:
            (self.root / (kind + '.md')).unlink()
        result = run('context', 'K417', '--root', self.root)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Missing goals.md', result.stdout)
        self.assertEqual(run('context', 'Z999', '--root', self.root).returncode, 1)

    def test_init_preserves_bytes(self):
        empty = self.root / 'new folder'
        result = run('init', *KINDS, '--root', empty)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(run('check', '--root', empty).returncode, 0)
        before = {p: p.read_bytes() for p in empty.iterdir()}
        self.assertEqual(run('init', *KINDS, '--root', empty).returncode, 0)
        self.assertEqual(before, {p: p.read_bytes() for p in empty.iterdir()})
        default = self.root / 'default'
        self.assertEqual(run('init', '--root', default).returncode, 0)
        self.assertEqual([p.name for p in default.iterdir()], ['backlog.md'])

    def test_guard(self):
        git(self.root, 'init')
        git(self.root, 'add', '.')
        git(self.root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'base')
        self.assertEqual(run('guard', '--base', 'HEAD', '--root', self.root).returncode, 0)
        path = self.root / 'backlog.md'
        before = path.read_text(encoding='utf-8')
        path.write_text(before.replace('In Progress', 'Done'), encoding='utf-8')
        result = run('guard', '--base', 'HEAD', '--root', self.root)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('newly Done: K417', result.stdout)
        self.assertIn('Nothing was changed.', result.stdout)
        self.assertEqual(run('guard', '--base', 'missing-ref', '--root', self.root).returncode, 2)
        path.write_text(before.replace('K418', 'K417'), encoding='utf-8')
        self.assertEqual(run('guard', '--base', 'HEAD', '--root', self.root).returncode, 2)

    def test_hook_command(self):
        config = json.loads((TREE / 'hooks/hooks.json').read_text(encoding='utf-8'))
        command = config['hooks']['PostToolUse'][0]['hooks'][0]['command']
        # Claude shell form: sh -c on Unix; Git Bash on Windows runners.
        shell = shutil.which('bash' if os.name == 'nt' else 'sh')
        self.assertIsNotNone(shell)
        plugin = Path(self.tmp.name) / 'plugin with spaces'
        shutil.copytree(TREE, plugin, ignore=shutil.ignore_patterns('__pycache__'))
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(plugin), PYTHONUTF8='1')
        bad = self.root / 'backlog.md'
        shutil.copyfile(FIXTURES / 'broken/backlog.md', bad)
        readme = self.root / 'README.md'
        readme.write_text('Unrelated text', encoding='utf-8')
        for path, expected in ((bad, 2), (readme, 0)):
            event = dict(session_id='ci-test', transcript_path='', cwd=str(self.root),
                         hook_event_name='PostToolUse', tool_name='Write',
                         tool_input=dict(file_path=str(path), content=path.read_text(encoding='utf-8')),
                         tool_response=dict(success=True), tool_use_id='ci-write')
            result = subprocess.run([shell, '-c', command], input=json.dumps(event), env=env,
                                    capture_output=True, text=True, encoding='utf-8', cwd=self.root)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertEqual(result.stdout, '')
            if expected:
                self.assertIn('updated', result.stderr)
                self.assertIn('backlog.md:', result.stderr)
            else:
                self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
