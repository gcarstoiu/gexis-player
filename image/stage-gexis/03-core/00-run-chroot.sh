python3 -m venv /opt/gexis-core/venv

# Exact-pinned deps come from core/pyproject.toml (see ADR-0021's venv
# addendum). Runs under QEMU aarch64 emulation like every other chroot
# step in this build; pip resolves arm64/cp3xx wheels from PyPI/piwheels
# the same way apt already resolves arm64 .debs here - confirmed
# reachable before this stage was written, not assumed.
/opt/gexis-core/venv/bin/pip install --no-cache-dir /opt/gexis-core/src

# The venv now owns an installed copy (site-packages); the source tree
# that was only there to install from would otherwise ship twice for no
# reason.
rm -rf /opt/gexis-core/src

# **The group that may connect to the plugin socket** (ADR-0084 as amended
# 2026-09-25). The daemon runs as root, so `0660` on the socket is root-only by
# itself - which made the access model "every plugin runs as root", the thing
# ADR-0087 refused for Beszel. Found by the first plugin written outside this
# repository: it ran as `pi` and the kernel refused it before it could speak.
#
# `pi` is in it because that is who plugin units run as today. A plugin with its
# own account joins this group instead of being given root.
if ! getent group gexis-plugins > /dev/null; then
	addgroup --system gexis-plugins
fi
adduser pi gexis-plugins
