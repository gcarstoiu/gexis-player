# ADR-0087 — The Beszel agent is the first service plugin

**Status:** Proposed — three of the four questions Phase 10 criterion 3 left
open are answered by measurement
([Finding 078](../findings/078-what-the-beszel-agent-costs-and-listens-on.md));
**the fourth is George's and is marked below.**
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
loop, with no hub attached. The connected number is not measured and the finding
says so; it gets re-measured under a scroll after enrolment, against Finding
067's panel numbers.

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
- **Rows:** the hub URL, and the enrolment secrets. The token and the hub public
  key are credentials, so they follow ADR-0022's treatment of the Wi-Fi
  passphrase rather than sitting in a settings row as plain text — **this is the
  part still to draw**, and it is why the row list below is not final.

## Still to decide — George

**Does it ship in the image, or install on demand?** The two differ in more than
delivery:

- **In the image.** Simplest: a `03-core`-style stage installs the 9.5 MB binary
  and the manifest, exactly as the three renderers are installed, and
  `beszel.enabled` defaults **off** so an unenrolled device runs nothing. Cost:
  every device carries a monitoring agent it may never use, and the binary is
  pinned to whatever version the image was built with — `beszel-agent update`
  exists but writing into `/usr/` from a running service is not how anything
  else on this device is updated.
- **On demand.** Closer to what ADR-0016 imagines a plugin is, and needs
  machinery that does not exist: a writable plugin directory (manifests are
  discovered under `/usr/share/gexis/plugins`, which the image owns), a download
  with a checksum, and a decision about who is allowed to ask for it. None of
  that is built, and building it for one agent would be the first half of a
  plugin installer.

**Recommendation: in the image, defaulting off.** Phase 10 is about whether the
*contract* can carry a non-renderer, and an image-installed manifest tests that
completely. An installer is a phase of its own and should be argued as one, not
arrived at sideways because the first service plugin needed somewhere to put a
binary.

## Consequences

- The contract gains its non-renderer proof without gaining a non-renderer code
  path — no `kind == "service"` branch in the core, only the absence of the
  things a renderer declares.
- **v1 cannot be frozen before this lands.** Criterion 1 is the frozen contract
  and criterion 3 is the plugin that has already amended it once; freezing in
  the other order would freeze a contract that the next plugin breaks.
- George gets the throttle log he asked for on 2026-09-18, which nothing on the
  device can currently produce.
- Two settings rows join ADR-0022's inventory, **after George confirms**, plus
  the synthesised `beszel.enabled`.
