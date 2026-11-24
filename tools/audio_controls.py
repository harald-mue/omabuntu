#!/usr/bin/env python3
"""Closed local audio RPC: transactional profiles and proof-bound virtual input.

No recording, daemon management, alternate endpoint, default routing or replay.
Native observations are not functional/call/hardware acceptance.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import signal
import sys

import audio_pactl as pulse
import audio_profiles as profiles
from audio_recovery import Journal, key

SCOPE = re.compile(r'[a-f0-9]{16,64}\Z')
NAME = re.compile(r'[A-Za-z0-9_.:+-]{1,256}\Z')
CHANNEL = re.compile(r'[a-z0-9-]{1,32}\Z')
LIMIT = 262144


def verified_runner(argv):
    binary = Path('/usr/bin/pactl')
    try:
        info = binary.lstat()
    except FileNotFoundError as error:
        raise pulse.AudioError('pactl-unavailable-no-installation-attempted') from error
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o6022
            or not os.access(binary, os.X_OK)):
        raise pulse.AudioError('trusted-pactl-required')
    return pulse.command(argv)


def endpoint(raw, kind):
    if not isinstance(raw, dict) or not isinstance(raw.get('properties'), dict):
        raise pulse.AudioError('invalid-audio-endpoint')
    name, serial = raw.get('name'), raw['properties'].get('object.serial')
    if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(serial, str) or not pulse.SERIAL.fullmatch(serial):
        raise pulse.AudioError('missing-audio-endpoint-identity')
    channel_map = raw.get('channel_map')
    if not isinstance(channel_map, str):
        raise pulse.AudioError('invalid-audio-channels')
    channels = channel_map.split(',')
    volumes = raw.get('volume')
    if (not 1 <= len(channels) <= 32 or len(set(channels)) != len(channels)
            or any(not CHANNEL.fullmatch(c) for c in channels)
            or not isinstance(volumes, dict) or set(volumes) != set(channels)
            or type(raw.get('mute')) is not bool):
        raise pulse.AudioError('invalid-audio-channels')
    levels = [pulse.integer(volumes[c].get('value'), 4 * 65536) if isinstance(volumes[c], dict)
              else pulse.integer(None) for c in channels]
    return {'kind': kind, 'index': pulse.integer(raw.get('index')), 'name': name,
            'serial': serial, 'channels': channels, 'levels': levels, 'muted': raw['mute'],
            'volume': max(levels) / 65536}


class Client(pulse.Client):
    def call(self, args, context):
        if not isinstance(args, list) or not all(isinstance(v, str) for v in args):
            raise pulse.AudioError('unadmitted-audio-command')
        allowed = args in (['info'], ['list', 'sources'], ['list', 'sinks'])
        if args and args[0] in ('set-source-volume', 'set-source-mute', 'set-sink-mute'):
            allowed = (3 <= len(args) <= 34 and isinstance(args[1], str) and NAME.fullmatch(args[1])
                       and all(isinstance(v, str) and v.isascii() and v.isdigit() for v in args[2:]))
            if allowed:
                allowed = (len(args) == 3 and args[2] in ('0', '1')) if args[0].endswith('mute') else all(int(v) <= 65536 for v in args[2:])
        if not allowed:
            raise pulse.AudioError('unadmitted-audio-command')
        if self.context() != context:
            raise pulse.AudioError('server-context-changed')
        prefix = ['/usr/bin/pactl', '--server=unix:' + context['socket'], '--client-name=omabuntu-audio-controls']
        if args[0] in ('info', 'list'):
            prefix += ['--format=json']
        data = self.runner(prefix + ["--"] + args)
        if self.context() != context:
            raise pulse.AudioError('server-context-changed')
        return data

    def inspect_audio(self):
        context = self.context()
        raw_info = pulse.decode(self.call(['info'], context))
        server = pulse.server_info(raw_info, context)
        result = {'context': context, 'server': server}
        for kind in ('sources', 'sinks'):
            rows = pulse.decode(self.call(['list', kind], context))
            if not isinstance(rows, list) or len(rows) > 512:
                raise pulse.AudioError('audio-endpoint-limit')
            projected = [endpoint(row, kind[:-1]) for row in rows]
            for field in ('index', 'name', 'serial'):
                if len({row[field] for row in projected}) != len(projected):
                    raise pulse.AudioError('ambiguous-audio-endpoint')
            result[kind] = sorted(projected, key=lambda row: row['name'])
            name = raw_info.get('default_' + kind[:-1] + '_name')
            if not isinstance(name, str) or not NAME.fullmatch(name):
                raise pulse.AudioError('unknown-audio-default')
            result['default_' + kind[:-1]] = name
        after = pulse.decode(self.call(['info'], context))
        if (pulse.server_info(after, context) != server or any(
                after.get('default_' + kind + '_name') != result['default_' + kind] for kind in ('sink', 'source'))):
            raise pulse.AudioError('audio-default-or-instance-changed')
        return result


class Backend:
    def __init__(self, client=None, profile_backend=None, root=None):
        self.client = client or Client(runner=verified_runner)
        self.profiles = profile_backend or profiles.Backend(client=pulse.Client(runner=verified_runner), root=root)
        self.journal = Journal(root)

    def inspect(self, scope):
        state = self.client.inspect_audio()
        cards = self.profiles.client.inspect()
        if any(cards[field] != state[field] for field in ('context', 'server')):
            raise pulse.AudioError('audio-owner-changed-between-inventories')
        history = self.profiles.store.history()
        records = self.journal.history()
        return {'key': key(scope, state), 'sources': state['sources'], 'sinks': state['sinks'],
                'default_source': state['default_source'], 'default_sink': state['default_sink'],
                'cards': cards['cards'], 'partial': cards['partial'],
                'blocked': cards['partial'] or len(records) >= 4096 or any(r['status'] == 'prepared' for r in records),
                'profile_blocked': any(r['status'] in profiles.PENDING for _, r, _ in history),
                'profile_history': [{'id': p.name, 'status': r['status'], 'profile': r['profile']} for p, r, _ in history],
                'control_history': [{'id': r['id'], 'status': r['status']} for r in records], 'notice': profiles.NOTICE}

    def change(self, scope, expected, operation, target, value, output=None):
        pulse.normal_user()
        if not isinstance(scope, str) or not SCOPE.fullmatch(scope):
            raise pulse.AudioError('invalid-audio-scope')
        if not isinstance(target, dict) or set(target) != {'name', 'serial'}:
            raise pulse.AudioError('audio-target-required')
        if not isinstance(expected, str) or not profiles.DIGEST.fullmatch(expected):
            raise pulse.AudioError('audio-proof-required')
        with self.profiles.store.locked(), self.journal.lock():
            history = self.journal.history()
            if len(history) >= 4096:
                raise pulse.AudioError('audio-journal-limit')
            if any(r['status'] in profiles.PENDING for _, r, _ in self.profiles.store.history()):
                raise pulse.AudioError('pending-profile-recovery')
            if any(r['status'] == 'prepared' for r in history):
                raise pulse.AudioError('audio-recovery-required')
            before = self.client.inspect_audio()
            if key(scope, before) != expected:
                raise pulse.AudioError('stale-audio-observation')
            source = self.find(before, 'source', target, default=True)
            if operation == 'volume':
                if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise pulse.AudioError('invalid-audio-volume')
                maximum = max(source['levels'])
                levels = [round(value * 65536 * (v / maximum if maximum else 1)) for v in source['levels']]
                changes = [{'kind': 'source', 'name': source['name'], 'serial': source['serial'], 'field': 'levels', 'value': levels}]
            elif operation in ('mute', 'master') and type(value) is bool:
                changes = [{'kind': 'source', 'name': source['name'], 'serial': source['serial'], 'field': 'muted', 'value': value}]
                if operation == 'master':
                    if (not isinstance(output, dict) or set(output) != {'name', 'serial', 'selected'}
                            or output.get('selected') != before['default_sink']
                            or output.get('name') != output.get('selected')):
                        raise pulse.AudioError('output-default-changed')
                    sink = self.find(before, 'sink', output, default=False)
                    if value != (not source['muted'] or not sink['muted']):
                        raise pulse.AudioError('audio-master-state-changed')
                    changes.insert(0, {'kind': 'sink', 'name': sink['name'], 'serial': sink['serial'], 'field': 'muted', 'value': value})
            else:
                raise pulse.AudioError('unadmitted-audio-action')
            if all(self.find(before, c['kind'], c, default=c['kind'] == 'source')[c['field']] == c['value'] for c in changes):
                return {'status': 'unchanged', 'receipt': None}
            record = {'schema': 1, 'id': '%08d' % (len(history) + 1), 'status': 'prepared',
                      'scope': scope, 'before': before, 'expected': expected, 'changes': changes, 'after': None}
            self.journal.write(record)
            # Revalidate immediately before issuance; a race is not atomic CAS.
            if self.client.inspect_audio() != before:
                raise pulse.AudioError('audio-state-changed-after-prepare')
            for change in changes:
                args = ['set-' + change['kind'] + ('-volume' if change['field'] == 'levels' else '-mute'), change['name']]
                args += [str(v) for v in change['value']] if change['field'] == 'levels' else ['1' if change['value'] else '0']
                if self.client.call(args, before['context']).strip():
                    raise pulse.AudioError('unexpected-audio-write-output')
            after = self.client.inspect_audio()
            if any(after[k] != before[k] for k in ('context', 'server', 'default_source', 'default_sink')):
                raise pulse.AudioError('audio-readback-uncertain')
            for change in changes:
                row = self.find(after, change['kind'], change, default=change['kind'] == 'source')
                prior = self.find(before, change['kind'], change, default=change['kind'] == 'source')
                if (row[change['field']] != change['value']
                        or any(row[field] != prior[field] for field in ('index', 'channels'))):
                    raise pulse.AudioError('audio-readback-uncertain')
            record.update(status='confirmed', after=after)
            self.journal.write(record)
            return {'status': 'observed', 'receipt': record['id']}

    @staticmethod
    def find(state, kind, target, default):
        if not isinstance(target, dict):
            raise pulse.AudioError('audio-target-required')
        rows = [r for r in state[kind + 's'] if r['name'] == target.get('name') and r['serial'] == target.get('serial')]
        if len(rows) != 1 or (default and rows[0]['name'] != state['default_' + kind]):
            raise pulse.AudioError('audio-target-changed')
        return rows[0]

    def acknowledge(self, token):
        pulse.normal_user()
        with self.journal.lock():
            pending = [r for r in self.journal.history() if r['status'] == 'prepared']
            if not pending or pending[-1]['id'] != token:
                raise pulse.AudioError('latest-pending-audio-receipt-required')
            record = pending[-1]; record['status'] = 'acknowledged'; self.journal.write(record)
            return {'status': 'acknowledged', 'restored': False}


def dispatch(backend, packet, write=False, acknowledge=False):
    if not isinstance(packet, dict) or not isinstance(packet.get('scope'), str) or not SCOPE.fullmatch(packet['scope']):
        raise pulse.AudioError('invalid-audio-scope')
    scope, op = packet['scope'], packet.get('op')
    fields = {'history': set(), 'inspect': set(), 'review-profile': {'card', 'profile', 'card_identity', 'expected'},
              'apply-profile': {'review', 'review_key', 'digest'}, 'restore-profile': {'transaction'},
              'ack-profile': {'transaction'}, 'ack-control': {'transaction'},
              'volume': {'target', 'value', 'expected'}, 'mute': {'target', 'value', 'expected'},
              'master': {'target', 'value', 'expected', 'output'}}
    if not isinstance(op, str) or op not in fields:
        raise pulse.AudioError('unadmitted-audio-operation')
    required = {'scope', 'op'} | fields[op]
    if set(packet) != required and not (op in ('volume', 'mute') and set(packet) == required | {'output'}):
        raise pulse.AudioError('unadmitted-audio-fields')
    if op == 'history':
        return {'profile_history': [{'id': p.name, 'status': r['status'], 'profile': r['profile']}
                for p, r, _ in backend.profiles.store.history()],
                'control_history': [{'id': r['id'], 'status': r['status']} for r in backend.journal.history()]}
    if op == 'inspect':
        return backend.inspect(scope)
    if op == 'review-profile':
        review = backend.profiles.review(packet.get('card'), packet.get('profile'))
        identity = packet.get('card_identity')
        state = backend.client.inspect_audio()
        if (not isinstance(identity, dict) or set(identity) != {'index', 'serial'}
                or any(identity[field] != review['before']['card'][field] for field in identity)
                or packet.get('expected') != key(scope, state)
                or any(state[field] != review['before'][field] for field in ('context', 'server'))):
            raise pulse.AudioError('stale-profile-card-or-audio-owner')
        return {'review': review, 'review_key': key(scope, review)}
    if op in ('apply-profile', 'restore-profile'):
        if not write:
            raise pulse.AudioError('audio-write-grant-required')
        if any(r['status'] == 'prepared' for r in backend.journal.history()):
            raise pulse.AudioError('audio-recovery-required')
        if op == 'restore-profile':
            return backend.profiles.restore(packet.get('transaction'))
        review = packet.get('review')
        if packet.get('review_key') != key(scope, review):
            raise pulse.AudioError('stale-profile-ui-review')
        return backend.profiles.apply(review, packet.get('digest'))
    if op in ('volume', 'mute', 'master'):
        if not write:
            raise pulse.AudioError('audio-write-grant-required')
        return backend.change(scope, packet.get('expected'), op, packet.get('target'), packet.get('value'), packet.get('output'))
    if op in ('ack-profile', 'ack-control'):
        if not acknowledge:
            raise pulse.AudioError('audio-acknowledgement-required')
        return (backend.profiles.acknowledge(packet.get('transaction')) if op == 'ack-profile'
                else backend.acknowledge(packet.get('transaction')))
    raise pulse.AudioError('unadmitted-audio-operation')


def main(argv=None, backend=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-existing-user-audio-queries', action='store_true')
    parser.add_argument('--allow-local-socket-activation-risk', action='store_true')
    parser.add_argument('--apply-user-audio', action='store_true')
    parser.add_argument('--acknowledge-unresolved', action='store_true')
    args = parser.parse_args(argv)
    try:
        if not args.allow_existing_user_audio_queries or not args.allow_local_socket_activation_risk:
            raise pulse.AudioError('audio-query-and-connection-risk-grants-required')
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise pulse.AudioError('audio-request-limit')
        packet = pulse.decode(raw)
        def interrupted(signum, frame):
            raise pulse.AudioError('audio-request-interrupted-or-timeout')
        previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGALRM)}
        signal.setitimer(signal.ITIMER_REAL, 70)
        try:
            result = dispatch(backend or Backend(), packet, args.apply_user_audio, args.acknowledge_unresolved)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            for sig, handler in previous.items(): signal.signal(sig, handler)
        output = {'ok': True, 'scope': packet['scope'], 'result': result}
    except (pulse.AudioError, OSError, ValueError, TypeError, KeyError) as error:
        output = {'ok': False, 'error': error.code if isinstance(error, pulse.AudioError) else 'audio-operation-unavailable'}
    data = profiles.encode(output)
    if len(data) > LIMIT:
        output = {'ok': False, 'error': 'audio-result-limit'}
        data = profiles.encode(output)
    sys.stdout.buffer.write(data)
    return 0 if output['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
