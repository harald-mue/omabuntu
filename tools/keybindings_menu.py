#!/usr/bin/env python3
"""Searchable Hyprland keybindings menu, matching Omarchy's Super+K behavior.

The menu reads the compositor's current binds and can run one of those existing
actions. It never creates, changes, or removes a binding. Lua bindings, which
Hyprland reports as dispatcher __lua, are recovered by loading the local
configuration inside a restricted Lua state. Session-ending commands stay
visible but are not launched from the menu.
"""
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


COLUMN = 35
MAX_SOURCE = 262144
MAX_BINDS = 1_000_000
ALTERNATIVES = (
    "Close window",
    "Calculator",
    "Toggle scratchpad",
    "Move window to scratchpad",
)
RENAMES = {
    "comma": "COMMA", "grave": "~", "period": "PERIOD",
    "minus": "MINUS", "equal": "EQUAL", "slash": "SLASH",
}
MODIFIERS = {
    0: "", 1: "SHIFT", 4: "CTRL", 5: "SHIFT CTRL", 8: "ALT", 9: "SHIFT ALT",
    12: "CTRL ALT", 13: "SHIFT CTRL ALT", 64: "SUPER", 65: "SUPER SHIFT",
    68: "SUPER CTRL", 69: "SUPER SHIFT CTRL", 72: "SUPER ALT", 73: "SUPER SHIFT ALT",
    76: "SUPER CTRL ALT", 77: "SUPER SHIFT CTRL ALT",
}
FALLBACK_CODES = {
    "10": "1", "11": "2", "12": "3", "13": "4", "14": "5", "15": "6",
    "16": "7", "17": "8", "18": "9", "19": "0", "20": "MINUS", "21": "EQUAL",
    "59": "COMMA", "60": "PERIOD", "61": "SLASH",
}
MOUSE = {"272": "LEFT MOUSE BUTTON", "273": "RIGHT MOUSE BUTTON", "274": "MIDDLE MOUSE BUTTON"}
DISPATCHER_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
SESSION_TOKENS = (
    "systemctl", "loginctl", "shutdown", "reboot", "poweroff", "halt",
    "hyprlock", "swaylock", "swayidle", "lock", "suspend", "hibernate",
    "idle", "exit", "logout",
)


class CommandError(Exception):
    def __init__(self, token):
        super().__init__(token)
        self.token = token


def _priority(label):
    """Omarchy's description order. Later matches replace earlier ones."""
    line = re.sub(r" / [^\u2192]*\u2192", " \u2192", label, count=1)
    score = 50
    if re.search(r"Keybindings", line):
        score = 0
    if re.search(r"Omarchy menu", line):
        score = 1
    if re.search(r"Terminal", line):
        score = 2
    if re.search(r"Browser", line) and not re.search(r"Browser\s*\(", line) and not re.search(
            r"SUPER SHIFT.*\+.*B.*\u2192.*Browser", line):
        score = 3
    if re.search(r"File manager", line) and not re.search(r"File manager \(cwd\)", line):
        score = 4
    rules = (
        (r"Launch apps", 5), (r"System menu", 6), (r"Theme menu", 7), (r"Full screen", 8),
        (r"Full width", 9), (r"Close window", 10), (r"Close all windows", 11), (r"Lock system", 12),
        (r"Toggle window floating", 13), (r"Toggle window split", 14), (r"Pop window", 15),
        (r"Universal", 16), (r"Clipboard", 17), (r"Audio controls", 18), (r"Bluetooth controls", 19),
        (r"Wifi controls", 20), (r"Emojis", 21), (r"Color picker", 22), (r"Screenshot", 23),
        (r"Screenrecording", 24), (r"Tmux", 25), (r"Herdr", 26),
        (r"SUPER SHIFT.*\+.*B.*\u2192.*Browser", 27), (r"File manager \(cwd\)", 28),
        (r"(?:Switch|Next|Former|Previous).*workspace", 29), (r"Move window to workspace", 30),
        (r"Move window silently to workspace", 31), (r"Swap window", 32), (r"Focus", 33),
        (r"Move window$", 34), (r"Resize window", 35), (r"Expand window", 36), (r"Shrink window", 37),
        (r"scratchpad", 38), (r"notification", 39), (r"Toggle window transparency", 40),
        (r"Toggle workspace gaps", 41), (r"Toggle nightlight", 42), (r"Toggle locking", 43),
        (r"group", 94), (r"Scroll active workspace", 95), (r"Cycle to", 96), (r"Reveal active", 97),
        (r"Apple Display", 98), (r"XF86", 99), (r"Tmux keybindings", 100), (r"Herdr keybindings", 101),
    )
    for pattern, value in rules:
        if re.search(pattern, line):
            score = value
    return score


