#!/bin/bash -e

# **Qobuz Connect: the adapter, and how the receiver will be run** (ADR-0098).
#
# **Nothing that speaks to Qobuz is in the image.** The receiver, Pibuz (MIT, by
# Filippo Vicentini), is downloaded on the device from its author's release by
# `gexis-fetch@pibuz` (ADR-0100, pin in `03-core/files/components/pibuz.env`),
# only after the user switches Qobuz Connect on and confirms the notice the
# manifest carries. What ships here is ours, from `gcarstoiu/gexis-qobuz`: the
# adapter, the receiver's unit and configuration, the manifest and the mark.
PLUGIN_VERSION="0.1.0"
PLUGIN_ASSET="gexis-qobuz-${PLUGIN_VERSION}.tar.gz"
PLUGIN_URL="https://github.com/gcarstoiu/gexis-qobuz/releases/download/v${PLUGIN_VERSION}/${PLUGIN_ASSET}"
PLUGIN_SHA256="1dd12f75733e117af1518caf28cc9d86d4f490ff6459111ff9db16b5572de4fa"

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

# shellcheck source=../fetch-cached.sh
. /pi-gen/stage-gexis/fetch-cached.sh
fetch_cached "${PLUGIN_URL}" "${PLUGIN_SHA256}" "${WORK}/${PLUGIN_ASSET}"
tar -xzf "${WORK}/${PLUGIN_ASSET}" -C "${WORK}"
SRC="${WORK}/gexis-qobuz"

# `rm -rf` first, or a warm rebuild copies into the old tree (08-plexamp found
# that the hard way). The receiver's own directory is never shipped: a rebuild
# over a rootfs that somehow holds one must not keep it.
rm -rf "${ROOTFS_DIR}/opt/gexis-qobuz"
mkdir -p "${ROOTFS_DIR}/opt/gexis-qobuz/src"
cp -a "${SRC}/src/gexis_qobuz" "${ROOTFS_DIR}/opt/gexis-qobuz/src/gexis_qobuz"
install -m 755 "${SRC}/pibuz-configure" "${ROOTFS_DIR}/opt/gexis-qobuz/pibuz-configure"
install -D -m 644 "${SRC}/pibuz.service" "${ROOTFS_DIR}/etc/systemd/system/pibuz.service"
install -D -m 644 "${SRC}/gexis-qobuz.service" "${ROOTFS_DIR}/etc/systemd/system/gexis-qobuz.service"
install -D -m 644 "${SRC}/plugin.json" "${ROOTFS_DIR}/usr/share/gexis/plugins/qobuz/plugin.json"
install -D -m 644 "${SRC}/mark.png" "${ROOTFS_DIR}/usr/share/gexis/plugins/qobuz/mark.png"

# **Neither unit is enabled**, and must not be: enabling `pibuz.service` is
# what downloads the receiver, and that is the user's decision behind a notice.
rm -f "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/pibuz.service" \
	"${ROOTFS_DIR}/etc/systemd/system/pibuz.service.wants/gexis-qobuz.service"
