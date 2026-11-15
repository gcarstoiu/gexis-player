<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A station's logo** (design/source/31, `StationLogo`). It fills its tile.
  A logo smaller than `--station-logo-native-max` (64 px) is drawn at its own
  size, centred on the plate, and never enlarged (a third of the directory's
  are tiny or missing, ADR-0180 item 4). None, or one that fails to load: the
  radio mark on the radio's tint.

  `src` is the player's own address for the logo (`/stations/logo/<key>`):
  the screens never fetch from a station's site (George, 2026-11-14).
-->
<script>
  import RadioMark from './RadioMark.svelte';

  let {
    src = null,
    //: The tile's side, px, as the artboard gives it (46 in panel rows, 160
    //: for a preset, 72 on a bar card, 44 on the phone, 40 on the card).
    size = 46,
    //: The tile's corner: one of the radius tokens.
    radius = 'var(--station-logo-row-radius)',
    //: The fallback mark's side; the artboards draw it at about 0.46 of the
    //: tile (21 in a 46 row).
    mark = null,
    markStroke = 2,
    //: Some places dim a station's picture (Now Playing reconnecting: 0.45).
    dim = 1,
  } = $props();

  const NATIVE_MAX = 64;
  let failed = $state(false);
  let natural = $state(null);
  let shown = $state(null);
  $effect(() => {
    if (src !== shown) {
      shown = src;
      failed = false;
      natural = null;
    }
  });
  function loaded(event) {
    const image = event.currentTarget;
    natural = Math.max(image.naturalWidth, image.naturalHeight) || null;
  }
  const tiny = $derived(natural !== null && natural < NATIVE_MAX);
  const markSize = $derived(mark ?? Math.round(size * 0.46));
</script>

{#if src && !failed}
  <span class="logo" class:logo--tiny={tiny} style:width="{size}px" style:height="{size}px"
    style:border-radius={radius} style:opacity={dim}>
    <img {src} alt="" draggable="false" decoding="async" onload={loaded} onerror={() => (failed = true)}
      style:width={tiny ? `${Math.min(natural, size)}px` : '100%'}
      style:height={tiny ? `${Math.min(natural, size)}px` : '100%'} />
  </span>
{:else}
  <span class="logo logo--none" style:width="{size}px" style:height="{size}px" style:border-radius={radius}
    style:opacity={dim}>
    <RadioMark size={markSize} stroke={markStroke} />
  </span>
{/if}

<style>
  .logo {
    box-sizing: border-box;
    flex-shrink: 0;
    overflow: hidden;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--station-logo-plate);
  }
  .logo img { display: block; object-fit: contain; }
  .logo--tiny { border: 1px solid var(--station-logo-plate-line); }
  .logo--none {
    background: var(--station-fallback-ground);
    border: 1px solid var(--station-fallback-line);
  }
</style>
