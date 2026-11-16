<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The favourite's heart** (design/source/31, `HeartButton`): an outline in
  the second ink, filled in `--favourite`. The icon only; each surface draws
  its own button around it, at the size its artboard gives.
-->
<script>
  let { filled = false, size = 34, ink = 'rgba(var(--c-ink-rgb), 0.6)' } = $props();
</script>

{#if filled}
  <svg viewBox="0 0 24 24" width={size} height={size} fill="var(--favourite)" aria-hidden="true">
    <path d="M12 20.6s-7.6-4.7-9.4-9.4C1.3 7.9 3.3 4.4 6.9 4.4c2.1 0 3.7 1.2 5.1 3 1.4-1.8 3-3 5.1-3 3.6 0 5.6 3.5 4.3 6.8-1.8 4.7-9.4 9.4-9.4 9.4z"></path>
  </svg>
{:else}
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={ink} stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M12 20s-7.2-4.5-8.9-8.9C1.9 8 3.7 5 7 5c2 0 3.5 1.1 5 2.9C13.5 6.1 15 5 17 5c3.3 0 5.1 3 3.9 6.1C19.2 15.5 12 20 12 20z"></path>
  </svg>
{/if}

<style>
  svg { display: block; flex-shrink: 0; }
</style>
