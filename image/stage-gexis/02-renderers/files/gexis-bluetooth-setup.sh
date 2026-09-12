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
# yet to trigger "enter pairing mode" on demand). gexis-bt-agent.service
# is ordered before this unit so the agent answering pairing requests is
# already registered before discoverable mode turns on.
bluetoothctl pairable on
bluetoothctl discoverable on
