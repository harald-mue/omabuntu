# Elsewhen world clock beside the clock

## Goal and evidence

Mount Omarchy's Elsewhen world clock on the right of the top-bar clock. Pinned source is `03ff1eff` (`v4.5.0-rc1`). The default centerEnd order there is Elsewhen, then weather, then the system-update hint. This step takes only Elsewhen.

The panel author is Jason Fried, MIT, recorded in `vendor/omarchy/shell/plugins/panels/elsewhen/manifest.json`. The root Omarchy MIT notice still applies. Branded agent SVGs and the separate notification service stay out.

## Gap

Omabuntu's center slot is only the clock. Elsewhen is vendored but not staged. Its panel writes shell.json, fetches Open-Meteo and GitHub profiles with curl, and can run sudo timedatectl set-timezone. The preview command allowlist does not admit those calls. Style.bar.statusSlot, Style.spacing.lg, and Style.spacing.panelGap are missing, and the English catalog has no Elsewhen strings.

## Safety and exclusions

- Cities stay in the running process. No updateEntryInline and no shell.json write.
- No Open-Meteo geocode or forecast, no GitHub profile or avatar fetch, no omarchy-notification-send.
- No system timezone change. Choosing another city updates the panel only.
- Zone offsets and the zone catalogue go through tools/elsewhen_probe.py: date with TZ set in the environment, timedatectl show -p Timezone, and timedatectl list-timezones. The helper rejects anything that is not a timezone id. It has no set-timezone, sudo, or network.
- Weather, indicators, and the system-update hint stay out.
- No bar restart and no commit until asked. The running Quickshell process is left as it is.

## Shape

Stage the original Elsewhen directory under Elsewhen/. Derive the panel, model, and both globes so the data directory is OMABUNTU_ELSEWHEN_DIR and the probe is the helper above. Register Panel and PanelController. Mount the button in TrialPanel centerEndContent.

## Tasks

- [x] Record the Jason Fried notice and the reviewed derivation.
- [x] Stage Elsewhen without network, notification, or timezone-setting calls.
- [x] Mount it to the right of the clock and cover it with tests.
- [x] Run the unit suite. Do not restart the bar or commit.