def readable_action(kind, arg):
    """Label a binding whose configuration did not give it a description."""
    text = " ".join(str(arg or "").split())
    if kind == "exec":
        return text or "Run command"
    known = (
        (r"^hl\.dsp\.window\.close\(\)$", "Close window"),
        (r"^hl\.dsp\.window\.float\(", "Toggle floating"),
        (r"^hl\.dsp\.window\.fullscreen\(", "Full screen"),
        (r"^hl\.dsp\.window\.pseudo\(\)$", "Toggle pseudo tiling"),
        (r"^hl\.dsp\.layout\(\"togglesplit\"\)$", "Toggle split"),
        (r"^hl\.dsp\.window\.drag\(\)$", "Drag window"),
        (r"^hl\.dsp\.window\.resize\(\)$", "Resize window"),
        (r"^hl\.dsp\.focus\(\{ direction = \"([^\"]+)\" \}\)$", "Focus {0}"),
        (r"^hl\.dsp\.focus\(\{ workspace = ([0-9]+) \}\)$", "Switch to workspace {0}"),
        (r"^hl\.dsp\.window\.swap\(\{ direction = \"([^\"]+)\" \}\)$", "Swap {0}"),
        (r"^hl\.dsp\.window\.move\(\{ follow = false, workspace = ([0-9]+) \}\)$",
         "Move window silently to workspace {0}"),
        (r"^hl\.dsp\.window\.move\(\{ workspace = ([0-9]+) \}\)$", "Move window to workspace {0}"),
        (r"^hl\.dsp\.window\.move\(\{ follow = false, workspace = \"special:[^\"]+\" \}\)$",
         "Move window to scratchpad"),
        (r"^hl\.dsp\.workspace\.toggle_special\(\"([^\"]+)\"\)$", "Toggle scratchpad"),
    )
    for pattern, label in known:
        found = re.match(pattern, text)
        if found:
            return label.format(*found.groups())
    plain = text.removeprefix("hl.dsp.").strip()
    return (plain or "Key binding")[:40]


def session_action(value):
    text = str(value or "").lower()
    if "uwsm stop" in text:
        return True
    return any(re.search(rf"(^|[^a-z0-9_.-]){token}([^a-z0-9_.-]|$)" , text) for token in SESSION_TOKENS)


def parse_binds(text):
    """Parse plain `hyprctl binds` records. JSON is intentionally not used."""
    if len(text) > MAX_BINDS:
        raise CommandError("binds")
    records, current = [], None

    def emit():
        if current is not None:
            records.append(current)

    for line in text.splitlines():
        if line.startswith("bind"):
            emit()
            current = {"modmask": "0", "key": "", "keycode": "0", "description": "",
                       "dispatcher": "", "arg": ""}
            continue
        matched = re.match(r"^\t([a-z]+): (.*)$", line)
        if current is not None and matched and matched.group(1) in current:
            current[matched.group(1)] = matched.group(2)
    emit()
    return records


def _display_token(token, symbols):
    renamed = RENAMES.get(token, token)
    coded = re.match(r"^code:([0-9]+)$", renamed)
    if coded:
        code = coded.group(1)
        symbol = (symbols or {}).get(code) or FALLBACK_CODES.get(code)
        if not symbol:
            return renamed
        if symbol.upper() in ("GRAVE", "ASCIICIRCUM"):
            return "~" if symbol.upper() == "GRAVE" else "^"
        return symbol.upper() if any(character.isalpha() for character in symbol) else symbol
    mouse = re.match(r"^mouse:([0-9]+)$", renamed)
    if mouse:
        return MOUSE.get(mouse.group(1), renamed)
    return renamed


