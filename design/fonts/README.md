# fonts/

All four faces the design was authored against, vendored 2026-09-20.

    NunitoSans-Variable.woff2      Nunito Sans, variable, 300-800
    IBMPlexMono-Regular.woff2      IBM Plex Mono 400
    IBMPlexMono-SemiBold.woff2     IBM Plex Mono 600
    IBMPlexMono-Bold.woff2         IBM Plex Mono 700

Both families are SIL Open Font License and safe to redistribute. `../fonts.css`
declares the faces and points here; nothing further is needed.

The fallback stack behind them is `system-ui` and `Courier New`. It changes
metrics — mono columns lose their alignment, the 38px title wraps differently,
and the meta tabs measure 42px instead of 44px — so if spacing ever looks
wrong, check the faces are loading before changing a value.
