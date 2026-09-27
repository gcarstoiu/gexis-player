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

## Not decided here

- Whether a backup carries the receiver's login. Probably not: re-pairing is
  one tap in the app. Settled at step 2.
- The official route stays open. If Qobuz answers an enquiry (George's to make),
  this is revisited.

## Reversal conditions

A request from Qobuz, or Pibuz's author withdrawing it: the install action is
removed in the next image, and anything installed stops at the next start.
