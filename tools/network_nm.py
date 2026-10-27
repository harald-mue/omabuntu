#!/usr/bin/env python3
"""Ubuntu NetworkManager actions for the derived Omarchy network panel.

Reads and changes only the active connection's DNS, the active Wi-Fi band,
and existing Ethernet or VPN profiles. QR output is the module matrix, never
the passphrase. There is no sudo, no global DNS file, and no Omarchy helper.
"""
import ipaddress
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class CommandError(Exception):
    def __init__(self, token):
        super().__init__(token)
        self.token = token


TOOLS = {"nmcli", "ip", "iw", "curl"}
UUID = __import__("re").compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
PROVIDERS = {
    "Cloudflare": (["1.1.1.1", "1.0.0.1"], ["2606:4700:4700::1111", "2606:4700:4700::1001"]),
    "Google": (["8.8.8.8", "8.8.4.4"], ["2001:4860:4860::8888", "2001:4860:4860::8844"]),
}
BAND_TO_NM = {"2.4": "bg", "5": "a", "6": "6GHz"}
NM_TO_BAND = {"bg": "2.4", "a": "5", "6GHz": "6", "": "auto"}
PROFILE_TYPES = {"802-3-ethernet": "ethernet", "vpn": "vpn"}
DOWN_URL = "https://speed.cloudflare.com/__down?bytes=8000000"
UP_URL = "https://speed.cloudflare.com/__up"


def parse_terse(line):
    parts, buf, index = [], "", 0
    while index < len(line):
        if line[index] == "\\" and index + 1 < len(line):
            buf += line[index + 1]
            index += 2
            continue
        if line[index] == ":":
            parts.append(buf)
            buf = ""
            index += 1
            continue
        buf += line[index]
        index += 1
    parts.append(buf)
    return parts


def band_for_freq(value):
    digits = ""
    for char in str(value or ""):
        if char.isdigit():
            digits += char
        elif digits:
            break
    if not digits:
        return ""
    mhz = int(digits)
    if 2400 <= mhz < 2500:
        return "2.4"
    if 4900 <= mhz < 5925:
        return "5"
    if 5925 <= mhz < 7125:
        return "6"
    return ""


def wifi_escape(value):
    return "".join("\\" + char if char in "\\;,:\"" else char for char in value)


def wifi_payload(ssid, key_mgmt, psk):
    mgmt = (key_mgmt or "").lower()
    if "eap" in mgmt:
        raise CommandError("enterprise")
    if not ssid:
        raise CommandError("no-ssid")
    name = wifi_escape(ssid)
    if psk:
        return f"WIFI:T:WPA;S:{name};P:{wifi_escape(psk)};;"
    return f"WIFI:T:nopass;S:{name};;"


def matrix_for(payload):
    import qrcodegen
    code = qrcodegen.QrCode.encode_text(payload, qrcodegen.QrCode.Ecc.MEDIUM)
    size = code.get_size()
    modules = "".join("1" if code.get_module(x, y) else "0" for y in range(size) for x in range(size))
    if len(modules) != size * size or size > 80:
        raise CommandError("qr-failed")
    return {"ok": True, "size": size, "modules": modules}


def capture(run, argv, timeout=15):
    if not argv or argv[0] not in TOOLS:
        raise CommandError("usage")
    code, out = run(argv, timeout)
    if code != 0:
        raise CommandError("command-failed")
    return out or ""


def optional(run, argv, timeout=15):
    try:
        return capture(run, argv, timeout)
    except CommandError:
        return ""


def field(run, uuid, name):
    return optional(run, ["nmcli", "-g", name, "connection", "show", uuid]).strip()


