<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  A weather glyph, in one of the three sets `idle_icons` offers (ADR-0047 §1).

  **One geometry, three ways of painting it.** Nineteen conditions drawn
  three times over would be fifty-seven drawings to keep in agreement; this
  is nineteen compositions of six primitives - sun, cloud, drops, flakes,
  bolt, fog bars - and a set that decides how those primitives are painted:

  - **Solid** — filled, one ink. What a forecast looks like at a glance.
  - **Duotone** — the cloud dimmed, what falls out of it in the accent.
    Two tones is the whole idea, so the sun behind a cloud is accent too.
  - **Neon** — stroked, nothing filled, with a glow. It is the set that
    needs a dark background, which is what this screen is.

  The panel has no icon font (`design/screens.md`), so these are inline SVG
  like every other glyph here: they inherit `currentColor` and scale with
  their box rather than with a font size.
-->
<script>
  let { condition = 'unknown', set = 'Solid', size = 44 } = $props();

  // What each condition is made of. Nothing here is a special case: a
  // condition names its parts, and the parts are drawn below.
  const PARTS = {
    'clear': { sun: 'full' },
    'mostly-clear': { sun: 'full', cloud: 'small' },
    'partly-cloudy': { sun: 'peek', cloud: 'big' },
    'overcast': { cloud: 'double' },
    'fog': { cloud: 'big', fog: true },
    'drizzle': { cloud: 'big', fall: 'drizzle' },
    'freezing-drizzle': { cloud: 'big', fall: 'drizzle', freezing: true },
    'rain': { cloud: 'big', fall: 'rain' },
    'heavy-rain': { cloud: 'big', fall: 'heavy' },
    'freezing-rain': { cloud: 'big', fall: 'rain', freezing: true },
    'showers': { sun: 'peek', cloud: 'big', fall: 'rain' },
    'heavy-showers': { sun: 'peek', cloud: 'big', fall: 'heavy' },
    'snow': { cloud: 'big', fall: 'snow' },
    'heavy-snow': { cloud: 'double', fall: 'snow' },
    'snow-grains': { cloud: 'big', fall: 'grains' },
    'snow-showers': { sun: 'peek', cloud: 'big', fall: 'snow' },
    'thunderstorm': { cloud: 'big', bolt: true },
    'thunderstorm-hail': { cloud: 'big', bolt: true, fall: 'grains' },
    'unknown': { cloud: 'big', query: true },
  };

  const parts = $derived(PARTS[condition] ?? PARTS.unknown);
  const neon = $derived(set === 'Neon');
  const duo = $derived(set === 'Duotone');

  // Solid paints everything in the ink it inherits; duotone drops the cloud
  // back so what falls out of it reads first; neon draws nothing filled.
  const cloudFill = $derived(neon ? 'none' : duo ? 'rgba(233,238,242,0.38)' : 'currentColor');
  const markFill = $derived(neon ? 'none' : duo ? 'var(--accent)' : 'currentColor');
  const stroke = $derived(neon ? 'currentColor' : 'none');
  const markStroke = $derived(neon ? 'var(--accent)' : 'none');
</script>

<svg
  class="wicon"
  class:wicon--neon={neon}
  width={size}
  height={size}
  viewBox="0 0 64 64"
  role="img"
  aria-label={condition.replace(/-/g, ' ')}
  fill="none"
