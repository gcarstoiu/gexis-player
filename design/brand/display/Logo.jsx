/* Vendored from the brand package (uploads/logo/display/Logo.jsx), pristine
   except for this module boundary: the original's `import React from 'react'`
   and `export function` need a bundler, and this project loads the file
   directly in the browser. The component body below is unchanged. */

/* The gexis mark: four letter tiles on a 2x2 grid rotated 45deg, so the
   diagonal gap between them is the x. g e i s run clockwise from the top.

   `lead` is the mark's one real variant. Unset, every tile is lit — that is
   the master mark. Set to a letter, that tile keeps its colour and the other
   three drop to slate, which is how a single property signs itself.

   Letters are dropped below --logo-letters-min (28px): four colours still
   read at favicon size, four letterforms do not. */

const LETTERS = ['g', 'e', 'i', 's'];

const HUE = {
  g: 'var(--logo-g)',
  e: 'var(--logo-e)',
  i: 'var(--logo-i)',
  s: 'var(--logo-s)'
};

const INK = {
  g: 'var(--logo-ink-g)',
  e: 'var(--logo-ink-e)',
  i: 'var(--logo-ink-i)',
  s: 'var(--logo-ink-s)'
};

function Logo({
  size = 96,
  lead = null,
  wordmark = false,
  sublabel = null,
  mono = null,
  style,
  ...rest
}) {
  /* One tile edge drives the rest. Ratios are fixed in tokens/brand.css:
     the grid is 2 tiles + 1 gap across, and the rotation needs no extra
     room because the wrapper is sized to the rotated bounding box. */
  const tile = size / 2.235;
  const gap = tile * 0.235;
  const radius = tile * 0.265;
  const glyph = tile * 0.53;
  const box = Math.SQRT2 * (tile * 2 + gap);
  const showLetters = size >= 28;

  const tiles = (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `${tile}px ${tile}px`,
        gridTemplateRows: `${tile}px ${tile}px`,
        gap,
        transform: 'rotate(45deg)',
        flexShrink: 0
      }}
    >
      {LETTERS.map((l) => {
        const isLit = mono ? true : lead === null || l === lead;
        const fill = mono || (isLit ? HUE[l] : 'var(--logo-unlit)');
        const ink = mono
          ? 'var(--bg-base)'
          : isLit
            ? INK[l]
            : 'var(--logo-unlit-ink)';
        return (
          <div
            key={l}
            style={{
              borderRadius: radius,
              background: fill,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {showLetters && (
              <span
                style={{
                  transform: 'rotate(-45deg)',
                  fontFamily: 'var(--logo-face)',
                  fontWeight: 'var(--logo-weight)',
                  fontSize: glyph,
                  lineHeight: 1,
                  color: ink
                }}
              >
                {l}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );

  const mark = (
    <div
      style={{
        width: box,
        height: box,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}
    >
      {tiles}
    </div>
  );

  if (!wordmark) {
    return <div style={{ display: 'inline-flex', ...style }} {...rest}>{mark}</div>;
  }

  return (
    <div
      style={{ display: 'inline-flex', alignItems: 'center', gap: size * 0.19, ...style }}
      {...rest}
    >
      {mark}
      <div style={{ display: 'flex', flexDirection: 'column', gap: size * 0.045 }}>
        <span
          style={{
            fontFamily: 'var(--logo-face)',
            fontWeight: 600,
            fontSize: size * 0.4,
            letterSpacing: 'var(--track-tight)',
            lineHeight: 1,
            color: mono || 'var(--ink)'
          }}
        >
          gexis
        </span>
        {sublabel && (
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: Math.max(11, size * 0.115),
              fontWeight: 'var(--w-semibold)',
              letterSpacing: 'var(--track-label)',
              textTransform: 'uppercase',
              color: mono || (lead ? HUE[lead] : 'var(--ink-quiet)')
            }}
          >
            {sublabel}
          </span>
        )}
      </div>
    </div>
  );
}

module.exports = { Logo };
