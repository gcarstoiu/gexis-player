# ADR-0181 — go-librespot from upstream's own build until a release carries its fix

**Status:** **Accepted** 2026-11-15 (George chose this, option B, over waiting
for upstream's next release). A one-off exception to
[ADR-0093](0093-we-do-not-build-or-patch-the-renderers.md)'s *pinned
upstream release binary*; its rule against building or patching the renderers
stands unchanged.
**Relates to:** [ADR-0107](0107-our-parts-as-debian-packages.md) (the
package), [ADR-0042](0042-a-local-cache-for-vendored-downloads.md) and
[ADR-0173](0173-releases-built-on-github.md) (the `inputs` mirror),
[ADR-0182](0182-upstream-releases-checked-daily-and-a-part-only-patch-release.md)
(how the next one is caught sooner).

## Context

George's phone, 2026-11-15: the Spotify app on Android closes with an error
while it casts to a player, and the music plays on. It matches go-librespot's
issue 434 (Spotify for Android 9.1.94): the app closes about 1.5 s after a
track from another playlist or album is picked while go-librespot plays. On
that change go-librespot publishes a state that names a stream (`playback_id`)
but no track, and the app fails on it. Spotify's own devices do not.

Upstream fixed it on 2026-11-07 (`908536471`, *drop the playback id together
with the track*, four files). Its latest release is still v0.10.5
(2026-10-16), which every player runs; nothing in the player can change what
go-librespot tells Spotify.

Upstream's own workflow builds every commit to `master` with the release's
script (`crosscompile.sh`, the same `arm64` target) and keeps the result 7
days. The build of `775ba5883` (2026-11-11, `master` at the time, run
43070007237) holds the fix; it expires 2026-11-18.

## Decision

1. **The player ships upstream's build of `775ba5883`**, the `arm64` tarball
   as upstream's workflow made it: not built or changed by us.
2. **A copy is kept** in the `inputs` mirror under its sha256 (`6bc18207…`),
   with the source archive of the same commit beside it (GPL-3.0, as for the
   release); `packaging/inputs.tsv` names the run it came from. The pin's
   download address is the mirror's, since the original expires.
3. **Its version is `0.10.5+git20261111.775ba58`** (package
   `0.10.5+git20261111.775ba58-4`): after 0.10.5, before any later release.
4. **It goes out as 1.16.3, from `main`**, with nothing else changed, after a
   preview on a test player that George checks: picking a track from another
   playlist while Spotify plays (the crash), casting, volume from the phone
   and the panel, skipping, another source taking over, and a group.
5. **The first upstream release that contains `775ba5883` replaces it**, by
   the usual route; `packaging/check-upstream.sh` reports the build as
   waiting until then, not as behind or current.

## Consequences

- **Twelve other upstream changes come with it**, none yet released: vorbis
  decoding fixes, an audio chunk retried when it stalls, pooled HTTP/2
  connections checked, incomplete metadata described instead of a crash, the
  access points' order and *device as a speaker group* as options (off),
  control of other Connect devices, library and queue listings, a station
  listed from the pages fetched before one fails, `prev`
  without rewinding as an option. Read against the core: it ignores the new
  `queue` event (no branch for unknown events) and calls `prev` as before.
- **The binary names its commit, not a version** (`running go-librespot
  775ba588`): upstream's script takes the version from a tag, and a `master`
  build has none. The package's version says which build it is.

## Preview (2026-11-15)

In the preview from `preview-radio-mdns` (`5dd200f8`, run 43709205656) on
bedroompi and guestpi at 12:40, both idle: the three packages upgraded and
nothing removed in the dry run and the install; go-librespot started as
`775ba588`, the core reconnected to it, Spotify Connect announced, the
player's own config kept. ShelvesPi and sofapi were playing and were left.
- Same libraries as 0.10.5 (`readelf -d`: libasound, libc, libm, libpthread,
  libresolv).