def _lookup_key(record):
    key = record["key"].rsplit(" + ", 1)[-1]
    if not key and record["keycode"] not in ("", "0"):
        key = "code:" + record["keycode"]
    return key


def _cache(lua_rows):
    by_key, described, key_for_description = {}, {}, {}
    for row in lua_rows or []:
        modmask, key = str(row.get("modmask", "")), str(row.get("key", ""))
        kind, description = str(row.get("kind", "")), str(row.get("description", ""))
        if not modmask.isdigit() or not key or kind not in ("exec", "lua", "sendshortcut"):
            continue
        meta = {"kind": kind, "arg": str(row.get("arg", "")), "description": description}
        by_key[(modmask, key)] = meta
        if description:
            described[(modmask, description, key)] = meta
            key_for_description[(modmask, description)] = key
    return by_key, described, key_for_description


def command_label(dispatcher, arg):
    """Omarchy's label when a bind has no description of its own."""
    action = ",".join(part for part in (dispatcher, arg) if part)
    action = re.sub(r"(^|,)\s*exec\s*,?", "", action)
    action = re.sub(r"(^|\s)uwsm(?:-app| app)\s+--\s+", "", action)
    return " ".join(action.split()).strip(" ,")


def format_binds(text, lua_rows=None, symbols=None):
    by_key, described, key_for_description = _cache(lua_rows)
    prepared = []
    seen = set()
    for record in parse_binds(text):
        row = dict(record)
        modmask, key = row["modmask"], _lookup_key(row)
        if not key and row["description"]:
            key = key_for_description.get((modmask, row["description"]), "")
        if row["dispatcher"] == "__lua" and row["description"] and key:
            found = described.get((modmask, row["description"], key))
            row["dispatcher"] = found["kind"] if found else ""
            row["arg"] = found["arg"] if found else ""
        if not row["description"] and row["dispatcher"] in ("__lua", ""):
            found = by_key.get((modmask, key))
            if not found:
                continue
            row["dispatcher"] = found["kind"]
            row["arg"] = found["arg"]
            row["description"] = found["description"] or readable_action(found["kind"], found["arg"])
        if not row["description"]:
            row["description"] = command_label(row["dispatcher"], row["arg"])
        if not row["description"] or key == "code:201":
            continue
        identity = (modmask, key, row["description"], row["dispatcher"], row["arg"])
        if identity in seen:
            continue
        seen.add(identity)
        chord_key = _display_token(key, symbols)
        modifiers = MODIFIERS.get(int(modmask), modmask) if str(modmask).isdigit() else modmask
        chord = f"{modifiers} + {chord_key}" if modifiers and chord_key else modifiers or chord_key
        prepared.append({"chord": chord, "action": row["description"], "dispatcher": row["dispatcher"],
                         "arg": row["arg"]})

    merged, leads = [], {}
    for row in prepared:
        if not row["action"]:
            continue
        identity = (row["action"], row["dispatcher"], row["arg"])
        previous = leads.get(identity)
        together = f"{previous['chord']} / {row['chord']}" if previous else ""
        if previous and row["action"] in ALTERNATIVES and row["dispatcher"] and len(together) <= COLUMN:
            previous["chord"] = together
            continue
        leads[identity] = row
        merged.append(row)
    rows = [{"label": f"{row['chord']:<{COLUMN}} \u2192 {row['action']}", "chord": row["chord"],
             "action": row["action"], "dispatcher": row["dispatcher"], "arg": row["arg"]} for row in merged]
    rows.sort(key=lambda row: (_priority(row["label"]), row["label"], row["dispatcher"], row["arg"]))
    return rows


_LUA = None


