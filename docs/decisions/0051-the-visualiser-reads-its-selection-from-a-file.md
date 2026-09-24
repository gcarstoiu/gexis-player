# ADR-0051 — The visualiser reads its skin selection from a file

**Status:** Accepted
**Date:** 2026-09-22
**Raised by:** Phase 9 subphase 9h. Three settings describe what the meter
draws — `skin_corpus`, `skin_rotate`, and `skin`, which the 2026-09-22
design adds as a picker — and **none of them reaches the renderer**. Two of
them are not even writable today: the daemon refuses a write to an unwired
row (ADR-0035), and nothing reads them.
**Amends:** [ADR-0019](0019-peppy-screen-lifecycle.md) and
[ADR-0026](0026-peppymeter-native-process-integration.md) (what the driver
reads), [ADR-0050](0050-skin-previews-are-the-skins-own-picture.md) (which
skins `/skins` lists)

## Context

The renderer is a separate process with no command channel: the daemon can
raise and hide its window with `wlrctl` and nothing else (ADR-0026). It
already reads one file the daemon writes — `/run/gexis/nowplaying.json`,
stat-ed and re-read about ten times a second inside the frame hook, which is
how a skin change follows a track change.

Two measurements decide the rest of this record, both taken on the device on
2026-09-22.

**1. A corpus choice against one directory is empty.** The engine loads the
skins of a single directory — `[current] base.folder` + `meter.folder`, today
`/opt/gexis-peppy/skins/gelo5/templates/1280x800`. What each of the pack's
two directories holds, by what the skins *declare* rather than where they
live:

| directory | skins | meters | spectrum | both |
|---|---|---|---|---|
| `gelo5/templates` | 71 | **71** | 0 | 0 |
| `gelo5/templates_spectrum` | 13 | 0 | **3** | **10** |

So "Spectrum" and "VU meters + spectrum" — two of the four words George asked
for (ADR-0019 as amended) — would offer **nothing at all** while the engine
reads one directory. The corpus has to span both.

**2. It can.** `Meter.load_image` builds every path from
`meter_config[base.path]` and `meter_config[screen.info][meter.folder]` **at
build time**, so pointing `base.path` at another directory around the factory
call is enough — the same trick the driver already uses for `meter`, which it
swaps around `MeterFactory` and puts back. A headless probe built all **13 of
13** skins of `templates_spectrum` that way, against the running config, with
the 71-skin directory still configured.

## Decision

### 1. The selection is a file the driver polls

`/run/gexis/visualisation.json`, written by the daemon whenever one of the
three settings changes and once at start:

    {"corpus": "VU meters", "skin": "06G5_McIntosh", "rotate": true}

The driver re-reads it on the same poll as the metadata, applies a change at
once, and needs no restart. **The same shape as `nowplaying.json`** — one
writer, one reader, a stat and a small read — rather than a socket, a signal
or a restart, none of which the two processes have between them today.

A missing or unreadable file is not an error: the driver keeps what it has,
which is the corpus it loaded and rotation on. The settings database is the
record; this file is a projection of it.

### 2. The pool is what a skin shows, across every pack

The driver loads **all four** template directories — two per pack — keeps
each skin's own directory beside it, and swaps `base.path` around the
factory call. `skin_corpus` then filters by kind — `meter.visible` and
`spectrum.visible`, the same derivation `skins.py` makes for the daemon, and
not the directory (ADR-0019 as amended: `templates/` is not "the meter
corpus"). **99 skins, all 99 offered** (two were excluded on 2026-09-23 and
put back the same day, once the fault turned out to be a wrong filename the
image now corrects — [Finding 050](../findings/050-two-skins-name-the-wrong-background.md))**: 77 meters, 9 spectrum, 13 both**, which is the count
this device has always had.

The configured pack is read first, so a device still starts on the skin it
has always started on, and a name two packs share resolves to the first.

