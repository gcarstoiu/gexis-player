<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The idle screen's weather glyph, in the set `idle_icons` names.

  **Built from the design, not from an idea about icons.** The drop draws
  these in `source/Now Playing.dc.html` (the idle screen lives in that file,
  not in a file of its own) and they are DOM shapes, not line art: a yellow
  disc with four spinning rays, a white cloud that drifts, blue bars that
  fall. Three sets, each with its own palette and its own animation:

  - **Solid** — flat colour. Sun `#f2c14f` with a glow, cloud `#eef3f7`,
    rain `#8fc4e8`.
  - **Duotone** — a shadow shape offset behind each light one, and the sun
    pulsing rather than spinning.
  - **Neon** — nothing filled: rings and bars in `#9fe6ff` / `#ffd766` with
    their own glow.

  **Every measurement is a ratio of the box**, taken from the design's two
  sizes (124px beside the current conditions, 80px in a forecast column).
  Both sets of numbers reduce to the same fractions, so one component draws
  either without a second table.

  **Four conditions are drawn in the design and a forecast has more.** Sun,
  part, cloud and rain are the mock's whole vocabulary; snow, storm and fog
  are built here from the same primitives, in the same palette, because a
  real week needs them and inventing a second visual language for them would
  be worse than extending this one.
-->
<script>
  let { condition = 'unknown', set = 'Solid', size = 80 } = $props();

  // Which primitives each condition is made of. The design's own `cond()`
  // maps sun/part/cloud/rain; the rest extend it.
  const PARTS = {
    'clear': { sun: true },
    'mostly-clear': { sun: true, cloud: true },
    'partly-cloudy': { sun: true, cloud: true },
    'overcast': { cloud: true },
    'fog': { cloud: true, fog: true },
    'drizzle': { cloud: true, rain: 'light' },
    'freezing-drizzle': { cloud: true, rain: 'light' },
    'rain': { cloud: true, rain: true },
    'heavy-rain': { cloud: true, rain: true },
    'freezing-rain': { cloud: true, rain: true },
    'showers': { sun: true, cloud: true, rain: true },
    'heavy-showers': { sun: true, cloud: true, rain: true },
    'snow': { cloud: true, snow: true },
    'heavy-snow': { cloud: true, snow: true },
    'snow-grains': { cloud: true, snow: true },
    'snow-showers': { sun: true, cloud: true, snow: true },
    'thunderstorm': { cloud: true, bolt: true },
    'thunderstorm-hail': { cloud: true, bolt: true, snow: true },
    'unknown': { cloud: true },
  };

  const parts = $derived(PARTS[condition] ?? PARTS.unknown);
  const kind = $derived(String(set).toLowerCase());
  const px = (ratio) => `${(size * ratio).toFixed(2)}px`;
  // The rain bars sit at these three fractions across the box; a light
  // shower drops the middle one rather than shrinking them all.
  const wet = $derived(parts.rain === 'light' ? [0.22, 0.74] : [0.22, 0.48, 0.74]);
</script>

<span
  class="wx wx--{kind}"
  style:width={`${size}px`}
  style:height={`${size}px`}
  style:--s={`${size}px`}
  role="img"
  aria-label={condition.replace(/-/g, ' ')}
