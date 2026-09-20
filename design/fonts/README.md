> **In this repository the four files are present** (2026-09-20). They were
> vendored on 2026-09-19 and are listed below only because Claude Design
> cannot emit binary files in an export, so every drop arrives without them.
> **Do not unpack a drop over `design/fonts/`** — copy the drop's files in
> additively, or these four and the two licences are deleted. The panel does
> not read them either way: `ui/src/main.js` imports the faces from npm
> `@fontsource`, and this directory exists so the design package renders
> standalone.

# fonts/

Four files are missing from this package and must be added before the panel is
offline-correct. I cannot produce binary font files.

    NunitoSans-Variable.woff2      Nunito Sans, variable, 300-800
    IBMPlexMono-Regular.woff2      IBM Plex Mono 400
    IBMPlexMono-SemiBold.woff2     IBM Plex Mono 600
    IBMPlexMono-Bold.woff2         IBM Plex Mono 700

Both families are SIL Open Font License and safe to vendor. `../fonts.css`
already declares the faces and points here; dropping the files in is the whole
task.

Until then the CSS falls back to `system-ui` and `Courier New`, which changes
metrics: mono columns lose their alignment and the 38px title wraps
differently. **Do not judge spacing before the real faces are in place** — the
meta tabs measured 42px instead of 44px for exactly this reason.
