# ADR-0087 — The Beszel agent is the first service plugin

**Status:** **Accepted** — George, 2026-09-25: *"In the image. And it should be
visible in the settings under a plugin entry. Then beszel could be enabled or
disabled from there. When enabled fields appear that allow keys to be
provided."* Three of the four questions Phase 10 criterion 3 left open were
answered by measurement
([Finding 078](../findings/078-what-the-beszel-agent-costs-and-listens-on.md));
the fourth was his, and that is his answer, with a shape for the screen that
the record did not ask for and now follows.
**Date:** 2026-09-25
**Raised by:** Phase 10 criterion 3 — *"a second plugin that is not a renderer …
If the contract cannot express that, it is a renderer API wearing a plugin's
name."*
**Relates to:** [0086](0086-a-plugin-declares-itself-in-a-manifest.md) (the
manifest this uses, and the amendment this exercise caused),
[0084](0084-plugins-speak-json-lines-over-a-unix-socket.md) (the socket it does
*not* need), [0016](0016-plugins-as-separate-processes.md) (plugins are separate
processes), [0028](0028-ui-serving-and-command-channel.md) (no authentication on
a trusted LAN — the stance this plugin was expected to test),
[0022](0022-settings.md) (the inventory its rows join)

## Context

Criterion 3 asks for a plugin with no metadata, no transport and no claim on the
audio device. The Beszel agent is that: it samples CPU, temperature, clocks,
memory, disk and network, and reports them to a hub elsewhere. George's hub is
already running — *"Hub is present at http://192.168.178.69:8090/"*, 2026-09-25
— so the hub is not this device's job and never was.

It has already earned its keep before shipping. **It found the gap in ADR-0086**
that the amendment closes: a plugin could declare settings rows but nothing
could switch it off, because the three renderers got their `Enabled` toggle from
a hardcoded `RENDERER_ROWS` a plugin has no access to. That is exactly the
failure criterion 3 was written to catch, and it was caught by a plugin that
does nothing else.

## The three answers

**1. The hub is not here.** George's existing hub. Nothing on this device serves
Beszel; the agent is a client.

**2. It listens on nothing.** This was the real question, and the default is the
wrong answer: given `--url` and `--token`, the outbound configuration, the agent
*still* starts an inbound SSH listener on `*:45876`. Measured. With
`--listen -1` it owns **no listening socket at all** while the outbound
WebSocket keeps working. So **ADR-0028's stance does not need extending** —
there is nothing inbound for it to cover. `--listen 127.0.0.1:45876` is the
documented fallback; `-1` is a value the flag parser accepts and the log prints
back as `:-1`, so it gets an assertion where the agent is installed rather than
trust.

**3. It costs 14 MB and under 1 % of one core** — as a floor, in a reconnect
loop, with no hub attached. **Enrolled, it costs 0.02 % of one core and the same
14.2 MB** ([Finding 080](../findings/080-the-agent-enrolled.md)). The floor was
the expensive case: reconnecting cost, reporting does not, so the re-measurement
under a scroll that this record promised is not worth taking.

## The shape

A plugin by ADR-0086, `"kind": "service"`:

- **`/usr/share/gexis/plugins/beszel/plugin.json`** — id `beszel`, kind
  `service`, unit `beszel-agent.service`. It declares **no `enabled_row`**, so
  ADR-0086's amendment synthesises `beszel.enabled` and wires it to
  `systemctl enable/disable --now`. That is the whole of what criterion 3 says a
  service plugin wants — *"installed, started, kept running and switched off
  again"* — and the contract now expresses it without a line of Beszel-specific
  code in the core.
- **It never opens the socket.** ADR-0084's Unix socket carries state and
  commands; this plugin has neither. A service plugin that only wants a unit
  managed is a manifest and nothing more, and proving that is half the point of
  the criterion.
- **Rows:** the hub URL and the two enrolment secrets, as `secret` text rows —
  the treatment the three existing API keys already get, not the Wi-Fi
  passphrase's. The passphrase never reaches the registry at all:
  `wifi.join` hands it to `nmcli`, which stores it, and no row holds it. A token this device has to hand to a process it
  starts is the API keys' problem, not the passphrase's. Listed in full below.

## Where it lives: the image, defaulting off

George's answer. A `02-renderers`-style stage installs the binary and the
manifest exactly as the three renderers are installed, and `beszel.enabled`
defaults **off**, so a device nobody enrolled runs nothing.

The alternative was an on-demand install, and it was rejected on what it would
have had to build first: a writable plugin directory (manifests are discovered
under `/usr/share/gexis/plugins`, which the image owns), a checksummed
download, and a rule about who may ask for one. That is the first half of a
plugin installer, and an installer is a phase of its own rather than something
arrived at sideways because the first service plugin needed somewhere to put a
binary.

