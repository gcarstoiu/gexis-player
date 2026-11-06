<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Where the microphone goes (ADR-0175; design/source/29, *The drawing*):
  top-down, the two speakers at the top, the seat low in the middle, a
  dashed ring of about 50 cm round the head, and the three positions - the
  one in use lit, the ones done ticked. Moving to a new one, a dashed arrow
  from the head shows the way. The speaker playing is outlined.
-->
<script>
  import { PLACES } from '../../lib/room.svelte.js';

  //: `active`: the position in use (from 1) or 0; `done`: those measured;
  //: `playing`: 'L', 'R', 'both' or null; `arrow`: draw the way from the head to `active`.
  let { active = 1, done = [], playing = null, arrow = false } = $props();

  const places = $derived(PLACES.map(([x, y], i) => {
    const n = i + 1;
    return { n, x, y, on: n === active, done: done.includes(n) && n !== active };
  }));
  const way = $derived.by(() => {
    if (!arrow || active < 2) return null;
    const [x1, y1] = PLACES[0];
    const [x2, y2] = PLACES[active - 1];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.hypot(dx, dy);
    const ux = dx / len;
    const uy = dy / len;
    const sx = x1 + ux * 13;
    const sy = y1 + uy * 13;
    const ex = x2 - ux * 19;
    const ey = y2 - uy * 19;
    return {
      line: `M${sx},${sy}L${ex},${ey}`,
      head: `M${ex + ux * 6},${ey + uy * 6}L${ex - uy * 5},${ey + ux * 5}L${ex + uy * 5},${ey - ux * 5}Z`,
    };
  });
</script>

<div class="card">
  <div class="box" role="img" aria-label={`Where the microphone goes: position ${active || 1} of ${PLACES.length} around your seat`}>
    <div class="spk spk--l" class:is-playing={playing === 'L' || playing === 'both'}><span></span></div>
    <div class="spk spk--r" class:is-playing={playing === 'R' || playing === 'both'}><span></span></div>
    <span class="spklab spklab--l" class:is-playing={playing === 'L' || playing === 'both'}>L</span>
    <span class="spklab spklab--r" class:is-playing={playing === 'R' || playing === 'both'}>R</span>
    <div class="seat"><span>Your seat</span></div>
    <div class="ring"></div>
    {#if way}
      <svg viewBox="0 0 340 196" class="way" aria-hidden="true">
        <path d={way.line} class="way__line" />
        <path d={way.head} class="way__head" />
      </svg>
    {/if}
    {#each places as p (p.n)}
      <span class="place" class:is-on={p.on} class:is-done={p.done}
            style="left:{(p.x / 340) * 100}%;top:{(p.y / 196) * 100}%">{p.done ? '✓' : p.n}</span>
    {/each}
  </div>
</div>

<style>
  .card {
    flex-shrink: 0;
    border-radius: var(--r-18);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    padding: 12px;
  }
  .box {
    position: relative;
    width: 100%;
    aspect-ratio: 340 / 196;
  }
  .spk {
    position: absolute;
    top: 5.1%;
    width: 8.2%;
    height: 18.4%;
    border-radius: var(--r-5);
    box-sizing: border-box;
    background: var(--ink-fill);
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1.5px solid var(--c-ink-30);
  }
  .spk span {
    width: 52%;
    aspect-ratio: 1;
    border-radius: 50%;
    border: 1.5px solid var(--c-ink-30);
    display: block;
  }
  .spk--l,
  .spklab--l {
    left: 11.2%;
  }
  .spk--r,
  .spklab--r {
    left: 80.6%;
  }
  .spk.is-playing {
    border-color: var(--accent-lms);
  }
  .spklab {
    position: absolute;
    width: 8.2%;
    top: 25.5%;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    color: var(--ink-quiet);
  }
  .spklab.is-playing {
    color: var(--accent-lms);
  }
  .seat {
    position: absolute;
    left: 26%;
    top: 52%;
    width: 48%;
    height: 44%;
    border-radius: var(--r-18);
    background: var(--c-ink-05);
    border: 1px solid var(--c-ink-12);
    box-sizing: border-box;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 4px;
  }
  .seat span {
    font-size: 11px;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .ring {
    position: absolute;
    left: 34.7%;
    top: 23%;
    width: 30.6%;
    aspect-ratio: 1;
    border-radius: 50%;
    border: 1px dashed var(--c-ink-22);
    box-sizing: border-box;
  }
  .way {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
    pointer-events: none;
  }
  .way__line {
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 2;
    stroke-dasharray: 4 4;
    stroke-linecap: round;
  }
  .way__head {
    fill: var(--accent-lms);
  }
  .place {
    position: absolute;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 800;
    transform: translate(-50%, -50%);
    background: var(--c-dark-1b2a34);
    border: 2px solid var(--c-ink-30);
    color: var(--ink-body);
  }
  .place.is-done {
    background: var(--c-lms-20);
    border-color: var(--c-lms-60);
    color: var(--accent-lms);
  }
  .place.is-on {
    width: 30px;
    height: 30px;
    background: var(--accent-lms);
    border-color: var(--accent-lms);
    color: var(--ink-on-accent);
    box-shadow: 0 0 0 6px var(--c-lms-20);
  }
</style>
