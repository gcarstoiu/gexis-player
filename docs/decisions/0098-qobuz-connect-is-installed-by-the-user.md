# ADR-0098 — Qobuz Connect is installed by the user, from its own author's release

**Status:** **Accepted** — George, 2026-09-27: *"follow what moOde is doing as
well. It is up to the user to decide whether to install it or not. We give the
possibility but not retain any code that could leave the entire player into
trouble."* **Supersedes** [ADR-0016](0016-plugins-as-separate-processes.md)'s
plan for a *private* Qobuz repository, and amends Phase 12's acceptance.
**Building.**
**Date:** 2026-09-27
**Raised by:** [Finding 093](../findings/093-qobuz-connect-in-september-2026.md).
Qobuz had QBZ taken down in September 2026. moOde points at Pibuz (MIT), which
its users install themselves. Every open client uses the web player's scraped
credentials, which Qobuz's terms forbid.

## Decision

1. **Nothing that speaks to Qobuz lives in our repositories or our image.** The
   receiver is **Pibuz** ([PhilipVinc/pibuz](https://github.com/PhilipVinc/pibuz),
   MIT), the one moOde uses. It is fetched **on the device, when the user asks
   for it**, from its author's GitHub release: the `linux-aarch64` tarball,
   checked against the `.sha256` the author publishes beside it and against the
   checksum we pin. Our code holds a URL, a version and a checksum, never the
   receiver.
2. **The user decides, knowingly.** The install is a Settings action. It first
   shows what it is: an unofficial receiver, not affiliated with or endorsed by
   Qobuz, which may stop working at any time, and whose use Qobuz's terms may
   not permit, at the user's own risk and on their own account. Nothing is
   fetched until the user confirms. **Uninstall** removes the receiver and
   everything it wrote.
3. **Our side is an adapter, and it is public.** A `gexis-qobuz` plugin (the
   ADR-0086 contract, the same shape as gexis-plexamp) drives the installed
   receiver through what Pibuz exposes (MPRIS, its JSON events, its hook
   script). It contains no Qobuz protocol, credentials or keys. It ships in the
   image **inert**: its source row says *not installed* until the receiver is
   there, and its unit cannot start without it. The licence gives no reason for
   a private repository, and ADR-0090's public, checksum-pinned fetch needs a
   public one.
4. **The pin moves when we choose.** A Pibuz release is taken after it has been
   run on `gexis`, as go-librespot and Plexamp are. The receiver never updates
   itself.

## Order of work

1. A spike on `gexis`, installed by hand. Does it appear in the Qobuz app? Is
   24/192 bit-perfect on our `output`? What happens when another renderer holds
   the device, on takeover and release? What do its events carry? Written up as
   a Finding.
2. The install and uninstall action in the core: download, verify, unpack to
   `/opt/gexis-qobuz-receiver`, a unit, and an acknowledgement stored with the
   settings.
3. The `gexis-qobuz` plugin: manifest, acquisition, release, metadata, volume,
   transport.
4. The panel: source pill, handoff, Peppy badge, the Qobuz mark (trademark; see
   ADR-0099).
5. George's regression pass.

## How (design, 2026-09-27, after Finding 094)

The spike worked. George cast from the Qobuz app, played up to 24/192 at native
rates through `output`, and used volume, seek and next. Takeover failed in both
directions, because the core did not know Pibuz existed. The adapter fixes this:

- **Install (step 2)** uses ADR-0100's mechanism. `components/pibuz.env` pins
  the `linux-aarch64` release, and `gexis-fetch@pibuz` fetches it. The Plugins
  switch is guarded by the notice in decision 2: the switch is refused until
  the notice has been confirmed once, and the confirmation is stored.
- **The receiver runs as `pibuz.service`** (a system unit, `User=pi`), with its
  config under `/var/lib/gexis-qobuz`. `audio.device output`,
  `audio.cache_to_disk false`, and the control API bound to `127.0.0.1`,
  because Pibuz's default is the whole LAN (Finding 094). Device name: the
  player's name (ADR-0048).
- **The adapter** (`gexis-qobuz`, public, the ADR-0084 contract) reads
  `GET /api/events` (SSE) for state, track, volume and session, and drives
  `/api/playback/*`:
  - **Acquisition** is Pibuz going `loading` or `playing`. It is reported to the
    core at once. Pibuz retries a busy card for about six seconds, which is the
    window in which the core releases the current holder. This fixes test 2.
  - **Release** is pause, which frees the card (test 3), then stop. This fixes
    test 1.
  - **Metadata** comes from `TrackStarted` (title, artist, album, cover, rate,
    depth) and position updates.
  - **Volume** is the level `VolumeChanged` reports.
  - **Mark:** Gexis's own disc, Q3 (`design/marks/qobuz.svg`), never Qobuz's
    logo.

## Built on gexis (2026-09-27, by hand; not yet in an image)

- **The switch asks first.** Qobuz Connect's manifest carries the notice, the
  core puts it on the switch as a `warn`, and the panel shows it when the
  switch is turned on: *"I understand, switch it on"* or Cancel. Nothing is
  fetched before that. Off never asks.
- **The download goes through ADR-0100**, with its progress in the row. The
  first attempt **refused Pibuz 2.5.0**: its author had re-published that
  release's asset with different bytes after we pinned it. The row said the
  checksum did not match, and nothing was installed. It is pinned to **2.5.1**
  now; its checksum is the author's own, cross-checked by a separate download.
- **Retry had a bug, found on the panel.** It read a setting from a worker
  thread, SQLite refused, and the row said *"Starting the download"* over
  nothing. Now it is read on the loop's thread. A failed Retry says so. A
  *preparing* standing more than a minute becomes *"The download did not
  start"*.
- **Running:** `pibuz.service` as `pi`, with its state in `/var/lib/gexis-qobuz`.
  Its control API is on `127.0.0.1:8182` only; the pairing listener on `:8183`
  is the one port on the LAN, because casting needs it. It advertises as the
  player's name. `gexis-qobuz` connected to the core, which registered it as a
  renderer. The adapter is `BindsTo=` the receiver, so it does not poll a
  receiver that never started.
- **Volume: George kept this arrangement (2026-09-27, "we keep it as it is set
  now").** The core does not manage it (`volume_managed: false`): the Qobuz
  app's slider moves Pibuz's digital level, and the panel's moves the DAC.
  Nothing is applied twice. An `external` mode (report the level, do not apply
  it, as go-librespot's `external_volume`) was requested upstream:
  [PhilipVinc/pibuz#3](https://github.com/PhilipVinc/pibuz/issues/3).

## Not decided here

- Whether a backup carries the receiver's login. Probably not: re-pairing is
  one tap in the app. Settled at step 2.
- The official route stays open. If Qobuz answers an enquiry (George's to make),
  this is revisited.

## Reversal conditions

A request from Qobuz, or Pibuz's author withdrawing it: the install action is
removed in the next image, and anything installed stops at the next start.

## Amended 2026-09-28: the adapter asks, and a release is a kill

[Finding 096](../findings/096-qobuz-connect-with-the-adapter.md), from George's
first round with the adapter. Two lines above no longer hold:

- **"reads `GET /api/events` (SSE)"**: the stream arrives in bursts, seconds
  late, and missed a skip's `TrackStarted`. The adapter now polls
  `/api/status` every 0.5 s, and `/api/now-playing` when the track changes or
  every 2 s. A position more than 3 s from where the playhead should be is
  sent at once, which is the seek George saw the panel miss.
- **"Release is pause, which frees the card"**: it frees it after 2.06 s,
  whatever the buffer. go-librespot needs the card within 0.26 s, so
  Spotify's first track was lost. The ladder's polite grace is now 0, as for
  Plexamp (ADR-0091): the core checks once and kills. Pibuz comes back in
  2 s, stopped, and still visible in the Qobuz app, which can cast to it again.

## Not built: uninstall (found 2026-09-28, closing Phase 12)

§2's "Uninstall removes the receiver and everything it wrote" was never built.
The plugin switch stops Pibuz, and the download stays in
`/opt/gexis-qobuz/receiver` with its data under `/var/lib/gexis-qobuz`. The
Legal page said *"Uninstalling it removes it from the device"*. It now says
what happens: switching off stops it, and the download stays. Whether to build
removal, and in what form, was a decision owed to George. **Decided
2026-09-28: switching off stops it, and a separate Remove deletes the download**
(ADR-0100's amendment of that date, which covers Plexamp too).

