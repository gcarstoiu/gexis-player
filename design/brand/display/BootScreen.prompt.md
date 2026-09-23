The boot sequence — an intro that plays **once**, then a pulse that **loops**.

```jsx
<BootScreen lands="s" style={{ width: 1280, height: 800 }} />  {/* the device */}
<BootScreen lands="g" />            {/* gazette — caret on a ruled line */}
<BootScreen lands="e" />            {/* engine room — status leds        */}
<BootScreen lands="i" />            {/* inbox — one unread                */}
<BootScreen lands="s" flourish={null} label={null} />          {/* bare */}
```

**Intro, 2 s, once.** Light crosses the tiles `g → e → i → s` and settles at
46% on the booting property's letter; `gexis` rises, the sub-label and the
flourish fade in. It does not replay — the travel is an opening.

**Pulse, 2 s, for ever.** A lub-dub and a rest. This is what is on screen
for almost all of a real boot, so it is the part worth getting right.

**The travel order never changes.** Tile `g` is always slot 1, `e` slot 2,
`i` slot 3, `s` slot 4. Only which tile *holds* depends on `lands`, via the
`-h` variant of its own slot rule. Do not rebind slots to make a different
letter land — that changes when it lights, and three of the four screens
once shipped travelling in the wrong order exactly that way.

**`size` is the mark, not the screen.** The wordmark comes out about 2.7×
wider than the mark, deliberately: the mark is the smaller thing above the
text. Everything derives from `size`, so the screen scales as one piece.

**Wavefronts launch clear of the tiles** (mark radius is `size × 0.465`).
If you resize the mark without the ring box following, each ring emerges
from behind the tiles and you get four wedges flashing at the corners.

**Why it is cheap.** Every tile is an unlit base with a lit overlay; only
the overlay's opacity animates, so nothing repaints. The indefinite part is
just the 2 s pulse — see the exception declared in
`tokens/patterns-brand.css`. `flourish={null}` removes even that.

**On the device this is not what ships.** The panel's browser is not up
during boot, so the sound sequence ships as a Plymouth PNG sequence: 100
frames at 1280×800, 25 fps, **intro 1–50 played once, pulse 51–100 looped**,
with a pixel-identical wrap. Same two ranges, same timings — if these change,
the frames must be re-rendered.
