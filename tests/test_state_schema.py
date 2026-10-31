"""Schema policy tests: no state files are rewritten."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import state_schema as schema
import release_update as update
import user_install


class SchemaPolicyTests(unittest.TestCase):
    def test_same_schema_does_not_write_or_register_a_migration(self):
        decision = schema.decision(1, 1)
        self.assertEqual(decision['action'], 'none')
        self.assertFalse(decision['writes_state'])
        self.assertTrue(decision['rollback_safe'])
        self.assertEqual(schema.MIGRATIONS, {})

    def test_schema_change_is_refused_without_a_bidirectional_review(self):
        with self.assertRaisesRegex(schema.SchemaError, 'understood schema'):
            schema.decision(1, 2)
        with self.assertRaisesRegex(schema.SchemaError, 'understood schema'):
            schema.decision(None, 2)
        with self.assertRaisesRegex(schema.SchemaError, 'bidirectional'):
            schema.decision(2, 1)

    def test_inventory_names_files_without_reading_contents(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            state = Path(directory)
            path = state / 'settings/weather.json'
            path.parent.mkdir()
            path.write_text('{"city":"secret"}')
            listed = schema.inventory(state)
        self.assertEqual(listed, [{'path': 'settings/weather.json', 'bytes': len(b'{"city":"secret"}')}])
        self.assertNotIn('secret', json.dumps(listed))

    def test_release_review_records_no_migration_for_schema_1(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            base = Path(directory)
            app = user_install.Installation(base / 'data', base / 'state', base / 'bin/omabuntu')
            bundle = base / 'bundle'
            bundle.mkdir()
            for name in user_install.INCOMING:
                path = bundle / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
                path.chmod(0o444)
            meta = {'schema_version': 1, 'scope': 'omabuntu-user-release-v1', 'version': 'v1',
                    'autostart': False, 'lock_activation': False, 'update_contract': update.contract(),
                    'files': user_install.file_manifest(bundle)}
            (bundle / 'release.json').write_text(json.dumps(meta))
            reviewed = update.review(app, bundle)
        self.assertEqual(reviewed['schema_decision']['action'], 'none')
        self.assertFalse(reviewed['schema_decision']['writes_state'])
