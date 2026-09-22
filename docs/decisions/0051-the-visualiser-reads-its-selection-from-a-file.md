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

### 2. The pool is what a skin shows, across the pack's two directories

The driver loads **both** template directories of the pack it is configured
for, keeps each skin's own directory beside it, and swaps `base.path` around
the factory call. `skin_corpus` then filters by kind — `meter.visible` and
`spectrum.visible`, the same derivation `skins.py` makes for the daemon, and
not the directory (ADR-0019 as amended: `templates/` is not "the meter
corpus").

**One pack, not every pack.** The corpus is the pack peppy's own
`base.folder` names — Gelo5's 84, which is the corpus ADR-0015 is written
against and `make skins` validates. The `stock` pack stays installed and
stays out: its spectrum sections are not the ones the spectrum engine is
pointed at, so a stock spectrum skin would draw no spectrum, and that is a
separate piece of work rather than a silent half-feature. `GET /skins` is
narrowed to the same pack, so the picker offers what the renderer can draw.

### 3. The spectrum engine is created whatever the first skin is

It is built once per run and re-pointed per skin (`SpectrumState.follow`),
but until now it was only built **if the starting skin had a spectrum** —
true when the corpus was one spectrum directory, false for a mixed corpus
that starts on a needle. It is now created against the first section the
corpus offers and immediately re-pointed, so a spectrum skin chosen an hour
later has an engine to draw with.

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
- **84 skins instead of 71**, and for the first time the spectrum-bearing
  ones are reachable without editing `config.txt` by hand.
- **The image must ship the new driver.** Until the next build, the device
  carries it by deployment, which is how it was verified.
