# **Everything up to date here, where there is room** (found 2026-10-01).
# pi-gen's export-image stage runs `apt-get dist-upgrade` inside the image
# file it has already sized (the rootfs plus about 20%). The day the
# Raspberry Pi archive published a new Chromium among a batch of updates,
# that upgrade ran out of space and failed the 0.3.2 build - an hour after
# 0.3.1 had built with nothing to upgrade. Upgrading here, in the stage's
# directory, leaves export-image nothing to do. After the alsa-lib hold
# above, which a dist-upgrade respects.
apt-get -o Acquire::Retries=3 update
apt-get -o Acquire::Retries=3 -y dist-upgrade --auto-remove --purge
