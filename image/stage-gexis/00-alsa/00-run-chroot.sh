# Pin moved 1.2.14-1+rpt1 -> 1.2.14-1+rpt1+deb13u1, George's decision
# 2026-09-12, after the old pin stopped resolving and failed a build:
# archive.raspberrypi.com/debian trixie no longer indexes 1.2.14-1+rpt1
# (read from its own binary-arm64 Packages index, not inferred from apt's
# error). +deb13u1 is a Debian stable-update whose changelog carries
# exactly one line - "CVE-2026-25068" - on the same upstream 1.2.14: a
# missing bounds check in tplg_decode_control_mixer1(), the topology
# (.tplg) file decoder. Not the PCM or plugin path Findings 002/003
# measured, and a path this device never executes - the HiFiBerry overlay
# comes from the HAT's own EEPROM and no .tplg files are involved.
# ADR-0021's pin rationale ("tested against a known version, not the next
# one") is what makes this a decision rather than a version bump; see that
# record's amended pin bullet.
apt-get -o Acquire::Retries=3 install --no-install-recommends -y libasound2t64=1.2.14-1+rpt1+deb13u1
apt-mark hold libasound2t64
