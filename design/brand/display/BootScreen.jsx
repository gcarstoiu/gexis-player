import React from 'react';

/* The boot sequence: an intro that plays ONCE, then a pulse that loops until
   something else takes the screen.

     intro  2 s   light crosses the tiles g → e → i → s and settles on the
                  booting property's letter; the lockup resolves
     pulse  2 s   a lub-dub heartbeat and a rest, repeating

   Every tile is two stacked layers — an unlit base and a lit overlay — and
   only the overlay's opacity animates. Nothing repaints.

   PROPORTION. `size` is the MARK's width, and the wordmark is deliberately
   larger than it: the mark reads as the smaller thing above the text, not a
   badge the text hangs off. All type derives from `size` so the screen
   scales as one piece.

   On the device this ships as a Plymouth PNG sequence, not as this
   component — the panel's browser is not up during boot. Same two ranges,
   same timings. Keep them in step. */

const LETTERS = ['g', 'e', 'i', 's'];
const SLOT = { g: 1, e: 2, i: 3, s: 4 };   // tile → time slot. NEVER reorder.
const HUE = { g:'var(--logo-g)', e:'var(--logo-e)', i:'var(--logo-i)', s:'var(--logo-s)' };
const INK = { g:'var(--logo-ink-g)', e:'var(--logo-ink-e)', i:'var(--logo-ink-i)', s:'var(--logo-ink-s)' };
const RGB = { g:'126,214,188', e:'224,167,88', i:'159,180,232', s:'242,164,143' };
const NAME = { g:'gazette', e:'engine room', i:'inbox', s:'sound' };

