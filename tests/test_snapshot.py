"""Pre/post snapshots must never attribute the person's earlier edits to the agent."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from test_public import FIXTURES, git, run
import shutil


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='inwoven snapshot ')
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.state = Path(self.tmp.name) / 'outside repo'
        self.state.mkdir()
        self.env = dict(os.environ, TMPDIR=str(self.state), TEMP=str(self.state), TMP=str(self.state))
        shutil.copytree(FIXTURES / 'valid', self.repo)
        git(self.repo, 'init')
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=Acme', '-c', 'user.email=acme@example.invalid', 'commit', '-m', 'base')
        self.path = self.repo / 'backlog.md'
        self.before = self.path.read_text(encoding='utf-8')

    def event(self, phase, session='person-session', call='call-1', path=None):
        payload = dict(session_id=session, tool_use_id=call, cwd=str(self.repo),
                       hook_event_name=phase, tool_name='Edit', tool_input=dict(file_path=str(path or self.path)))
        return run('hook', input=json.dumps(payload), env=self.env)

    def context(self, result):
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        return json.loads(result.stdout)['hookSpecificOutput']['additionalContext'] if result.stdout else ''

    def test_only_this_call_changes_not_person_uncommitted_changes(self):
        manual = self.before.replace('In Progress', 'Done<br>Accepted: 2026-10-14', 1)
        self.path.write_text(manual, encoding='utf-8')
        self.assertEqual(self.context(self.event('PreToolUse')), '')
        self.path.write_text(manual.replace('In Progress', 'Done', 1), encoding='utf-8')
        context = self.context(self.event('PostToolUse'))
        self.assertIn('Did the person ask in this conversation for K418 to be Done? If not, undo it now.', context)
        self.assertNotIn('K417', context)
        self.assertNotIn('Keep it only', context)
        self.assertEqual(list(self.state.rglob('*.json')), [])
        self.assertEqual(self.context(self.event('PostToolUse')), '')

    def test_housekeeping_is_not_request_gated(self):
        self.event('PreToolUse')
        self.path.write_text(self.before.replace('In Progress', 'Done', 1), encoding='utf-8')
        context = self.context(self.event('PostToolUse'))
        date_line = next(line for line in context.splitlines() if 'updated' in line)
        self.assertNotIn('Did the person', date_line)
        self.assertIn('Set updated to ', date_line)

    def test_no_snapshot_untracked_and_new_file_are_format_only(self):
        self.path.write_text(self.before.replace('In Progress', 'Done', 1), encoding='utf-8')
        self.assertEqual(self.context(self.event('PostToolUse')), '')
        git(self.repo, 'rm', '--cached', 'backlog.md')
        self.event('PreToolUse')
        self.path.write_text(self.before, encoding='utf-8')
        self.assertEqual(self.context(self.event('PostToolUse')), '')
        self.path.unlink()
        self.event('PreToolUse')
        self.path.write_text(self.before, encoding='utf-8')
        self.assertEqual(self.context(self.event('PostToolUse')), '')
        self.assertEqual(list(self.state.rglob('*.json')), [])

    def test_session_and_tool_call_isolation(self):
        self.event('PreToolUse')
        self.path.write_text(self.before.replace('In Progress', 'Done', 1), encoding='utf-8')
        self.assertEqual(self.context(self.event('PostToolUse', session='other')), '')
        self.assertEqual(self.context(self.event('PostToolUse', call='other')), '')
        self.assertIn('K417 to be Done', self.context(self.event('PostToolUse')))

    def test_invalid_format_still_cleans_snapshot_and_exits_two(self):
        self.event('PreToolUse')
        self.path.write_text('broken', encoding='utf-8')
        result = self.event('PostToolUse')
        self.assertEqual((result.returncode, result.stdout), (2, ''))
        self.assertIn('restore backlog header', result.stderr)
        self.assertEqual(list(self.state.rglob('*.json')), [])

    def test_cancelled_call_cleanup_and_bounds(self):
        # Stale snapshots cannot be replayed. A successful post consumes its snapshot.
        self.event('PreToolUse')
        files = list(self.state.rglob('*.json'))
        self.assertEqual(len(files), 1)
        os.utime(files[0], (1, 1))
        self.path.write_text(self.before.replace('In Progress', 'Done', 1), encoding='utf-8')
        self.assertEqual(self.context(self.event('PostToolUse')), '')
        self.assertEqual(list(self.state.rglob('*.json')), [])
        for n in range(40):
            self.event('PreToolUse', session='s' + str(n))
        self.assertLessEqual(len(list(self.state.rglob('*.json'))), 32)
        self.assertFalse(any(self.repo.rglob('*snapshot*')))

    def test_session_end_removes_pending_snapshots(self):
        self.event('PreToolUse')
        self.assertTrue(list(self.state.rglob('*.json')))
        self.assertEqual(self.context(self.event('SessionEnd')), '')
        self.assertEqual(list(self.state.rglob('*.json')), [])

    def test_oversized_source_and_missing_call_identity_are_format_only(self):
        self.path.write_text(self.before + '# padding\n' * 110000, encoding='utf-8')
        self.event('PreToolUse')
        self.assertEqual(list(self.state.rglob('*.json')), [])
        self.path.write_text(self.before, encoding='utf-8')
        self.event('PreToolUse', call='')
        self.path.write_text(self.before.replace('In Progress', 'Done', 1), encoding='utf-8')
        self.assertEqual(self.context(self.event('PostToolUse', call='')), '')

    def test_patch_move_has_no_row_reminder(self):
        patch = '*** Begin Patch\n*** Update File: backlog.md\n*** Move to: old-backlog.md\n@@\n-x\n+y\n*** End Patch'
        event = dict(session_id='move', tool_use_id='call', cwd=str(self.repo), tool_name='apply_patch', tool_input=dict(command=patch))
        run('hook', input=json.dumps(dict(event, hook_event_name='PreToolUse')), env=self.env)
        self.path.rename(self.repo / 'old-backlog.md')
        result = run('hook', input=json.dumps(dict(event, hook_event_name='PostToolUse')), env=self.env)
        context = self.context(result)
        self.assertEqual(context, '')
        self.assertNotIn('to be added', context)

    def test_temp_override_inside_another_checkout_never_stores_product_text(self):
        other = Path(self.tmp.name) / 'another checkout'
        other.mkdir()
        git(other, 'init')
        state = other / 'temp'
        state.mkdir()
        env = dict(self.env, TMPDIR=str(state), TEMP=str(state), TMP=str(state))
        event = dict(session_id='outside-product', tool_use_id='call', cwd=str(other), hook_event_name='PreToolUse',
                     tool_name='Edit', tool_input=dict(file_path=str(self.path)))
        run('hook', input=json.dumps(event), env=env)
        self.assertEqual(list(state.rglob('*.json')), [])

    def test_corrupt_snapshot_does_not_suppress_format_errors(self):
        self.event('PreToolUse')
        saved = next(self.state.rglob('*.json'))
        saved.write_text('{partial', encoding='utf-8')
        self.path.write_text('broken', encoding='utf-8')
        result = self.event('PostToolUse')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(self.state.rglob('*.json')), [])

    def test_non_product_paths_never_access_snapshot_store(self):
        self.event('PreToolUse')
        saved = next(self.state.rglob('*.json'))
        os.utime(saved, (1, 1))
        self.event('PreToolUse', path=self.repo / 'notes.txt')
        self.assertTrue(saved.exists())  # No TTL sweep for unrelated paths.
        self.event('PostToolUse', path=self.repo / 'notes.txt')
        self.assertTrue(saved.exists())

    def test_malformed_patch_payload_is_silent(self):
        event = dict(session_id='malformed', hook_event_name='PreToolUse', tool_name='apply_patch', tool_input=['bad'])
        result = run('hook', input=json.dumps(event), env=self.env)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        self.assertEqual(list(self.state.iterdir()), [])

    def test_invalid_sibling_preserves_backlog_reminder(self):
        patch = '*** Begin Patch\n*** Update File: backlog.md\n*** Update File: goals.md\n*** End Patch'
        event = dict(session_id='siblings', tool_use_id='call', cwd=str(self.repo), tool_name='apply_patch', tool_input=dict(command=patch))
        run('hook', input=json.dumps(dict(event, hook_event_name='PreToolUse')), env=self.env)
        self.path.write_text(self.before.replace('In Progress', 'Done', 1), encoding='utf-8')
        (self.repo / 'goals.md').write_text('broken', encoding='utf-8')
        result = run('hook', input=json.dumps(dict(event, hook_event_name='PostToolUse')), env=self.env)
        self.assertEqual(result.returncode, 2)
        self.assertIn('K417 to be Done', result.stderr)
        self.assertIn('restore goals header', result.stderr)

    def test_move_checks_destination_format_only(self):
        patch = '*** Begin Patch\n*** Update File: backlog.md\n*** Move to: moved/backlog.md\n*** End Patch'
        event = dict(session_id='rename', tool_use_id='call', cwd=str(self.repo), tool_name='apply_patch', tool_input=dict(command=patch))
        run('hook', input=json.dumps(dict(event, hook_event_name='PreToolUse')), env=self.env)
        target = self.repo / 'moved/backlog.md'
        target.parent.mkdir()
        self.path.rename(target)
        target.write_text('broken', encoding='utf-8')
        result = run('hook', input=json.dumps(dict(event, hook_event_name='PostToolUse')), env=self.env)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Did the person', result.stderr)
        self.assertIn(str(target), result.stderr)
