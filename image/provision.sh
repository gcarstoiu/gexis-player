#!/bin/bash
set -euo pipefail

usage() {
	echo "Usage: $0 <device>" >&2
	echo "  <device> is the whole flashed card, e.g. /dev/sdb - NOT a" >&2
	echo "  partition (/dev/sdb1), and never guessed: pass it explicitly." >&2
	exit 1
}

DEVICE="${1:-}"
[ -n "${DEVICE}" ] || usage

if [ ! -b "${DEVICE}" ]; then
	echo "ERROR: ${DEVICE} is not a block device" >&2
	exit 1
fi

# Refuse anything that looks like it could be the machine's own disk.
# Not foolproof, but writing to the wrong device is destructive and this
# is a free check.
ROOT_SOURCE="$(findmnt -n -o SOURCE / 2>/dev/null || true)"
if [ -n "${ROOT_SOURCE}" ] && [[ "${ROOT_SOURCE}" == "${DEVICE}"* ]]; then
	echo "ERROR: ${DEVICE} appears to hold this machine's own root filesystem" \
		"(${ROOT_SOURCE}). Refusing." >&2
	exit 1
fi

# Partition naming differs: /dev/sdb -> /dev/sdb1, but
# /dev/mmcblk0 -> /dev/mmcblk0p1 (common for SD card readers).
case "${DEVICE}" in
	*mmcblk*|*nvme*|*loop*)
		BOOT_PART="${DEVICE}p1"
		;;
	*)
		BOOT_PART="${DEVICE}1"
		;;
esac

if [ ! -b "${BOOT_PART}" ]; then
	echo "ERROR: expected boot partition ${BOOT_PART} not found" >&2
	exit 1
fi

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/provision.local.env"
if [ ! -f "${ENV_FILE}" ]; then
	echo "ERROR: ${ENV_FILE} not found." >&2
	echo "       cp image/provision.env.example image/provision.local.env" \
		"and fill it in." >&2
	exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# "Missing" (key absent from the file entirely) is checked separately from
# "empty" (present, blank) - WIFI_SSID etc. are legitimately blank by
# design (Ethernet-only, keep the default hostname). A typo'd or deleted
# key is a different failure and should say so.
for key in SSH_PUBKEY WIFI_SSID WIFI_PASS WIFI_COUNTRY HOSTNAME; do
	if [ -z "${!key+x}" ]; then
		echo "ERROR: ${key} is not defined in ${ENV_FILE}" >&2
		exit 1
	fi
done

# SSH_PUBKEY is the one value that must not be empty: this is the exact
# failure Phase 0 hit - a card with no working remote access, discovered
# only by flashing it.
if [ -z "${SSH_PUBKEY}" ]; then
	echo "ERROR: SSH_PUBKEY is empty in ${ENV_FILE}." >&2
	echo "       A card provisioned with this blank boots unreachable." >&2
	exit 1
fi

MOUNT_POINT="$(mktemp -d)"
cleanup() {
	umount "${MOUNT_POINT}" 2>/dev/null || true
	rmdir "${MOUNT_POINT}" 2>/dev/null || true
}
trap cleanup EXIT

# Mounted with our own uid/gid so the rest of this script needs no further
# sudo - only the mount and unmount of the actual device do.
sudo mount -o "uid=$(id -u),gid=$(id -g)" "${BOOT_PART}" "${MOUNT_POINT}"

FIRSTRUN="${MOUNT_POINT}/firstrun.sh"
if [ ! -f "${FIRSTRUN}" ]; then
	echo "ERROR: ${FIRSTRUN} not found - is ${DEVICE} a gexis-player card?" >&2
	exit 1
fi

