# Omabuntu developer entry points.
#
# This is a thin wrapper around the reviewed Python tools. It installs no
# packages, uses no sudo and publishes nothing. Explicit live targets reload
# Hyprland configuration, never the compositor process or login session. Targets
# that change the host keep the tools' own refusals and print what they do.
#
# Every target that needs a release name takes VERSION=<name>, for example:
#   make update VERSION=my-change BUILD_DIR=work/builds/<build-id>

PYTHON ?= python3
VERSION ?=
# No implicit machine-specific stage: release operations require BUILD_DIR.
BUILD_DIR ?=
RELEASES ?= $(CURDIR)/work/user-releases
BUNDLE ?= $(RELEASES)/$(VERSION)
OMABUNTU ?= $(HOME)/.local/bin/omabuntu
# Evaluated once per invocation; existing versions are never overwritten.
DEV_VERSION := $(if $(VERSION),$(VERSION),dev-$(shell date -u +%Y%m%dT%H%M%S.%NZ))

.DEFAULT_GOAL := help

.PHONY: help test doctor release preflight plan install update start stop status \
        autostart autostart-plan autostart-remove hypr-settings hypr-settings-plan \
        hypr-settings-remove reload restart dev-update check-version check-build

help:
	@echo 'Omabuntu targets:'
	@echo '  make test                              unit suite'
	@echo '  make doctor                            private read-only report'
	@echo '  make release VERSION=<name> BUILD_DIR=<stage>  prepare a local release'
	@echo '  make preflight VERSION=<name>          read-only bundle check'
	@echo '  make plan VERSION=<name>               read-only deployment plan'
	@echo '  make install VERSION=<name>            install a prepared release'
	@echo '  make update VERSION=<name> BUILD_DIR=<stage>  prepare, stop, install, start'
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
	@echo 'Nothing here installs packages, starts the shell implicitly,'
	@echo 'publishes a release or changes Git history.'

test:
	$(PYTHON) -m unittest discover -s tests -v

doctor:
	$(PYTHON) tools/omabuntu.py doctor

check-version:
	@case "$(VERSION)" in \
	  ''|*[!A-Za-z0-9._-]*) \
	    echo 'VERSION is required, for example: make release VERSION=my-change BUILD_DIR=work/builds/<build-id>' >&2; \
	    exit 2;; \
	esac

check-build:
	@test -n '$(BUILD_DIR)' || { echo 'BUILD_DIR is required: choose an explicit verified work/builds/<build-id> stage' >&2; exit 2; }

release: check-version check-build
	$(PYTHON) tools/package_user.py --version '$(VERSION)' --build-dir '$(BUILD_DIR)'

preflight: check-version
	$(PYTHON) tools/install.py preflight '$(BUNDLE)'

plan: check-version
	$(PYTHON) tools/user_install.py plan '$(BUNDLE)'

install: check-version
	@echo 'Installing $(VERSION); the shell is not started.'
	$(OMABUNTU) install '$(BUNDLE)' --apply

# The requested one-command local source update. Only this target starts the
# desktop process, and only after a successful release switch.
update: check-version
	@test -d '$(BUNDLE)' || $(MAKE) --no-print-directory release VERSION='$(VERSION)'
	@echo 'Stopping the owned shell before the release switch.'
	$(OMABUNTU) stop
	@echo 'Installing $(VERSION).'
	$(OMABUNTU) install '$(BUNDLE)' --apply
	@echo 'Starting $(VERSION).'
	$(OMABUNTU) start

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
	$(MAKE) --no-print-directory release VERSION='$(DEV_VERSION)'
	$(MAKE) --no-print-directory preflight VERSION='$(DEV_VERSION)'
	$(MAKE) --no-print-directory hypr-settings-plan
	$(MAKE) --no-print-directory autostart-plan
	$(OMABUNTU) stop
	$(PYTHON) tools/user_install.py install '$(RELEASES)/$(DEV_VERSION)' --apply
	$(MAKE) --no-print-directory hypr-settings
	$(MAKE) --no-print-directory autostart
	$(MAKE) --no-print-directory reload
	$(OMABUNTU) start
