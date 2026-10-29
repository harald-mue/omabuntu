#!/usr/bin/env python3
"""Original weather providers via fixed, bounded HTTPS requests.

wttr.in: weather report and public-IP city. Open-Meteo: forecast and typed
city search. No arbitrary URL, shell, credentials or timezone changes.
"""
import json
import math
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

import menu_common

MAX_RESPONSE = 262144
DAILY = 'weather_code,temperature_2m_max,temperature_2m_min'
CURRENT = 'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,is_day'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Weather redirects are not allowed')


def clean_text(value, maximum=160, empty=False):
    if (not isinstance(value, str) or len(value) > maximum
            or (not empty and not value.strip())
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Invalid weather text')
    return value.strip()


def coordinates(latitude, longitude):
    lat, lon = float(latitude), float(longitude)
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Invalid weather coordinates')
    return lat, lon


def request_url(mode, args):
    if mode == 'locate' and not args:
        return 'https://wttr.in/?format=%l', False
    if mode == 'report' and len(args) == 1:
        query = clean_text(urllib.parse.unquote(args[0]), empty=True)
        return 'https://wttr.in/' + urllib.parse.quote(query, safe='') + '?format=j1', True
    if mode == 'search' and len(args) == 1:
        query = clean_text(args[0], maximum=100)
        if len(query) < 2:
            raise ValueError('City search is too short')
        params = {'name': query, 'count': '5', 'language': 'en', 'format': 'json'}
        return 'https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode(params), True
    if mode == 'forecast' and len(args) == 2:
        lat, lon = coordinates(*args)
        params = {'latitude': lat, 'longitude': lon, 'daily': DAILY,
                  'current': CURRENT, 'forecast_days': '4', 'timezone': 'auto'}
        return 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(params), True
    raise ValueError('Unknown weather request')


def fetch(mode, args, opener=None):
    url, is_json = request_url(mode, args)
    if opener is None:
        opener = urllib.request.build_opener(NoRedirect()).open
    request = urllib.request.Request(url, headers={'User-Agent': 'Omabuntu-Weather/1.0'})
    with opener(request, timeout=10) as response:
        data = response.read(MAX_RESPONSE + 1)
    if len(data) > MAX_RESPONSE:
        raise ValueError('Weather response exceeds limit')
    if not is_json:
        return clean_text(data.decode('utf-8').strip(), maximum=500).split(',')[0]
    parsed = json.loads(data)
    if not isinstance(parsed, dict) or parsed.get('error'):
        raise ValueError('Invalid weather report')
    if mode == 'forecast' and (not isinstance(parsed.get('current'), dict)
                              or not isinstance(parsed.get('daily'), dict)
                              or not isinstance(parsed['current'].get('temperature_2m'), (int, float))):
        raise ValueError('Invalid forecast')
    if mode == 'report' and not isinstance(parsed.get('current_condition'), list):
        raise ValueError('Invalid current report')
    if mode == 'search' and not isinstance(parsed.get('results', []), list):
        raise ValueError('Invalid city search')
    return parsed


def location_path(root=None):
    base = Path(root or os.environ.get('OMABUNTU_STATE_HOME') or Path.home() / '.local/state/omabuntu')
    path = base / 'settings/weather.json'
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe weather state path')
    if path.exists() and not path.is_file():
        raise ValueError('Weather state must be a regular file')
    return path


def save_location(args, root=None):
    if len(args) not in (1, 2):
        raise ValueError('Expected city and optional coordinates')
    name = clean_text(args[0])
    payload = {'name': name}
    if len(args) == 2:
        parts = args[1].split(',')
        if len(parts) != 2:
            raise ValueError('Expected latitude,longitude')
        payload['latitude'], payload['longitude'] = coordinates(*parts)
    path = location_path(root)
    backup = menu_common.backup_and_write(path, lambda target: menu_common.write_json(target, payload))
    menu_common.record('weather-location-set', name, backup)


def clear_location(root=None):
    path = location_path(root)
    if path.exists():
        backup = menu_common.backup_and_write(path, lambda target: target.unlink())
        menu_common.record('weather-location-clear', 'auto-ip', backup)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if not args:
        return 2
    try:
        if args[0] == 'set':
            save_location(args[1:])
        elif args == ['clear']:
            clear_location()
        else:
            # Validate before opening a connection.
            request_url(args[0], args[1:])
            result = fetch(args[0], args[1:])
            print(json.dumps(result, allow_nan=False) if isinstance(result, dict) else result)
    except (OSError, ValueError) as error:
        print('Weather unavailable: ' + type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