# Single-quoted in the output, not double-quoted: firstrun.sh is a shell
# script that EXECUTES later, and a double-quoted assignment expands
# $(...) and backticks at that point - a password containing either would
# run as shell code on first boot, not just get treated as a string. This
# is the same escaping imager_custom's own set_wlan already uses elsewhere
# in this codebase (sed "s/'/'\\\\''/g"), not a new convention.
#
# Rewritten line-by-line rather than with sed's s/// on the whole line:
# WIFI_PASS and SSH_PUBKEY are arbitrary content that could contain sed's
# delimiter or characters sed's replacement syntax treats specially.
# printf '%s' never reinterprets any of that - the whole reason this tool
# exists is to remove transcription risk, not add a new subtler one.
sq_escape() {
	printf '%s' "$1" | sed "s/'/'\\\\''/g"
}

TMP_FIRSTRUN="$(mktemp)"
while IFS= read -r line || [ -n "${line}" ]; do
	case "${line}" in
		SSH_PUBKEY=*)    printf "SSH_PUBKEY='%s'\n" "$(sq_escape "${SSH_PUBKEY}")" ;;
		WIFI_SSID=*)     printf "WIFI_SSID='%s'\n" "$(sq_escape "${WIFI_SSID}")" ;;
		WIFI_PASS=*)     printf "WIFI_PASS='%s'\n" "$(sq_escape "${WIFI_PASS}")" ;;
		WIFI_COUNTRY=*)  printf "WIFI_COUNTRY='%s'\n" "$(sq_escape "${WIFI_COUNTRY}")" ;;
		HOSTNAME=*)      printf "HOSTNAME='%s'\n" "$(sq_escape "${HOSTNAME}")" ;;
		*)               printf '%s\n' "${line}" ;;
	esac
done < "${FIRSTRUN}" > "${TMP_FIRSTRUN}"
mv "${TMP_FIRSTRUN}" "${FIRSTRUN}"

# Verify the substitution actually took - do not assume it worked just
# because nothing errored. Checked by having the shell that will run
# firstrun.sh parse the written line back out, not by re-deriving the
# escaped form and string-comparing it - that would only prove the escaper
# is consistent with itself, not that the file actually holds the right
# value.
FAILED=0
for key in SSH_PUBKEY WIFI_SSID WIFI_PASS WIFI_COUNTRY HOSTNAME; do
	expected_value="${!key}"
	written_line="$(grep "^${key}='" "${FIRSTRUN}" || true)"
	if [ -z "${written_line}" ]; then
		echo "ERROR: ${key} substitution did not take (no such line)" >&2
		FAILED=1
		continue
	fi
	actual_value="$(unset "${key}"; eval "${written_line}"; eval "printf '%s' \"\${${key}}\"")"
	if [ "${actual_value}" != "${expected_value}" ]; then
		echo "ERROR: ${key} substitution did not verify (round-trip mismatch)" >&2
		FAILED=1
	fi
done

if [ "${FAILED}" -ne 0 ]; then
	echo "ERROR: verification failed - card not safe to boot as-is." >&2
	exit 1
fi

sync

echo "Provisioned ${FIRSTRUN} on ${BOOT_PART}."

# Every reflash generates a new SSH host key at first boot, so connecting
# to the same hostname after a reflash fails with REMOTE HOST
# IDENTIFICATION HAS CHANGED until the stale entry is cleared. Expected
# behaviour, not a fault - this is why this step exists, not a workaround
# for something broken. ssh-keygen -R matches the exact string given, so
# the bare hostname and the .local form are both cleared separately.
if [ -n "${HOSTNAME}" ]; then
	ssh-keygen -R "${HOSTNAME}" >/dev/null 2>&1 || true
	ssh-keygen -R "${HOSTNAME}.local" >/dev/null 2>&1 || true
	echo "Cleared stale SSH host key entries for ${HOSTNAME} and ${HOSTNAME}.local."
else
	echo "HOSTNAME is blank in ${ENV_FILE} - skipping ssh-keygen -R" \
		"(nothing to clear; the image's default hostname is unknown here)."
fi
