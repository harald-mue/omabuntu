"""Review and explicitly provision one scoped PPA; never alter other sources.

Plans use fixed source/key destinations and verified private staging files.
No apt-key, shell, unauthenticated APT, package upgrade or desktop action.
"""
import datetime
import email.utils
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

import install as guided
import omabuntu
import user_install

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'packages/bootstrap.json'
FINGERPRINT = 'A54D23B62FF3FCC76EFF71E8FDBAAA1CF0CCF48E'
URI = 'https://ppa.launchpadcontent.net/cppiber/hyprland/ubuntu'
API = 'https://api.launchpad.net/1.0/~cppiber/+archive/ubuntu/hyprland'
REFERENCE = '~cppiber/ubuntu/hyprland'
ORIGIN = 'LP-PPA-cppiber-hyprland'
SOURCE_NAME = 'omabuntu-hyprland.sources'
KEY_NAME = 'omabuntu-hyprland.gpg'


class SourceError(ValueError):
    pass


def manifest():
    value = json.loads(MANIFEST.read_text())
    expected = {'reference': REFERENCE, 'api_url': API, 'uri': URI,
                'origin': ORIGIN, 'fingerprint': FINGERPRINT, 'component': 'main'}
    if (value.get('schema_version') != 1 or value.get('name') != 'omabuntu-bootstrap'
            or value.get('target') != {'ubuntu': '26.04', 'codename': 'resolute', 'architecture': 'amd64'}
            or value.get('ppa') != expected):
        raise SourceError('Bootstrap source policy differs from the reviewed identity')
    return value


def source_text():
    return ('Types: deb\nURIs: ' + URI + '\nSuites: resolute\nComponents: main\n'
            'Architectures: amd64\nSigned-By: /etc/apt/keyrings/' + KEY_NAME + '\n')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceError('Source/key redirects are not allowed')


