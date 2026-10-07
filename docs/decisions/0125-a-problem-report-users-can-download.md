# ADR-0125 — A problem report users can download, with the personal parts taken out

**Status:** **Accepted** — George, 2026-10-07, with both decisions below
answered (*"take them out too"*; *"give both options"*). Raised by George: *"have an option to
download logs - pii scrubed - for users to be able to report possible issues
back to us."* Needed before the first public release.
**Builds on:** [ADR-0103](0103-debug-logs-keep-the-journal.md) (Debug logs
keep the journal across restarts), [ADR-0101](0101-a-mini-player-on-the-phone.md)
(the phone page), [ADR-0105](0105-updates-over-the-network.md) (the updater's
own log).

## Context

Today a problem on a user's player can be read only by someone with SSH on
it. *Debug logs* (ADR-0103) keeps the journal across restarts, but nothing
takes it off the device. A user who wants to report a problem has nothing to
attach.

The logs are full of things that identify a person or a home: Wi-Fi network
names, addresses on the home network, the device's and phones' names,
Bluetooth addresses, a NAS's name and share, account names, the weather
location, the music being played. None of it may leave the device unless the
user has seen what goes.

## Decision

1. **[N] *Problem report*** - *Settings → System*, after *Debug logs*; an
   action, no stored value. It builds one file, `gexis-report-<date>.zip`,
   and the browser downloads it. **On the phone page or a computer only**:
   the panel has nowhere to save a file, so there the row says to open
   Settings on a phone and shows the address.
2. **What goes in:**
   - the journal: since the last start, or the kept one when *Debug logs*
     is on (ADR-0103), the newest 20 MB at most;
   - the updater's own log (`apt.log`, the status file) and the release
     notes' versions;
   - what is installed: the Gexis packages and their versions, the kernel,
     the image's build;
   - the hardware: Pi model and memory, the sound card and its mixer
     controls, the chosen output and board, the screen's maker, model and
     modes (never its serial number), temperatures and throttling;
   - the settings, **without any row marked `secret`** (keys, tokens,
     passwords never leave);
   - an optional line from the user: *"What happened?"*, typed before the
     download.
3. **What is taken out, on the device, before the file is written** (each
   kind replaced by a stable token, so the same address reads `ip-3`
   everywhere and the log still makes sense):
   | Kind | Becomes |
   |---|---|
   | IP addresses (v4 and v6) except loopback | `ip-1`, `ip-2`, ... |
   | MAC and Bluetooth addresses | `mac-1`, ... |
   | Wi-Fi network names, the device's name, host names, `.local` names | `net-1`, `host-1`, ... |
   | Phones' and Bluetooth devices' names | `device-1`, ... |
   | Share paths, NAS names, user names, account names | `share-1`, `user-1`, ... |
   | The weather location, latitude and longitude | `place` |
   | Track, album and artist names, file paths in the library | `title-1`, `path-1`, ... (George: *"take them out too"*) |
   | Anything shaped like a key or token (long hex or base64 runs) | `secret` |
   Known values are taken from the device itself (its own SSIDs, names,
   shares, server address, paired devices) and replaced wherever they
   appear; patterns catch the rest.
4. **The user sees it before sending.** The download is followed by a short
   summary on the same page - *"Taken out: 4 addresses, 2 network names, 1
   share..."* - and the file is plain text in a zip, so it can be opened
   and read. Nothing is sent anywhere by the player.
5. **How it reaches us - both ways** (George: *"give both options"*): the
   row links to a GitHub issue form, *"Report a problem"*, where the file is
   attached, and gives an e-mail address for people without a GitHub
   account. **The address is owed:** a project address, never a personal
   one (the repository is public).

## Consequences

- One ADR-0022 row, `problem_report` [R], appended 2026-10-07.
- Taking things out by pattern can miss something. The row's note says so
  plainly: *"Personal details are taken out, but read the file before
  sharing it."*
- Track names out means a problem tied to one album is harder to follow;
  the user can name it in *"What happened?"* if they choose.
- The scrubber gets its own tests, with a fixture journal holding every
  kind in decision 3.

## Decided (George, 2026-10-07)

1. **Track, album and artist names are taken out** with the rest.
2. **Both routes:** the GitHub issue form and an e-mail address.
