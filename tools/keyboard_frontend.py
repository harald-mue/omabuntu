"""Reviewed visibility splice for the Omarchy keyboard-layout bar widget.

The vendored parent stays byte-identical; one witnessed splice only. Upstream
hides the widget on seats that run a single layout and a single input method,
but an Omabuntu seat is exactly that, and the user asked for the widget. The
splice adds an ``alwaysShow`` widget setting (default true) so the label stays
on the bar; upstream behavior is restored by passing ``alwaysShow: false``.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/omarchy/shell/plugins/bar/widgets/KeyboardLayout.qml"
MIRROR = ROOT / "config/shell/preview/KeyboardLayout.qml"


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Keyboard layout replacement witness differs")
    return text.replace(old, new)


def derive_keyboard_layout(data):
    text = data.decode()
    text = replace(
        text,
        '  visible: inputLabel !== "" && KeyboardLayoutModel.showIndicator(layoutLabel, multipleLayouts, multipleInputs)\n',
        '  // Omabuntu splice (keyboard-layout-widget-v1): single-layout seats keep\n'
        '  // the label on the bar. Upstream hides a one-layout, one-method seat; the\n'
        '  // ``alwaysShow`` setting (default true) restores upstream behavior when false.\n'
        '  visible: inputLabel !== "" && (KeyboardLayoutModel.showIndicator(layoutLabel, multipleLayouts, multipleInputs) || root.setting("alwaysShow", true))\n')
    return text.encode()


def main():
    data = derive_keyboard_layout(VENDOR.read_bytes())
    MIRROR.write_bytes(data)
    print(MIRROR)


if __name__ == "__main__":
    main()
