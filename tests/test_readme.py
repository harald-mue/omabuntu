"""Keep end-user release installation separate from source development."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CURL = 'curl -fsSL https://raw.githubusercontent.com/harald-mue/omabuntu/main/install.sh | bash'


class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'README.md').read_text()

    def section(self, heading):
        return self.text.split('## ' + heading + '\n', 1)[1].split('\n## ', 1)[0]

    def test_install_and_update_use_the_same_no_checkout_command(self):
        for heading in ('Install', 'Update'):
            section = self.section(heading)
            self.assertIn(CURL, section)
            self.assertNotIn('make ', section)
            self.assertNotIn('git clone', section)
        self.assertLess(self.text.index('## Install'), self.text.index('## For developers'))

    def test_obsolete_channel_and_local_stage_instructions_are_absent(self):
        self.assertNotRegex(self.text.lower(), r'\bchannels?\b|\bstable\b')
        for old in ('make update VERSION=', 'BUILD_DIR=', 'make dev-update', '--channels'):
            self.assertNotIn(old, self.text)

    def test_wordmark_and_safety_boundaries_remain_visible(self):
        self.assertIn('█▀█ █▀▄▀█ ▄▀█ █▄▄ █░█ █▄░█ ▀█▀ █░█', self.text)
        for phrase in ('not with sudo', 'publisher signature', 'separate opt-in steps',
                       'public GitHub Release is still pending', 'does not undo APT'):
            self.assertIn(phrase, self.text)

    def test_local_document_links_exist(self):
        for link in re.findall(r'\]\(([^)]+)\)', self.text):
            if '://' not in link:
                self.assertTrue((ROOT / link.split('#', 1)[0]).is_file(), link)


if __name__ == '__main__':
    unittest.main()
