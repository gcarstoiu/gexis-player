# Finding 079 — What the plugin contract carries to a unit

**Date:** 2026-09-25
**Question:** Does [ADR-0088](../decisions/0088-a-plugins-settings-reach-its-unit-as-environment.md)
work — a value typed into a settings row arriving at a process that will never
speak [ADR-0084](../decisions/0084-plugins-speak-json-lines-over-a-unix-socket.md)'s
protocol — and does George's *"when enabled fields appear that allow keys to be
provided"* hold on the device rather than in a unit test?
**Scope:** `gexis`, the branch's core deployed over the installed one. A
**temporary** plugin, `envtest`: a manifest with three rows (two carrying `env`
and `onlyWhen`, one carrying neither) and a unit whose `ExecStart` echoes what it
was given and sleeps. Driven through `PUT /settings/<key>` from the device
itself, which is the route the panel uses. **Beszel was not involved** — no hub,
no token, no agent. Both the manifest and the unit were removed afterwards.
Nothing here measures the panel's rendering; it measures what the API publishes
and what the process receives.

## The quoting, against real systemd rather than against the manual

The unit test asserts the bytes this code chooses, which is half a claim. So the
bytes were handed to systemd and the process's own `os.environ` compared with the
input:

```
PLAIN="http://192.168.178.69:8090"
SPACES="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI hub@host"
QUOTE="a\"b"
BSLASH="a\\b"
BOTH="\\\"x\\\""
DOLLAR="pa$$word%s"
TICK="a`b'c"
```

```
  OK   PLAIN   want='http://192.168.178.69:8090'
  OK   SPACES  want='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI hub@host'
  OK   QUOTE   want='a"b'
  OK   BSLASH  want='a\\b'
  OK   BOTH    want='\\"x\\"'
  OK   DOLLAR  want='pa$$word%s'
  OK   TICK    want="a`b'c"
ALL MATCH
```

Seven for seven, byte for byte. The space is the case that forced quoting at all
— a hub's public key is `ssh-ed25519 AAAA… comment`, and unquoted, systemd reads
everything after the first space as a second assignment.

## The rows, as published

```
  [group Env Test] type=group
  envtest.enabled  type=toggle   visible=True   value=False
  envtest.hub      type=text     visible=False  onlyWhen=['envtest.enabled', True]
  envtest.token    type=text     visible=False  onlyWhen=['envtest.enabled', True]
  envtest.note     type=text     visible=True   onlyWhen=None
```

The heading, the switch nothing declared, and **both `onlyWhen`s prefixed** —
the manifest says `["enabled", true]` and the registry holds
`["envtest.enabled", true]`. A row that is not conditional stays visible, so
this is the condition working and not a blanket hide.

## The defect this found: the switch was lying

**First run, before the fix:**

```
  envtest.enabled  value=True
--- unit actually:
disabled
inactive
```

ADR-0086's amendment synthesises the switch with `"default": True`, and
ADR-0087 has the image install Beszel's unit **disabled**. Those are two
statements of one fact and they disagreed: the screen would have shown Beszel
**Enabled** on a device where its unit was neither running nor going to start,
and the first thing George would have done is switch off something that was
already off.

**Fixed by asking systemd instead of declaring it.** `systemd.is_enabled`, read
once at startup for each synthesised switch and used as that row's default; a
stored value takes over the moment the switch is used. `enabled-runtime` counts
as enabled, `static` and `masked` do not. Afterwards:

```
  envtest.enabled  value=False        <- agrees with the unit
  envtest.hub      visible=False      <- and the fields are hidden
```

**Why it matters beyond this row:** a declared default is a copy of something the
system already knows, and nothing would have caught the copy going stale. The
image installs the unit; the manifest would have had to agree with the image
forever, in a file the image does not own.

## Every leg, driven through the API

```
=== 1. switch it on
  unit:    enabled / active
  process saw: started HUB_URL=[] TOKEN=[] NOTE=[]
