#!/usr/bin/env python3
"""Opt-in indicator RPC with private before/outcome receipts and no replay."""
import argparse
import contextlib
import fcntl
import itertools
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from indicator_native import Native, NativeError, action_key, bounded

KINDS = ('dnd', 'nightlight')
SCOPE = re.compile(r'[0-9a-f]{16,64}\Z')
KEY = re.compile(r'[0-9a-f]{64}\Z')
RECEIPT = re.compile(r'[0-9]{8}\.json\Z')


class Store:
    def __init__(self, root=None):
        default = str(Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'omabuntu')
        self.root = Path(root) if root is not None else Path(os.environ.get('OMABUNTU_STATE_HOME', default)) / 'native-indicators'
        if not self.root.is_absolute():
            raise NativeError('absolute-state-root-required')

    def check(self, create=False):
        for p in reversed((self.root, *self.root.parents)):
            if p.is_symlink():
                raise NativeError('unsafe-receipt-path')
            if not p.exists():
                if create:
                    p.mkdir(mode=0o700)
                else:
                    continue
            else:
                s = p.stat()
                if not stat.S_ISDIR(s.st_mode) or s.st_mode & 0o022 or s.st_uid not in (0, os.getuid()):
                    raise NativeError('unsafe-receipt-path')
        if self.root.exists() and (self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077):
            raise NativeError('private-receipt-directory-required')

    def records(self):
        self.check()
        if not self.root.exists():
            return []
        entries = list(itertools.islice(self.root.iterdir(), 4098))
        if len(entries) > 4097:
            raise NativeError('receipt-limit')
        records = []
        for p in sorted(entries):
            if p.name != 'lock' and not RECEIPT.fullmatch(p.name):
                raise NativeError('unexpected-receipt-file')
            s = p.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o077 or s.st_nlink != 1:
                raise NativeError('unsafe-receipt-file')
            if p.name == 'lock':
                continue
            data = json.loads(bounded(p, 32768))
            if (not isinstance(data, dict) or data.get('schema') != 1 or data.get('id') != p.stem
                    or data.get('status') not in ('prepared', 'confirmed', 'uncertain', 'acknowledged')
                    or data.get('kind') not in KINDS or type(data.get('desired')) is not bool
                    or not isinstance(data.get('scope'), str) or not SCOPE.fullmatch(data['scope'])
                    or not isinstance(data.get('before'), dict) or type(data['before'].get('active')) is not bool
                    or not isinstance(data['before'].get('proof'), dict)
                    or data.get('before_key') != action_key(data['scope'], data['kind'], data['before'])):
                raise NativeError('invalid-receipt')
            if data['status'] == 'confirmed' and (not isinstance(data.get('after'), dict)
                    or type(data['after'].get('active')) is not bool or data['after']['active'] != data['desired']
                    or data['after'].get('proof') != data['before']['proof']
                    or data.get('after_key') != action_key(data['scope'], data['kind'], data['after'])):
                raise NativeError('invalid-receipt')
            if data['status'] == 'acknowledged' and data.get('restored') is not False:
                raise NativeError('invalid-receipt')
            records.append(data)
        return records

    def blocked(self):
        return any(r['status'] in ('prepared', 'uncertain') for r in self.records())

    @contextlib.contextmanager
    def lock(self):
        self.check(create=True)
        fd = os.open(self.root / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            s = os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o077 or s.st_nlink != 1:
                raise NativeError('unsafe-receipt-lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise NativeError('indicator-action-busy') from None
            yield
        finally:
            os.close(fd)

    def write(self, record):
        self.check()
        fd, name = tempfile.mkstemp(prefix='.pending-', dir=self.root)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(record, stream, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.root / (record['id'] + '.json'))
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def acknowledge(self, identifier):
        if not re.fullmatch(r'[0-9]{8}', identifier):
            raise NativeError('invalid-receipt-id')
        with self.lock():
            record = next((r for r in self.records() if r['id'] == identifier), None)
            if record is None or record['status'] not in ('prepared', 'uncertain'):
                raise NativeError('no-pending-receipt')
            record['status'] = 'acknowledged'
            record['restored'] = False
            self.write(record)
        return {'status': 'acknowledged', 'restored': False, 'receipt': identifier}


def validate(scope, kind=None, expected=None, desired=None):
    if not isinstance(scope, str) or not SCOPE.fullmatch(scope):
        raise NativeError('invalid-provider-scope')
    if kind is not None and (kind not in KINDS or not isinstance(expected, str) or not KEY.fullmatch(expected) or type(desired) is not bool):
        raise NativeError('invalid-indicator-request')


def inspect(native, store, scope):
    validate(scope)
    result = {'schema': 1, 'scope': scope, 'states': {}, 'blocked': False}
    try:
        result['blocked'] = store.blocked()
    except (OSError, ValueError):
        result['blocked'] = True
    for kind in KINDS:
        try:
            state = native.read(kind)
            result['states'][kind] = {'known': True, 'active': state['active'], 'key': action_key(scope, kind, state)}
        except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as error:
            reason = str(error) if isinstance(error, NativeError) else ('timeout' if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else 'owner-command-or-response-unavailable')
            result['states'][kind] = {'known': False, 'reason': reason}
    count = sum(value['known'] for value in result['states'].values())
    result['status'] = 'ready' if count == 2 else ('partial' if count else 'unavailable')
    return result


def change(native, store, scope, kind, expected, desired):
    validate(scope, kind, expected, desired)
    with store.lock():
        records = store.records()
        if any(r['status'] in ('prepared', 'uncertain') for r in records):
            raise NativeError('previous-action-uncertain-review-receipt')
        before = native.read(kind)
        if action_key(scope, kind, before) != expected:
            raise NativeError('state-or-owner-changed')
        if before['active'] == desired:
            return {'status': 'unchanged'}
        number = max([int(r['id']) for r in records] + [0]) + 1
        if number > 99999999 or len(records) >= 4096:
            raise NativeError('receipt-limit')
        record = {'schema': 1, 'id': '%08d' % number, 'status': 'prepared', 'kind': kind,
                  'scope': scope, 'before': before, 'before_key': expected, 'desired': desired}
        # Durable previous state exists before entering a possibly mutating call.
        store.write(record)
        try:
            after = native.set(kind, desired, before)
            record.update(status='confirmed', after=after, after_key=action_key(scope, kind, after))
        except Exception:
            # Never repeat a setter, restore a hardcoded value or compensate.
            record['status'] = 'uncertain'
            store.write(record)
            return {'status': 'uncertain', 'receipt': record['id']}
        store.write(record)
        return {'status': 'confirmed', 'receipt': record['id']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inspect', 'set', 'acknowledge'))
    parser.add_argument('--allow-existing-owner-queries', action='store_true')
    parser.add_argument('--apply-user-indicator', action='store_true')
    parser.add_argument('--allow-session-bus-connection-risk', action='store_true')
    parser.add_argument('--acknowledge-uncertain', action='store_true')
    parser.add_argument('--receipt')
    args = parser.parse_args(argv)
    try:
        if os.getuid() == 0 or os.getuid() != os.geteuid() or os.environ.get('SUDO_USER') or os.environ.get('PKEXEC_UID'):
            raise NativeError('normal-user-required')
        store = Store()
        if args.operation == 'acknowledge':
            if not args.acknowledge_uncertain:
                raise NativeError('explicit-acknowledgement-required')
            result = store.acknowledge(args.receipt or '')
        else:
            if not args.allow_existing_owner_queries:
                raise NativeError('existing-owner-query-grant-required')
            if args.operation == 'set' and not args.apply_user_indicator:
                raise NativeError('explicit-user-action-required')
            request = json.loads(bounded('/dev/stdin', 4096))
            if not isinstance(request, dict) or set(request) != ({'scope'} if args.operation == 'inspect' else {'scope', 'kind', 'expected', 'desired'}):
                raise NativeError('invalid-request-fields')
            native = Native(bus_connection_granted=args.allow_session_bus_connection_risk)
            result = inspect(native, store, **request) if args.operation == 'inspect' else change(native, store, **request)
        print(json.dumps({'ok': True, **result}, separators=(',', ':')))
        return 0
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as error:
        # Never return stderr, socket paths, process inventories or payloads.
        code = str(error) if isinstance(error, NativeError) else 'indicator-request-failed'
        print(json.dumps({'ok': False, 'error': code}, separators=(',', ':')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
