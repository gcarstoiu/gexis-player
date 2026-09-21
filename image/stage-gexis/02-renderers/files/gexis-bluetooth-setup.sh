#!/bin/sh -e
# rfkill soft-blocks hci0 by default on this image and nothing in
# Raspberry Pi OS Lite's unattended boot ever clears it - that's
# normally done by raspi-config's interactive country-code step, which
# firstrun.sh's headless flow never runs. Found on hardware, 2026-09-06:
# bluetoothd starts fine regardless (it just can't power the adapter),
# traced to rfkill via hciconfig's explicit "RF-kill" error and
# /sys/class/rfkill/*/soft, not assumed from the "Failed to set mode:
# Failed (0x03)" bluetoothd log line alone.
rfkill unblock bluetooth

# main.conf's AutoEnable (default true) may already have powered the
# adapter by the time this runs now that it's unblocked - don't assume
# either way, ask and retry briefly rather than race it.
i=0
while [ "${i}" -lt 10 ]; do
	if bluetoothctl show | grep -q "Powered: yes"; then
		break
	fi
	bluetoothctl power on >/dev/null 2>&1 || true
	i=$((i + 1))
	sleep 1
done

# ADR-0024: pair without a PIN, at this installation - persistently
# discoverable/pairable is part of that same decision (there is no UI
# yet to trigger "enter pairing mode" on demand). gexis-core's own Agent1 (ADR-0045)
# is ordered before this unit so the agent answering pairing requests is
# already registered before discoverable mode turns on.
# **Discoverability is the daemon's, not this script's** (ADR-0045).
#
# This script ran `bluetoothctl pairable on; bluetoothctl discoverable on`
# here, and the second has never worked: `discoverable on` is not a state,
# it is a state with a timer attached, and `DiscoverableTimeout` has to be
# set *first*. BlueZ's 180 s default reverted it every time, so the device
# settled at `Discoverable: no` while the settings row claimed "3 min after
# boot" - which nothing had chosen either. Measured on the device
# 2026-09-21, hours after a boot: `Discoverable: no`,
# `DiscoverableTimeout: 0x000000b4 (180)`.
#
# `gexis_core.bluetooth_adapter_state` sets the timeout and the switch
# together, from the stored setting, and applies a change without a reboot.
# Leaving a second writer here would mean two things racing for one property
# at boot, with the loser silent - which is how this defect hid for so long.
#
# Powering the adapter above stays here: the daemon needs one on the bus
# before it can set anything on it.
