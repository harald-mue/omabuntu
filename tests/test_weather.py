"""Original weather location contracts: no real network or desktop activation."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import weather_frontend
import weather_probe
import check_clock_preview


class WeatherTests(unittest.TestCase):
    def test_forecast_uses_selected_coordinates_and_timeout(self):
        report = {'current': {'temperature_2m': 12.4}, 'daily': {'time': ['2026-10-29']}}
        calls = []
        def opener(request, timeout):
            calls.append((request.full_url, timeout))
            return io.BytesIO(json.dumps(report).encode())
        self.assertEqual(weather_probe.fetch('forecast', ['48.2082', '16.3738'], opener), report)
        url, timeout = calls[0]
        self.assertTrue(url.startswith('https://api.open-meteo.com/v1/forecast?'))
        self.assertIn('latitude=48.2082', url)
        self.assertIn('longitude=16.3738', url)
        self.assertEqual(timeout, 10)

    def test_original_endpoints_and_ip_location(self):
        url, is_json = weather_probe.request_url('locate', [])
        self.assertEqual(url, 'https://wttr.in/?format=%l')
        self.assertFalse(is_json)
        self.assertEqual(weather_probe.fetch('locate', [], lambda request, timeout: io.BytesIO(b'Vienna, Austria\n')), 'Vienna')
        self.assertEqual(weather_probe.request_url('report', [''])[0], 'https://wttr.in/?format=j1')
        self.assertIn('/Wien?format=j1', weather_probe.request_url('report', ['Wien'])[0])
        self.assertIn('name=New+York', weather_probe.request_url('search', ['New York'])[0])

    def test_url_injection_stays_an_encoded_path_not_another_host(self):
        url, _ = weather_probe.request_url('report', ['https://example.org/?x=y'])
        self.assertTrue(url.startswith('https://wttr.in/https%3A%2F%2Fexample.org'))
        self.assertNotIn('?x=', url)

    def test_invalid_arguments_do_not_reach_network(self):
        for mode, args in [('forecast', ['nan', '1']), ('forecast', ['91', '1']),
                           ('forecast', ['1', '181']), ('search', ['a']),
                           ('report', ['bad\ncity']), ('report', ['%0acity']),
                           ('fetch', ['https://example.org']), ('locate', ['extra'])]:
            with self.subTest(mode=mode, args=args), self.assertRaises(ValueError):
                weather_probe.fetch(mode, args, lambda *a, **k: self.fail('Unexpected network call'))

    def test_invalid_and_oversized_reports_are_refused(self):
        for data in (b'no json', b'{}', b'{"error":true}', b'x' * (weather_probe.MAX_RESPONSE + 1)):
            with self.subTest(data=data[:20]), self.assertRaises(ValueError):
                weather_probe.fetch('forecast', ['1', '2'], lambda request, timeout: io.BytesIO(data))

    def test_redirect_is_refused(self):
        with self.assertRaises(ValueError):
            weather_probe.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org')

    def test_unknown_cli_does_not_connect(self):
        with patch.object(weather_probe, 'fetch') as fetch, patch('builtins.print'):
            self.assertEqual(weather_probe.main([]), 2)
            for args in (['forecast'], ['https://wttr.in'], ['clear', 'extra']):
                self.assertEqual(weather_probe.main(args), 1)
            fetch.assert_not_called()

    def test_network_failure_is_nonzero(self):
        with patch.object(weather_probe, 'fetch', side_effect=OSError('offline')), patch('builtins.print'):
            self.assertEqual(weather_probe.main(['locate']), 1)

    def test_original_editor_and_backends_are_staged(self):
        base = ROOT / 'vendor/omarchy/shell/plugins/panels/weather'
        panel = weather_frontend.derive_panel((base / 'Panel.qml').read_bytes())
        widget = weather_frontend.derive_widget((base / 'BarWidget.qml').read_bytes())
        self.assertEqual(panel, (ROOT / 'config/shell/preview/Weather/WeatherPanel.qml').read_bytes())
        self.assertEqual(widget, (ROOT / 'config/shell/preview/Weather/WeatherWidget.qml').read_bytes())
        text = (panel + widget).decode()
        for forbidden in ('["curl"', 'https://', 'ShellIpc', 'root.bar.run(', '["omarchy-'):
            self.assertNotIn(forbidden, text)
        for required in ('OMABUNTU_WEATHER_HELPER', 'startEditingLocation', 'pickSuggestion',
                         'root.probeCommand("locate"', 'root.probeCommand("search"',
                         'settings/weather.json', 'heroRight', 'forecastRow'):
            self.assertIn(required, text)
        files, _ = check_clock_preview.verified_sources(ROOT)
        self.assertIn('Weather/Model.js', files)

    def test_derivation_fails_on_upstream_drift(self):
        with self.assertRaises(ValueError):
            weather_frontend.derive_panel(b'Panel {}')


class WeatherLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'OMABUNTU_STATE_HOME': str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_set_and_clear_keep_backups_of_previous_selection(self):
        weather_probe.save_location(['Wien', '48.2082,16.3738'])
        target = weather_probe.location_path()
        before = target.read_bytes()
        weather_probe.save_location(['London', '51.5074,-0.1278'])
        self.assertEqual(json.loads(target.read_text())['name'], 'London')
        weather_probe.clear_location()
        self.assertFalse(target.exists())
        backups = list((self.root / 'backups').glob('*/weather.json'))
        self.assertEqual(len(backups), 2)
        self.assertIn(before, [p.read_bytes() for p in backups])

    def test_invalid_location_does_not_write(self):
        for args in ([], ['x', 'nan,1'], ['x', '1,200'], ['bad\ncity'], ['x', '1,2', 'extra']):
            with self.subTest(args=args), self.assertRaises(ValueError):
                weather_probe.save_location(args)
        self.assertFalse((self.root / 'settings').exists())

    def test_symlinked_state_is_refused(self):
        target = self.root / 'elsewhere'
        target.mkdir()
        (self.root / 'settings').symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            weather_probe.save_location(['Wien'])
        with self.assertRaises(ValueError):
            weather_probe.clear_location()


if __name__ == '__main__':
    unittest.main()