def _lua_library():
    global _LUA
    if _LUA is None:
        library = ctypes.CDLL("liblua5.4.so.0")
        library.luaL_newstate.restype = ctypes.c_void_p
        library.luaL_openlibs.argtypes = [ctypes.c_void_p]
        library.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        library.luaL_loadstring.restype = ctypes.c_int
        library.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_ssize_t, ctypes.c_void_p]
        library.lua_pcallk.restype = ctypes.c_int
        library.lua_getglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        library.lua_type.argtypes = [ctypes.c_void_p, ctypes.c_int]
        library.lua_type.restype = ctypes.c_int
        library.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        library.lua_tolstring.restype = ctypes.c_char_p
        library.lua_close.argtypes = [ctypes.c_void_p]
        _LUA = library
    return _LUA


def _lua_string(library, state):
    if library.lua_type(state, -1) != 4:
        return ""
    value = library.lua_tolstring(state, -1, None)
    return value.decode() if value else ""


SCAN_LUA = r'''
local user_source = __USER_SOURCE__
local results = {}
local modifiers = { SHIFT = 1, CTRL = 4, CONTROL = 4, ALT = 8, SUPER = 64 }

local function clean(value)
  return tostring(value or ""):gsub("[%z\t\r\n]", " "):sub(1, 2000)
end

local function split_keys(keys)
  local modmask, key = 0, ""
  for part in string.gmatch(tostring(keys or ""), "[^+]+") do
    local value = part:gsub("^%s+", ""):gsub("%s+$", "")
    local modifier = modifiers[string.upper(value)]
    if modifier then modmask = modmask + modifier else key = value end
  end
  return modmask, key
end

local function lua_literal(value)
  local value_type = type(value)
  if value_type == "string" then return string.format("%q", value)
  elseif value_type == "number" or value_type == "boolean" then return tostring(value)
  elseif value_type == "table" then
    local parts, keys, count = {}, {}, #value
    for index = 1, count do parts[#parts + 1] = lua_literal(value[index]) end
    for key in pairs(value) do
      if not (type(key) == "number" and key >= 1 and key <= count and math.floor(key) == key) then
        keys[#keys + 1] = key
      end
    end
    table.sort(keys, function(left, right) return tostring(left) < tostring(right) end)
    for _, key in ipairs(keys) do
      local prefix = (type(key) == "string" and key:match("^[%a_][%w_]*$")) and (key .. " = ")
        or ("[" .. lua_literal(key) .. "] = ")
      parts[#parts + 1] = prefix .. lua_literal(value[key])
    end
    return "{ " .. table.concat(parts, ", ") .. " }"
  end
  return "nil"
end

local function call_expression(path, ...)
  local args = {}
  for index = 1, select("#", ...) do args[index] = lua_literal(select(index, ...)) end
  return path .. "(" .. table.concat(args, ", ") .. ")"
end

local function dispatcher(kind, arg, expr)
  return { __omarchy_dispatcher = true, kind = kind or "", arg = arg or "", expr = expr or "" }
end

local function dsp_proxy(path)
  return setmetatable({ path = path }, {
    __index = function(self, key) return dsp_proxy(self.path .. "." .. tostring(key)) end,
    __call = function(self, ...)
      local first = ...
      local expr = call_expression(self.path, ...)
      if self.path == "hl.dsp.exec_cmd" and type(first) == "string" then
        return dispatcher("exec", first, expr)
      end
      return dispatcher("lua", expr, expr)
    end,
  })
end

local noop
noop = setmetatable({}, { __index = function() return noop end, __call = function() return noop end })
local hl = setmetatable({
  dsp = dsp_proxy("hl.dsp"),
  bind = function(keys, bind_dispatcher, opts)
    opts = type(opts) == "table" and opts or {}
    local modmask, key = split_keys(keys)
    if key == "" then return noop end
    local kind, arg = "", ""
    if type(bind_dispatcher) == "table" and bind_dispatcher.__omarchy_dispatcher then
      kind, arg = bind_dispatcher.kind or "", bind_dispatcher.arg or bind_dispatcher.expr or ""
    elseif type(bind_dispatcher) == "string" and bind_dispatcher ~= "" then
      kind, arg = "exec", bind_dispatcher
    end
    if kind ~= "" then
      results[#results + 1] = table.concat({
        tostring(modmask), clean(opts.description), clean(key), kind, clean(arg)
      }, "\t")
    end
    return noop
  end,
}, { __index = function() return noop end })

local env = {
  hl = hl, ipairs = ipairs, pairs = pairs, type = type, tostring = tostring, tonumber = tonumber,
  select = select, next = next, pcall = pcall, error = error, assert = assert,
  string = string, table = table, math = math, _VERSION = _VERSION,
}
env._G = env
local chunk, load_error = load(user_source, "hyprland.lua", "t", env)
if not chunk then
  OMABUNTU_SCAN_OUTPUT, OMABUNTU_SCAN_ERROR = "", tostring(load_error)
else
  debug.sethook(function() error("scan limit") end, "", 200000)
  local ok, run_error = pcall(chunk)
  debug.sethook()
  OMABUNTU_SCAN_OUTPUT = table.concat(results, "\n")
  OMABUNTU_SCAN_ERROR = ok and "" or tostring(run_error)
end
'''


