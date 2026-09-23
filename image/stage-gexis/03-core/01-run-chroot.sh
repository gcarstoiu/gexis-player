# ADR-0049: what samba will serve, asked of samba.
#
# **Not a grep on the file we just wrote.** That is a check on our own
# `install`, and `docs/LESSONS.md` case 9 is that exact mistake costing a
# subphase: the edit landed every time and the setting did nothing.
# `testparm` is samba's own parser, so it answers the question that matters
# - what the running daemon will read.
#
# (`on_chroot` runs this under `bash -e`; the explicit exits below are for
# the greps, which are conditions rather than failures.)

share="$(testparm -s --section-name=pictures 2>/dev/null || true)"
grep -q "^[[:space:]]*path = /var/lib/gexis-core/pictures$" <<<"${share}" || {
	echo "ERROR: samba does not serve the pictures share (ADR-0049)" >&2
	testparm -s 2>&1 | head -40 >&2
	exit 1
}
# Writable and guest-reachable, or the row this exists for stays empty and
# the reason is invisible from every screen this product has.
grep -q "^[[:space:]]*read only = No$" <<<"${share}" || {
	echo "ERROR: the pictures share is not writable (ADR-0049)" >&2; exit 1; }
grep -q "^[[:space:]]*guest ok = Yes$" <<<"${share}" || {
	echo "ERROR: the pictures share is not guest-reachable (ADR-0049)" >&2; exit 1; }

# **And nothing else is shared.** Debian's stock smb.conf adds `[homes]` -
# every local user's home directory - plus `[printers]` and `[print$]`. Our
# include says `available = no` to all three, and this asserts the effect:
# any section that is not `pictures` must be unavailable, whatever a later
# package upgrade adds to their file.
testparm -s 2>/dev/null | awk '
	/^\[/        { section = $0; available = "yes" }
	/available/  { available = $3 }
	/^$/         { if (section != "" && section != "[global]") print section, available; section = "" }
	END          { if (section != "" && section != "[global]") print section, available }
' | while read -r section available; do
	if [ "${section}" != "[pictures]" ] && [ "${available}" != "No" ]; then
		echo "ERROR: samba also serves ${section} (ADR-0049: one directory)" >&2
		exit 1
	fi
done