def connected_wifi(run):
    text = optional(run, ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"])
    for line in text.splitlines():
        parts = parse_terse(line)
        if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
            return parts[0]
    return ""


def default_device(run):
    text = optional(run, ["ip", "-4", "route", "show", "default"])
    for line in text.splitlines():
        parts = line.split()
        if "dev" in parts:
            index = parts.index("dev")
            if index + 1 < len(parts):
                return parts[index + 1]
    return connected_wifi(run)


def device_uuid(run, device):
    if not device:
        return ""
    return optional(run, ["nmcli", "-g", "GENERAL.CON-UUID", "device", "show", device]).strip()


def active_uuid(run):
    found = device_uuid(run, default_device(run))
    return found if UUID.match(found or "") else ""


def normalize_servers(value):
    parts = []
    for token in str(value or "").replace(";", ",").replace(" ", ",").split(","):
        token = token.strip()
        if token:
            parts.append(str(ipaddress.ip_address(token)))
    return parts


def provider_for(v4_ignore, v4, v6_ignore, v6):
    if v4_ignore != "yes" or not v4:
        return "DHCP"
    try:
        current4 = normalize_servers(v4)
        current6 = normalize_servers(v6) if v6_ignore == "yes" and v6 else []
    except ValueError:
        return "Custom"
    for name, (want4, want6) in PROVIDERS.items():
        if current4 == want4 and (not current6 or current6 == want6):
            return name
    return "Custom"


def dns_status(run, uuid):
    if not uuid:
        return "DHCP"
    return provider_for(
        field(run, uuid, "ipv4.ignore-auto-dns"),
        field(run, uuid, "ipv4.dns"),
        field(run, uuid, "ipv6.ignore-auto-dns"),
        field(run, uuid, "ipv6.dns"))


def parse_servers(text):
    try:
        servers = normalize_servers(text)
    except ValueError:
        raise CommandError("dns") from None
    if not 1 <= len(servers) <= 4:
        raise CommandError("dns")
    v4 = [item for item in servers if ":" not in item]
    v6 = [item for item in servers if ":" in item]
    if not v4 and not v6:
        raise CommandError("dns")
    return v4, v6


def write_dns(run, uuid, v4_ignore, v4, v6_ignore, v6):
    capture(run, ["nmcli", "connection", "modify", uuid,
                  "ipv4.ignore-auto-dns", v4_ignore,
                  "ipv4.dns", v4,
                  "ipv6.ignore-auto-dns", v6_ignore,
                  "ipv6.dns", v6], 20)


def dns_set(run, provider, custom):
    uuid = active_uuid(run)
    if not uuid:
        raise CommandError("no-connection")
    previous = (
        field(run, uuid, "ipv4.ignore-auto-dns") or "no",
        field(run, uuid, "ipv4.dns"),
        field(run, uuid, "ipv6.ignore-auto-dns") or "no",
        field(run, uuid, "ipv6.dns"))
    if provider == "DHCP":
        desired = ("no", "", "no", "")
    elif provider == "Custom":
        v4, v6 = parse_servers(custom)
        desired = ("yes" if v4 else "no", ",".join(v4), "yes" if v6 else "no", ",".join(v6))
    elif provider in PROVIDERS:
        v4, v6 = PROVIDERS[provider]
        desired = ("yes", ",".join(v4), "yes", ",".join(v6))
    else:
        raise CommandError("dns")
    write_dns(run, uuid, *desired)
    device = default_device(run)
    if device:
        code, _out = run(["nmcli", "device", "reapply", device], 20)
        if code != 0:
            write_dns(run, uuid, *previous)
            raise CommandError("reverted")
    return {"ok": True}


def band_status(run):
    device = connected_wifi(run)
    if not device:
        return {"band": "", "selected": "auto", "available": []}
    link = optional(run, ["iw", "dev", device, "link"])
    ssid, freq = "", ""
    for line in link.splitlines():
        stripped = line.strip()
        if stripped.startswith("SSID:"):
            ssid = stripped.split("SSID:", 1)[1].strip()
        elif stripped.startswith("freq:"):
            freq = stripped.split("freq:", 1)[1].strip()
    current = band_for_freq(freq)
    found = {current} if current else set()
    listing = optional(run, ["nmcli", "-t", "-f", "SSID,FREQ", "dev", "wifi", "list", "ifname", device, "--rescan", "no"])
    for line in listing.splitlines():
        parts = parse_terse(line)
        if len(parts) >= 2 and parts[0] == ssid:
            band = band_for_freq(parts[1])
            if band:
                found.add(band)
    uuid = device_uuid(run, device)
    selected = "auto"
    if UUID.match(uuid or ""):
        selected = NM_TO_BAND.get(field(run, uuid, "802-11-wireless.band"), "auto")
    order = [band for band in ("2.4", "5", "6") if band in found]
    return {"band": current, "selected": selected, "available": order}


def band_set(run, target):
    if target not in {"auto", "2.4", "5", "6"}:
        raise CommandError("band")
    device = connected_wifi(run)
    uuid = device_uuid(run, device)
    if not UUID.match(uuid or ""):
        raise CommandError("no-wifi")
    status = band_status(run)
    if target != "auto" and target not in status["available"]:
        raise CommandError("not-available")
    previous = field(run, uuid, "802-11-wireless.band")
    desired = "" if target == "auto" else BAND_TO_NM[target]
    if previous == desired:
        return {"ok": True}
    capture(run, ["nmcli", "connection", "modify", uuid, "802-11-wireless.band", desired], 20)
    code, _out = run(["nmcli", "connection", "up", uuid], 30)
    if code != 0:
        run(["nmcli", "connection", "modify", uuid, "802-11-wireless.band", previous], 20)
        run(["nmcli", "connection", "up", uuid], 30)
        raise CommandError("reverted")
    return {"ok": True}


def profiles(run):
    text = optional(run, ["nmcli", "-t", "-f", "UUID,TYPE,NAME,DEVICE", "connection", "show"])
    rows = {"ethernet": [], "vpn": []}
    for line in text.splitlines():
        parts = parse_terse(line)
        if len(parts) < 4 or not UUID.match(parts[0] or "") or parts[1] not in PROFILE_TYPES:
            continue
        rows[PROFILE_TYPES[parts[1]]].append({
            "uuid": parts[0], "name": parts[2] or parts[0], "active": bool(parts[3])})
    return rows


def change_profile(run, uuid, up):
    if not UUID.match(uuid or ""):
        raise CommandError("profile")
    kind = field(run, uuid, "connection.type")
    if kind not in PROFILE_TYPES:
        raise CommandError("profile")
    action = "up" if up else "down"
    code, _out = run(["nmcli", "connection", action, uuid], 30)
    if code != 0:
        raise CommandError("failed")
    return {"ok": True}


def qr(run):
    device = connected_wifi(run)
    uuid = device_uuid(run, device)
    if not UUID.match(uuid or ""):
        raise CommandError("no-wifi")
    ssid = field(run, uuid, "802-11-wireless.ssid")
    mgmt = field(run, uuid, "802-11-wireless-security.key-mgmt")
    if "eap" in mgmt.lower():
        raise CommandError("enterprise")
    psk = ""
    if mgmt and mgmt.lower() not in {"owe", "none"}:
        code, out = run(["nmcli", "--show-secrets", "-g", "802-11-wireless-security.psk", "connection", "show", uuid], 15)
        psk = out.strip() if code == 0 else ""
        if not psk:
            raise CommandError("no-secret")
    try:
        return matrix_for(wifi_payload(ssid, mgmt, psk))
    except CommandError:
        raise
    except Exception:
        raise CommandError("qr-failed") from None


def megabits(value):
    try:
        rate = float(str(value).strip() or "nan")
    except ValueError:
        raise CommandError("unavailable") from None
    if rate < 0 or rate != rate:
        raise CommandError("unavailable")
    return round(rate * 8 / 1_000_000, 1)


def speed(run):
    payload = tempfile.NamedTemporaryFile(prefix="omabuntu-speed-", delete=False)
    try:
        payload.write(b"\0" * (512 * 1024))
        payload.close()
        down_code, down_out = run(
            ["curl", "-fsS", "--proto", "=https", "--max-time", "8", "-o", "/dev/null",
             "-w", "%{speed_download}", DOWN_URL], 12)
        up_code, up_out = run(
            ["curl", "-fsS", "--proto", "=https", "--max-time", "8", "-o", "/dev/null",
             "-w", "%{speed_upload}", "-X", "POST", "--data-binary", "@" + payload.name, UP_URL], 12)
    finally:
        payload.close()
        Path(payload.name).unlink(missing_ok=True)
    if down_code != 0 or up_code != 0:
        raise CommandError("unavailable")
    return {"ok": True, "down": megabits(down_out), "up": megabits(up_out)}


def active_ap_signal(run):
    """Read cached AP strength without requesting a scan or any secrets."""
    device = connected_wifi(run)
    strength = -1
    if device:
        text = optional(run, ["nmcli", "-t", "-f", "IN-USE,SIGNAL", "dev", "wifi", "list",
                              "ifname", device, "--rescan", "no"])
        for line in text.splitlines():
            parts = parse_terse(line)
            if len(parts) == 2 and parts[0] == "*":
                try:
                    value = int(parts[1])
                except ValueError:
                    continue
                if 0 <= value <= 100:
                    strength = value
                    break
    return {"ok": True, "iface": device, "signal": strength}


def status(run):
    uuid = active_uuid(run)
    band = band_status(run)
    saved = profiles(run)
    return {"ok": True, "dns": dns_status(run, uuid), **band,
            "ethernet": saved["ethernet"], "vpn": saved["vpn"]}


def dispatch(argv, run):
    command = argv[1] if len(argv) > 1 else ""
    try:
        if command == "signal" and len(argv) == 2:
            result = active_ap_signal(run)
        elif command == "status" and len(argv) == 2:
            result = status(run)
        elif command == "dns-set" and len(argv) == 3 and argv[2] in {"DHCP", "Cloudflare", "Google"}:
            result = dns_set(run, argv[2], "")
        elif command == "dns-set" and len(argv) == 4 and argv[2] == "Custom":
            result = dns_set(run, "Custom", argv[3])
        elif command == "band-set" and len(argv) == 3:
            result = band_set(run, argv[2])
        elif command == "connect" and len(argv) == 3:
            result = change_profile(run, argv[2], True)
        elif command == "disconnect" and len(argv) == 3:
            result = change_profile(run, argv[2], False)
        elif command == "qr" and len(argv) == 2:
            result = qr(run)
        elif command == "speed" and len(argv) == 2:
            result = speed(run)
        else:
            result = {"ok": False, "error": "usage"}
    except CommandError as error:
        result = {"ok": False, "error": error.token}
    return result


def live_run(argv, timeout):
    if not argv or argv[0] not in TOOLS:
        raise CommandError("usage")
    binary = shutil.which(argv[0])
    if not binary:
        raise CommandError("missing")
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    try:
        completed = subprocess.run([binary, *argv[1:]], check=False, capture_output=True,
                                   text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise CommandError("timeout") from None
    return completed.returncode, completed.stdout


def main(argv):
    result = dispatch(argv, live_run)
    print(json.dumps(result), flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
