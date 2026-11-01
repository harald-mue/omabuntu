# Omabuntu developer entry points.
#
# This is a thin wrapper around the reviewed Python tools. The release target
# explicitly commits and publishes after confirmations. Explicit live targets reload
# Hyprland configuration, never the compositor process or login session. Targets
# that change the host keep the tools' own refusals and print what they do.
#
# Every target that needs a release name takes VERSION=<name>, for example:
#   make release VERSION=0.1.1
#   make package VERSION=my-change BUILD_DIR=work/builds/<build-id>

PYTHON ?= python3
VERSION ?=
# Legacy stage packaging requires an explicit machine-specific BUILD_DIR.
BUILD_DIR ?=
RELEASES ?= $(CURDIR)/work/user-releases
BUNDLE ?= $(RELEASES)/$(VERSION)
OMABUNTU ?= $(HOME)/.local/bin/omabuntu
# Evaluated once per invocation; existing versions are never overwritten.
DEV_VERSION := $(if $(VERSION),$(VERSION),dev-$(shell date -u +%Y%m%dT%H%M%S.%NZ))

.DEFAULT_GOAL := help

.PHONY: help test doctor guide release release-resume build packages runtime-packages plugin-packages \
        plugins plugins-prepare plugins-migrate plugins-migrate-apply plugins-recover plugins-recover-apply plugins-activate font acceptance rollback \
        package preflight plan install update start stop status \
        autostart autostart-plan autostart-remove hypr-settings hypr-settings-plan \
        hypr-settings-remove reload restart dev-update check-version check-build

help:
	@echo 'Omabuntu targets:'
	@echo ''
	@echo 'Installer:'
	@echo '  make guide                             show the next step; may offer to install'
	@echo '  make build                             build a local development bundle'
	@echo '  make release VERSION=0.1.1             reviewed commit, build, tag and GitHub publication'
	@echo '  make release-resume VERSION=0.1.1      verify existing archive, resume signing/publication only'
	@echo '  make packages                          review source-build packages; no install'
	@echo '  make runtime-packages                  review published-runtime dependencies only'
	@echo '  make plugin-packages                   review hyprpm build dependencies only'
	@echo '  make plugins                           read-only hyprpm plan'
	@echo '  make plugins-prepare                   approved pinned manager build; refuses enabled plugins'
	@echo '  make plugins-migrate                   read-only known legacy manager migration plan'
	@echo '  make plugins-migrate-apply             backed-up migration; explicit repository replacement; no load'
	@echo '  make plugins-recover JOURNAL=...       review the exact interrupted PPA-header checkpoint'
	@echo '  make plugins-recover-apply JOURNAL=... backed-up pinned build continuation; no load'
	@echo '  make plugins-activate                  explicit live hyprbars enable/load; may request sudo'
	@echo '  make plugins-repair                    review the enabled-but-unloaded hyprbars repair; no load'
	@echo '  make plugins-repair-apply              one explicit live reload of the verified hyprbars'
	@echo '  make font                              review the desktop font; no install'
	@echo '  make acceptance                        read-only stock-install gates'
	@echo '  make rollback                          review the previous application release'
	@echo ''
	@echo 'Development:'
	@echo '  make test                              unit suite'
	@echo '  make doctor                            private read-only report'
	@echo '  make package VERSION=<name> BUILD_DIR=<stage>  package an existing build stage'
	@echo '  make preflight VERSION=<name>          read-only bundle check'
	@echo '  make plan VERSION=<name>               read-only deployment plan'
	@echo '  make install VERSION=<name>            install a prepared release'
	@echo '  make update                            download and install the latest signed GitHub Release'
	@echo '  make start                             start the installed shell'
	@echo '  make stop                              stop the owned shell'
	@echo '  make status                            show the recorded shell state'
	@echo '  make autostart                         install and enable login unit'
	@echo '  make autostart-remove                  remove the login unit'
	@echo '  make hypr-settings                     plan + apply managed Hyprland settings'
	@echo '  make hypr-settings-remove              roll the managed settings back'
	@echo '  make hypr-settings-plan                read-only settings diff'
	@echo '  make autostart-plan                    read-only unit/helper plan'
	@echo '  make reload                            live config reload + error check'
	@echo '  make restart                           restart only the owned shell'
	@echo '  make dev-update BUILD_DIR=<stage> [VERSION=<fresh>]  fresh release + managed files + live reload'
	@echo ''
	@echo 'Release publication and installation require interactive approval.'
	@echo 'make build never commits, publishes or changes the running desktop.'

test:
	$(PYTHON) -m unittest discover -s tests -v

