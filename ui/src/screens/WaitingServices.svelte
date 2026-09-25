<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The library root's footer while no renderer is connected (design/screens.md
  §3): a pulsing mark for each service waiting to be used. Ported from
  source/Now Playing.dc.html. A service the daemon reports unavailable is not
  drawn - the design only draws ones that are waiting.
-->
<script>
  import SourceMark from '../lib/SourceMark.svelte';
  import { sources } from '../lib/state.js';

  // **ADR-0079: `full` promotes this from a footer to the whole screen.** With
  // LMS off there is no library for it to sit under, and "nothing is playing
  // and here is what could be" becomes the entire message. Same marks, same
  // ring delays, same order - scaled, not stretched (George: *"not the entire
  // height and width of the screen"*), so the cluster grows and the screen
  // keeps its air.
  let { availability = {}, full = false } = $props();

  // Order, colours, labels, sizes and ring delays are the design's.
  //
  // The marks are 38/38/41, not the 24/24/26 shipped until 2026-09-20: the
  // design calls them `waitIcon…Lg` and sizes them
  // `sourceIcon('lms', '#7ed6bc', 38, 1)`, `('spotify', '#e9eef2', 38, 0.72)`
  // and `('bluetooth', '#e9eef2', 41, 0.72)`. Bluetooth is the odd one
  // because its glyph is taller than it is wide, so matching it by height
  // would leave it visibly smaller than the other two.
  //
  // **ADR-0086: the name and the status line come from the manifest**, the
  // sizes and ring delays stay here. The split is what each thing belongs to:
  // a plugin knows what it is called and what it is waiting for; the design
  // knows how big a mark is drawn and when a ring pulses.
  const DRAWN = {
    lms: { size: 38, lead: true, delays: [0, 1400] },
    spotify: { size: 38, lead: false, delays: [900, 2300] },
    bluetooth: { size: 41, lead: false, delays: [1800, 400] },
  };
  //: A source the design has no drawing values for - any plugin - gets the
  //: middle of the three rather than nothing.
  const GENERIC = { size: 38, lead: false, delays: [600, 1900] };
  const shown = $derived(
    Object.values($sources)
      .filter((s) => s.kind === 'renderer' && availability[s.id])
      .map((s) => ({ ...(DRAWN[s.id] ?? GENERIC), ...s })),
  );
  // The mark is an SVG sized by a prop, not by CSS, so it scales with the
  // disc rather than sitting small inside a bigger circle. 1.8x, the same
  // factor the metrics below use, rounded to whole pixels - and Bluetooth
  // stays the odd one for the reason above.
  const FULL = 1.8;
  const markSize = $derived((s) => (full ? Math.round(s.size * FULL) : s.size));
</script>

<div class="waiting" class:is-full={full}>
  <div class="row">
    {#each shown as s (s.id)}
      <div class="service" class:is-lead={s.lead}>
        <div class="rings">
          {#each s.delays as delay}
            <div class="ring" style:animation-delay={`${delay}ms`}></div>
          {/each}
          <div class="disc">
            <SourceMark
              source={s.id}
              mark={s.mark}
              size={markSize(s)}
              color={s.lead ? 'var(--accent-lms)' : 'var(--ink)'}
              opacity={s.lead ? 1 : 0.72}
            />
          </div>
        </div>
        <div class="label">
          <div class="name">{s.name}</div>
          <div class="status">{s.status}</div>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .waiting {
    /* Every size below is one of these, so `.is-full` re-states the six
       numbers rather than the fifteen rules that use them. */
    --wait-ring: 100px;
    --wait-disc: 90px;
    --wait-col: 172px;
    --wait-gap: 30px;
    --wait-name: 16px;
    --wait-stack: 13px;
    position: relative;
    height: 186px;
    flex-shrink: 0;
    border-top: 1px solid rgba(159, 180, 232, 0.24);
    background: rgba(20, 31, 40, 0.78);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 40px;
    box-sizing: border-box;
  }
  /* 1.8x the footer's cluster on a 1280x800 panel: two services come to
     680px of the width and about 300px of the height, centred, which reads as
     a screen about waiting rather than a bar that was pulled out of shape.
     No border and no plate - there is nothing above it to be divided from. */
  .waiting.is-full {
    --wait-ring: 180px;
    --wait-disc: 162px;
    --wait-col: 310px;
    --wait-gap: 60px;
    --wait-name: 27px;
    --wait-stack: 24px;
    height: 100%;
    border-top: 0;
    background: transparent;
    padding: 0 48px;
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--wait-gap);
  }
  .service {
    width: var(--wait-col);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--wait-stack);
  }
  /* 100px rings around a 90px disc, per the design's notice footer. The
     whole cluster shipped undersized - 72px rings around a 58px disc - which
     is what made the marks inside look small (George, 2026-09-20). */
  .rings {
    position: relative;
    width: var(--wait-ring);
    height: var(--wait-ring);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .ring {
    position: absolute;
    width: var(--wait-ring);
    height: var(--wait-ring);
    border-radius: 50%;
    border: 2px solid rgba(233, 238, 242, 0.6);
    animation: ring 2800ms ease-out infinite;
    box-sizing: border-box;
  }
  .is-lead .ring {
    border-color: var(--accent-lms);
  }
  @keyframes ring {
    0% { transform: scale(0.82); opacity: 0.55; }
    100% { transform: scale(1.75); opacity: 0; }
  }
  .disc {
    width: var(--wait-disc);
    height: var(--wait-disc);
    border-radius: 50%;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.16);
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
  }
  .is-lead .disc {
    background: rgba(126, 214, 188, 0.14);
    border-color: rgba(126, 214, 188, 0.4);
  }
  .label {
    text-align: center;
  }
  .name {
    font-size: var(--wait-name);
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
  }
  .status {
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.16em;
  }
  .is-full .status {
    font-size: 15px;
    margin-top: 9px;
    text-transform: uppercase;
    color: var(--ink-quiet);
    margin-top: 4px;
    white-space: nowrap;
  }
  .is-lead .status {
    color: var(--accent-lms);
  }
</style>