def fetch(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'Omabuntu-Setup/1.0'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise SourceError('Source response exceeds limit')
    return data


def run(argv, data=None):
    result = subprocess.run(argv, input=data, capture_output=True, timeout=30, check=False)
    if result.returncode:
        raise SourceError('Source signature/key verification failed')
    return result.stdout


def validate_key_listing(text, now=None):
    now = time.time() if now is None else now
    primary = []
    primary_count = 0
    expecting = False
    for line in text.splitlines():
        fields = line.split(':')
        if fields[0] == 'pub':
            primary_count += 1
            if len(fields) < 7 or fields[1] in ('r', 'e', 'd'):
                raise SourceError('Revoked, expired or disabled PPA key')
            if fields[6] and (not fields[6].isdigit() or int(fields[6]) <= now):
                raise SourceError('PPA key has expired')
            expecting = True
        elif fields[0] == 'fpr' and expecting:
            if len(fields) < 10:
                raise SourceError('Malformed key fingerprint')
            primary.append(fields[9])
            expecting = False
    if primary_count != 1 or expecting or primary != [FINGERPRINT]:
        raise SourceError('PPA primary key fingerprint changed or multiple keys supplied')


def validate_release(data, now=None):
    """Inspect cleartext only after gpgv has verified the complete signed file."""
    text = data.decode('utf-8')
    start = text.find('\n\n')
    end = text.find('\n-----BEGIN PGP SIGNATURE-----')
    if not text.startswith('-----BEGIN PGP SIGNED MESSAGE-----') or start < 0 or end < start:
        raise SourceError('Malformed InRelease')
    fields = {}
    for line in text[start + 2:end].splitlines():
        if line.startswith('- '):
            line = line[2:]
        if line and not line[0].isspace() and ':' in line:
            key, value = line.split(':', 1)
            if key in fields:
                raise SourceError('Duplicate InRelease field')
            fields[key] = value.strip()
    if (fields.get('Origin') != ORIGIN or fields.get('Codename') != 'resolute'
            or fields.get('Suite') != 'resolute' or 'amd64' not in fields.get('Architectures', '').split()
            or 'main' not in fields.get('Components', '').split()):
        raise SourceError('Signed PPA suite/origin/architecture differs')
    now = datetime.datetime.now(datetime.timezone.utc) if now is None else now
    try:
        published = email.utils.parsedate_to_datetime(fields['Date'])
        if published > now + datetime.timedelta(days=1):
            raise SourceError('PPA metadata date is in the future')
        if 'Valid-Until' in fields and email.utils.parsedate_to_datetime(fields['Valid-Until']) <= now:
            raise SourceError('PPA metadata has expired')
    except (KeyError, TypeError, ValueError) as error:
        raise SourceError('PPA metadata dates are invalid or expired') from error
    return {key: fields[key] for key in ('Origin', 'Codename', 'Date')}


def verify_inputs(case, execute=run):
    user_install.private_directory(case)
    for name, limit in [('key.asc', 65536), ('InRelease', 2097152), ('archive.json', 65536)]:
        path = case / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
            raise SourceError('Invalid staged source input')
    if (case / 'key.gpg').is_symlink():
        raise SourceError('Symlinked staged key refused')
    home = user_install.private_directory(case / 'gnupg')
    key = (case / 'key.asc').read_bytes()
    listing = execute(['/usr/bin/gpg', '--batch', '--no-options', '--homedir', str(home),
                       '--with-colons', '--show-keys'], key).decode('utf-8')
    validate_key_listing(listing)
    binary = execute(['/usr/bin/gpg', '--batch', '--no-options', '--homedir', str(home), '--dearmor'], key)
    (case / 'key.gpg').write_bytes(binary)
    execute(['/usr/bin/gpgv', '--homedir', str(home), '--keyring', str(case / 'key.gpg'), str(case / 'InRelease')])
    release = validate_release((case / 'InRelease').read_bytes())
    metadata = json.loads((case / 'archive.json').read_text())
    if (metadata.get('reference') != REFERENCE or metadata.get('private') is not False
            or metadata.get('signing_key_fingerprint') != FINGERPRINT):
        raise SourceError('Launchpad archive identity changed')
    return {'fingerprint': FINGERPRINT, 'key_sha256': hashlib.sha256(binary).hexdigest(),
            'inrelease_sha256': hashlib.sha256((case / 'InRelease').read_bytes()).hexdigest(),
            'archive_sha256': hashlib.sha256((case / 'archive.json').read_bytes()).hexdigest(),
            'release': release}


def path_state(path):
    user_install.safe_parents(path.parent)
    if path.is_symlink():
        raise SourceError('Symlinked source/key path refused')
    if not path.exists():
        return {'existed': False}
    if not path.is_file() or path.stat().st_size > 262144:
        raise SourceError('Unexpected source/key path')
    return {'existed': True, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': path.stat().st_mode & 0o777, 'uid': path.stat().st_uid}


def destinations(apt_root):
    return {'source': apt_root / 'sources.list.d' / SOURCE_NAME,
            'key': apt_root / 'keyrings' / KEY_NAME}


def conflicts(apt_root):
    paths = [apt_root / 'sources.list', *(apt_root / 'sources.list.d').glob('*.list'),
             *(apt_root / 'sources.list.d').glob('*.sources')]
    result = []
    for path in paths:
        if path.is_symlink():
            raise SourceError('Symlinked APT source requires manual review')
        if path.name == SOURCE_NAME or not path.is_file():
            continue
        if path.stat().st_size > 262144:
            raise SourceError('APT source file exceeds review limit')
        lines = '\n'.join(line for line in path.read_text(errors='replace').splitlines()
                          if not line.lstrip().startswith('#'))
        if any(domain + '/cppiber/hyprland/ubuntu' in lines
               for domain in ('ppa.launchpad.net', 'ppa.launchpadcontent.net')):
            result.append(str(path))
    return sorted(result)


def host_check():
    import platform
    info = omabuntu.read_os_release()
    if (info.get('status') != 'ok' or info.get('values', {}).get('ID') != 'ubuntu'
            or info['values'].get('VERSION_ID') != '26.04' or platform.machine() != 'x86_64'):
        raise SourceError('PPA provisioning supports Ubuntu 26.04 x86_64 only')


def prepare(case, apt_root=Path('/etc/apt'), downloader=fetch, execute=run, check_host=host_check):
    spec = manifest()
    check_host()
    if execute is run and any(not os.access(path, os.X_OK) for path in ('/usr/bin/gpg', '/usr/bin/gpgv')):
        raise SourceError('GnuPG tools are missing; review --packages --base-only before --ppa')
    case = user_install.private_directory(case)
    for name, url, limit in [
        ('archive.json', API, 65536),
        ('key.asc', 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x' + FINGERPRINT, 65536),
        ('InRelease', URI + '/dists/resolute/InRelease', 2097152),
    ]:
        target = case / name
        with target.open('xb') as stream:
            stream.write(downloader(url, limit))
    verified = verify_inputs(case, execute)
    paths = destinations(apt_root)
    before = {name: path_state(path) for name, path in paths.items()}
    blockers = []
    for name, data in [('source', source_text().encode()), ('key', (case / 'key.gpg').read_bytes())]:
        if before[name]['existed'] and (before[name]['sha256'] != hashlib.sha256(data).hexdigest()
                                         or before[name]['uid'] != 0 or before[name]['mode'] != 0o644):
            blockers.append('Existing managed ' + name + ' differs in content/ownership/mode; refusing replacement')
        if before[name]['existed']:
            (case / ('before-' + name)).write_bytes(paths[name].read_bytes())
    duplicates = conflicts(apt_root)
    if duplicates:
        blockers.append('PPA is already configured outside these managed paths; review duplicate sources')
    plan = {'schema_version': 1, 'kind': 'omabuntu-ppa-plan', 'case': str(case.absolute()),
            'policy_digest': guided.digest(spec), 'verified': verified, 'before': before,
            'duplicates': duplicates, 'blockers': blockers, 'apt_root': str(apt_root),
            'source': source_text(), 'status': 'blocked' if blockers else 'review-required'}
    user_install.atomic_json(case / 'plan.json', plan)
    return plan


def apply(plan, approval, execute=guided.terminal_install, check_host=host_check, verify=verify_inputs):
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise SourceError('Run as a normal user; sudo is only used for the approved commands')
    if guided.digest(plan) != approval or plan.get('kind') != 'omabuntu-ppa-plan' or plan.get('blockers'):
        raise SourceError('Source plan approval is missing, changed or blocked')
    check_host()
    if plan['policy_digest'] != guided.digest(manifest()) or plan['source'] != source_text():
        raise SourceError('Source policy changed; review again')
    # Public CLI never accepts a system destination override.
    if plan['apt_root'] != '/etc/apt':
        raise SourceError('Only the fixed Ubuntu APT directory is permitted')
    case = user_install.safe_parents(Path(plan['case']))
    if verify(case) != plan['verified']:
        raise SourceError('Staged source verification changed; review again')
    apt_root = Path('/etc/apt')
    paths = destinations(apt_root)
    if {name: path_state(path) for name, path in paths.items()} != plan['before'] or conflicts(apt_root) != plan['duplicates']:
        raise SourceError('APT sources changed; review again')
    staged_source = case / 'source.sources'
    if staged_source.is_symlink() or (staged_source.exists() and not staged_source.is_file()):
        raise SourceError('Unsafe staged source file')
    if staged_source.exists():
        if staged_source.read_bytes() != source_text().encode():
            raise SourceError('Staged source file changed')
    else:
        with staged_source.open('x') as stream:
            stream.write(source_text())
    journal = {'status': 'applying', 'before': plan['before'], 'commands_completed': 0}
    user_install.atomic_json(case / 'apply.json', journal)
    commands = []
    for name, staged in [('key', case / 'key.gpg'), ('source', case / 'source.sources')]:
        parent = paths[name].parent
        user_install.safe_parents(parent)
        if not parent.exists():
            commands.append(['sudo', 'install', '-d', '-m', '0755', '--', str(parent)])
        if not plan['before'][name]['existed']:
            commands.append(['sudo', 'install', '-m', '0644', '--', str(staged), str(paths[name])])
    commands.append(['sudo', 'apt-get', 'update'])
    try:
        for command in commands:
            if command[:2] == ['sudo', 'install'] and '-d' not in command:
                name = next(name for name, target in paths.items() if str(target) == command[-1])
                if path_state(paths[name]) != plan['before'][name]:
                    raise SourceError('Source/key changed before write; refusing replacement')
            if execute(command) != 0:
                raise SourceError('Source apply/metadata refresh failed; inspect private journal')
            journal['commands_completed'] += 1
            user_install.atomic_json(case / 'apply.json', journal)
        expected = {'source': source_text().encode(), 'key': (case / 'key.gpg').read_bytes()}
        for name, data in expected.items():
            if path_state(paths[name]).get('sha256') != hashlib.sha256(data).hexdigest():
                raise SourceError('Installed source/key verification differs')
        journal['status'] = 'verified'
    except BaseException as error:
        journal.update(status='incomplete-review-required', error=type(error).__name__)
        user_install.atomic_json(case / 'apply.json', journal)
        raise
    user_install.atomic_json(case / 'apply.json', journal)
    return {'status': 'source-installed-metadata-refreshed', 'journal': str(case / 'apply.json'),
            'packages_installed': False, 'desktop_changed': False}
