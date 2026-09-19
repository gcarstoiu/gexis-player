# Shared by the stages that vendor a third-party artefact (ADR-0042).
#
# fetch_cached <url> <sha256> <dest>
#
# Looks in a content-addressed cache before the network and fills it on a
# miss. The cache file IS its checksum, so a hit is self-verifying and a
# changed pin is a different file rather than a stale one.
#
# The cache is optional by design: with no CACHE_DIR mounted this behaves
# exactly as the plain curl-and-verify it replaced. A build that has never
# seen the cache has to work, or the cache becomes a hidden build dependency.

CACHE_DIR="${GEXIS_BUILD_CACHE:-/pi-gen/gexis-cache}"

fetch_cached() {  # url sha256 dest
	local url="$1" sum="$2" dest="$3"
	local cached="${CACHE_DIR}/${sum}"

	if [ -r "${cached}" ]; then
		# Verified on the way out as well as on the way in: a cache is a
		# place a corrupted file could live.
		if echo "${sum}  ${cached}" | sha256sum -c - >/dev/null 2>&1; then
			cp "${cached}" "${dest}"
			echo "cache hit  ${sum}  $(basename "${url}")"
			return 0
		fi
		echo "cache entry ${sum} failed its own checksum, refetching" >&2
		rm -f "${cached}" || true
	fi

	# Every failure is checked explicitly rather than left to `set -e`: this
	# is a function, and errexit does not apply to one called in a condition
	# or before `||`. Tested 2026-09-19 - without these an unverified download
	# was stored under the checksum it had failed, which is a poisoned cache
	# entry that every later build would hit.
	if ! curl -fsSL -o "${dest}" "${url}"; then
		echo "fetch failed: ${url}" >&2
		return 1
	fi
	if ! echo "${sum}  ${dest}" | sha256sum -c -; then
		rm -f "${dest}" || true
		echo "checksum mismatch, refusing to cache: ${url}" >&2
		return 1
	fi

	# Only ever store something already verified. A partly written entry
	# would be a poisoned hit next time, so write beside it and rename.
	if [ -d "${CACHE_DIR}" ] && [ -w "${CACHE_DIR}" ]; then
		local temporary="${cached}.$$"
		if cp "${dest}" "${temporary}" 2>/dev/null; then
			mv -f "${temporary}" "${cached}"
			echo "cached     ${sum}  $(basename "${url}")"
		else
			rm -f "${temporary}" || true
			echo "could not write to ${CACHE_DIR}, continuing uncached" >&2
		fi
	fi
}
