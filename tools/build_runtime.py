#!/usr/bin/env python3
"""Build the pinned runtime in Bubblewrap; default only prints the plan.

No sudo, package installation, system runtime installation, or desktop activation.
--build explicitly permits source downloads and project-local build/staging writes.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/opt/omabuntu-runtime"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024


class BuildError(RuntimeError):
    pass


def run_with_heartbeat(label, function, interval=15):
    """Show life during a long logged command without printing compiler noise."""
    stop = threading.Event()
    started = time.monotonic()
    def beat():
        while not stop.wait(interval):
            elapsed = int(time.monotonic() - started)
            print('  %s still running (%ds). Details stay in the log.' % (label, elapsed), flush=True)
    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        return function()
    finally:
        stop.set()
        thread.join(timeout=1)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def load_inputs(root):
    manifest = json.loads((root / "packages" / "quickshell-plan.json").read_text())
    lock = json.loads((root / "upstream" / "source-lock.json").read_text())
    if manifest.get("schema_version") != 1 or lock.get("schema_version") != 1:
        raise BuildError("Unsupported build input schema")
    requested = {item["name"]: item for item in manifest["sources"]}
    locked = {item["name"]: item for item in lock["sources"]}
    if set(requested) != {"cpptrace", "quickshell"} or set(locked) != set(requested):
        raise BuildError("Build requires exactly the two reviewed sources")
    for name, item in locked.items():
        expected = requested[name]
        if item["commit"] != expected["commit"] or item["repository"] != expected["url"]:
            raise BuildError("Source lock does not match the package manifest")
        if not re.fullmatch(r"[a-f0-9]{40}", item["commit"]):
            raise BuildError("Source must use a full commit")
        if not re.fullmatch(r"[a-f0-9]{64}", item["archive_sha256"]):
            raise BuildError("Source archive must have a SHA-256 lock")
        repository = item["repository"].removeprefix("https://github.com/")
        expected_url = f"https://codeload.github.com/{repository}/tar.gz/{item['commit']}"
        if not item["repository"].startswith("https://github.com/") or item["archive_url"] != expected_url:
            raise BuildError("Only the exact locked GitHub archive URL is supported")
        if item["archive_root"] != f"{name}-{item['commit']}":
            raise BuildError("Unexpected archive root in lock")
    return manifest, locked


def private_directory(path):
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o077:
        raise BuildError(f"Expected a private real directory: {path}")
    return path


def fetch_archive(spec, cache):
    """Fetch only locked bytes; never execute archive content during download."""
    path = cache / f"{spec['name']}-{spec['commit']}.tar.gz"
    if path.is_symlink():
        raise BuildError("Refusing a symlinked source archive")
    if not path.exists():
        request = urllib.request.Request(spec["archive_url"], headers={"User-Agent": "Omabuntu-pinned-source-build"})
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read(MAX_ARCHIVE_BYTES + 1)
        if len(body) > MAX_ARCHIVE_BYTES or hashlib.sha256(body).hexdigest() != spec["archive_sha256"]:
            raise BuildError("Downloaded archive exceeds the size limit or checksum differs")
        with path.open("xb") as stream:
            stream.write(body)
    if path.stat().st_size != spec["archive_bytes"] or digest(path) != spec["archive_sha256"]:
        raise BuildError("Cached archive does not match source lock; do not silently reseal it")
    return path


def extract_source(archive_path, destination, spec):
    """Reject links/special files and traversal before extracting reviewed archives."""
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 20000 or sum(item.size for item in members) > MAX_EXPANDED_BYTES:
            raise BuildError("Expanded source exceeds safety limits")
        for item in members:
            path = PurePosixPath(item.name)
            if (path.is_absolute() or ".." in path.parts or not path.parts
                    or path.parts[0] != spec["archive_root"]
                    or not (item.isfile() or item.isdir())):
                raise BuildError("Source archive has unsafe paths, links, or special files")
        archive.extractall(destination, members=members, filter="data")
    source = destination / spec["archive_root"]
    if not (source / "CMakeLists.txt").is_file():
        raise BuildError("Source root has no CMakeLists.txt")
    return source


def sandbox_command(workspace, command, source_root, extra_environment=None):
    """Do not expose the host home, session sockets, credentials, or network."""
    args = [
        "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
        "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
        "--dir", "/etc", "--ro-bind", "/etc/alternatives", "/etc/alternatives",
        "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(source_root), "/source",
        "--bind", str(workspace / "build"), "/build",
        "--bind", str(workspace / "stage"), "/stage",
        "--bind", str(workspace / "home"), "/home/build",
        "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", "/home/build", "--setenv", "LANG", "C.UTF-8",
        "--setenv", "LC_ALL", "C.UTF-8", "--setenv", "XDG_CACHE_HOME", "/home/build/.cache",
        "--setenv", "QT_QPA_PLATFORM", "offscreen",
    ]
    for key, value in (extra_environment or {}).items():
        args.extend(["--setenv", key, value])
    return [*args, "--chdir", "/build", "--", *command]


def cmake_command(name, spec, options):
    flags = {
        "CMAKE_BUILD_TYPE": "Release", "CMAKE_INSTALL_PREFIX": PREFIX,
        "CMAKE_INSTALL_LIBDIR": "lib", **options,
    }
    if flags["CMAKE_INSTALL_PREFIX"] != PREFIX or flags["CMAKE_INSTALL_LIBDIR"] != "lib":
        raise BuildError("Unexpected installation layout")
    if name == "quickshell":
        flags["CMAKE_PREFIX_PATH"] = "/stage" + PREFIX
    return [
        "cmake", "-S", "/source/" + spec["archive_root"], "-B", "/build/" + name, "-G", "Ninja",
        *[f"-D{key}={value}" for key, value in sorted(flags.items())],
    ]


def artifact_manifest(stage):
    entries = []
    for path in sorted(stage.rglob("*")):
        relative = str(path.relative_to(stage))
        if path.is_symlink():
            entries.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append({"path": relative, "type": "file", "sha256": digest(path), "bytes": path.stat().st_size})
    return entries


def warning_summary(logs):
    """Keep known upstream diagnostics visible; zero shader failures is not readiness."""
    patterns = {
        "shader_optimizer_failures": r"Failed to run spirv-opt",
        "qt_qml_link_targets": r"The qml plugin '",
        "wayland_xml_validation": r"XML failed validation",
        "compiler_diagnostics": r"warning:",
        "qml_typeinfo": r"is used as base type but cannot be found",
        "unused_cmake_options": r"Manually-specified variables were not used",
    }
    text = "\n".join(path.read_text(errors="replace") for path in sorted(logs.glob("*.log")))
    return {name: len(re.findall(pattern, text)) for name, pattern in patterns.items()}


def assess_outputs(workspace):
    """Assess existing artifacts without rebuilding or launching a desktop."""
    result = {}
    module_root = workspace / "stage" / PREFIX.lstrip("/") / "lib/qt6/qml/Quickshell"
    required_modules = (
        "", "Io", "Wayland", "Hyprland", "Bluetooth", "Networking",
        "Services/Pam", "Services/Polkit", "Services/Pipewire", "Services/Mpris",
        "Services/Notifications", "Services/SystemTray", "Services/UPower",
    )
    result["qml_metadata"] = {
        module or "Quickshell": (module_root / module / "qmldir").is_file()
        for module in required_modules
    }
    if not all(result["qml_metadata"].values()):
        raise BuildError("Required staged QML metadata is incomplete")
    shader_files = sorted(path for path in (workspace / "build/quickshell").rglob("*.qsb") if path.is_file())
    result["shaders"] = [
        {"path": str(path.relative_to(workspace)), "sha256": digest(path), "bytes": path.stat().st_size}
        for path in shader_files
    ]
    required_shaders = {"cliprect.frag.qsb", "cliprect-ub.frag.qsb"}
    if not required_shaders.issubset({path.name for path in shader_files}) or any(path.stat().st_size == 0 for path in shader_files):
        raise BuildError("Expected compiled shader outputs are absent or empty")
    result["warning_counts"] = warning_summary(workspace / "logs")
    if result["warning_counts"]["shader_optimizer_failures"]:
        raise BuildError("Shader optimization failed; inspect the private build log")
    result["artifacts"] = artifact_manifest(workspace / "stage")
    result["warnings"] = [
        f"{category}: {count} diagnostic(s); see logs and runtime-build documentation."
        for category, count in result["warning_counts"].items() if count
    ]
    result["status"] = "staged-with-warnings" if result["warnings"] else "staged"
    result["acceptance"] = "Compilation, staging, and version probe only; not desktop or QML runtime acceptance."
    return result


def build(root=ROOT, jobs=4):
    manifest, sources = load_inputs(root)
    for program in ("bwrap", "cmake", "ninja", "g++", "spirv-opt"):
        if shutil.which(program) is None:
            raise BuildError(f"Required build tool is absent: {program}")
    work = private_directory(root / "work")
    cache = private_directory(work / "source-cache")
    builds = private_directory(work / "builds")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    workspace = private_directory(builds / stamp)
    for name in ("sources", "build", "stage", "home", "logs"):
        private_directory(workspace / name)
    report_path = workspace / "report.json"
    report = {
        "schema_version": 1, "status": "running", "steps": [], "jobs": jobs,
        "source_lock": sources, "manifest": manifest, "prefix": PREFIX,
        "isolation": "Bubblewrap private namespaces; network unavailable; sources read-only; project-only writable binds",
        "limits": "Build/staging only. No custom runtime system installation, shell launch, or desktop/security acceptance.",
    }

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    def run_step(name, command, environment=None, timeout=900):
        argv = sandbox_command(workspace, command, workspace / "sources", environment)
        log_path = workspace / "logs" / (name + ".log")
        step = {"name": name, "command": argv, "log": str(log_path.relative_to(workspace)), "status": "running"}
        report["steps"].append(step)
        save()
        print(f"Running {name}; log: {log_path}", flush=True)
        with log_path.open("x") as stream:
            try:
                result = run_with_heartbeat(name, lambda: subprocess.run(
                    argv, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False))
                step.update(returncode=result.returncode, status="passed" if result.returncode == 0 else "failed")
            except subprocess.TimeoutExpired:
                step.update(returncode=None, status="timeout")
        save()
        if step["status"] != "passed":
            raise BuildError(f"{name} failed; inspect {log_path}")

    save()
    print(f"Private build workspace: {workspace}", flush=True)
    try:
        run_step("sandbox-preflight", ["/usr/bin/true"], timeout=15)
        run_step("shader-tool-version", ["spirv-opt", "--version"], timeout=15)
        for name in ("cpptrace", "quickshell"):
            spec = sources[name]
            archive = fetch_archive(spec, cache)
            extract_source(archive, workspace / "sources", spec)
        for name in ("cpptrace", "quickshell"):
            run_step(name + "-configure", cmake_command(name, sources[name], manifest["proposed_cmake_options"][name]), timeout=180)
            run_step(name + "-build", ["cmake", "--build", "/build/" + name, "--parallel", str(jobs)])
            run_step(name + "-stage", ["cmake", "--install", "/build/" + name], {"DESTDIR": "/stage"}, timeout=120)
        run_step("quickshell-version", ["/stage" + PREFIX + "/bin/quickshell", "--version"], timeout=30)
        report.update(assess_outputs(workspace))
    except (OSError, ValueError, tarfile.TarError, BuildError) as error:
        report.update(status="failed", error=str(error))
        save()
        raise BuildError(f"{error}\nPrivate report: {report_path}") from error
    save()
    print(f"Runtime built and staged, not installed: {workspace / 'stage'}", flush=True)
    for warning in report["warnings"]:
        print(f"Warning: {warning}", flush=True)
    return report_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Explicitly fetch locked sources and build/stage in Bubblewrap")
    parser.add_argument("--jobs", type=int, default=4, choices=range(1, 9), metavar="1..8")
    args = parser.parse_args(argv)
    if not args.build:
        manifest, sources = load_inputs(ROOT)
        print("Plan only. No download, build, staging, or installation performed.")
        for name in ("cpptrace", "quickshell"):
            print(f"  {name}: {sources[name]['commit']}")
        print("After target-specific approval: python3 tools/build_runtime.py --build")
        return 0
    os.umask(0o077)
    try:
        build(jobs=args.jobs)
    except (OSError, ValueError, BuildError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
