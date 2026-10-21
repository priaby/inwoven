"""Install public releases and candidate trees without model calls."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

GH_VERSION = 'v2.102.0'
SKIPS = []


def notice(message):
    print('::warning::' + message, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(message + '\n\n')


def command(*args, cwd=None, allow_auth=False, quiet=False, expected=0):
    executable = shutil.which(args[0])
    if not executable:
        raise RuntimeError('Missing CLI: ' + args[0])
    argv = [executable, *args[1:]]
    if os.name == 'nt' and executable.endswith(('.cmd', '.bat')):
        import shlex
        argv = [shutil.which('bash'), '-c', shlex.join(argv)]
    env = dict(os.environ)
    if Path(executable).stem.lower() != 'gh':
        env.pop('GH_TOKEN', None)
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding='utf-8', timeout=180)
    output = result.stdout + result.stderr
    print('$ ' + ' '.join(args), flush=True)
    if not quiet: print(output, end='', flush=True)
    if result.returncode != expected:
        auth = ('authentication required', 'not logged in', 'log in to continue', 'login required')
        if allow_auth and any(phrase in output.lower() for phrase in auth):
            SKIPS.append(args[0])
            notice('SKIPPED ' + args[0] + ' install: host requires account authentication.')
            return None
        raise RuntimeError('Command exited ' + str(result.returncode) + '; expected ' + str(expected))
    return output


def installed_hook(plugin, root, host):
    config = json.loads((plugin / 'hooks/hooks.json').read_text(encoding='utf-8'))
    group = config['hooks']['PostToolUse'][0]
    assert 'Edit' in group['matcher']
    manifest = json.loads((plugin / 'plugin.json').read_text(encoding='utf-8'))
    legacy = os.environ.get('INWOVEN_SOURCE') == 'published' and manifest['version'] == '0.2.1'
    if host == 'codex':
        manifest = json.loads((plugin / 'plugin.json').read_text(encoding='utf-8'))
        # No non-interactive hook inventory in Codex 0.162.1. This is the
        # installed-cache proxy for legacy discovery, not a native trust receipt.
        # https://learn.chatgpt.com/docs/hooks
        # https://agent-plugins.org/specification#52-manifest-object
        try:
            assert '$schema' not in manifest, 'Codex legacy hook discovery disabled by $schema'
        except AssertionError:
            if os.environ.get('INWOVEN_SOURCE') != 'published' or manifest['version'] != '0.2.1':
                raise
            notice('KNOWN RELEASE DEFECT: published 0.2.1 has $schema; Codex hook discovery is unproven. Candidate must omit it.')
    hook_command = group['hooks'][0]['command']
    script = plugin / 'skills/inwoven/scripts/inwoven.py'
    assert script.is_file()
    if 'run-hook.sh' in hook_command:
        assert (plugin / 'hooks/run-hook.sh').is_file(), 'Installed launcher missing'
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(plugin))
    env.pop('GH_TOKEN', None)
    shell = shutil.which('bash' if os.name == 'nt' else 'sh')
    path = root / 'docs/product/backlog.md'
    for tool in (('Edit',) if host == 'claude' else ('apply_patch',)):
        # Published 0.2.1 predates apply_patch support; still exercise its installed
        # command through the compatible Edit event, with a visible limitation.
        if legacy: tool = 'Edit'
        tool_input = dict(file_path=str(path)) if tool == 'Edit' else dict(command='*** Begin Patch\n*** Update File: docs/product/backlog.md\n@@\n-x\n+y\n*** End Patch')
        payload = json.dumps(dict(session_id='install-ci', cwd=str(root), hook_event_name='PostToolUse',
                                 tool_name=tool, tool_input=tool_input, tool_response=dict(success=True)))
        result = subprocess.run([shell, '-c', hook_command], cwd=root, env=env, input=payload,
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        assert result.returncode == 2 and 'restore separator' in result.stderr, result
        assert result.stdout == '', result.stdout
    print('Installed ' + host + ' hook rejected broken backlog with exit 2.', flush=True)


def exercise(script, root, plugin=None, host=None):
    assert script.is_file(), 'Missing installed script: ' + str(script)
    root.mkdir()
    command('git', 'init', str(root))
    command(sys.executable, str(script), 'init', 'backlog', 'goals', 'impact', 'wardley', 'learnings', cwd=root)
    command(sys.executable, str(script), 'check', cwd=root)
    path = root / 'docs/product/backlog.md'
    path.write_text(path.read_text(encoding='utf-8').replace('|---|---|---|---|---|\n', ''), encoding='utf-8')
    output = command(sys.executable, str(script), 'check', cwd=root, expected=1)
    assert 'restore separator' in output, output
    if plugin: installed_hook(plugin, root, host)


def hosts(candidate=False):
    os.environ['INWOVEN_SOURCE'] = 'candidate' if candidate else 'published'
    source = str(Path(__file__).resolve().parents[1]) if candidate else 'priaby/inwoven'
    tag = os.environ.get('GITHUB_REF_NAME', '')
    pinned = not candidate and os.environ.get('GITHUB_REF_TYPE') == 'tag' and re.fullmatch(r'v\d+\.\d+\.\d+', tag)
    with tempfile.TemporaryDirectory(prefix='installed consumer ') as tmp:
        tmp = Path(tmp)
        home = Path.home()
        for host, add in (('claude', 'install'), ('codex', 'add')):
            command(host, '--version')
            if command(host, 'plugin', 'marketplace', 'add', source + (('#' if host == 'claude' else '@') + tag if pinned else ''), allow_auth=True) is None: continue
            if command(host, 'plugin', add, 'inwoven@inwoven', allow_auth=True) is None: continue
            if host == 'claude':
                output = command('claude', 'plugin', 'details', 'inwoven')
                assert 'inwoven' in output and 'Skills' in output and 'PostToolUse' in output, output
                cache = home / '.claude/plugins/cache'
            else:
                output = command('codex', 'plugin', 'list')
                assert 'inwoven' in output and 'enabled' in output.lower(), output
                cache = home / '.codex/plugins/cache'
            scripts = list(cache.rglob('skills/inwoven/scripts/inwoven.py'))
            assert scripts, 'No installed skill under ' + str(cache)
            plugin = scripts[0].parents[3]
            if pinned:
                assert json.loads((plugin / 'plugin.json').read_text())['version'] == tag[1:]
            exercise(scripts[0], tmp / host, plugin, host)
        if candidate or os.environ.get('GITHUB_EVENT_NAME') == 'schedule' or len(SKIPS) == 2:
            assert not SKIPS, 'Install coverage incomplete: ' + ', '.join(SKIPS)
        consumer = tmp / 'gh'
        consumer.mkdir()
        args = ['gh', 'skill', 'install', source, 'inwoven', '--agent', 'claude-code']
        if candidate: args.append('--from-local')
        if pinned: args.extend(['--pin', tag])
        command(*args, cwd=consumer)
        exercise(consumer / '.claude/skills/inwoven/scripts/inwoven.py', tmp / 'gh-run')


def gh_cli():
    release = json.loads(command('gh', 'api', 'repos/cli/cli/releases/tags/' + GH_VERSION, quiet=True))
    arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'amd64'
    system = {'Linux': 'linux', 'Darwin': 'macOS', 'Windows': 'windows'}[platform.system()]
    suffix = system + '_' + arch + ('.tar.gz' if system == 'linux' else '.zip')
    asset = next(a for a in release['assets'] if a['name'].endswith(suffix))
    checksums = next(a for a in release['assets'] if a['name'].endswith('_checksums.txt'))
    dest = Path(os.environ['RUNNER_TEMP']) / 'inwoven-gh'
    dest.mkdir(exist_ok=True)
    archive = dest / asset['name']
    urllib.request.urlretrieve(asset['browser_download_url'], archive)
    checksum_file = dest / checksums['name']
    urllib.request.urlretrieve(checksums['browser_download_url'], checksum_file)
    entries = dict((name.lstrip('*'), digest) for digest, name in
                   (line.split(maxsplit=1) for line in checksum_file.read_text().splitlines()))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == entries[asset['name']], 'GitHub CLI checksum mismatch'
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as z: z.extractall(dest)
    else:
        with tarfile.open(archive) as z: z.extractall(dest, filter='data')
    binary = next(dest.rglob('gh.exe' if os.name == 'nt' else 'gh'))
    if os.name != 'nt': binary.chmod(0o755)
    with open(os.environ['GITHUB_PATH'], 'a', encoding='utf-8') as stream: stream.write(str(binary.parent) + '\n')
    command(str(binary), 'version')


def release():
    with tempfile.TemporaryDirectory(prefix='release consumer ') as tmp:
        tmp = Path(tmp)
        tag = os.environ.get('GITHUB_REF_NAME', '')
        pinned = os.environ.get('GITHUB_REF_TYPE') == 'tag' and re.fullmatch(r'v\d+\.\d+\.\d+', tag)
        args = ['gh', 'release', 'download'] + ([tag] if pinned else [])
        command(*args, '--repo', 'priaby/inwoven', '--pattern', 'inwoven.zip', '--dir', str(tmp))
        with zipfile.ZipFile(tmp / 'inwoven.zip') as z:
            names = z.namelist()
            assert 'inwoven/SKILL.md' in names and 'inwoven/scripts/inwoven.py' in names
            assert all(n.startswith('inwoven/') and '..' not in Path(n).parts for n in names)
            assert not any('/tests/' in n or '/hooks/' in n or '/.github/' in n for n in names)
            z.extractall(tmp)
        if pinned:
            import base64
            manifest = json.loads(base64.b64decode(command('gh', 'api', 'repos/priaby/inwoven/contents/plugin.json?ref=' + tag, '--jq', '.content', quiet=True)))
            assert manifest['version'] == tag[1:]
        exercise(tmp / 'inwoven/scripts/inwoven.py', tmp / 'zip-run')


if __name__ == '__main__':
    {'hosts': hosts, 'candidate': lambda: hosts(True), 'gh-cli': gh_cli, 'release': release}[sys.argv[1]]()