def _quote_lua(value):
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", "\\r").replace("\n", "\\n")
    return '"' + escaped.replace("\0", "\\0") + '"'


def scan_lua_source(source):
    if not source or len(source) > MAX_SOURCE:
        return []
    library = _lua_library()
    state = library.luaL_newstate()
    if not state:
        raise CommandError("lua")
    try:
        library.luaL_openlibs(state)
        script = SCAN_LUA.replace("__USER_SOURCE__", _quote_lua(source), 1).encode()
        if library.luaL_loadstring(state, script) != 0 or library.lua_pcallk(state, 0, 0, 0, 0, None) != 0:
            return []
        library.lua_getglobal(state, b"OMABUNTU_SCAN_OUTPUT")
        output = _lua_string(library, state)
    finally:
        library.lua_close(state)
    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 5 or not parts[0].isdigit() or not parts[2]:
            continue
        if parts[3] not in ("exec", "lua", "sendshortcut"):
            continue
        rows.append({"modmask": parts[0], "description": parts[1], "key": parts[2],
                     "kind": parts[3], "arg": "\t".join(parts[4:])})
    return rows


def load_source(path=None):
    selected = path
    if selected is None:
        override = os.environ.get("OMABUNTU_KEYBINDINGS_CONFIG", "")
        selected = Path(override) if override else Path.home() / ".config/hypr/hyprland.lua"
    selected = Path(selected)
    if not selected.is_file() or selected.is_symlink():
        return ""
    data = selected.read_bytes()
    if len(data) > MAX_SOURCE:
        return ""
    return data.decode("utf-8", "replace")


def _accepted(result):
    code, output = result
    return code == 0 and str(output).strip() in ("", "ok")


def _send_key_state(mods, key, window, state):
    return (
        "hl.dsp.send_key_state({ mods = " + json.dumps(mods, ensure_ascii=False)
        + ", key = " + json.dumps(key, ensure_ascii=False)
        + ', state = "' + state + '", window = ' + json.dumps(window, ensure_ascii=False)
        + " })"
    )


def issue(dispatcher, arg, run):
    if dispatcher in ("exec", "lua", "sendshortcut") and not str(arg).strip():
        return {"ok": False, "error": "failed"}
    if dispatcher == "exec":
        expression = "hl.dsp.exec_cmd(" + json.dumps(arg, ensure_ascii=False) + ")"
        if _accepted(run(["hyprctl", "dispatch", expression])):
            return {"ok": True}
        if _accepted(run(["hyprctl", "dispatch", "exec", arg])):
            return {"ok": True}
        return {"ok": False, "error": "failed"}
    if dispatcher == "lua":
        if not str(arg).startswith("hl."):
            return {"ok": False, "error": "refused"}
        return {"ok": True} if _accepted(run(["hyprctl", "dispatch", arg])) else {"ok": False, "error": "failed"}
    if dispatcher == "sendshortcut":
        parts = [part.strip() for part in str(arg).split(",")]
        mods = parts[0] if parts else ""
        key = parts[1] if len(parts) > 1 else ""
        window = parts[2] if len(parts) > 2 and parts[2] else "activewindow"
        if key and _accepted(run(["hyprctl", "dispatch", _send_key_state(mods, key, window, "down")])):
            time.sleep(0.05)
            _accepted(run(["hyprctl", "dispatch", _send_key_state(mods, key, window, "up")]))
            return {"ok": True}
        if _accepted(run(["hyprctl", "dispatch", "sendshortcut", arg])):
            return {"ok": True}
        return {"ok": False, "error": "failed"}
    if not DISPATCHER_NAME.fullmatch(dispatcher):
        return {"ok": False, "error": "refused"}
    command = ["hyprctl", "dispatch", dispatcher] + ([arg] if arg else [])
    return {"ok": True} if _accepted(run(command)) else {"ok": False, "error": "failed"}