export function BootScreen({
  lands = 's',
  label,
  size = 114,
  flourish,
  intro = 2,
  pulse = 2,
  style,
  ...rest
}) {
  const tile   = size * 0.316;
  const gap    = size * 0.079;
  const radius = size * 0.088;
  const glyph  = size * 0.167;
  const wordPx = size * 1.20;          // ≈ 2.7 × the mark's width
  const subPx  = Math.max(11, size * 0.23);

  const introClock = `${intro}s linear 1 forwards`;
  const pulseClock = `${pulse}s linear ${intro}s infinite`;

  const accent = HUE[lands];
  const rgb = RGB[lands];
  const sub = label === undefined ? NAME[lands] : label;
  const fx = flourish === undefined ? lands : flourish;

  /* Wavefronts must launch CLEAR of the tiles, or each ring emerges from
     behind the mark and the visible remnant is four wedges flashing at the
     tile corners. The mark's circumscribed radius is size × 0.465. */
  const ringBox = size * 1.74;

  const tiles = (
    <div
      style={{
        position: 'relative', display: 'grid',
        gridTemplateColumns: `${tile}px ${tile}px`,
        gridTemplateRows: `${tile}px ${tile}px`,
        gap, transform: 'rotate(45deg)'
      }}
    >
      {LETTERS.map((l) => (
        <div
          key={l}
          style={{
            position: 'relative', borderRadius: radius,
            background: 'var(--logo-unlit)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}
        >
          <span style={{
            transform: 'rotate(-45deg)', fontFamily: 'var(--logo-face)',
            fontWeight: 'var(--logo-weight)', fontSize: glyph, lineHeight: 1,
            color: 'var(--logo-unlit-ink)'
          }}>{l}</span>
          <div
            style={{
              position: 'absolute', inset: 0, borderRadius: radius,
              background: HUE[l], display: 'flex', alignItems: 'center',
              justifyContent: 'center', opacity: 0,
              /* slot rule; the landing tile holds instead of fading */
              animation: `iv-${SLOT[l]}${l === lands ? 'h' : ''} ${introClock}`
            }}
          >
            <span style={{
              transform: 'rotate(-45deg)', fontFamily: 'var(--logo-face)',
              fontWeight: 'var(--logo-weight)', fontSize: glyph, lineHeight: 1,
              color: INK[l]
            }}>{l}</span>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div
      style={{
        position: 'relative', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: size * 0.26,
        background: 'var(--bg-base)', overflow: 'hidden', boxSizing: 'border-box',
        paddingBottom: fx === 'g' || fx === 'e' ? size * 0.38 : 0,
        ...style
      }}
      {...rest}
    >
      {fx === 's' && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', pointerEvents: 'none', opacity: 0,
          animation: `iv-fx ${introClock}`
        }}>
          <div style={{ position: 'relative', width: ringBox, height: ringBox }}>
            <div style={{
              position: 'absolute', inset: 0, borderRadius: 'var(--r-circle)',
              background: `radial-gradient(circle, rgba(${rgb},.17), transparent 68%)`,
              animation: `pl-halo ${pulseClock}`
            }} />
            <div style={{
              position: 'absolute', inset: 0, borderRadius: 'var(--r-circle)',
              border: `2px solid ${accent}`, opacity: 0,
              animation: `pl-w1 ${pulseClock}`
            }} />
            <div style={{
              position: 'absolute', inset: 0, borderRadius: 'var(--r-circle)',
              border: `2px solid ${accent}`, opacity: 0,
              animation: `pl-w2 ${pulseClock}`
            }} />
          </div>
        </div>
      )}

      {fx === 'i' && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', pointerEvents: 'none', opacity: 0,
          animation: `iv-fx ${introClock}`
        }}>
          <div style={{
            width: size * 1.55, height: size * 1.55, borderRadius: 'var(--r-circle)',
            background: `radial-gradient(circle, rgba(${rgb},.17), transparent 68%)`,
            animation: `pl-halo ${pulseClock}`
          }} />
        </div>
      )}

      <div style={{ position: 'relative' }}>
        {tiles}
        {fx === 'i' && (
          <div style={{
            position: 'absolute', right: -size * 0.115, top: -size * 0.115,
            opacity: 0, animation: `iv-fx ${introClock}`
          }}>
            <div style={{
              width: size * 0.175, height: size * 0.175,
              borderRadius: 'var(--r-circle)', background: accent,
              color: INK[lands], display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              fontFamily: 'var(--logo-face)', fontWeight: 'var(--logo-weight)',
              fontSize: size * 0.097,
              animation: `pl-badge ${pulseClock}`
            }}>1</div>
          </div>
        )}
      </div>

      <div style={{
        position: 'relative', display: 'flex', flexDirection: 'column',
        alignItems: 'center', gap: size * 0.1
      }}>
        <span style={{
          fontFamily: 'var(--logo-face)', fontWeight: 'var(--word-weight)',
          fontSize: wordPx, letterSpacing: 'var(--track-tight)',
          lineHeight: 1, color: 'var(--ink)', opacity: 0,
          animation: `iv-word ${introClock}`
        }}>gexis</span>
        {sub && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: subPx,
            fontWeight: 'var(--w-semibold)', letterSpacing: 'var(--track-label)',
            textTransform: 'uppercase', color: accent, opacity: 0,
            animation: `iv-sub ${introClock}`
          }}>{sub}</span>
        )}
      </div>

      {fx === 'g' && (
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0,
          animation: `iv-fx ${introClock}`
        }}>
          <div style={{
            position: 'absolute', bottom: size * 0.21, left: '50%',
            transform: 'translateX(-50%)', display: 'flex',
            alignItems: 'center', gap: 7
          }}>
            <div style={{ width: size * 0.84, height: 1, background: `rgba(${rgb},.35)` }} />
            <div style={{
              width: 2, height: size * 0.15, background: accent,
              animation: `pl-caret 1s steps(1,end) ${intro}s infinite`
            }} />
          </div>
        </div>
      )}

      {fx === 'e' && (
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0,
          animation: `iv-fx ${introClock}`
        }}>
          <div style={{
            position: 'absolute', bottom: size * 0.23, left: '50%',
            transform: 'translateX(-50%)', display: 'flex', gap: 10
          }}>
            {[1, 2, 3].map((n) => (
              <div key={n} style={{
                width: 8, height: 8, borderRadius: 'var(--r-circle)',
                background: accent,
                animation: `pl-led${n} 1.5s linear ${intro}s infinite`
              }} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
