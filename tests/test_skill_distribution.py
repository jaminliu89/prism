"""Contract checks for Prism's installable root Agent Skill."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SkillDistributionTests(unittest.TestCase):
    def test_root_skill_has_discoverable_frontmatter(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\n'))
        header = text.split('---', 2)[1]
        self.assertRegex(header, r'(?m)^name: prism$')
        self.assertRegex(header, r'(?m)^description: .{30,}$')
        self.assertNotIn('TODO', header)
        self.assertIn('npx skills add jaminliu89/prism', text)
        self.assertIn('npx skills add ./prism', text)

    def test_all_declared_local_routes_exist(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        expected = (
            'docs/AUDIT_PROMPT.md',
            'docs/REPORT_CONTRACT.md',
            'docs/INTEGRATION.md',
            'docs/FOUNDRY_WORKBENCH_V03.md',
            'sources/skillhub/blueprint/MASTER_PROMPT.md',
            'sources/skillhub/blueprint/DOCUMENT_CONTRACT.md',
            'scripts/prism.py',
            'scripts/foundry.py',
            'scripts/foundry_web.py',
        )
        for path in expected:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

    def test_no_implicit_public_or_release_permission(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('Never make the private repository public', text)
        self.assertIn('not authenticated approval', text)


if __name__ == '__main__':
    unittest.main()
