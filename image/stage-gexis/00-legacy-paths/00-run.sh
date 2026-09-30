#!/bin/bash -e

# **ADR-0107: our programs and units moved** - out of /usr/local and
# /etc/systemd/system, into /usr/bin, /usr/lib/gexis and /usr/lib/systemd/system,
# where a package installs them. A warm build (CONTINUE=1) keeps what an earlier
# build wrote, and **a unit in /etc/systemd/system overrides one of the same name
# in /usr/lib/systemd/system**: an old copy left behind would silently win over
# the new one. So every copy an earlier build put in the old places goes, by
# name. The "enabled" links go too; the stages below make them again, pointing
# at the new place. Masks (links to /dev/null) are not ours to remove and stay.
ETC="${ROOTFS_DIR}/etc/systemd/system"
for unit in gexis-core.service gexis-meter.service gexis-park.service \
	gexis-uploaded-renderer@.service gexis-uploaded-service@.service \
	gexis-fetch@.service go-librespot.service squeezelite.service \
	gexis-bluetooth-setup.service gexis-kiosk.service gexis-panel-warmup.service \
	gexis-peppy.service gexis-splash-backstop.service gexis-splash-backstop.timer \
	beszel-agent.service plexamp.service gexis-plexamp.service; do
	rm -f "${ETC}/${unit}" \
		"${ETC}/multi-user.target.wants/${unit}" \
		"${ETC}/timers.target.wants/${unit}"
done
rm -rf "${ETC}/bluealsa-aplay.service.d/override.conf" "${ETC}/bluealsa.service.d/override.conf"
rmdir "${ETC}/bluealsa-aplay.service.d" "${ETC}/bluealsa.service.d" 2>/dev/null || true
for prog in go-librespot beszel-agent gexis-kiosk-start gexis-panel-warmup \
	gexis-peppy-start gexis-splash-fb; do
	rm -f "${ROOTFS_DIR}/usr/local/bin/${prog}"
done
rm -rf "${ROOTFS_DIR}/usr/local/lib/gexis"
