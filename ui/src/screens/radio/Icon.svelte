<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The radio screens' glyphs, as design/source/31 draws them (24-unit SVGs in
  one ink, `currentColor`): §8's category shapes at the size its discs carry
  them, and the controls the lists and Now Playing add. The colour is the
  caller's, through `color`.
-->
<script>
  let { name, size = 24, width = 2 } = $props();
  const FILLED = new Set(['note', 'play', 'stop']);
  const filled = $derived(FILLED.has(name));
</script>

<svg viewBox="0 0 24 24" width={size} height={size} fill={filled ? 'currentColor' : 'none'}
  stroke={filled ? 'none' : 'currentColor'} stroke-width={width} stroke-linecap="round"
  stroke-linejoin="round" aria-hidden="true">
  {#if name === 'pin'}
    <path d="M12 21s-6.4-6-6.4-11a6.4 6.4 0 0 1 12.8 0c0 5-6.4 11-6.4 11z"></path><circle cx="12" cy="10" r="2.3"></circle>
  {:else if name === 'note'}
    <path d="M12 3V13.55C11.41 13.21 10.73 13 10 13C7.79 13 6 14.79 6 17S7.79 21 10 21 14 19.21 14 17V7H18V3H12Z"></path>
  {:else if name === 'globe'}
    <circle cx="12" cy="12" r="8.6"></circle><ellipse cx="12" cy="12" rx="3.8" ry="8.6"></ellipse><path d="M3.6 12h16.8"></path>
  {:else if name === 'speech'}
    <path d="M5 5.5h14a1.8 1.8 0 0 1 1.8 1.8v8a1.8 1.8 0 0 1-1.8 1.8H11l-4.4 3.4V17.1H5a1.8 1.8 0 0 1-1.8-1.8v-8A1.8 1.8 0 0 1 5 5.5z"></path>
  {:else if name === 'search'}
    <circle cx="10.5" cy="10.5" r="6.3"></circle><path d="M15.3 15.3l5.2 5.2"></path>
  {:else if name === 'chevron'}
    <path d="M9.5 5.5 16 12l-6.5 6.5"></path>
  {:else if name === 'meter'}
    <path d="M6 19v-6M10 19V7M14 19v-9M18 19v-4"></path>
  {:else if name === 'play'}
    <path d="M8,5.14V19.14L19,12.14L8,5.14Z"></path>
  {:else if name === 'stop'}
    <rect x="6" y="6" width="12" height="12" rx="2"></rect>
  {:else if name === 'up'}
    <path d="M12 19V5.5M6 11l6-6 6 6"></path>
  {:else if name === 'down'}
    <path d="M12 5v13.5M6 13l6 6 6-6"></path>
  {:else if name === 'cloud-off'}
    <path d="M7 18.5h10.2a3.8 3.8 0 0 0 .9-7.5 6 6 0 0 0-10.3-3.3M5 9.6A4.5 4.5 0 0 0 7 18.5"></path><path d="M3.5 3.5l17 17"></path>
  {:else if name === 'retry'}
    <path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"></path><path d="M19.5 4.5v4h-4"></path>
  {:else if name === 'clear'}
    <path d="M6.5 6.5l11 11M17.5 6.5l-11 11"></path>
  {:else if name === 'spinner'}
    <path d="M12 3.5a8.5 8.5 0 1 1-8.5 8.5"></path>
  {:else if name === 'warning'}
    <path d="M12 4 2.8 19.5h18.4L12 4z"></path><path d="M12 10v4.2"></path><circle cx="12" cy="16.9" r="0.6" fill="currentColor"></circle>
  {/if}
</svg>

<style>
  svg { display: block; flex-shrink: 0; }
</style>
