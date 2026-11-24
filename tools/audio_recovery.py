"""Private audio-control receipts shared with profile mutation admission.

Records prove retained observations, not atomic native transactions or restoration.
"""
import contextlib
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import stat

import appearance_backend as files
import audio_pactl as pulse

SCOPE = re.compile(r'[a-f0-9]{16,64}\Z')
NAME = re.compile(r'[A-Za-z0-9_.:+-]{1,256}\Z')
MAX_BYTES = 1024 * 1024


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode()


def key(scope, state):
    return hashlib.sha256(encode({'scope': scope, 'state': state})).hexdigest()


def valid_state(state):
    if (not isinstance(state, dict) or set(state) != {'context', 'server', 'sources', 'sinks',
            'default_source', 'default_sink'} or not isinstance(state['context'], dict)
            or not isinstance(state['server'], dict)):
        return False
    context, server = state['context'], state['server']
    if (set(context) != {'exe', 'exe_dev', 'exe_ino', 'pid', 'start', 'uid', 'socket',
                         'socket_dev', 'socket_ino', 'listener'}
            or context['exe'] != '/usr/bin/pipewire-pulse'
            or any(type(context[field]) is not int or not 0 <= context[field] <= 0xffffffffffffffff
                   for field in ('exe_dev', 'exe_ino', 'pid', 'uid', 'socket_dev', 'socket_ino'))
            or context['pid'] == 0 or context['uid'] == 0
            or context['socket'] != '/run/user/%d/pulse/native' % context['uid']
            or any(not isinstance(context[field], str) or not re.fullmatch(r'[0-9]{1,20}', context[field])
                   for field in ('start', 'listener'))
            or set(server) != {'instance', 'name', 'version', 'protocol'}
            or not isinstance(server['instance'], str) or not re.fullmatch(r'[a-f0-9]{64}', server['instance'])
            or not isinstance(server['name'], str) or not re.fullmatch(r'PulseAudio \(on PipeWire [A-Za-z0-9.+~_-]+\)', server['name'])
            or not isinstance(server['version'], str) or not 1 <= len(server['version']) <= 128
            or type(server['protocol']) is not int or not 0 <= server['protocol'] <= 65535):
        return False
    for kind in ('source', 'sink'):
        rows = state[kind + 's']
        if (not isinstance(rows, list) or len(rows) > 512
                or not isinstance(state['default_' + kind], str)
                or not NAME.fullmatch(state['default_' + kind])):
            return False
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'kind', 'index', 'name', 'serial',
                    'channels', 'levels', 'muted', 'volume'} or row['kind'] != kind
                    or type(row['index']) is not int or not 0 <= row['index'] <= 0xffffffff
                    or not isinstance(row['name'], str) or not NAME.fullmatch(row['name'])
                    or not isinstance(row['serial'], str) or not pulse.SERIAL.fullmatch(row['serial'])
                    or type(row['muted']) is not bool or not isinstance(row['channels'], list)
                    or not isinstance(row['levels'], list) or not 1 <= len(row['levels']) <= 32
                    or len(row['channels']) != len(row['levels'])
                    or any(not isinstance(c, str) or not re.fullmatch(r'[a-z0-9-]{1,32}', c) for c in row['channels'])
                    or len(set(row['channels'])) != len(row['channels'])
                    or any(type(v) is not int or not 0 <= v <= 4 * 65536 for v in row['levels'])
                    or type(row['volume']) not in (int, float) or row['volume'] != max(row['levels']) / 65536):
                return False
        if any(len({row[field] for row in rows}) != len(rows) for field in ('index', 'name', 'serial')):
            return False
    return True