**Pinned like go-librespot, and verified three ways rather than one.** ADR-0042's
stage comment insists a checksum be "verified independently before trusting it,
not just copied from the API", so: `beszel-agent_linux_arm64.tar.gz` at
**v0.20.0**, sha256
`dbb292d7309ca00cfd7f3d8f86480991f7c959e65af6506754a55d3e345452ab` —
agreeing across the computed sum, the GitHub API's asset digest, and upstream's
own `beszel_0.20.0_checksums.txt`. There is an arm64 `.deb` in the same release
and it is not used: it brings its own unit, user and update path, and this
plugin's unit has to carry `--listen -1` and the environment file below.

## What the screen shows

George: *"visible in the settings under a plugin entry … when enabled fields
appear that allow keys to be provided."* Every piece of that already exists and
none of it is Beszel-specific:

- **The entry.** ADR-0086 already gives a plugin a `group` row carrying its own
  name, so `Beszel` is a heading in **System**, the way a renderer's is in
  Sources.
- **The switch.** ADR-0086 as amended synthesises `beszel.enabled`, wired to
  `systemctl enable/disable --now`.
- **The fields appearing.** ADR-0044's `onlyWhen`, which already has this exact
  precedent: `wallpaper_key` is a secret text row revealed by
  `onlyWhen: ["idle_background", "Wallpapers online"]`. The plugin's rows carry
  `onlyWhen: ["enabled", true]` and **the merge has to prefix the key they
  name**, which it does not do today — a manifest saying `enabled` would be
  refused at load as naming an unknown setting, and the plugin would vanish
  from the screen with only a log line to say why. That is the one code change
  the screen needs, and it is in the contract, not in Beszel.
- **Reaching the agent.** A row's value has to arrive at a third-party binary
  that will never speak ADR-0084's protocol.
  [ADR-0088](0088-a-plugins-settings-reach-its-unit-as-environment.md) is that,
  and it is generic.

**The secrets are not protected, and this changes nothing about that.**
`secret: true` masks a value on the panel; the daemon publishes it in full over
`GET /settings`, which
[ADR-0083](0083-a-backup-leaves-the-device.md) already states outright for the
three API keys that are there today. The Beszel token and hub key join them on
the same terms. Not a new exposure, and not a fixed one either.

## Proposed rows, for ADR-0022's inventory — George to confirm

Declared in the manifest, so they exist on the device whether or not anything is
enrolled. Marked `[N]` as new suggestions until confirmed:

| Key | Type | Why |
|---|---|---|
| `beszel.enabled` | toggle | Synthesised by ADR-0086; defaults **off** |
| `beszel.hub` | text | The hub's URL. `HUB_URL` |
| `beszel.token` | text, `secret` | From the hub's Add System dialog. `TOKEN` |
| `beszel.key` | text, `secret` | The hub's public SSH key, same dialog. `KEY` |

The three below are **deliberately not rows**, and each has a reason:

- **`LISTEN=-1`** is on the unit's `ExecStart`. It is a security property, not a
  preference — Finding 078 measured that the default opens an inbound port even
  in outbound mode, and a row would let it be turned back on by accident.
- **`DATA_DIR`** is `/var/lib/beszel-agent`, fixed. It holds the agent's
  `fingerprint`, which is the identity the hub binds this system to.
- The agent's own update mechanism is not exposed. The binary is the image's.

**`var/lib/beszel-agent` joins [ADR-0083](0083-a-backup-leaves-the-device.md)'s
backup members**, for the same reason `var/lib/go-librespot` had to: a reflash
that loses the fingerprint is a device the hub no longer recognises, and that
was exactly how the Spotify pairing was lost.

## Consequences

- The contract gains its non-renderer proof without gaining a non-renderer code
  path — no `kind == "service"` branch in the core, only the absence of the
  things a renderer declares.
- **v1 cannot be frozen before this lands.** Criterion 1 is the frozen contract
  and criterion 3 is the plugin that has already amended it once; freezing in
  the other order would freeze a contract that the next plugin breaks.
- ~~George gets the throttle log he asked for on 2026-09-18, which nothing on the
  device can currently produce.~~ **Wrong, corrected 2026-09-25 once the agent
  was enrolled** ([Finding 080](../findings/080-the-agent-enrolled.md)): the
  binary contains no `throttl`, `vcgencmd`, `vcio` or `undervolt` string at all.
  The Pi's throttle state is not a Linux sensor — it comes from
  `vcgencmd get_throttled` over `/dev/vcio`, and this agent never opens it.

  **What he does get is two of the four parts he asked for**: temperature and CPU
  over time, which is enough to see a thermal event coming and to say what the
  CPU was doing. Not the throttle bits, and nothing about the GPU. **That leaves
  a question owed** — whether something small should sample
  `vcgencmd get_throttled` on its own — and it is a new decision, not part of
  this one.
- Two settings rows join ADR-0022's inventory, **after George confirms**, plus
  the synthesised `beszel.enabled`.
