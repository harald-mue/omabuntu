#!/usr/bin/env python3
"""Start, inspect or stop the reviewed bar for this login session, without expiry."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import check_clock_preview as preview
import check_runtime

ROOT = Path(__file__).resolve().parents[1]
GRANT = {"schema_version": 1, "scope": "bar-session-v1", "lifetime": "session"}


def process_identity(pid):
    if type(pid) is not int or pid <= 1:
        return None
    try:
        base = Path("/proc") / str(pid)
        if base.stat().st_uid != os.getuid():
            return None
        stat = (base / "stat").read_text()
        start = stat[stat.rfind(")") + 2:].split()[19]
        args = (base / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        return {"start_ticks": start, "argv": [arg.decode() for arg in args]}
    except (OSError, ValueError, IndexError, UnicodeError):
        return None


def matches(record):
    if not isinstance(record, dict):
        return False
    expected = record.get("identity")
    if not isinstance(expected, dict) or not isinstance(expected.get("argv"), list):
        return False
    args = expected["argv"]
    if len(args) != 4 or args[1:3] != ["--no-color", "--path"]:
        return False
    try:
        binary = Path(args[0]).relative_to(ROOT / "work/builds")
        entry = Path(args[3]).relative_to(ROOT / "work/bar-session")
    except (TypeError, ValueError):
        return False
    if ".." in binary.parts or ".." in entry.parts:
        return False
    if binary.parts[-5:] != ("stage", "opt", "omabuntu-runtime", "bin", "quickshell") or entry.parts[-2:] != ("probe", "TrialShell.qml"):
        return False
    return process_identity(record.get("pid")) == expected


def read_record(parent):
    path = parent / "current.json"
    if not path.exists():
        return None
    return json.loads(preview.audit_widgets.bounded(ROOT, str(path.relative_to(ROOT)), 8192))


def start(parent, candidate):
    previous = read_record(parent)
    if matches(previous):
        print("Bar already running, PID", previous["pid"])
        return 0
    existing = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "quickshell"], capture_output=True, check=False)
    if existing.returncode != 1:
        raise RuntimeError("Another Quickshell is present or process lookup failed; not starting a second one")
    files, _ = preview.verified_sources(ROOT)
    _, runtime, _ = check_runtime.verify_stage(ROOT, candidate)
    runtime_dir = "/run/user/" + str(os.getuid())
    query_env = {**os.environ, "XDG_RUNTIME_DIR": runtime_dir}
    instances = json.loads(subprocess.check_output(["hyprctl", "instances", "-j"], env=query_env, timeout=10))
    if len(instances) != 1:
        raise RuntimeError("Require exactly one running Hyprland instance")
    instance = instances[0]
    display = instance.get("wl_socket")
    if not isinstance(display, str) or not display.startswith("wayland-") or not display[8:].isdigit():
        raise RuntimeError("Unexpected Wayland socket name")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    base = check_runtime.builder.private_directory(parent / stamp)
    probe = check_runtime.builder.private_directory(base / "probe")
    for name, data in files.items():
        path = probe / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o400)
    env = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME", "LANG", "DBUS_SESSION_BUS_ADDRESS") if key in os.environ}
    env.update(PATH="/usr/local/bin:/usr/bin:/bin:/snap/bin", XDG_RUNTIME_DIR=runtime_dir,
               XDG_CURRENT_DESKTOP="Hyprland", XDG_SESSION_TYPE="wayland", WAYLAND_DISPLAY=display,
               HYPRLAND_INSTANCE_SIGNATURE=instance["instance"], QT_QPA_PLATFORM="wayland",
               QML_IMPORT_PATH=str(runtime / "lib/qt6/qml") + ":" + str(probe),
               OMABUNTU_CLOCK_TRIAL=json.dumps(GRANT), QS_DISABLE_CRASH_HANDLER="1",
               OMABUNTU_NETWORK_HELPER=str(ROOT / "tools" / "network_nm.py"),
               OMABUNTU_DISPLAY_HELPER=str(ROOT / "tools" / "display_backend.py"),
               OMABUNTU_KEYBINDINGS_HELPER=str(ROOT / "tools" / "keybindings_menu.py"),
               OMABUNTU_MENU_HELPER=str(ROOT / "tools" / "menu_model.py"),
               OMABUNTU_MENU_DEFINITIONS=str(ROOT / "config/shell/omabuntu-menu.jsonc"),
               OMABUNTU_MENU_THEMES=str(ROOT / "config/menu/themes.json"),
               OMABUNTU_ELSEWHEN_HELPER=str(ROOT / "tools" / "elsewhen_probe.py"),
               OMABUNTU_WEATHER_HELPER=str(ROOT / "tools" / "weather_probe.py"),
               OMABUNTU_ELSEWHEN_DIR=str(probe / "Elsewhen"))
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=" + runtime_dir + "/bus")
    command = [str(runtime / "bin/quickshell"), "--no-color", "--path", str(probe / "TrialShell.qml")]
    with (base / "output.log").open("x") as log:
        child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    record = {"pid": child.pid, "identity": process_identity(child.pid), "grant": GRANT,
              "log": str(base / "output.log"), "autostart": False}
    (base / "launch.json").write_text(json.dumps(record, indent=2) + "\n")
    temporary = parent / "current.tmp"
    with temporary.open("x") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    temporary.replace(parent / "current.json")
    for _ in range(40):
        text = (base / "output.log").read_text(errors="replace")
        if child.poll() is not None:
            raise RuntimeError("Bar exited; inspect " + record["log"])
        if "OMABUNTU_BAR_SESSION_NO_EXPIRY" in text and "Configuration Loaded" in text:
            print("Bar running without expiry, PID", child.pid)
            print("Log:", record["log"])
            return 0
        time.sleep(0.1)
    raise RuntimeError("Startup not confirmed; process state retained for status/stop, log: " + record["log"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    parser.add_argument("--build-dir", type=Path)
    args = parser.parse_args(argv)
    if args.action == "start" and args.build_dir is None:
        parser.error("start requires --build-dir")
    os.umask(0o077)
    parent = check_runtime.builder.private_directory(ROOT / "work/bar-session")
    descriptor = os.open(parent / "control.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == "start":
            return start(parent, args.build_dir)
        record = read_record(parent)
        if not matches(record):
            print("Bar is not running (no matching recorded process)")
            return 0
        if args.action == "status":
            print("Bar running without expiry, PID", record["pid"])
            return 0
        os.kill(record["pid"], signal.SIGTERM)
        for _ in range(40):
            if not matches(record):
                print("Bar stopped; applications and Hyprland remain running")
                return 0
            time.sleep(0.1)
        raise RuntimeError("Bar did not stop; no forced kill or session stop performed")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, check_runtime.builder.BuildError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
