# ADR-0138 — Reports in steps, a visible checklist, and one way to send for both

**Status:** **Accepted** — 2026-10-11, George, all four decisions as
recommended: the GitHub issue carries the text and the log's last errors
inline, the file an extra; all seven checklist lines; a text file for
hardware feedback; a prepared report kept one hour. Raised by George: *"Can we improve the
problem report as well? I'm thinking we should have steps there too. One for
free text entry, another one for preparing the data with details on what is
being prepared similar to a checklist ... Lastly on the last step of the
problem report user is given choice of direct submit to GitHub where
everything will be prefilled or download zip file to send by email. This last
step should be the same for the hardware feedback."*
**Amends:** [ADR-0125](0125-a-problem-report-users-can-download.md) (the
problem report: one download and a summary), [ADR-0126](0126-hardware-reports-from-users.md)
(hardware feedback: its last step, *Send on GitHub*).

## Context

The problem report is one sheet today: an optional line, *Download*, then a
sentence of what was taken out with a GitHub link and an e-mail address.
Nothing shows what the player is doing during the up to a minute it takes,
and the two ways to send are links in a paragraph.

**One limit decides the GitHub route: a link can fill in an issue's text,
not attach a file.** GitHub takes no attachment through the address that
opens its form, and nothing else can reach it without the user's own GitHub
sign-in on the player. The problem report's file (the journal, often several
megabytes) can only be attached by the user, dragging it onto the form. What
a link can carry is text, up to about 7,500 characters.

## Proposal

### 1. The problem report in three steps (phone or computer; the panel says to open Settings there, as now)

1. **What happened** - the text (*What you did, what you expected, what
   happened instead*) and *How often*: *Every time*, *Sometimes*, *Once so
   far*. *Next: prepare the report*.
2. **Preparing** - a checklist the player works down, each line ticked as it
   is done, with what it found:
   - Reading the player's log - *since the last start* or *the kept log, N
     days* (Debug logs, ADR-0103), its size;
   - Reading the updater's log;
   - Reading the versions and the hardware;
   - Reading the settings - *keys, tokens and passwords left out*;
   - Learning what is personal on this player - its network names, its name,
     the phones and Bluetooth devices paired, the music shares, what is
     playing;
   - Taking out personal details - with the counts: *4 addresses, 2 network
     names, 12 track, album or artist names, ...*;
   - Writing the file - its name and size.
   Then *Read what is in it* (the files and their sizes) and *Next: send it*.
   Nothing has left the player at this point.
3. **Send** - the step both features share (§3).

### 2. Hardware feedback keeps its steps (Screen, Sound, Anything else) and ends on the same Send step

### 3. The Send step, the same for both

Two choices, side by side:

- **On GitHub** (needs a GitHub account): opens the issue form filled in.
  - *Hardware feedback*: everything - it fits in the link.
  - *Problem report*: what happened, how often, the version, what was taken
    out, and **the last errors and warnings from the log, cleaned like the
    rest, as much as fits** (see decision 1). The file itself is attached
    on GitHub by dragging it there; the step offers the download beside the
    button and says so.
- **By e-mail**: downloads the file and shows the address with a *Copy*
  button (a mail link may open nothing, ADR-0125). *Problem report*: the
  zip. *Hardware feedback*: see decision 3.

A line under both: *Nothing is sent until you send it. Read the file first:
taking things out by pattern can miss something.*

### 4. What the player keeps

The prepared report stays on the player for **one hour** (decision 4), so
the Send step can offer it more than once without preparing it again, and is
deleted after. Hardware feedback keeps its last one as now (ADR-0126 amended).

## Decided (George, 2026-10-11)

1. **The GitHub route for the problem report**: (a) the issue carries the
   text and the log's last errors inline, the file attached by hand as an
   extra; or (b) the issue carries only the text and asks for the file every
   time.
2. **The checklist's lines** as in §1, or fewer.
3. **Hardware feedback's download**: one readable text file, or a zip like
   the problem report's.
4. **How long a prepared report stays on the player**: one hour, or until the
   sheet closes.

## Not a setting

No ADR-0022 row: both stay actions on the System page.
