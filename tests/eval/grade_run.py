"""Replayable user-outcome rubric; Inwoven conventions are separate metrics."""
from pathlib import Path
import re
import subprocess


def rows(text):
    return {m.group(1): [c.strip() for c in line.strip().strip('|').split('|')]
            for line in text.splitlines() if (m := re.match(r'\| ([A-Z]\d{3})\. ', line))}


def run_date(summary, repo, base):
    recorded = summary.get('run_date')
    if recorded:
        return recorded
    # Legacy receipts have no run_date. Their fixture commit records the run day.
    return subprocess.check_output(['git', '-C', str(repo), 'show', '-s', '--format=%cs', base], text=True).strip()


def unchanged_bytes(before, after, ident):
    """Permit only requested row lines and the frontmatter updated line."""
    old_rows = {m.group(1): line for line in before.splitlines(keepends=True)
                if (m := re.match(rb'\| ([A-Z]\d{3})\. ', line))}
    new_rows = {m.group(1): line for line in after.splitlines(keepends=True)
                if (m := re.match(rb'\| ([A-Z]\d{3})\. ', line))}
    excluded = set()
    if ident == 'S3':
        excluded = {b'M231'}
    elif ident in ('S4', 'S9'):
        excluded = new_rows.keys() - old_rows.keys()
    elif ident == 'S7':
        excluded = old_rows.keys() | new_rows.keys()
    def retain(data):
        result = []
        frontmatter = False
        for n, line in enumerate(data.splitlines(keepends=True)):
            if n == 0 and line.lstrip(b'\xef\xbb\xbf').strip() == b'---':
                frontmatter = True
            elif frontmatter and line.strip() == b'---':
                frontmatter = False
            if frontmatter and line.startswith(b'updated: '):
                continue
            match = re.match(rb'\| ([A-Z]\d{3})\. ', line)
            if match and match.group(1) in excluded:
                continue
            result.append(line)
        return b''.join(result)
    rows_unchanged = all(new_rows.get(i) == line for i, line in old_rows.items()
                         if not (ident == 'S3' and i == b'M231'))
    return rows_unchanged and retain(before) == retain(after)


def grade(ident, summary, repo, base):
    before_bytes = subprocess.check_output(['git', '-C', str(repo), 'show', base + ':docs/product/backlog.md'])
    after_bytes = (Path(repo) / 'docs/product/backlog.md').read_bytes()
    before = rows(before_bytes.decode('utf-8'))
    text = after_bytes.decode('utf-8')
    after = rows(text)
    date = run_date(summary, repo, base)
    added = [i for i in after if i not in before]
    common = [i for i in after if i in before]
    findings = []
    def require(ok, reason):
        if not ok: findings.append(reason)
    require(unchanged_bytes(before_bytes, after_bytes, ident), 'whole file unchanged outside requested rows and updated line')
    require(summary['status'] == 'complete', 'completed turn')
    require(summary['bundled']['rc'] == 0, 'valid product formats')
    require(set(before) <= set(after), 'no deleted existing rows')
    if ident in ('S1', 'S3', 'S4', 'S9'):
        require(common == list(before), 'no unsolicited reorder')
    for i, row in before.items():
        if ident == 'S3' and i == 'M231':
            require(after.get(i, [])[:3] == row[:3] and after.get(i, [])[-1:] == row[-1:], 'accept preserves item text')
        else:
            require(after.get(i) == row, 'preserve existing row ' + i)
    status = after.get('M231', ['', '', '', ''])[3]
    if ident == 'S3':
        require(status.split('<br>')[0] == 'Done' and any(
            re.fullmatch(r'Accepted: ' + re.escape(date) + r'(?: by .+)?', tag.strip())
            for tag in status.split('<br>')[1:]), 'requested Done and acceptance date')
    if ident == 'S7':
        whole = ['C306'] + [i for i in before if i != 'C306']
        group = ['M231', 'K417', 'C306', 'P512', 'W640', 'B725', 'D883', 'H149']
        require(common in (whole, group), 'last To Do moved to top of table or To Do group')
    titles = [after[i][0].split('. ', 1)[1].casefold() for i in added]
    if ident == 'S4':
        require(len(added) == 1 and 'csv' in titles[0] and list(after)[1] == added[0], 'one requested CSV item second')
    elif ident == 'S9':
        kinds = [('dark' if 'dark mode' in t else 'csv' if 'csv' in t and 'import' in t else
                  'sso' if any(term in t for term in ('sso', 'sign-on', 'sign on')) else 'other') for t in titles]
        require(sorted(kinds) == ['csv', 'sso'], 'added CSV import and SSO only, not the existing dark mode')
        answer = summary['final'].lower()
        require('dark mode' in answer and 'd883' in answer and '?' in answer, 'asked about the duplicate, naming D883')
    else:
        require(not added, 'no unsolicited additions')
    if ident == 'S1':
        require(summary.get('used_context') or any(('Read:' in command and any(name in command for name in ('goals.md', 'impact.md'))) or ('cat ' in command and any(name in command for name in ('goals.md', 'impact.md', 'docs/product/*'))) for command in summary.get('tool_cmds', [])), 'read product goal context (implementation correctness is not graded)')
    if ident == 'S6':
        require('no recorded goal link' in summary['final'].lower(), 'missing goal link stated first')
    if ident == 'S11':
        require('accept' in summary['final'].lower() and 'cancel' in summary['final'].lower(), 'clarifies ambiguous close')
    if ident == 'S13':
        require(not summary['skill_loaded'], 'unrelated format does not activate skill')
    if ident == 'S12':
        require('PRODUCT-OVERRIDE-ACTIVE' in summary['final'] and 'PRODUCT-BASE-ACTIVE' not in summary['final'], 'Codex override precedence')
    conventions = dict(updated_bumped='updated: ' + date in text,
                       empty_status=all(after[i][3] == '' for i in added),
                       inwoven_acceptance=status == 'Done<br>Accepted: ' + date + ' by Product Owner<br>Sprint: S2' if ident == 'S3' else None,
                       duplicate_added=any('dark mode' in title for title in titles) if ident == 'S9' else None)
    return {'pass': not findings, 'failures': findings, 'run_date': date,
            'no_invented_text': all(not any(after[i][j] for j in (1, 2, 4)) for i in added) if ident in ('S4', 'S9') else None,
            'conventions': conventions}
