#!/usr/bin/env python3
"""Manual, reviewed ALSA profile requests; not installed or exposed through QML.

Restoration covers the active-profile name only, never complete audio topology.
No automatic retry, compensation, daemon activation, Bluetooth policy or off action.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import appearance_backend as files
import audio_pactl as pactl

SCOPE = 'user-audio-alsa-profile'
NOTICE = ('Changes this user\'s shared audio card across concurrent desktops, including GNOME. '
          'Inputs/outputs and ongoing calls may be interrupted. Restore covers only the '
          'previous profile name, not defaults, streams, volume, routing or policy. '
          'A local socket connection can race a stopping service and trigger socket activation.')
DIGEST = re.compile(r'[a-f0-9]{64}\Z')
STATES = {'prepared', 'applied', 'restore-prepared', 'restored', 'cancelled', 'acknowledged'}
PENDING = {'prepared', 'restore-prepared'}
CLOSED = {'restored', 'cancelled', 'acknowledged'}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def validate_state(value):
    if not isinstance(value, dict) or set(value) != {'context', 'server', 'card'}:
        raise pactl.AudioError('invalid-profile-state')
    context, server, card = value['context'], value['server'], value['card']
    if (not isinstance(context, dict) or set(context) != {'exe', 'exe_dev', 'exe_ino', 'pid', 'start',
            'uid', 'socket', 'socket_dev', 'socket_ino', 'listener'}
            or context['exe'] != '/usr/bin/pipewire-pulse'):
        raise pactl.AudioError('invalid-profile-context')
    for key in ('exe_dev', 'exe_ino', 'pid', 'uid', 'socket_dev', 'socket_ino'):
        pactl.integer(context[key], 2**64 - 1)
    if (context['uid'] == 0 or context['pid'] == 0
            or context['socket'] != '/run/user/%s/pulse/native' % context['uid']
            or any(not isinstance(context[key], str) or not pactl.SERIAL.fullmatch(context[key])
                   for key in ('start', 'listener'))):
        raise pactl.AudioError('invalid-profile-context')
    if (not isinstance(server, dict) or set(server) != {'instance', 'name', 'version', 'protocol'}
            or not isinstance(server['instance'], str) or not DIGEST.fullmatch(server['instance'])
            or not isinstance(server['name'], str)
            or not re.fullmatch(r'PulseAudio \(on PipeWire [A-Za-z0-9.+~_-]+\)', server['name'])):
        raise pactl.AudioError('invalid-profile-server')
    pactl.text(server['version'], 128)
    if not pactl.integer(server['protocol'], 65535):
        raise pactl.AudioError('invalid-profile-server')
    if not isinstance(card, dict) or set(card) != {'index', 'name', 'serial', 'active_profile', 'profiles'}:
        raise pactl.AudioError('invalid-profile-card')
    projected = pactl.card({**card, 'properties': {'device.api': 'alsa', 'object.serial': card['serial']}})
    if projected != card:
        raise pactl.AudioError('invalid-profile-card')
    if len(encode(value)) > files.MAX_BYTES:
        raise pactl.AudioError('profile-state-limit')
    return value


def same_identity(a, b):
    return (a['context'] == b['context'] and a['server'] == b['server']
            and all(a['card'][key] == b['card'][key] for key in ('index', 'name', 'serial')))


def require_profile(state, name, recovery=False):
    if not isinstance(name, str) or not pactl.PROFILE.fullmatch(name):
        raise pactl.AudioError('unsupported-profile')
    profile = state['card']['profiles'].get(name)
    if (not profile or not profile['available']
            or (not recovery and (name == 'off' or profile['sinks'] + profile['sources'] == 0))):
        raise pactl.AudioError('unavailable-or-excluded-profile')


def validate_review(review, approval=None):
    if (not isinstance(review, dict) or set(review) != {'schema_version', 'scope', 'before', 'profile', 'notice', 'digest'}
            or type(review['schema_version']) is not int or review['schema_version'] != 1
            or review['scope'] != SCOPE or review['notice'] != NOTICE
            or not isinstance(review['digest'], str) or not DIGEST.fullmatch(review['digest'])):
        raise pactl.AudioError('invalid-profile-review')
    if digest({key: value for key, value in review.items() if key != 'digest'}) != review['digest']:
        raise pactl.AudioError('profile-review-integrity')
    if approval is not None and (not isinstance(approval, str) or approval != review['digest']):
        raise pactl.AudioError('profile-approval-differs')
    validate_state(review['before'])
    require_profile(review['before'], review['profile'])
    return review


class Store:
    def __init__(self, root=None):
        self.root = files.safe((files.state_root() if root is None else Path(root)) / 'audio-profile-transactions')

    def private_directory(self, path):
        files.safe(path)
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise pactl.AudioError('unsafe-profile-directory')

    def read(self, path):
        files.safe(path)
        info = path.stat()
        if info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
            raise pactl.AudioError('unsafe-profile-file')
        raw = files.read_bytes(path)
        if raw is None:
            raise pactl.AudioError('missing-profile-file')
        return raw

    def write(self, path, value):
        raw = encode(value)
        if len(raw) > files.MAX_BYTES:
            raise pactl.AudioError('profile-state-limit')
        if path.exists() or path.is_symlink():
            self.read(path)
        files.atomic(path, raw)
        self.sync_directory(path.parent)

    def sync_directory(self, path):
        fd = os.open(path, os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def history(self):
        if not self.root.exists() and not self.root.is_symlink():
            return []
        self.private_directory(self.root)
        result = []
        for path in sorted(self.root.iterdir()):
            if path.name == 'operation.lock':
                self.read(path)
                continue
            if not files.TOKEN.fullmatch(path.name):
                raise pactl.AudioError('unrecognized-profile-journal-path')
            self.private_directory(path)
            if {child.name for child in path.iterdir()} != {'before.json', 'transaction.json'}:
                raise pactl.AudioError('incomplete-profile-journal')
            record = pactl.decode(self.read(path / 'transaction.json'))
            before_raw = self.read(path / 'before.json')
            before = validate_state(pactl.decode(before_raw))
            if (not isinstance(record, dict) or set(record) != {'schema_version', 'scope', 'status', 'before_sha256',
                    'before_mode', 'review_digest', 'profile', 'sequence'}
                    or type(record['schema_version']) is not int or record['schema_version'] != 1
                    or type(record['sequence']) is not int or record['sequence'] < 1
                    or record['scope'] != SCOPE or not isinstance(record['status'], str) or record['status'] not in STATES
                    or record['before_mode'] != 0o600
                    or record['before_sha256'] != hashlib.sha256(before_raw).hexdigest()
                    or not isinstance(record['review_digest'], str) or not DIGEST.fullmatch(record['review_digest'])
                    or not isinstance(record['profile'], str) or not pactl.PROFILE.fullmatch(record['profile'])):
                raise pactl.AudioError('invalid-profile-journal')
            require_profile(before, record['profile'])
            review = {'schema_version': 1, 'scope': SCOPE, 'before': before, 'profile': record['profile'], 'notice': NOTICE}
            if digest(review) != record['review_digest']:
                raise pactl.AudioError('profile-journal-review-integrity')
            result.append((path, record, before))
        result.sort(key=lambda row: row[1]['sequence'])
        if [row[1]['sequence'] for row in result] != list(range(1, len(result) + 1)):
            raise pactl.AudioError('profile-journal-order-integrity')
        return result

    @contextlib.contextmanager
    def locked(self):
        missing = []
        path = self.root
        while not path.exists() and not path.is_symlink():
            missing.append(path)
            path = path.parent
        files.mkdirs(self.root)
        for directory in reversed(missing):
            self.sync_directory(directory.parent)
        self.private_directory(self.root)
        path = files.safe(self.root / 'operation.lock')
        if path.exists() or path.is_symlink():
            self.read(path)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'r+b') as stream:
            self.sync_directory(self.root)
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise pactl.AudioError('profile-operation-busy') from error
            yield


class Backend:
    def __init__(self, client=None, root=None):
        self.client = pactl.Client() if client is None else client
        self.store = Store(root)

    def state(self, name):
        snapshot = self.client.inspect()
        if snapshot['partial']:
            raise pactl.AudioError('partial-card-inventory')
        matches = [card for card in snapshot['cards'] if card['name'] == name]
        if len(matches) != 1:
            raise pactl.AudioError('current-alsa-card-required')
        return validate_state({'context': snapshot['context'], 'server': snapshot['server'], 'card': matches[0]})

    def review(self, name, profile):
        state = self.state(name)
        require_profile(state, profile)
        if any(record['status'] in PENDING for _, record, _ in self.store.history()):
            raise pactl.AudioError('pending-profile-recovery')
        result = {'schema_version': 1, 'scope': SCOPE, 'before': state, 'profile': profile, 'notice': NOTICE}
        return {**result, 'digest': digest(result)}

    def apply(self, review, approval):
        pactl.normal_user()
        if not isinstance(approval, str) or not DIGEST.fullmatch(approval):
            raise pactl.AudioError('profile-approval-required')
        validate_review(review, approval)
        before = review['before']
        if any(record['status'] in PENDING for _, record, _ in self.store.history()):
            raise pactl.AudioError('pending-profile-recovery')
        if self.state(before['card']['name']) != before:
            raise pactl.AudioError('profile-review-drift')
        if before['card']['active_profile'] == review['profile']:
            return {'status': 'unchanged', 'scope': SCOPE, 'notice': NOTICE}
        with self.store.locked():
            history = self.store.history()
            if any(record['status'] in PENDING for _, record, _ in history):
                raise pactl.AudioError('pending-profile-recovery')
            if self.state(before['card']['name']) != before:
                raise pactl.AudioError('profile-review-drift')
            token = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + os.urandom(6).hex()
            case = self.store.root / token
            record = {'schema_version': 1, 'scope': SCOPE, 'status': 'prepared', 'sequence': len(history) + 1,
                      'before_sha256': hashlib.sha256(encode(before)).hexdigest(), 'before_mode': 0o600,
                      'review_digest': review['digest'], 'profile': review['profile']}
            try:
                case.mkdir(mode=0o700)
                self.store.sync_directory(self.store.root)
                self.store.write(case / 'before.json', before)
                self.store.write(case / 'transaction.json', record)
                if self.state(before['card']['name']) != before:
                    record['status'] = 'cancelled'
                    self.store.write(case / 'transaction.json', record)
                    raise pactl.AudioError('profile-review-drift')
                self.client.set_profile(before, review['profile'])
                after = self.state(before['card']['name'])
                if not same_identity(after, before) or after['card']['active_profile'] != review['profile']:
                    raise pactl.AudioError('profile-readback-uncertain')
                record['status'] = 'applied'
                self.store.write(case / 'transaction.json', record)
            except (pactl.AudioError, OSError, ValueError) as error:
                if record['status'] == 'applied':
                    record['status'] = 'prepared'
                    try:
                        self.store.write(case / 'transaction.json', record)
                    except (OSError, ValueError):
                        pass  # No native compensation; preserve pending when writable.
                code = error.code if isinstance(error, pactl.AudioError) else 'profile-journal-outcome-uncertain'
                raise pactl.AudioError(code, token) from error
            return {'status': 'profile-observed', 'transaction': token, 'scope': SCOPE, 'notice': NOTICE}

    def latest(self, token):
        if not isinstance(token, str) or not files.TOKEN.fullmatch(token):
            raise pactl.AudioError('invalid-profile-transaction')
        records = self.store.history()
        live = [row for row in records if row[1]['status'] not in CLOSED]
        if not live or live[-1][0].name != token:
            raise pactl.AudioError('latest-unclosed-transaction-required')
        return live[-1]

    def restore(self, token):
        pactl.normal_user()
        self.latest(token)  # Do not allocate state for a missing/invalid transaction.
        with self.store.locked():
            case, record, before = self.latest(token)
            try:
                current = self.state(before['card']['name'])
                if not same_identity(current, before):
                    raise pactl.AudioError('profile-restore-identity-drift')
                prior = before['card']['active_profile']
                if current['card']['active_profile'] != prior:
                    if current['card']['active_profile'] != record['profile']:
                        raise pactl.AudioError('profile-restore-active-drift')
                    require_profile(current, prior, recovery=True)
                    record['status'] = 'restore-prepared'
                    self.store.write(case / 'transaction.json', record)
                    if self.state(before['card']['name']) != current:
                        raise pactl.AudioError('profile-restore-state-drift')
                    self.client.set_profile(current, prior)
                    restored = self.state(before['card']['name'])
                    if not same_identity(restored, before) or restored['card']['active_profile'] != prior:
                        raise pactl.AudioError('profile-restore-readback-uncertain')
                record['status'] = 'restored'
                self.store.write(case / 'transaction.json', record)
            except (pactl.AudioError, OSError, ValueError) as error:
                if record['status'] == 'restored':
                    record['status'] = 'restore-prepared'
                    try:
                        self.store.write(case / 'transaction.json', record)
                    except (OSError, ValueError):
                        pass
                code = error.code if isinstance(error, pactl.AudioError) else 'profile-journal-outcome-uncertain'
                raise pactl.AudioError(code, token) from error
            return {'status': 'previous-profile-observed', 'transaction': token, 'scope': SCOPE, 'notice': NOTICE}

    def acknowledge(self, token):
        pactl.normal_user()
        self.latest(token)
        with self.store.locked():
            case, record, _ = self.latest(token)
            record['status'] = 'acknowledged'
            self.store.write(case / 'transaction.json', record)
        return {'status': 'unresolved-acknowledged-without-native-writes', 'restored': False,
                'transaction': token, 'scope': SCOPE, 'notice': NOTICE}


def main(argv=None, backend=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    inspect = sub.add_parser('inspect', help='Read admitted cards; no state writes')
    inspect.add_argument('--query-running-user-audio', action='store_true')
    review = sub.add_parser('review', help='Read-only normalized profile review')
    review.add_argument('card'); review.add_argument('profile')
    review.add_argument('--query-running-user-audio', action='store_true')
    apply = sub.add_parser('apply', help='Apply exactly one digest-reviewed profile')
    apply.add_argument('--review-file', required=True)
    apply.add_argument('--approve-digest', required=True)
    apply.add_argument('--apply-user-audio', action='store_true')
    restore = sub.add_parser('restore', help='Explicit latest-first profile-only recovery')
    restore.add_argument('transaction'); restore.add_argument('--apply-user-audio', action='store_true')
    acknowledge = sub.add_parser('acknowledge', help='Retain an unresolved receipt, without native writes')
    acknowledge.add_argument('transaction'); acknowledge.add_argument('--acknowledge-unresolved', action='store_true')
    sub.add_parser('history', help='Read private receipts only, no server connection')
    for command in (inspect, review, apply, restore):
        command.add_argument('--allow-local-socket-activation-risk', action='store_true',
                             help='Separately approved risk: service can stop after listener preflight')
    args = parser.parse_args(argv)
    try:
        service = Backend() if backend is None else backend
        if (args.action in ('inspect', 'review', 'apply', 'restore')
                and not args.allow_local_socket_activation_risk):
            raise pactl.AudioError('explicit-local-socket-activation-risk-consent-required')
        if args.action in ('inspect', 'review'):
            if not args.query_running_user_audio:
                raise pactl.AudioError('explicit-running-user-audio-query-required')
            result = service.client.inspect() if args.action == 'inspect' else service.review(args.card, args.profile)
        elif args.action == 'history':
            result = [{'transaction': path.name, 'status': record['status'], 'profile': record['profile']}
                      for path, record, _ in service.store.history()]
        elif args.action == 'acknowledge':
            if not args.acknowledge_unresolved:
                raise pactl.AudioError('explicit-unresolved-acknowledgement-required')
            result = service.acknowledge(args.transaction)
        else:
            if not args.apply_user_audio:
                raise pactl.AudioError('explicit-user-audio-consent-required')
            if args.action == 'restore':
                result = service.restore(args.transaction)
            else:
                review = pactl.decode(service.store.read(Path(args.review_file).absolute()))
                if isinstance(review, dict) and set(review) == {'ok', 'result'} and review['ok'] is True:
                    review = review['result']
                result = service.apply(review, args.approve_digest)
        print(json.dumps({'ok': True, 'result': result}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        code = error.code if isinstance(error, pactl.AudioError) else 'profile-input-or-state-unavailable'
        result = {'ok': False, 'error': code}
        if isinstance(error, pactl.AudioError) and error.transaction:
            result['transaction'] = error.transaction
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
