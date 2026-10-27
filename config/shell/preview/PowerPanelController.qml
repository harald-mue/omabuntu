import QtQuick
import Quickshell.Services.UPower
import qs.Commons
import "Port/PowerModel.js" as Model

// UPower and the native Ubuntu power-profiles-daemon interface only.
// No session control, shell execution, timers or global configuration writes.
DesktopPanelController {
  id: root
  readonly property var battery: UPower.displayDevice
  property bool showPercentage: false
  property int profileIndex: 0
  property var previousProfiles: []
  readonly property var profiles: PowerProfiles.hasPerformanceProfile
    ? ["power-saver", "balanced", "performance"] : ["power-saver", "balanced"]
  readonly property string activeProfile: PowerProfiles.profile === PowerProfile.PowerSaver ? "power-saver"
    : PowerProfiles.profile === PowerProfile.Performance ? "performance" : "balanced"
  readonly property bool batteryPresent: !!battery && battery.isPresent
  readonly property bool discharging: batteryPresent && UPower.onBattery
  readonly property bool chargeThresholdActive: Model.chargeThresholdActive(battery, discharging, states())
  readonly property real batteryFraction: Model.batteryFraction(battery)
  readonly property bool fullyCharged: batteryPresent && battery.state === UPowerDeviceState.FullyCharged && !chargeThresholdActive
  readonly property bool batteryFull: fullyCharged || (!discharging && batteryFraction >= 1)
  readonly property bool batteryFlowIdle: batteryFull || chargeThresholdActive
  readonly property bool charging: batteryPresent && !discharging && !batteryFlowIdle
  readonly property color batteryFillColor: bar.foreground
  readonly property string heroStatusText: Model.modeLabel(battery, discharging, states(), I18n.t)
  readonly property var batteryInfo: batteryPresent ? ({
    percentage: Math.round(batteryFraction * 100) + "%",
    size: battery.energyCapacity.toFixed(1) + "Wh",
    rate: battery.changeRate.toFixed(1) + "W",
    time: timeLabel(discharging ? battery.timeToEmpty : battery.timeToFull)
  }) : ({})
  function states() { return { Charging: UPowerDeviceState.Charging, Discharging: UPowerDeviceState.Discharging,
    FullyCharged: UPowerDeviceState.FullyCharged, PendingCharge: UPowerDeviceState.PendingCharge }; }
  function timeLabel(seconds) {
    if (!(seconds > 0)) return "—";
    var minutes = Math.round(seconds / 60);
    return Math.floor(minutes / 60) + "h " + (minutes % 60) + "m";
  }
  function batteryIcon() { return Model.batteryIcon(battery, discharging, states()); }
  function profileIcon(name) { return Model.profileIcon(name); }
  function reading(value) { return value === undefined ? "" : String(value); }
  function togglePercentage() { showPercentage = !showPercentage; }
  function selectProfileByDelta(delta) { profileIndex = Model.selectProfileIndex(profileIndex, delta, profiles); }
  function activateSelectedProfile() { setProfile(profiles[profileIndex]); }
  function setProfile(profile) {
    if (profiles.indexOf(profile) < 0) return;
    previousProfiles = previousProfiles.concat([activeProfile]);
    PowerProfiles.profile = profile === "power-saver" ? PowerProfile.PowerSaver
      : profile === "performance" ? PowerProfile.Performance : PowerProfile.Balanced;
  }
}