doctor:
	$(PYTHON) tools/omabuntu.py doctor

check-version:
	@case "$(VERSION)" in \
	  ''|*[!A-Za-z0-9._-]*) \
	    echo 'VERSION is required, for example: make package VERSION=my-change BUILD_DIR=work/builds/<build-id>' >&2; \
	    exit 2;; \
	esac

check-build:
	@test -n '$(BUILD_DIR)' || { echo 'BUILD_DIR is required: choose an explicit verified work/builds/<build-id> stage' >&2; exit 2; }

guide:
	./install.sh --plain

release: check-version
	$(PYTHON) tools/publish_release.py --version '$(VERSION)'

release-resume: check-version
	$(PYTHON) tools/publish_release.py --version '$(VERSION)' --resume-signing

build:
	./install.sh --build-release --apply

packages:
	./install.sh --packages --plain

runtime-packages:
	./install.sh --packages --runtime-only --plain

plugin-packages:
	./install.sh --packages --plugin-build-only --plain

plugins:
	./install.sh --plugins --plain

plugins-prepare:
	./install.sh --plugins --apply --plain

plugins-migrate:
	./install.sh --plugins-migrate --plain

plugins-migrate-apply:
	./install.sh --plugins-migrate --apply --plain

plugins-recover:
	@test -n "$(JOURNAL)" || (echo 'Specify JOURNAL=/absolute/path/to/transaction.json'; exit 1)
	./install.sh --plugins-recover "$(JOURNAL)" --plain

plugins-recover-apply:
	@test -n "$(JOURNAL)" || (echo 'Specify JOURNAL=/absolute/path/to/transaction.json'; exit 1)
	./install.sh --plugins-recover "$(JOURNAL)" --apply --plain

plugins-activate:
	./install.sh --plugins-activate --apply --plain

plugins-repair:
	./install.sh --plugins-repair --plain

plugins-repair-apply:
	./install.sh --plugins-repair --apply --plain

font:
	./install.sh --font --plain

acceptance:
	./install.sh --acceptance --plain

rollback:
	./install.sh --rollback --plain

package: check-version check-build
	$(PYTHON) tools/package_user.py --version '$(VERSION)' --build-dir '$(BUILD_DIR)'

preflight: check-version
	$(PYTHON) tools/install.py preflight '$(BUNDLE)'

plan: check-version
	$(PYTHON) tools/user_install.py plan '$(BUNDLE)'

install: check-version
	@echo 'Installing $(VERSION); the shell is not started.'
	$(OMABUNTU) install '$(BUNDLE)' --apply

# Published releases do not follow the development checkout or local mtimes.
update:
	./install.sh --download-release

start:
	$(OMABUNTU) start

stop:
	$(OMABUNTU) stop

status:
	$(OMABUNTU) status

autostart-plan:
	$(PYTHON) tools/deploy_autostart.py plan

autostart:
	$(PYTHON) tools/deploy_autostart.py plan
	$(PYTHON) tools/deploy_autostart.py apply --replace

autostart-remove:
	$(PYTHON) tools/deploy_autostart.py remove

# Installer-managed Hyprland settings (splash, logo, donation nag). Apply keeps
# a backup of the user's hyprland.lua and only adds one require line; it never
# reloads Hyprland or touches systemd.
hypr-settings-plan:
	$(PYTHON) tools/deploy_hypr_settings.py plan

hypr-settings:
	$(PYTHON) tools/deploy_hypr_settings.py plan
	$(PYTHON) tools/deploy_hypr_settings.py apply

hypr-settings-remove:
	$(PYTHON) tools/deploy_hypr_settings.py remove

reload:
	$(PYTHON) tools/reload_hyprland.py

restart:
	$(OMABUNTU) stop
	$(OMABUNTU) start

# Sequential recipe (also under make -j). Never reuses a stale source bundle.
# Uses the checkout manager so deployment fixes do not depend on the old release.
# Failure stops here; recovery/rollback is explicit, not an automatic session reset.
dev-update: check-build
	$(MAKE) --no-print-directory package VERSION='$(DEV_VERSION)'
	$(MAKE) --no-print-directory preflight VERSION='$(DEV_VERSION)'
	$(MAKE) --no-print-directory hypr-settings-plan
	$(MAKE) --no-print-directory autostart-plan
	$(OMABUNTU) stop
	$(PYTHON) tools/user_install.py install '$(RELEASES)/$(DEV_VERSION)' --apply
	$(MAKE) --no-print-directory hypr-settings
	$(MAKE) --no-print-directory autostart
	$(MAKE) --no-print-directory reload
	$(OMABUNTU) start
