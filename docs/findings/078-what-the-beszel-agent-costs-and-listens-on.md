# Finding 078 — What the Beszel agent costs and what it listens on

**Date:** 2026-09-25
**Question:** Two of the four things Phase 10 criterion 3 says are "to decide
when it is built, not now": *what the agent listens on and whether
[ADR-0028](../decisions/0028-ui-serving-and-command-channel.md)'s
"unauthenticated on the LAN" stance extends to it*, and *what it costs in
memory and CPU on a Pi 4 that is already frame-limited*.
**Scope:** `gexis`, `beszel-agent` **0.20.0** (arm64 release binary, run from
`/tmp`, not installed as a unit). **No hub connection was ever established** —
every run used a deliberately invalid token and a syntactically valid but
fictitious hub key, so the agent sat in its 10-second reconnect loop. The cost
numbers are therefore a **floor with a retry loop on top**, not the cost of a
monitored device streaming metrics; the real number comes after enrolment. One
run per configuration, 8–45 s each. Nothing was measured about the hub.

## It opens an inbound SSH port even when told to use the hub

The agent has two transports: the hub connects **in** over SSH on 45876, or the
agent connects **out** over a WebSocket to `--url` with `--token`. Given both a
URL and a token — the outbound configuration — it still starts the listener:

```
INFO Starting SSH server addr=:45876 network=tcp
WARN WebSocket connection failed err="unexpected status code: 401"
```

```
LISTEN 0  4096  *:45876  *:*
```

So the question was not rhetorical: by default this plugin would put a new
listening port on the appliance, and ADR-0028's stance would have to be argued
about rather than simply not engaged.

## `--listen -1` removes it entirely, and the outbound path survives

Three values were tried. Each run checked what was listening on 45876 and
whether the WebSocket attempts continued.

| `--listen` | log line | listening socket |
|---|---|---|
| (unset) | `addr=:45876` | `*:45876` — reachable from the LAN |
| `127.0.0.1:45876` | `addr=127.0.0.1:45876` | `127.0.0.1:45876` — loopback only |
| `-1` | `addr=:-1` | **none** |
| `0` | `addr=:0` | none on 45876 |

With `-1`, checked against the process's own pid rather than the port alone:

```
pid=13716 alive=yes
--- any listening socket owned by it
  none
--- websocket still retrying?
3
```

The process stays alive, owns **no listening socket at all**, and keeps
attempting the outbound WebSocket every 10 s. The bind failure is not fatal.

**This is the configuration to ship.** It is the strongest available answer to
the ADR-0028 question: the stance does not need extending, because there is
nothing inbound to extend it to. `127.0.0.1:45876` is the fallback if a future
Beszel version makes `-1` fatal — it is documented behaviour (an address), where
`-1` is a number the flag parser happens to accept and the log prints back as
`:-1`. **`-1` is not documented Beszel behaviour and could change without
notice**; a regression check belongs with whatever installs the agent.

## Cost floor: 14 MB and under 1 % of one core

Measured at 45 s, WebSocket mode, reconnect loop running, no hub:

```
    PID   RSS %CPU     ELAPSED CMD
  13471 14336  0.8       00:45 /tmp/beszel-agent --url ... --token ... --key ...
utime+stime ticks: 38
```

- **RSS 14.3 MB.**
- **38 ticks = 0.38 s CPU over 45 s ≈ 0.84 % of one core**, agreeing with
  `%CPU`'s 0.8.
- Binary on disk: **9,502,880 bytes**.

**What this does not measure:** the cost while actually connected and sampling,
which is the number that matters for a frame-limited panel. Four of those
0.38 s were spent on failed TLS-less HTTP handshakes that a connected agent
would not repeat, and none of it on the metric collection a connected agent
does on every interval. Re-measure after enrolment, under a scroll, against
[Finding 067](067-what-the-panel-presents-at-the-end-of-criterion-0.md)'s
numbers.

## Still owed

- **Whether it ships in the image or installs on demand** — the remaining
  question of criterion 3's four, and George's, not measurable. The first two
  are answered above; the hub's location he answered on 2026-09-25: *"Hub is
  present at http://192.168.178.69:8090/"*, so not this device.
- **Enrolment is blocked** on the token and the hub's public key, which live in
  the hub's Add System dialog. `http://192.168.178.69:8090/api/beszel/getkey`
  returns 401 unauthenticated, so this session cannot read the key itself.