=== 2. give it a hub and a token (spaces and a quote in the token)
  env file:
    HUB_URL="http://192.168.178.69:8090"
    TOKEN="ssh-ed25519 AAAAC3 hub@host \"x\""
  process saw: started HUB_URL=[http://192.168.178.69:8090] TOKEN=[ssh-ed25519 AAAAC3 hub@host "x"] NOTE=[]
=== 3. a row with no env must not restart it
  restarted: no (correct)
=== 4. rewriting the same value must not restart it either
  restarted: no (correct)
=== 5. switch it off
  unit:    disabled / inactive
=== 6. changing a value while off must not start it
  unit:    disabled / inactive
  env file still written:
    HUB_URL="http://192.168.178.69:8090"
    TOKEN="changed-while-off"
```

Legs 3 and 4 are the ones worth naming, because getting them wrong is invisible
until it is annoying: a settings screen that bounces a running service on every
unrelated write. The changed/unchanged answer from the writer is what makes them
hold — and leg 6 is the other side of it: a plugin that is off stays off when its
credential changes.

## The second defect, and this one the temporary plugin could not have found

The restart was `systemctl try-restart`, which touches a unit that is **active**.
Then the real plugin was installed and switched on before anything had been typed
into it, which is what anyone would do — the fields only appear once it is on.
The agent refused to start, correctly and with a clear reason:

```
Failed to load public keys: no key provided: must set -key flag, KEY env var, or KEY_FILE env var
beszel-agent.service: Failed with result 'exit-code'.
```

**A failed unit is not an active one, so typing the token did nothing.** The
value was stored, the file was written, and nothing read it until the next
reboot. In the first run of this test the agent was started by hand and the
mechanism looked fine, which is exactly how this would have shipped.

**The gate is now `is-enabled`, not `is-active`:** enabled means somebody asked
for this to run, and a value they just typed is how it gets to. Disabled still
means off. `reset-failed` runs before the restart, because a unit that spent its
`StartLimitBurst` while unconfigured refuses a plain restart with *"start request
repeated too quickly"* — and for this plugin that is the expected path, not an
edge case.

Re-run with the real plugin, nothing typed in, and nothing touched afterwards
except the three fields:

```
=== A. switched on with nothing typed in - it should fail, and say why
  unit:  enabled / activating
    beszel-agent.service: Failed with result 'exit-code'.
=== B. now type the three values, and touch nothing else
  unit:  enabled / active
  recovered by itself: YES
    2026/09/25 18:26:58 INFO Starting SSH server addr=:-1 network=tcp
    Started beszel-agent.service
    2026/09/25 18:27:08 WARN WebSocket connection failed err="unexpected status code: 401"
  listening on 45876:
    nothing (correct)
```

```
gexis_core.systemd INFO systemctl reset-failed + restart beszel-agent.service
gexis_core.plugin_env INFO plugins: beszel environment written (3 variable(s))
```

The 401 is the fake token being refused by George's real hub, which is the
furthest this can go without the enrolment values.

## The shipped plugin, as the screen publishes it

Installed by hand exactly as `07-beszel` installs it — binary, unit, check
script, manifest, `beszel` system user — with the unit left **disabled**, which
is how the image will ship it:

```
  group [System] -> heading 'Beszel'
  beszel.enabled   visible=True  value=False
  beszel.hub       visible=False onlyWhen=['beszel.enabled', True]
  beszel.token     visible=False onlyWhen=['beszel.enabled', True]  secret=True
  beszel.key       visible=False onlyWhen=['beszel.enabled', True]  secret=True
```

George's sentence, item by item: an entry of its own under System, a switch that
enables and disables it, and three fields that appear when it is on, two of them
masked. **The switch reads `False` because the unit is disabled** — the fix
above, doing its job on the plugin it was written for.

Under the unit's own restrictions (`User=beszel`, `ProtectSystem=strict`,
`ProtectHome`, `NoNewPrivileges`, `PrivateTmp`) the agent detected the disk and
`wlan0`, wrote its `fingerprint` to `/var/lib/beszel-agent`, and cost **13.9 MB
RSS** — the same as Finding 078's floor, so the sandbox costs nothing
measurable. It was still unconnected, so that is still a floor.

The file is `-rw------- root root` throughout, and `/run` is tmpfs, so nothing
here survives a reboot — which is the point. The values live in the settings
store; this file is derived from them.

## What this does not show

- **Nothing about the panel.** Every number above is from the API and from
  `journalctl`. Whether the fields visibly appear when the toggle is tapped is
  George's to see; `visible` is what the panel obeys (ADR-0044 §6) and it
  flipped correctly.
- **Nothing about a working enrolment.** Every run above ends in a 401 from
  George's real hub, because the token was fake. What the hub shows, what the
  agent reports, whether **throttle state** is among it, and what it costs while
  connected are all unmeasured and blocked on the hub's Add System dialog.
- **Nothing about a plugin that is also a renderer.** `envtest` is a service.
  Arbitration still does not carry plugins.
- **The latency of a restart was not measured.** The restart was given 3–14 s in
  each leg and had always finished; nothing establishes what it costs for a unit
  that is slow to stop.
- **Nothing was built from the `07-beszel` stage.** Its files were installed by
  hand, with the same paths, modes and user. The stage itself has not run, so a
  `make image` is still the first test of the download, the checksum and the
  chroot step.
