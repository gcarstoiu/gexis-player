#!/bin/bash -e

# Source for the venv install below (00-run-chroot.sh) has to be inside
# ${ROOTFS_DIR} before that chroot step runs - it can't reach outside the
# chroot to find it. Copied from the Makefile's second bind-mount
# (/pi-gen/gexis-core-src -> repo root's core/), not vendored into
# stage-gexis itself, so `core/`'s own tests (tier 1, every commit) run
# against one source tree, not a copy that can drift from it.
CORE_SRC="/pi-gen/gexis-core-src"
if [ ! -f "${CORE_SRC}/pyproject.toml" ]; then
	echo "ERROR: ${CORE_SRC}/pyproject.toml not found - is the core/ bind-mount wired up in the Makefile?" >&2
	exit 1
fi

install -d -m 755 "${ROOTFS_DIR}/opt/gexis-core"
rm -rf "${ROOTFS_DIR}/opt/gexis-core/src"
cp -r "${CORE_SRC}" "${ROOTFS_DIR}/opt/gexis-core/src"
# .git-ish or test-cache cruft from a dev checkout shouldn't ship, even
# though it wouldn't be installed - keep the copy itself clean.
rm -rf "${ROOTFS_DIR}/opt/gexis-core/src/.pytest_cache"
find "${ROOTFS_DIR}/opt/gexis-core/src" -name "__pycache__" -exec rm -rf {} +

install -D -m 644 files/core.toml "${ROOTFS_DIR}/etc/gexis/core.toml"
install -D -m 644 files/gexis-core.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-core.service"
install -D -m 644 files/gexis-boot-volume.service \
	"${ROOTFS_DIR}/etc/systemd/system/gexis-boot-volume.service"
