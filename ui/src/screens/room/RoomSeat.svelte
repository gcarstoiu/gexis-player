<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Where the microphone goes (ADR-0175; ADR-0187 D10, George 2026-11-25:
  F of four mock-ups, *one move at a time*). Two views of the seat: from
  above - the speakers turned in, the seat, the head, the five positions,
  those done ticked - where the stand moves across the floor along a ruler
  in 10 cm steps; and from the side, where its height is set against a cm
  scale. Moving to a position the two play in turn (C12), each caption lit
  while its move plays; elsewhere, or with the phone set to reduce motion,
  the stand stands where it goes. The speaker playing is outlined.
-->
<script>
  import { POSITION_CM, SEAT_STEPS } from '../../lib/room.svelte.js';

  //: `active`: the position in use (from 1); `done`: those measured;
  //: `playing`: 'L', 'R', 'both' or null; `moving`: play the two moves.
  let { active = 1, done = [], playing = null, moving = false } = $props();

  //: The drawing's scale: 1.6 px a cm from above, 2 from the side; the head
  //: at (170, 148) from above, the ear at 92 from the side.
  const K = 1.6;
  const HX = 170;
  const HY = 148;
  const EAR = 92;
  const r1 = (v) => Math.round(v * 10) / 10;
  const still = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const animate = $derived(moving && !still);

  const at = (k) => (k === 5 ? [HX + 14, HY - 14] : [HX + K * POSITION_CM[k][0], HY - K * POSITION_CM[k][1]]);
  const marks = $derived([1, 2, 3, 4, 5].filter((k) => k !== active).map((k) => {
    const [x, y] = at(k);
    const ticked = done.includes(k);
    return { k, x: r1(x), y: r1(y), ticked,
      tick: ticked ? `M${r1(x - 3)} ${r1(y)}L${r1(x - 0.8)} ${r1(y + 2.4)}L${r1(x + 3.5)} ${r1(y - 2.8)}` : '' };
  }));
  const move = $derived.by(() => {
    const [x, y, z] = POSITION_CM[active] ?? [0, 0, 0];
    const tx = K * x;
    const ty = -K * y;
    const cm = Math.hypot(x, y);
    let trail = '';
    let ticks = '';
    let label = null;
    if (cm) {
      const ux = tx / (K * cm);
      const uy = ty / (K * cm);
      trail = `M${HX} ${HY}L${r1(HX + tx)} ${r1(HY + ty)}`;
      for (let d = 10; d < cm; d += 10) {
        const px = HX + ux * K * d;
        const py = HY + uy * K * d;
        ticks += `M${r1(px - uy * 3.5)} ${r1(py + ux * 3.5)}L${r1(px + uy * 3.5)} ${r1(py - ux * 3.5)}`;
      }
      label = y ? { x: HX + 10, y: r1(HY + ty / 2), a: 'start', t: `${cm} cm` }
        // Under the ruler, not over it as drawn: there it met position 5's mark.
        : { x: r1(HX + tx / 2), y: HY + 13, a: 'middle', t: `${cm} cm` };
    }
    return { tx: r1(tx), ty: r1(ty), dz: -2 * z, trail, ticks, label };
  });
  const steps = $derived(SEAT_STEPS[active] ?? SEAT_STEPS[1]);
  const clip = `seat-stand-${Math.random().toString(36).slice(2, 8)}`;
</script>

