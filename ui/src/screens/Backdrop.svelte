<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The background picture** - the idle screen's (ADR-0047, ADR-0120), and
  since ADR-0133 the waiting screen's too, which follows the same
  *Background*. One place that asks the core for the next picture, holds it
  until the browser has it, places it by what it shows, and changes it every
  *Change the picture every* minutes. The screen above it binds `picture`
  and `shown` for its own credit line and for whether there is a picture.
-->
<script>
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { screen } from '../lib/family.svelte.js';

  let { settings = {}, active = true, picture = $bindable(null), shown = $bindable(null) } = $props();

  let panelHeight = $state(window.innerHeight || 800);
  let panelWidth = $state(window.innerWidth || 1280);
  const background = $derived(settings.idle_background ?? 'Gexis wallpapers');
  const bar = $derived(screen.family === 'bar');
  //: The shape of what is on screen, measured when it loads rather than
  //: asked of the source - a wallpaper service, a photo plugin and a folder
  //: somebody filled have nothing in common except the pixels.
  let ratio = $state(null);

  //: **Fill, unless filling would cost too much of the picture.**
  //: `cover` crops whatever does not match the panel, which is right for a
  //: photograph taken in landscape and brutal for one taken in portrait: a
  //: phone picture loses about two thirds of its height, centred, and the
  //: screen gives no sign that anything is missing.
  //:
  //: So: work out what `cover` would cost, and if it is more than a
  //: quarter of the picture, show the whole thing instead and fill the rest
  //: with a blurred copy of itself. **A quarter** because that is where the
  //: two common landscape shapes fall on the safe side - 3:2 loses 6%, 16:9
  //: 10%, 4:3 17% - while a square (38%) and anything portrait (65%+) fall
  //: on the other. The shapes that were composed to be looked at wide stay
  //: edge to edge.
  const PANEL_RATIO = $derived((screen.family === 'bar' ? screen.width : 1280) / panelHeight);
  //: **On a bar, a wide picture fills it** (George, 2026-10-04, "C"): a
  //: 16:9 picture loses 44% of its height on a 1280 x 400 bar and 61% on a
  //: 1480 x 320 one, and shown whole it was a small picture between two
  //: blurred wings. Up to 70% is cropped there, from a point above the
  //: middle where faces tend to be; a square (78% on the 11.9") or a
  //: portrait still sits whole on its halo.
  const CROP_LIMIT = $derived(screen.family === 'bar' ? 0.7 : 0.25);
  const cropped = $derived(
    ratio === null ? 0 : 1 - (ratio < PANEL_RATIO ? ratio / PANEL_RATIO : PANEL_RATIO / ratio)
  );
  //: ADR-0120: where the core placed this picture by what it shows -
  //: `y` the band's height on the picture, `width` the share of the screen
  //: it fills (under 1, over its own blur). Without it, the old rule.
  const place = $derived(picture?.place ?? null);
  const shrunk = $derived(place ? place.width < 0.999 : false);
  const fit = $derived(place ? false : cropped > CROP_LIMIT);
  const position = $derived(place ? `50% ${(place.y * 100).toFixed(1)}%` : null);

  // `background_brightness`, George's row: the design's 0.62 is the default and
  // the number is his to move. **The contour does not move with it** - it
  // is what carries the type at *any* brightness, and it matters most at
  // the top of this range where the picture is brightest.
  const brightness = $derived(Math.max(20, Math.min(100, Number(settings.background_brightness ?? 62))) / 100);

  // **Loaded before it is shown.** Swapping the source on a visible picture
  // paints the gap; this holds the new one until the browser has it.
  async function loadPicture() {
    if (!active || background === 'Black') return;
    let answer;
    try {
      // The size, so the core places the picture for this screen (ADR-0120).
      const response = await fetch(`/idle/wallpaper?w=${Math.round(panelWidth)}&h=${Math.round(panelHeight)}`);
      answer = response.ok ? await response.json() : null;
    } catch {
      answer = null;
    }
    if (!answer?.url) {
      picture = answer ?? null;
      return;
    }
    const image = new Image();
    image.onload = () => {
      picture = answer;
      shown = answer.url;
      ratio = image.naturalHeight ? image.naturalWidth / image.naturalHeight : null;
    };
    image.onerror = () => (picture = { error: 'That picture could not be loaded.' });
    image.src = answer.url;
  }

  onMount(() => {
    loadPicture();
    const every = Math.max(1, Number(settings.background_interval ?? 15)) * 60 * 1000;
    const pictures = setInterval(loadPicture, every);
    return () => clearInterval(pictures);
  });
</script>

<svelte:window bind:innerHeight={panelHeight} bind:innerWidth={panelWidth} />

{#if shown && active}
  {#key shown}
    <div class="picture" class:picture--bar={bar} in:fade={{ duration: 900 }}>
      {#if fit || shrunk}
        <!-- The same picture, out of focus and filling the screen, so a
             tall one sits on its own colour rather than on black bars.
             **Static**, not a backdrop filter: ADR-0041 bans live
             readback (24.5 ms a frame), and this rasterises once per
             picture and then only composites. Scaled up because a blur
             fades out at the edges of what it is blurring. -->
        <img
          class="bg bg--halo"
          src={shown}
          alt=""
          style:filter={`blur(38px) brightness(${(brightness * 0.75).toFixed(2)}) saturate(0.9)`}
        />
      {/if}
      <img
        class="bg"
        class:bg--fit={fit}
        src={shown}
        alt=""
        style:object-position={position}
        style:width={shrunk ? `${(place.width * 100).toFixed(1)}%` : null}
        style:left={shrunk ? `${((1 - place.width) * 50).toFixed(1)}%` : null}
        style:filter={`brightness(${brightness}) saturate(0.9)`}
      />
    </div>
  {/key}
{/if}

<style>
  /* The design's own treatment: the picture is dimmed and slightly
     desaturated in the image itself, not under a dark sheet. The amount is
     `background_brightness` and arrives as an inline style; 0.62 is the design's
     value and the row's default. */
  .picture {
    position: absolute;
    inset: 0;
  }
  .bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  /* The whole picture, on top of its own halo. */
  .bg--fit {
    object-fit: contain;
  }
  .bg--halo {
    transform: scale(1.12);
  }
  /* Without a placement from the core (ADR-0120), the old fixed band. */
  .picture--bar .bg:not(.bg--fit):not(.bg--halo) {
    object-position: 50% 35%;
  }
</style>
