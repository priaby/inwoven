"""Self-contained public metadata checks; no private repository dependencies."""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

TREE = Path(__file__).resolve().parents[1]
SKILL = TREE / 'skills/inwoven/SKILL.md'


def frontmatter(text):
    if not text.startswith('---\n'):
        return {}
    match = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
    if not match:
        raise ValueError('unterminated frontmatter')
    fields = {}
    for line in match[1].splitlines():
        key, separator, value = line.partition(': ')
        if not separator or not re.fullmatch(r'[a-z][a-z0-9_-]*', key) or key in fields:
            raise ValueError('invalid or duplicate frontmatter key')
        if value.startswith('"'):
            value = json.loads(value)
            if not isinstance(value, str): raise ValueError('expected string')
        elif ': ' in value or ' #' in value or value.startswith(tuple('!&*{}[],#|>@`%-?:')):
            raise ValueError('ambiguous frontmatter scalar')
        fields[key] = value
    return fields


class MetadataTests(unittest.TestCase):
    def test_manifest_and_install_metadata(self):
        root = json.loads((TREE / 'plugin.json').read_text())
        self.assertEqual(root, json.loads((TREE / '.claude-plugin/plugin.json').read_text()))
        self.assertRegex(root['version'], r'\A(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z')
        market = json.loads((TREE / '.claude-plugin/marketplace.json').read_text())
        self.assertEqual(market['name'], root['name'])
        for plugin in market['plugins']:
            self.assertEqual(plugin['name'], root['name'])
            self.assertTrue((TREE / plugin['source'] / 'skills/inwoven/SKILL.md').is_file())
        readme = (TREE / 'README.md').read_text()
        for prefix in ('/plugin install ', 'codex plugin add '):
            self.assertIn(prefix + root['name'] + '@' + market['name'], readme)
        self.assertIn('gh skill install priaby/inwoven ' + root['name'], readme)

    def test_all_relative_links(self):
        for path in TREE.rglob('*.md'):
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if '://' in target or target.startswith(('mailto:', '#')): continue
                target = unquote(target.split('#', 1)[0].strip('<>'))
                self.assertTrue((path.parent / target).exists(), str(path) + ': ' + target)

    def test_strict_frontmatter_and_budget(self):
        for path in TREE.rglob('*.md'):
            frontmatter(path.read_text(encoding='utf-8'))
        text = SKILL.read_text(encoding='utf-8')
        fields = frontmatter(text)
        self.assertEqual(set(fields), {'name', 'description', 'license'})
        self.assertEqual(fields['name'], SKILL.parent.name)
        self.assertEqual(fields['license'], 'MIT')
        self.assertTrue(1 <= len(fields['description']) <= 200)
        self.assertTrue(text.splitlines()[2].startswith('description: "'))
        self.assertLessEqual(len(text.splitlines()), 104)
        self.assertLessEqual(len(text.encode('utf-8')), 8000)
        for malformed in ('description: a: b', 'description: text # comment', 'name: a\nname: b', 'description: [bad'):
            with self.assertRaises(ValueError): frontmatter('---\n' + malformed + '\n---\n')

    def test_openai_yaml(self):
        text = (SKILL.parent / 'agents/openai.yaml').read_text()
        # This deliberately small scalar schema needs no YAML dependency.
        self.assertEqual(text.splitlines()[0], 'interface:')
        self.assertEqual(text.splitlines()[4], 'policy:')
        values = {}
        for line in text.splitlines():
            if line.startswith('  '):
                key, value = line.strip().split(': ', 1)
                self.assertNotIn(key, values)
                values[key] = json.loads(value)
        self.assertEqual(set(values), {'display_name', 'short_description', 'default_prompt', 'allow_implicit_invocation'})
        self.assertEqual(values['display_name'], 'Inwoven')
        self.assertTrue(25 <= len(values['short_description']) <= 64)
        self.assertIn('$inwoven', values['default_prompt'])
        self.assertIs(values['allow_implicit_invocation'], True)

    def test_instruction_contract(self):
        # Codex selects one file per directory, override first, then root-to-leaf:
        # https://learn.chatgpt.com/docs/agent-configuration/agents-md
        text = SKILL.read_text()
        self.assertIn('AGENTS.override.md before AGENTS.md', text)
        self.assertIn('nearer instructions take precedence', text)
        self.assertIn('git log -n 20 --grep <id>', text)
        self.assertNotIn('git log --oneline', text)