>
  {#if parts.sun === 'full'}
    <circle cx="32" cy="30" r="13" fill={markFill} stroke={markStroke} stroke-width="3" />
    {#each [0, 45, 90, 135, 180, 225, 270, 315] as angle (angle)}
      <line
        x1="32" y1="9" x2="32" y2="14"
        stroke={neon ? 'var(--accent)' : duo ? 'var(--accent)' : 'currentColor'}
        stroke-width="3.5"
        stroke-linecap="round"
        transform={`rotate(${angle} 32 30)`}
      />
    {/each}
  {:else if parts.sun === 'peek'}
    <!-- Behind the cloud and to the left, so the cloud reads as in front
         rather than as a second shape beside it. -->
    <circle cx="23" cy="22" r="10" fill={markFill} stroke={markStroke} stroke-width="3" />
    {#each [200, 245, 290] as angle (angle)}
      <line
        x1="23" y1="6" x2="23" y2="10"
        stroke={duo || neon ? 'var(--accent)' : 'currentColor'}
        stroke-width="3.5"
        stroke-linecap="round"
        transform={`rotate(${angle} 23 22)`}
      />
    {/each}
  {/if}

  {#if parts.cloud === 'double'}
    <path
      d="M20 24a9 9 0 0 1 17-3 8 8 0 0 1 10 10H23a7 7 0 0 1-3-7z"
      fill={neon ? 'none' : 'rgba(233,238,242,0.28)'}
      stroke={stroke}
      stroke-width="3"
      stroke-linejoin="round"
    />
  {/if}
  {#if parts.cloud}
    {@const y = parts.cloud === 'small' ? 6 : 0}
    <path
      d={parts.cloud === 'small'
        ? `M36 40a6 6 0 0 1 11-2 5.5 5.5 0 0 1 1 11H38a5 5 0 0 1-2-9z`
        : `M18 44a10 10 0 0 1 3-19 13 13 0 0 1 24-2 9 9 0 0 1 1 21H21a9 9 0 0 1-3-1z`}
      transform={`translate(0 ${y})`}
      fill={cloudFill}
      stroke={stroke}
      stroke-width="3"
      stroke-linejoin="round"
    />
  {/if}

  {#if parts.fall === 'drizzle' || parts.fall === 'rain' || parts.fall === 'heavy'}
    {@const drops = parts.fall === 'heavy' ? [20, 30, 40, 50] : parts.fall === 'rain' ? [24, 34, 44] : [27, 40]}
    {#each drops as x (x)}
      <line
        x1={x} y1="48" x2={x - 3} y2={parts.fall === 'drizzle' ? 55 : 59}
        stroke={markStroke === 'none' ? markFill : markStroke}
        stroke-width={parts.fall === 'drizzle' ? 3 : 4}
        stroke-linecap="round"
      />
    {/each}
  {:else if parts.fall === 'snow' || parts.fall === 'grains'}
    {@const flakes = parts.fall === 'snow' ? [[24, 52], [34, 57], [44, 52]] : [[26, 53], [38, 53]]}
    {#each flakes as [x, y] (x)}
      <circle
        cx={x} cy={y} r={parts.fall === 'snow' ? 3.4 : 2.6}
        fill={markFill}
        stroke={markStroke}
        stroke-width="2"
      />
    {/each}
  {/if}

  {#if parts.freezing}
    <!-- What tells freezing rain from rain: the line it lands on. -->
    <line x1="16" y1="60" x2="48" y2="60" stroke={markStroke === 'none' ? markFill : markStroke} stroke-width="3" stroke-linecap="round" />
  {/if}

  {#if parts.fog}
    {#each [50, 56, 62] as y, i (y)}
      <line
        x1={16 + i * 3} y1={y} x2={48 - i * 2} y2={y}
        stroke={neon || duo ? 'var(--accent)' : 'currentColor'}
        stroke-width="3.5"
        stroke-linecap="round"
        opacity={1 - i * 0.22}
      />
    {/each}
  {/if}

  {#if parts.bolt}
    <path
      d="M34 44l-9 13h7l-3 10 12-15h-8l4-8z"
      fill={markFill}
      stroke={markStroke}
      stroke-width="2.5"
      stroke-linejoin="round"
    />
  {/if}

  {#if parts.query}
    <text
      x="32" y="60" text-anchor="middle"
      font-size="18" font-weight="700"
      fill={neon ? 'none' : 'currentColor'}
      stroke={neon ? 'currentColor' : 'none'}
      stroke-width="1"
    >?</text>
  {/if}
</svg>

<style>
  .wicon {
    display: block;
    flex-shrink: 0;
    /* The accent the two painted sets use. Kept here rather than on each
       shape so a set is a paint change and never a geometry change. */
    --accent: #7ed6bc;
  }
  /* Neon is the one set that is not just a fill: a stroke this thin needs
     the glow to read as deliberate rather than as a hairline. */
  .wicon--neon {
    filter: drop-shadow(0 0 4px rgba(126, 214, 188, 0.55));
  }
</style>
