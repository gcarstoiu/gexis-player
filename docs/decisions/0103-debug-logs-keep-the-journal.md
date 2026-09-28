# ADR-0103 — Debug logs: the journal kept across restarts, when asked

**Status:** **Accepted** — George, 2026-09-28: *"Persistent logs based on debug
setting in Settings -> System. Off by default."*
**Date:** 2026-09-28
**Raised by:** a decision owed since 2026-09-26. A reboot destroyed the logs of a
bug George had just reproduced, because the journal lives in memory.

## Context

Raspberry Pi OS ships `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf`
with `Storage=volatile`: the journal is in RAM (54.8 MB on gexis on 2026-09-28),
and a reboot, including the one a restore does, loses it. That is the right
default for an SD card. It is the wrong one while a problem is being chased.

## Decision

1. **One switch, *Debug logs*, in Settings → System, off by default.**
2. **On:** the core writes `/etc/systemd/journald.conf.d/60-gexis-debug-logs.conf`
   with `Storage=persistent` and `SystemMaxUse=100M`. The higher number wins
   over the image's 40, so the journal goes to `/var/log/journal` and is capped
   at 100 MB of card. `systemd-journald` is restarted, and `journalctl --flush`
   moves what is already in memory onto the card, so the logs from before the
   switch are kept too.
3. **Off:** the core deletes that file, which puts the image's own volatile
   setting back, deletes `/var/log/journal`, and restarts `systemd-journald`.
   Off means no logs on the card, not old ones left behind.
4. **The device follows the switch at startup**, in both directions, as the
   other switches do (ADR-0077 as amended): a restore brings back the setting,
   not the file.
5. **What it is not:** more detailed logging. The unsurfaced `log_level` row
   (ADR-0022, [N]) stays as it is. The switch changes where logs are kept, not
   what is written.

## Consequences

- One ADR-0022 row, `debug_logs` [R] (George asked for it).
- Writes to the card while it is on: journald batches them, and the cap bounds
  the total. It is meant to be switched on while chasing something, then off.
- The core already runs as root, which is what writing under `/etc` and
  restarting journald need. No new privilege.