<div class="card">
  <svg viewBox="0 0 340 196" class="view" role="img" aria-label={`From above: ${steps[0]}`}>
    <text x="12" y="16" class="cap">{steps[0]}{#if animate}<animate attributeName="opacity" values="1;1;0.4;0.4" keyTimes="0;0.5;0.52;1" dur="5s" repeatCount="indefinite" />{/if}</text>
    <text x="328" y="16" text-anchor="end" class="view__lab">FROM ABOVE</text>
    <g transform="rotate(-47 64 50)" class="spk" class:is-playing={playing === 'L' || playing === 'both'}>
      <rect x="52" y="42" width="24" height="16" rx="3" />
      <path d="M54 58H74" />
    </g>
    <g transform="rotate(47 276 50)" class="spk" class:is-playing={playing === 'R' || playing === 'both'}>
      <rect x="264" y="42" width="24" height="16" rx="3" />
      <path d="M266 58H286" />
    </g>
    <text x="38" y="76" text-anchor="middle" class="spklab" class:is-playing={playing === 'L' || playing === 'both'}>L</text>
    <text x="302" y="76" text-anchor="middle" class="spklab" class:is-playing={playing === 'R' || playing === 'both'}>R</text>
    <path d="M72 57L160.5 139.2M268 57L179.5 139.2" class="aim" />
    <rect x="96" y="122" width="148" height="68" rx="14" class="seat" />
    <path d="M102 174H238" class="seat__back" />
    <text x="170" y="185" text-anchor="middle" class="seat__lab">Your seat</text>
    <circle cx="170" cy="148" r="13" class="head" />
    <path d="M165 133L170 128L175 133" class="head__nose" />
    {#each marks as m (m.k)}
      <circle cx={m.x} cy={m.y} r="7.5" class="mark" class:is-done={m.ticked} />
      {#if m.ticked}
        <path d={m.tick} class="mark__tick" />
      {:else}
        <text x={m.x} y={m.y} text-anchor="middle" dominant-baseline="central" class="mark__n">{m.k}</text>
      {/if}
    {/each}
    {#if move.trail}
      <path d={move.trail} class="trail" />
      <path d={move.ticks} class="trail__ticks" />
      <text x={move.label.x} y={move.label.y} text-anchor={move.label.a} dominant-baseline="central" class="trail__lab">{move.label.t}</text>
    {/if}
    {#key `${active}-${animate}`}
      <g transform={animate ? undefined : `translate(${move.tx} ${move.ty})`}>
        {#if animate}
          <animateTransform attributeName="transform" type="translate" values={`0 0;0 0;${move.tx} ${move.ty};${move.tx} ${move.ty}`} keyTimes="0;0.12;0.4;1" dur="5s" repeatCount="indefinite" />
        {/if}
        <circle cx="170" cy="148" r="18" class="mic__halo" />
        <circle cx="170" cy="148" r="12" class="mic" />
        <text x="170" y="148" text-anchor="middle" dominant-baseline="central" class="mic__n">{active}</text>
      </g>
    {/key}
  </svg>
  <div class="rule"></div>
  <svg viewBox="0 0 340 176" class="view" role="img" aria-label={`From the side: ${steps[1]}`}>
    <defs>
      <clipPath id={clip}><rect x="150" y="0" width="40" height="148" /></clipPath>
    </defs>
    <text x="12" y="16" class="cap">{steps[1]}{#if animate}<animate attributeName="opacity" values="0.4;0.4;1;1" keyTimes="0;0.5;0.52;1" dur="5s" repeatCount="indefinite" />{/if}</text>
    <text x="328" y="16" text-anchor="end" class="view__lab">FROM THE SIDE</text>
    <path d="M20 172H320" class="floor" />
    <path d="M60 92H232" class="ear" />
    <circle cx="170" cy="92" r="13" class="head head--side" />
    <path d="M182.5 88L188 92.5L182 95" class="head__nose head__nose--side" />
    <text x="150" y="80" text-anchor="end" class="seat__lab">where your head was</text>
    <path d="M236 26V128M236 32H246M236 42H241M236 52H241M236 62H246M236 72H241M236 82H241M236 92H246M236 102H241M236 112H241M236 122H246" class="ruler" />
    <text x="250" y="32" dominant-baseline="central" class="ruler__lab">+30</text>
    <text x="250" y="62" dominant-baseline="central" class="ruler__lab">+15</text>
    <text x="250" y="92" dominant-baseline="central" class="ruler__lab is-ear">ear</text>
    <text x="250" y="122" dominant-baseline="central" class="ruler__lab">−15</text>
    <text x="250" y="140" dominant-baseline="central" class="ruler__lab ruler__lab--unit">cm</text>
    <rect x="318" y="56" width="14" height="72" rx="3" class="spk-side" class:is-playing={!!playing} />
    <path d="M318 66V118" class="spk-side__front" class:is-playing={!!playing} />
    <text x="334" y="46" text-anchor="end" class="seat__lab">speakers</text>
    {#if move.dz}
      <path d={`M150 ${EAR + move.dz}H232`} class="target" />
    {/if}
    {#key `${active}-${animate}`}
      <g clip-path={`url(#${clip})`}>
        <g transform={animate ? undefined : `translate(0 ${move.dz})`}>
          {#if animate}
            <animateTransform attributeName="transform" type="translate" values={`0 0;0 0;0 ${move.dz};0 ${move.dz}`} keyTimes="0;0.52;0.76;1" dur="5s" repeatCount="indefinite" />
          {/if}
          <path d="M170 114V234" class="pole" />
        </g>
      </g>
      <path d="M170 148V158" class="pole__base" />
      <path d="M170 158L152 172M170 158L188 172M170 158V172" class="legs" />
      <g transform={animate ? undefined : `translate(0 ${move.dz})`}>
        {#if animate}
          <animateTransform attributeName="transform" type="translate" values={`0 0;0 0;0 ${move.dz};0 ${move.dz}`} keyTimes="0;0.52;0.76;1" dur="5s" repeatCount="indefinite" />
        {/if}
        <rect x="164" y="92" width="12" height="22" rx="6" class="mic" />
        <path d="M164 98H176" class="mic__band" />
      </g>
    {/key}
  </svg>
</div>

<style>
  .card {
    flex-shrink: 0;
    border-radius: var(--r-18);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    padding: 10px 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .view {
    width: 100%;
    height: auto;
    display: block;
  }
  .rule {
    height: 1px;
    background: var(--ink-line);
    margin: 0 4px;
  }
  .cap {
    font-size: 12.5px;
    font-weight: 800;
    fill: var(--accent-lms);
  }
  .view__lab {
    font-family: var(--font-mono);
    font-size: 9.5px;
    letter-spacing: 1.2px;
    fill: var(--c-ink-70);
  }
  .spk rect,
  .spk-side {
    fill: var(--ink-fill);
    stroke: var(--c-ink-30);
    stroke-width: 1.5;
  }
  .spk path,
  .spk-side__front {
    stroke: var(--c-ink-55);
    stroke-width: 2.5;
  }
  .spk.is-playing rect,
  .spk.is-playing path,
  .spk-side.is-playing,
  .spk-side__front.is-playing {
    stroke: var(--accent-lms);
  }
  .spklab {
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 600;
    fill: var(--c-ink-70);
  }
  .spklab.is-playing {
    fill: var(--accent-lms);
  }
  .aim {
    fill: none;
    stroke: var(--c-ink-16);
    stroke-dasharray: 3 4;
  }
  .seat {
    fill: var(--c-ink-05);
    stroke: var(--c-ink-13);
  }
  .seat__back {
    stroke: var(--c-ink-13);
  }
  .seat__lab {
    font-size: 10.5px;
    fill: var(--c-ink-70);
  }
  .head,
  .head__nose {
    fill: none;
    stroke: var(--c-ink-38);
  }
  .head {
    stroke-dasharray: 3 3;
  }
  .head--side,
  .head__nose--side {
    stroke: var(--c-ink-30);
  }
  .mark {
    fill: var(--c-dark-1b2a34);
    stroke: var(--c-ink-30);
    stroke-width: 1.5;
  }
  .mark.is-done {
    fill: var(--c-lms-20);
    stroke: var(--c-lms-60);
  }
  .mark__n {
    font-size: 10px;
    font-weight: 800;
    fill: var(--ink-body);
  }
  .mark__tick {
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .trail {
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 2;
    stroke-dasharray: 4 4;
    stroke-linecap: round;
  }
  .trail__ticks {
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 1.5;
    stroke-linecap: round;
  }
  .trail__lab {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    fill: var(--accent-lms);
  }
  .mic__halo {
    fill: var(--c-lms-20);
  }
  .mic {
    fill: var(--accent-lms);
  }
  .mic__n {
    font-size: 13px;
    font-weight: 800;
    fill: var(--ink-on-accent);
  }
  .mic__band {
    stroke: var(--ink-on-accent);
    stroke-width: 1;
  }
  .floor {
    stroke: var(--c-ink-16);
  }
  .ear {
    fill: none;
    stroke: var(--c-ink-20);
    stroke-dasharray: 3 4;
  }
  .ruler {
    fill: none;
    stroke: var(--c-ink-45);
  }
  .ruler__lab {
    font-family: var(--font-mono);
    font-size: 9.5px;
    fill: var(--c-ink-70);
  }
  .ruler__lab.is-ear {
    fill: var(--ink);
  }
  .ruler__lab--unit {
    font-size: 8.5px;
  }
  .target {
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 1.5;
    stroke-dasharray: 2 3;
  }
  .pole {
    stroke: var(--c-ink-55);
    stroke-width: 2.5;
  }
  .pole__base {
    stroke: var(--c-ink-45);
    stroke-width: 5;
    stroke-linecap: round;
  }
  .legs {
    fill: none;
    stroke: var(--c-ink-45);
    stroke-width: 1.5;
  }
</style>