>
  {#if parts.sun}
    <span class="sun">
      <span class="sun__rays">
        <span></span><span></span><span></span><span></span>
      </span>
      <span class="sun__disc"></span>
      <span class="sun__glow"></span>
    </span>
  {/if}

  {#if parts.cloud}
    <span class="cloud">
      <span class="cloud__shadow"></span>
      <span class="cloud__base"></span>
      <span class="cloud__big"></span>
      <span class="cloud__small"></span>
    </span>
  {/if}

  {#if parts.rain}
    {#each wet as x, i (x)}
      <span class="drop" style:left={px(x)} style:animation-delay={`${i * 0.35}s`}></span>
    {/each}
  {/if}

  {#if parts.snow}
    {#each [0.24, 0.5, 0.76] as x, i (x)}
      <span class="flake" style:left={px(x)} style:animation-delay={`${i * 0.4}s`}></span>
    {/each}
  {/if}

  {#if parts.fog}
    {#each [0.78, 0.9] as y, i (y)}
      <span class="fog" style:top={px(y)} style:width={px(0.84 - i * 0.18)}></span>
    {/each}
  {/if}

  {#if parts.bolt}
    <span class="bolt"></span>
  {/if}
</span>

<style>
  /* The design's four animations, verbatim. */
  @keyframes wxSpin {
    to {
      transform: rotate(360deg);
    }
  }
  @keyframes wxDrift {
    0%,
    100% {
      transform: translateX(-3px);
    }
    50% {
      transform: translateX(3px);
    }
  }
  @keyframes wxFall {
    0% {
      transform: translateY(-4px);
      opacity: 0;
    }
    30% {
      opacity: 1;
    }
    100% {
      transform: translateY(12px);
      opacity: 0;
    }
  }
  @keyframes wxPulse {
    0%,
    100% {
      opacity: 0.55;
    }
    50% {
      opacity: 1;
    }
  }

  .wx {
    position: relative;
    display: block;
    flex-shrink: 0;
  }
  .wx span {
    position: absolute;
    display: block;
  }

  /* ---- sun ------------------------------------------------------------ */
  .sun,
  .cloud {
    inset: 0;
  }
  .sun__rays {
    left: 50%;
    top: 50%;
    width: var(--s);
    height: var(--s);
    margin: calc(var(--s) / -2) 0 0 calc(var(--s) / -2);
    animation: wxSpin 18s linear infinite;
  }
  .sun__rays span {
    border-radius: 2px;
    background: #f2c14f;
  }
  .sun__rays span:nth-child(1) {
    left: 50%;
    top: 0;
    width: calc(var(--s) * 0.048);
    height: calc(var(--s) * 0.17);
    margin-left: calc(var(--s) * -0.024);
  }
  .sun__rays span:nth-child(2) {
    left: 50%;
    bottom: 0;
    width: calc(var(--s) * 0.048);
    height: calc(var(--s) * 0.17);
    margin-left: calc(var(--s) * -0.024);
  }
  .sun__rays span:nth-child(3) {
    top: 50%;
    left: 0;
    width: calc(var(--s) * 0.17);
    height: calc(var(--s) * 0.048);
    margin-top: calc(var(--s) * -0.024);
  }
  .sun__rays span:nth-child(4) {
    top: 50%;
    right: 0;
    width: calc(var(--s) * 0.17);
    height: calc(var(--s) * 0.048);
    margin-top: calc(var(--s) * -0.024);
  }
  .sun__disc {
    left: 50%;
    top: 50%;
    width: calc(var(--s) * 0.5);
    height: calc(var(--s) * 0.5);
    margin: calc(var(--s) * -0.25) 0 0 calc(var(--s) * -0.25);
    border-radius: 50%;
    background: #f2c14f;
    box-shadow: 0 0 calc(var(--s) * 0.3) rgba(242, 193, 79, 0.6);
  }
  .sun__glow {
    display: none;
  }

  /* ---- cloud ---------------------------------------------------------- */
  .cloud {
    top: calc(var(--s) * 0.3);
    height: calc(var(--s) * 0.42);
    animation: wxDrift 5s ease-in-out infinite;
  }
  .cloud__shadow {
    display: none;
  }
  .cloud__base {
    left: 0;
    bottom: 0;
    width: 100%;
    height: calc(var(--s) * 0.26);
    border-radius: var(--s);
    background: #eef3f7;
  }
  .cloud__big {
    left: calc(var(--s) * 0.16);
    top: 0;
    width: calc(var(--s) * 0.42);
    height: calc(var(--s) * 0.42);
    border-radius: 50%;
    background: #eef3f7;
  }
  .cloud__small {
    right: calc(var(--s) * 0.12);
    top: calc(var(--s) * 0.1);
    width: calc(var(--s) * 0.32);
    height: calc(var(--s) * 0.32);
    border-radius: 50%;
    background: #eef3f7;
  }

  /* ---- what falls ----------------------------------------------------- */
  .drop {
    bottom: 0;
    width: calc(var(--s) * 0.056);
    height: calc(var(--s) * 0.2);
    border-radius: 2px;
    background: #8fc4e8;
    animation: wxFall 1.1s linear infinite;
  }
  .flake {
    bottom: calc(var(--s) * 0.04);
    width: calc(var(--s) * 0.09);
    height: calc(var(--s) * 0.09);
    border-radius: 50%;
    background: #dceaf6;
    animation: wxFall 1.6s linear infinite;
  }
  .fog {
    left: calc(var(--s) * 0.08);
    height: calc(var(--s) * 0.05);
    border-radius: var(--s);
    background: #cfdae4;
    opacity: 0.85;
    animation: wxDrift 6s ease-in-out infinite;
  }
  .bolt {
    left: 50%;
    bottom: 0;
    width: calc(var(--s) * 0.16);
    height: calc(var(--s) * 0.3);
    margin-left: calc(var(--s) * -0.08);
    background: #f2c14f;
    clip-path: polygon(58% 0, 8% 58%, 42% 58%, 30% 100%, 92% 38%, 52% 38%);
    animation: wxPulse 2.4s ease-in-out infinite;
  }

  /* ---- duotone: a shadow shape behind every light one ------------------ */
  .wx--duotone .sun__rays {
    display: none;
  }
  .wx--duotone .sun__disc {
    width: calc(var(--s) * 0.52);
    height: calc(var(--s) * 0.52);
    margin: calc(var(--s) * -0.24) 0 0 calc(var(--s) * -0.22);
    background: #b8862f;
    box-shadow: none;
  }
  .wx--duotone .sun__glow {
    display: block;
    left: 50%;
    top: 50%;
    width: calc(var(--s) * 0.52);
    height: calc(var(--s) * 0.52);
    margin: calc(var(--s) * -0.26) 0 0 calc(var(--s) * -0.26);
    border-radius: 50%;
    background: #f7d777;
    animation: wxPulse 4s ease-in-out infinite;
  }
  .wx--duotone .cloud {
    animation-duration: 5.5s;
  }
  .wx--duotone .cloud__shadow {
    display: block;
    left: calc(var(--s) * 0.04);
    bottom: calc(var(--s) * -0.03);
    width: calc(var(--s) * 0.96);
    height: calc(var(--s) * 0.28);
    border-radius: var(--s);
    background: #8b98a6;
  }
  .wx--duotone .cloud__base {
    width: calc(var(--s) * 0.92);
    background: #f4f8fb;
  }
  .wx--duotone .cloud__big {
    left: calc(var(--s) * 0.14);
    width: calc(var(--s) * 0.44);
    height: calc(var(--s) * 0.44);
    background: #f4f8fb;
  }
  .wx--duotone .cloud__small {
    display: none;
  }
  .wx--duotone .drop {
    width: calc(var(--s) * 0.09);
    height: calc(var(--s) * 0.09);
    border-radius: 50% 50% 50% 0;
    transform: rotate(45deg);
    background: #7fc0ea;
    animation-duration: 1.2s;
  }
  .wx--duotone .flake {
    background: #cfe3f2;
  }

  /* ---- neon: nothing filled ------------------------------------------- */
  .wx--neon .sun__rays {
    display: none;
  }
  .wx--neon .sun__disc {
    background: none;
    box-sizing: border-box;
    border: calc(var(--s) * 0.048) solid #ffd766;
    box-shadow:
      0 0 calc(var(--s) * 0.18) rgba(255, 215, 102, 0.9),
      inset 0 0 calc(var(--s) * 0.1) rgba(255, 215, 102, 0.6);
    animation: wxPulse 2.8s ease-in-out infinite;
  }
  .wx--neon .cloud {
    animation-duration: 6s;
  }
  .wx--neon .cloud__base {
    background: none;
    height: calc(var(--s) * 0.3);
    box-sizing: border-box;
    border: calc(var(--s) * 0.048) solid #9fe6ff;
    box-shadow: 0 0 calc(var(--s) * 0.14) rgba(159, 230, 255, 0.8);
  }
  .wx--neon .cloud__big {
    background: none;
    left: calc(var(--s) * 0.18);
    box-sizing: border-box;
    border: calc(var(--s) * 0.048) solid #9fe6ff;
    box-shadow: 0 0 calc(var(--s) * 0.14) rgba(159, 230, 255, 0.8);
  }
  .wx--neon .cloud__small {
    display: none;
  }
  .wx--neon .drop {
    width: calc(var(--s) * 0.048);
    height: calc(var(--s) * 0.22);
    border-radius: var(--s);
    background: #7fe4ff;
    box-shadow: 0 0 calc(var(--s) * 0.1) rgba(127, 228, 255, 0.9);
  }
  .wx--neon .flake {
    background: #7fe4ff;
    box-shadow: 0 0 calc(var(--s) * 0.1) rgba(127, 228, 255, 0.9);
  }
  .wx--neon .fog {
    background: #7fe4ff;
    box-shadow: 0 0 calc(var(--s) * 0.08) rgba(127, 228, 255, 0.8);
  }
  .wx--neon .bolt {
    background: #ffd766;
    box-shadow: 0 0 calc(var(--s) * 0.12) rgba(255, 215, 102, 0.9);
  }
</style>