class Journal:
    def __init__(self, root=None):
        self.root = files.safe((files.state_root() if root is None else Path(root)) / 'audio-control-transactions')

    def history(self):
        if not self.root.exists():
            return []
        self.check_directory()
        entries = list(itertools.islice(self.root.iterdir(), 4098))
        if len(entries) > 4097:
            raise pulse.AudioError('audio-journal-limit')
        result = []
        for path in sorted(entries):
            if path.name == 'lock':
                self.read(path)
                continue
            if not re.fullmatch(r'[0-9]{8}\.json', path.name):
                raise pulse.AudioError('unexpected-audio-journal')
            record = pulse.decode(self.read(path))
            if (not isinstance(record, dict) or set(record) != {'schema', 'id', 'status', 'scope',
                    'before', 'expected', 'changes', 'after'} or type(record['schema']) is not int or record['schema'] != 1
                    or record['id'] != path.stem or not isinstance(record['scope'], str)
                    or not SCOPE.fullmatch(record['scope']) or not valid_state(record['before'])
                    or record['status'] not in ('prepared', 'confirmed', 'acknowledged')
                    or record['expected'] != key(record['scope'], record['before'])
                    or not isinstance(record['changes'], list) or not 1 <= len(record['changes']) <= 2
                    or (record['after'] is not None and not valid_state(record['after']))
                    or (record['status'] == 'confirmed' and record['after'] is None)):
                raise pulse.AudioError('corrupt-audio-journal')
            for change in record['changes']:
                if (not isinstance(change, dict) or set(change) != {'kind', 'name', 'serial', 'field', 'value'}
                        or change['kind'] not in ('source', 'sink')
                        or change['field'] not in ('levels', 'muted')):
                    raise pulse.AudioError('corrupt-audio-journal')
                rows = [r for r in record['before'][change['kind'] + 's']
                        if r['name'] == change['name'] and r['serial'] == change['serial']]
                if len(rows) != 1 or (change['field'] == 'muted' and type(change['value']) is not bool):
                    raise pulse.AudioError('corrupt-audio-journal')
                if rows[0]['name'] != record['before']['default_' + change['kind']]:
                    raise pulse.AudioError('corrupt-audio-journal')
                if change['field'] == 'levels' and (change['kind'] != 'source'
                        or not isinstance(change['value'], list) or len(change['value']) != len(rows[0]['levels'])
                        or any(type(v) is not int or not 0 <= v <= 65536 for v in change['value'])):
                    raise pulse.AudioError('corrupt-audio-journal')
                if record['status'] == 'confirmed':
                    observed = [r for r in record['after'][change['kind'] + 's']
                                if r['name'] == change['name'] and r['serial'] == change['serial']]
                    if (len(observed) != 1 or observed[0][change['field']] != change['value']
                            or any(observed[0][field] != rows[0][field] for field in ('index', 'channels'))):
                        raise pulse.AudioError('corrupt-audio-journal')
            if record['status'] == 'confirmed' and any(record['after'][field] != record['before'][field]
                    for field in ('context', 'server', 'default_source', 'default_sink')):
                raise pulse.AudioError('corrupt-audio-journal')
            if len(record['changes']) == 2 and (
                    [(c['kind'], c['field']) for c in record['changes']] != [('sink', 'muted'), ('source', 'muted')]
                    or record['changes'][0]['value'] != record['changes'][1]['value']):
                raise pulse.AudioError('corrupt-audio-journal')
            result.append(record)
        if [r['id'] for r in result] != ['%08d' % (i + 1) for i in range(len(result))]:
            raise pulse.AudioError('audio-journal-order')
        return result

    def read(self, path):
        files.safe(path)
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise pulse.AudioError('unsafe-audio-journal')
        return pulse.bounded_read(path, MAX_BYTES)

    def check_directory(self):
        files.safe(self.root)
        info = self.root.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise pulse.AudioError('unsafe-audio-journal-directory')

    @contextlib.contextmanager
    def lock(self):
        files.mkdirs(self.root)
        self.check_directory()
        fd = os.open(self.root / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            self.read(self.root / 'lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise pulse.AudioError('audio-operation-busy') from error
            yield
        finally:
            os.close(fd)

    def require_resolved(self):
        if any(r['status'] == 'prepared' for r in self.history()):
            raise pulse.AudioError('audio-recovery-required')

    def write(self, record):
        raw = encode(record)
        if len(raw) > MAX_BYTES:
            raise pulse.AudioError('audio-journal-size-limit')
        files.atomic(self.root / (record['id'] + '.json'), raw)
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
