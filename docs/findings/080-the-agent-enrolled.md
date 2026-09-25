# Finding 080 — The agent enrolled: what it costs, and the half it cannot see

**Date:** 2026-09-25
**Question:** What [ADR-0087](../decisions/0087-the-beszel-agent-is-the-first-service-plugin.md)
left unmeasured once the agent was actually talking to a hub — the cost while
connected, which [Finding 078](078-what-the-beszel-agent-costs-and-listens-on.md)
could only bound from below, and whether it records what that record claims it
does.
**Scope:** `gexis`, `beszel-agent` **0.20.0**, connected to George's hub at
`192.168.178.69:8090` with his own token and key, which he entered through the
settings screen and confirmed working. One 60-second sample, on an otherwise
idle device with no renderer playing. **The hub's own display was not seen from
here** — every claim below about what the agent *records* comes from the arm64
binary and from the unit's journal, not from the dashboard.

## Connected, it costs almost nothing — and the floor was the expensive part

```
  connected, over 60s:
    RSS      14192 kB -> 14212 kB
    CPU      1 tick at 100 Hz = 0.01s
    of one core: 0.02%
```

**0.02 % of one core**, against Finding 078's floor of **0.84 %**. That reads
backwards until you see what the floor was measuring: an agent with a bad token,
failing a WebSocket handshake every ten seconds. Reconnecting is what cost;
reporting does not. RSS is flat at **14.2 MB**, the same as unconnected, so the
unit's restrictions (`User=beszel`, `ProtectSystem=strict`, `ProtectHome`,
`NoNewPrivileges`, `PrivateTmp`) cost nothing measurable either.

For a panel measured against a 55 fps target
([Finding 067](067-what-the-panel-presents-at-the-end-of-criterion-0.md)), a
hundredth of a core is not a number that needs re-measuring under a scroll.

## It cannot see throttling, and ADR-0087 said it could

That record claimed *"George gets the throttle log he asked for on 2026-09-18,
which nothing on the device can currently produce."* **That is wrong**, and this
is what it was checked against — six string searches of the arm64 binary:

| searched for | hits |
|---|---|
| `throttl` | 0 |
| `vcgencmd` | 0 |
| `vcio` | 0 |
| `get_throttled` | 0 |
| `under-volt` | 0 |
| `undervolt` | 0 |

Against, for comparison, what it does carry: `CPUUsage`, `CpuCoresUsage`,
`CpuBreakdown`, `CpuPeak`, `CpuModel`, `Temperature`, `DashboardTemp`, and json
tags for memory, disk and network.

**The Pi's throttle state is not a number anything on Linux exposes as a
sensor** — it comes from `vcgencmd get_throttled`, which talks to the VideoCore
over `/dev/vcio`, and the agent never opens it. So George's 2026-09-18 question
— *"a log of when the Pi throttled, for how long, and what the CPU and GPU were
doing at the time"* — is answered **in two of its four parts**: it will have
temperature and CPU over time, which is enough to see a thermal event coming and
to say what the CPU was doing. It will not have the throttle bits themselves, and
nothing about the GPU.

**Caveat on the method.** A Go binary usually carries its field names and its
format strings, so the absence of all six is good evidence; it is not proof, and
a feature reached only through a numeric syscall would leave no such string. The
hub's own dashboard settles it in one glance and George is the one looking at it.

**What is certain either way:** the device has read `0xd0000` from
`vcgencmd get_throttled` this month — under-voltage, frequency capping and the
soft temperature limit have all *occurred* — and nothing samples or timestamps
that. The agent does not change it.

## The backup carries the enrolment

Taken through `POST /settings/backup`, the route the panel uses, and read back
out of the archive rather than off the device:

```
    var/lib/gexis-core/settings.db
    var/lib/beszel-agent/
    var/lib/beszel-agent/fingerprint

    beszel.enabled   true
    beszel.hub       "http://192.168.178.69:8090/"
    beszel.key       82 chars
    beszel.token     32 chars
    fingerprint      present, 48 bytes
```

**The three keys needed nothing added.** They are settings, and
`var/lib/gexis-core/settings.db` has been a backup member since
[ADR-0083](../decisions/0083-a-backup-leaves-the-device.md). The fingerprint did
need adding and it is there.

**The first archive taken did not contain it**, and the cause was not the code:
the device was still running the previous `backups.py`, deployed before
`var/lib/beszel-agent` joined `MEMBERS`. Checked — `grep -c beszel-agent` on the
installed module returned `0` — rather than concluded. After deploying it, the
same command produced the listing above.

## What this does not show

- **What the hub displays.** Not readable from here without credentials, and the
  question above turns on it.
- **Anything over time.** One 60-second sample on an idle device. What the agent
  costs while a renderer is playing and the panel is scrolling is unmeasured,
  though 0.02 % leaves little room for it to matter.
- **A restore.** The archive was read, not restored. Whether a restored
  fingerprint is accepted by the hub as the same system is untested — it is the
  reason the file is in the backup at all.
