"""Backend-only adaptation of original Omarchy weather, MIT, pin 03ff1eff.

Keep original location editing, city suggestions, state reload, IP discovery,
hero, forecast, refresh and retry behavior. No shell IPC or notification service.
"""
import elsewhen_frontend


def cut(text, start, end, replacement=''):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('Weather extraction boundaries differ: ' + start)
    a, b = text.index(start), text.index(end)
    if a >= b:
        raise ValueError('Weather extraction order differs')
    return text[:a] + replacement + text[b:]


def once(text, old, new=''):
    if text.count(old) != 1:
        raise ValueError('Weather extraction witness differs: ' + old)
    return text.replace(old, new)


def derive_panel(data):
    text = data.decode()
    text = once(text, '    path: Quickshell.env("HOME") + "/.local/state/omarchy/settings/weather.json"',
                '    path: (Quickshell.env("OMABUNTU_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state/omabuntu")) + "/settings/weather.json"')
    text = once(text, '  function refresh() {',
                '  function probeCommand(mode, args) {\n'
                '    return ["/usr/bin/python3", Quickshell.env("OMABUNTU_WEATHER_HELPER"), mode].concat(args || [])\n'
                '  }\n\n'
                '  function refresh() {')
    text = cut(text, '    var url = "https://api.open-meteo.com/v1/forecast"',
               '    dailyForecastProc.running = true',
               '    dailyForecastProc.command = root.probeCommand("forecast", [String(lat), String(lon)])\n')
    text = once(text, '["omarchy-weather-location", "--set", name, latitude + "," + longitude]',
                'root.probeCommand("set", [name, latitude + "," + longitude])')
    text = once(text, '["omarchy-weather-location", "--set", name]', 'root.probeCommand("set", [name])')
    text = once(text, '["omarchy-weather-location", "--clear"]', 'root.probeCommand("clear", [])')
    text = cut(text, '    geocodeProc.command = ["curl",', '    geocodeProc.running = true',
               '    geocodeProc.command = root.probeCommand("search", [geocodeActiveQuery])\n')
    text = once(text, '    command: ["curl", "-fsS", "--max-time", "10", "https://wttr.in/" + root.locationQuery + "?format=j1"]',
                '    command: root.probeCommand("report", [root.locationQuery])')
    text = once(text, '    command: ["curl", "-fsS", "--max-time", "4", "https://wttr.in/?format=%l"]',
                '    command: root.probeCommand("locate", [])')
    text = elsewhen_frontend._strip_shell_ipc(text)
    for forbidden in ('["curl"', 'https://', 'ShellIpc', '["omarchy-'):
        if forbidden in text:
            raise ValueError('Weather unreviewed backend remains: ' + forbidden)
    return ('// Derived from Omarchy weather/Panel.qml (MIT), pinned 03ff1eff.\n' + text).encode()


def derive_widget(data):
    text = data.decode()
    text = once(text, 'source: Qt.resolvedUrl("Panel.qml")', 'source: Qt.resolvedUrl("WeatherPanel.qml")')
    text = once(text, '    tooltipText: ""',
                '    tooltipText: "Weather: wttr.in and Open-Meteo.com (CC BY 4.0)"')
    old = '      if (b === Qt.RightButton) root.bar.run('
    if text.count(old) != 1:
        raise ValueError('Weather notification witness differs')
    text = '\n'.join(line for line in text.splitlines() if old not in line) + '\n'
    text = once(text, '      else if (b === Qt.MiddleButton)', '      if (b === Qt.MiddleButton)')
    return ('// Derived from Omarchy weather/BarWidget.qml (MIT), pinned 03ff1eff.\n' + text).encode()
