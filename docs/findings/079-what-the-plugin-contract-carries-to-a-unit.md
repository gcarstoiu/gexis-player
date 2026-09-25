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
unrelated write. `try-restart` and the changed/unchanged answer from the writer
are what make them hold — and leg 6 is `try-restart` again, from the other side:
a plugin that is off stays off when its credential changes.

The file is `-rw------- root root` throughout, and `/run` is tmpfs, so nothing
here survives a reboot — which is the point. The values live in the settings
store; this file is derived from them.

## What this does not show

- **Nothing about the panel.** Every number above is from the API and from
  `journalctl`. Whether the fields visibly appear when the toggle is tapped is
  George's to see; `visible` is what the panel obeys (ADR-0044 §6) and it
  flipped correctly.
- **Nothing about Beszel.** No hub, no token, no agent process. That is
  [ADR-0087](../decisions/0087-the-beszel-agent-is-the-first-service-plugin.md)'s
  own verification and it is blocked on the hub's Add System dialog.
- **Nothing about a plugin that is also a renderer.** `envtest` is a service.
  Arbitration still does not carry plugins.
- **The latency of a restart was not measured.** `try-restart` was given 3–4 s
  in each leg and had always finished; nothing establishes what it costs for a
  unit that is slow to stop.