> **Amended 2026-09-22, hours after this record was written.** It said *one*
> pack — Gelo5's 84 — because the stock pack's spectrum sections *"are not
> the ones the spectrum engine is pointed at"*. That described a hardcoded
> path, not the device: the pointing is one line in the driver, and the
> right answer was to point it at the pack the skin belongs to rather than
> to drop fifteen skins. George: *"there were 99 skins in total — why are
> you telling me now that there are only 84?"*
>
> **The spectrum engine follows the skin's pack**, in the file it reads and
> in the parser that already read it: `select_spectrum_section` rewrites
> `base.folder`, and `follow` sets `config[BASE_FOLDER]` too, because
> `get_spectrum_configs()` answers from what the parser holds. Setting only
> the file left the stock pack's `s.3` "missing from the corpus".

### 3. The spectrum engine is created whatever the first skin is — and cannot take the screen

It is built once per run and re-pointed per skin (`SpectrumState.follow`),
but until now it was only built **if the starting skin had a spectrum** —
true when the corpus was one spectrum directory, false for a mixed corpus
that starts on a needle. It is now created against the first section the
corpus offers and immediately re-pointed, so a spectrum skin chosen an hour
later has an engine to draw with.

**Three rules keep it from taking the screen with it**, all three written
after it did (George, 2026-09-22: *"tapping on the button in now playing
displays a black screen that I cannot exit by tapping"*).

- **Building it is not fatal.** It is the only code that writes to the
  spectrum engine's config, and that file shipped root-owned while the unit
  runs as `pi`: the `PermissionError` killed `main()` *after* the display
  existed. pygame's threads then kept the process alive, so the panel was
  left behind a black surface that owned every touch. A device with no
  spectrum engine is a device with meters.
- **The config is installed writable by the service user.** The driver
  rewrites it by design — the engine has no other way to be told which
  section to draw — so the image installs it `-o 1000 -g 1000`.
- **A skin that would draw nothing is not in the pool.** Without an engine,
  a spectrum-only skin honours `meter.visible = False` and paints nothing at
  all. Those skins leave the pool rather than reach the glass.

**And the engine's own random mode is off.** `config.txt` says
`meter = random`, which makes `VUMeter.get_meter()` choose a skin at
`start()` and overwrite `meter_config[METER]` on the way past. The driver
owns the choice (§1), so this is now cleared on the instance: before it was,
the first frame drew a skin nobody had asked for and the picker's answer
only took hold at the next track change — George chose McIntosh and got an
Electrocompaniet.

### 4. `skin` is a row with a picker

`type: choice`, `picker: true`, `optionsFrom: "skin_corpus"`,
`onlyWhen: ["skin_rotate", false]` — the design's own shape
(`design/settings.md`). The stored value is the **full section name**
(`06G5_McIntosh`); only the display splits off the `NNG5_` ordinal.

**Narrowing the corpus rewrites the value.** If the skin in use is not in the
new corpus, the first skin the new corpus offers is stored — a write, not a
silent substitution, so what the panel shows is what the renderer draws.

### 5. What is not decided here

**Rotation still ignores the kind boundary within a pool**: with `Random` and
rotation on, a needle can be followed by a spectrum, which is what "random"
means. **Nothing renders a preview**: ADR-0050 stands, a preview is the
skin's own `screen.bgr`.

## Consequences

- **Three rows become writable**, because something now reads them. `skin` is
  new and goes to ADR-0022's inventory as `[N]`, pending George.
- **The driver gains a second file to read** and a per-skin directory. Its
  failure mode is visible: a skin that cannot be built raises where the log
  can be read, and the run loop keeps the skin it has.
- **99 skins instead of 71**, and for the first time the spectrum-bearing
  ones draw their spectrum without editing `config.txt` by hand.
- **The image must ship the new driver** *and* the spectrum config's new
  ownership. Until the next build, the device carries both by deployment.
- **Verification means looking at the screen.** Every claim in this record
  about what is drawn is a `grim` capture of the panel, not a line in the
  driver's log: the log said `skin -> 103G5_Marschal Spectrum` while the
  screen was black (`docs/LESSONS.md` case 15).