def rows_from(binds_text, source="", symbols=None):
    return format_binds(binds_text, scan_lua_source(source) if source else [], symbols)


def perform(command, run, source="", symbols=None):
    code, binds_text = run(["hyprctl", "binds"])
    if code != 0:
        return {"ok": False, "error": "binds"}
    rows = rows_from(binds_text, source, symbols)
    if command == ["list"]:
        return {"ok": True, "rows": rows}
    if len(command) != 3 or command[0] != "dispatch":
        return {"ok": False, "error": "usage"}
    dispatcher, arg = command[1], command[2]
    if "\n" in dispatcher or "\n" in arg or "\0" in dispatcher or "\0" in arg or len(arg) > 2000:
        return {"ok": False, "error": "refused"}
    if not any(row["dispatcher"] == dispatcher and row["arg"] == arg and row["dispatcher"] for row in rows):
        return {"ok": False, "error": "unknown"}
    if session_action(dispatcher) or session_action(arg):
        return {"ok": False, "error": "refused"}
    return issue(dispatcher, arg, run)


def live_run(argv, timeout=8):
    if (not isinstance(argv, list) or len(argv) not in (2, 3, 4) or argv[0] != "hyprctl"
            or argv[1] not in ("binds", "dispatch") or any(not isinstance(part, str) or "\n" in part or "\0" in part
                                for part in argv)):
        raise CommandError("command")
    if argv[1] == "binds" and len(argv) != 2:
        raise CommandError("command")
    if argv[1] == "dispatch" and (len(argv) == 2 or not (DISPATCHER_NAME.fullmatch(argv[2]) or argv[2].startswith("hl."))):
        raise CommandError("command")
    kept = ("HOME", "USER", "XDG_RUNTIME_DIR", "HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY")
    env = {key: os.environ[key] for key in kept if key in os.environ}
    env["PATH"] = "/usr/bin:/bin"
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired:
        raise CommandError("timeout") from None
    return completed.returncode, completed.stdout


def parse_keymap(text):
    """Map XKB keycode numbers to the first symbol in a compiled keymap."""
    codes = {name: number for name, number in re.findall(r"<([A-Za-z0-9]+)> = (\d+);", text)}
    symbols = {}
    for name, symbol in re.findall(r"key <([A-Za-z0-9]+)> \{\s*\[\s*([^,\]]+)", text):
        number = codes.get(name)
        symbol = symbol.strip()
        if number and symbol and symbol not in ("NoSymbol", "VoidSymbol"):
            symbols[number] = symbol
    return symbols


def live_symbols():
    """Read the current layout when xkbcli is installed. Missing tool, no symbols."""
    if shutil.which("xkbcli") is None:
        return None
    try:
        completed = subprocess.run(
            ["xkbcli", "compile-keymap"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or not completed.stdout:
        return None
    return parse_keymap(completed.stdout) or None


def main(argv):
    command = list(argv[1:])
    if command == ["list"] or (len(command) == 3 and command[0] == "dispatch"):
        try:
            symbols = live_symbols() if command == ["list"] else None
            result = perform(command, live_run, load_source(), symbols)
        except CommandError as error:
            result = {"ok": False, "error": error.token}
    else:
        result = {"ok": False, "error": "usage"}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
