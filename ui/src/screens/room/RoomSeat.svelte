<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Where the microphone goes (ADR-0175; design/source/29, *The drawing*):
  top-down, the two speakers at the top, the seat low in the middle, a
  dashed ring of about 50 cm round the head, and the five positions - the
  one in use lit, the ones done ticked. Moving to a new one, a dashed arrow
  from the head shows the way. The speaker playing is outlined. **Height**
  (George, 2026-11-23, plan C of three mock-ups): each position off ear
  height carries its cm (↑15, ↓15, ↑30), position 5 is a badge lifted off
  the head, and a scale beside the drawing places every position by height.
-->
<script>
  import { HEIGHTS, PLACES } from '../../lib/room.svelte.js';

  //: `active`: the position in use (from 1) or 0; `done`: those measured;
  //: `playing`: 'L', 'R', 'both' or null; `arrow`: draw the way from the head to `active`.
  let { active = 1, done = [], playing = null, arrow = false } = $props();

  const places = $derived(PLACES.map(([x, y], i) => {
    const n = i + 1;
    const h = HEIGHTS[i] ?? 0;
    return { n, x, y, on: n === active, done: done.includes(n) && n !== active, above: n === 5,
      tag: h ? `${h > 0 ? '↑' : '↓'}${Math.abs(h)}` : '', side: n === 5 };
  }));
  //: The scale: its levels top to bottom, and each position on it - two at
  //: one height side by side.
  const LEVELS = [[30, '+30', 26], [15, '+15', 46], [0, 'ear', 66], [-15, '−15', 86]];
  const scale = $derived(places.map((p) => {
    const h = HEIGHTS[p.n - 1] ?? 0;
    const same = places.filter((q) => (HEIGHTS[q.n - 1] ?? 0) === h && q.n < p.n).length;
    return { ...p, top: LEVELS.find(([cm]) => cm === h)?.[2] ?? 66, left: 44 + same * 18 };
  }));
  const way = $derived.by(() => {
    if (!arrow || active < 2) return null;
    const [x1, y1] = PLACES[0];
    const [x2, y2] = PLACES[active - 1];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.hypot(dx, dy);
    // Straight above the head (5): its badge sits on it, no way to draw.
    if (len < 40) return null;
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
  <div class="row">
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
      <span class="place" class:is-on={p.on} class:is-done={p.done} class:place--above={p.above}
            style="left:{(p.x / 340) * 100}%;top:{(p.y / 196) * 100}%">{p.done ? '✓' : p.n}</span>
      {#if p.tag}
        <span class="tag" class:tag--side={p.side} class:is-on={p.on}
              style="left:{((p.side ? p.x - 13 : p.x) / 340) * 100}%;top:{((p.side ? p.y - 9 : p.y + 31) / 196) * 100}%">{p.tag}</span>
      {/if}
    {/each}
  </div>
  <div class="gauge" aria-hidden="true">
    <span class="gauge__cap">Height</span>
    <span class="gauge__rail"></span>
    {#each LEVELS as [cm, label, top] (cm)}
      <span class="gauge__lab" style="top:{top}%">{label}</span>
      <span class="gauge__tick" style="top:{top}%"></span>
    {/each}
    {#each scale as d (d.n)}
      <span class="dot" class:is-on={d.on} class:is-done={d.done} style="top:{d.top}%;left:{d.left}px">{d.n}</span>
    {/each}
  </div>
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
  .row {
    display: flex;
    gap: 4px;
  }
  .box {
    position: relative;
    flex: 1;
    min-width: 0;
    aspect-ratio: 340 / 196;
    /* The places scale with the drawing, so a narrow phone keeps them apart. */
    container-type: inline-size;
  }
  .tag {
    position: absolute;
    transform: translate(-50%, -50%);
    font-family: var(--font-mono);
    font-size: clamp(8px, 3.2cqw, 11px);
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .tag--side {
    transform: translate(-100%, -50%);
  }
  .tag.is-on {
    color: var(--accent-lms);
  }
  .gauge {
    position: relative;
    flex: 0 0 66px;
  }
  .gauge__cap {
    position: absolute;
    top: 3%;
    left: 0;
    right: 0;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .gauge__rail {
    position: absolute;
    left: 27px;
    top: 18%;
    bottom: 6%;
    width: 2px;
    border-radius: var(--r-pill);
    background: var(--c-ink-22);
  }
  .gauge__lab {
    position: absolute;
    right: calc(100% - 22px);
    transform: translateY(-50%);
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-quiet);
  }
  .gauge__tick {
    position: absolute;
    left: 24px;
    width: 8px;
    height: 1px;
    background: var(--c-ink-30);
  }
  .dot {
    position: absolute;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 800;
    transform: translate(-50%, -50%);
    background: var(--c-dark-1b2a34);
    border: 1.5px solid var(--c-ink-30);
    color: var(--ink-body);
  }
  .dot.is-done {
    background: var(--c-lms-20);
    border-color: var(--c-lms-60);
    color: var(--accent-lms);
  }
  .dot.is-on {
    width: 20px;
    height: 20px;
    background: var(--accent-lms);
    border-color: var(--accent-lms);
    color: var(--ink-on-accent);
    box-shadow: 0 0 0 4px var(--c-lms-20);
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
    width: clamp(16px, 7.2cqw, 26px);
    height: clamp(16px, 7.2cqw, 26px);
    border-radius: 50%;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: clamp(10px, 3.9cqw, 14px);
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
  .place--above {
    width: clamp(13px, 5.8cqw, 21px);
    height: clamp(13px, 5.8cqw, 21px);
    font-size: clamp(8px, 3.2cqw, 11px);
  }
  .place.is-on {
    width: clamp(20px, 8.8cqw, 32px);
    height: clamp(20px, 8.8cqw, 32px);
    background: var(--accent-lms);
    border-color: var(--accent-lms);
    color: var(--ink-on-accent);
    box-shadow: 0 0 0 clamp(3px, 1.6cqw, 6px) var(--c-lms-20);
  }
  .place--above.is-on {
    width: clamp(16px, 7cqw, 25px);
    height: clamp(16px, 7cqw, 25px);
    box-shadow: 0 0 0 clamp(2px, 1.2cqw, 4px) var(--c-lms-20);
  }
</style>
