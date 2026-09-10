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
