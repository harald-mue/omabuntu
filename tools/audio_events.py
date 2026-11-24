#!/usr/bin/env python3
"""Existing-owner audio event invalidation; session lifetime, no retry or setters."""
import argparse
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time

import audio_pactl as pulse

EVENT = re.compile(rb"Event '(?:new|change|remove)' on (?:source|sink|card|server) #[0-9]{1,10}\Z")


def subscribe(emit, probe=pulse.native_context, popen=subprocess.Popen):
    context = probe()
    binary = Path('/usr/bin/pactl'); info = binary.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o6022
            or not os.access(binary, os.X_OK)):
        raise pulse.AudioError('trusted-pactl-required')
    child = None
    selector = selectors.DefaultSelector()
    buffer = bytearray(); burst = 0; since = time.monotonic()
    try:
        child = popen([str(binary), '--server=unix:' + context['socket'],
            '--client-name=omabuntu-audio-events', 'subscribe'], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'HOME': '/nonexistent', 'XDG_CONFIG_HOME': '/nonexistent'})
        os.set_blocking(child.stdout.fileno(), False)
        selector.register(child.stdout, selectors.EVENT_READ)
        if probe() != context: raise pulse.AudioError('server-context-changed')
        if child.poll() is not None: raise pulse.AudioError('audio-subscription-ended')
        emit('ready')  # Context and child admission, not functional acceptance.
        while child.poll() is None:
            for _, _ in selector.select(0.5):
                data = os.read(child.stdout.fileno(), 4096)
                if not data: return
                buffer.extend(data)
                if len(buffer) > 8192: raise pulse.AudioError('audio-event-frame-limit')
                while b'\n' in buffer:
                    line, _, rest = buffer.partition(b'\n'); buffer[:] = rest
                    if len(line) > 128: raise pulse.AudioError('audio-event-frame-limit')
                    if time.monotonic() - since > 1: burst = 0; since = time.monotonic()
                    burst += 1
                    if burst > 256: raise pulse.AudioError('audio-event-rate-limit')
                    # Bound all frames, including facilities we do not consume.
                    if not EVENT.fullmatch(line): continue
                    if probe() != context: raise pulse.AudioError('server-context-changed')
                    emit('changed')
    finally:
        selector.close()
        if child is not None:
            if child.poll() is None: child.terminate()
            try: child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                try: child.wait(timeout=2)
                except subprocess.TimeoutExpired: pass
            child.stdout.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-existing-user-audio-queries', action='store_true')
    parser.add_argument('--allow-local-socket-activation-risk', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_existing_user_audio_queries or not args.allow_local_socket_activation_risk: return 2
    def stop(signum, frame): raise InterruptedError()
    signal.signal(signal.SIGTERM, stop)
    try:
        subscribe(lambda line: print(line, flush=True))
        return 1  # EOF revokes observation. No reconnect/supervision loop.
    except (pulse.AudioError, OSError, ValueError): return 1


if __name__ == '__main__':
    raise SystemExit(main())
