<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  A radio category's tinted disc and shape (design/screens.md §8), for the
  bars: their radio tiles had a plain folder or station icon where the
  standard screen draws ten shapes in ten tints (George, 2026-10-04: "In the
  radio tile the tiles inside do not have the same styling and icons as in
  the other ratio screen"). The look and the CSS are the standard screen's,
  from Library.svelte, which keeps its own copy for now.
-->
<script>
  let { label = '', station = false, card = false } = $props();

  //: Read by colour and silhouette before they are read by word; anything
  //: LMS reports that is not here - and every station - falls back to arcs.
  const RADIO_LOOK = {
    'Radio Now Playing': ['arcs', '#7ed6bc'],
    'My Presets': ['star', '#e0a758'],
    'Local Radio': ['pin', '#9fb4e8'],
    Music: ['note', '#f2a48f'],
    Sports: ['ball', '#7ed6bc'],
    News: ['lines', '#b0bcc4'],
    Talk: ['mic', '#c8a2d8'],
    'By Location': ['globe', '#8fc4d8'],
    'By Language': ['speech', '#9fb4e8'],
    // The design lists Rss among its shapes and assigns it no tint, so it
    // takes the fallback's - inventing one would be a colour nothing chose.
    Rss: ['rss', '#8fc4d8'],
  };
  const RADIO_FALLBACK = ['arcs', '#8fc4d8'];
  const look = $derived(station ? RADIO_FALLBACK : (RADIO_LOOK[label] ?? RADIO_FALLBACK));
</script>

<span class="rdisc" class:rdisc--card={card} style:--tint={look[1]}>
  <span class="rglyph rglyph--{look[0]}"><i></i><i></i><i></i></span>
</span>

<style>
  .rdisc {
    box-sizing: border-box;
    width: 46px;
    height: 46px;
    border-radius: 13px;
    background: color-mix(in srgb, var(--tint) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--tint) 30%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .rdisc--card { width: 54px; height: 54px; border-radius: var(--r-circle); }

  .rglyph { display: block; position: relative; color: var(--tint); }
  .rglyph i { display: block; position: absolute; background: currentColor; }

  /* arcs - the fallback, and Radio Now Playing */
  .rglyph--arcs { width: 20px; height: 20px; }
  .rglyph--arcs i {
    left: 50%; bottom: 1px; background: none;
    border: 2px solid currentColor; border-bottom-color: transparent;
    border-left-color: transparent; border-right-color: transparent;
    border-radius: 50%; transform: translateX(-50%);
  }
  .rglyph--arcs i:nth-child(1) { width: 8px; height: 8px; }
  .rglyph--arcs i:nth-child(2) { width: 15px; height: 15px; }
  .rglyph--arcs i:nth-child(3) { width: 22px; height: 22px; }

  /* star */
  .rglyph--star { width: 20px; height: 20px; }
  .rglyph--star i:nth-child(1) {
    inset: 0; background: currentColor;
    clip-path: polygon(50% 0, 61% 35%, 98% 35%, 68% 57%, 79% 92%, 50% 70%, 21% 92%, 32% 57%, 2% 35%, 39% 35%);
  }
  .rglyph--star i:nth-child(2), .rglyph--star i:nth-child(3) { display: none; }

  /* pin */
  .rglyph--pin { width: 16px; height: 21px; }
  .rglyph--pin i:nth-child(1) {
    inset: 0 0 5px 0; border-radius: 50% 50% 50% 50% / 55% 55% 45% 45%;
  }
  .rglyph--pin i:nth-child(2) {
    left: 50%; top: 13px; width: 2px; height: 8px; transform: translateX(-50%);
  }
  .rglyph--pin i:nth-child(3) {
    left: 50%; top: 5px; width: 6px; height: 6px; border-radius: 50%;
    transform: translateX(-50%); background: var(--bg-base);
  }

  /* note */
  .rglyph--note { width: 18px; height: 20px; }
  .rglyph--note i:nth-child(1) { left: 0; bottom: 0; width: 9px; height: 7px; border-radius: 50%; }
  .rglyph--note i:nth-child(2) { left: 7px; top: 0; width: 2px; height: 16px; }
  .rglyph--note i:nth-child(3) { left: 7px; top: 0; width: 11px; height: 2px; transform: skewY(14deg); transform-origin: left; }

  /* ball */
  .rglyph--ball { width: 20px; height: 20px; }
  .rglyph--ball i:nth-child(1) {
    inset: 0; background: none; border: 2px solid currentColor; border-radius: 50%;
  }
  .rglyph--ball i:nth-child(2) { left: 50%; top: 1px; width: 2px; height: 18px; transform: translateX(-50%); }
  .rglyph--ball i:nth-child(3) { top: 50%; left: 1px; height: 2px; width: 18px; transform: translateY(-50%); }

  /* lines */
  .rglyph--lines { width: 20px; height: 16px; }
  .rglyph--lines i { left: 0; height: 2px; border-radius: 1px; }
  .rglyph--lines i:nth-child(1) { top: 0; width: 20px; }
  .rglyph--lines i:nth-child(2) { top: 7px; width: 20px; }
  .rglyph--lines i:nth-child(3) { top: 14px; width: 12px; }

  /* mic */
  .rglyph--mic { width: 16px; height: 21px; }
  .rglyph--mic i:nth-child(1) { left: 4px; top: 0; width: 8px; height: 12px; border-radius: 4px; }
  .rglyph--mic i:nth-child(2) {
    left: 1px; top: 9px; width: 14px; height: 7px; background: none;
    border: 2px solid currentColor; border-top-color: transparent;
    border-radius: 0 0 8px 8px;
  }
  .rglyph--mic i:nth-child(3) { left: 50%; bottom: 0; width: 2px; height: 4px; transform: translateX(-50%); }

  /* globe */
  .rglyph--globe { width: 20px; height: 20px; }
  .rglyph--globe i:nth-child(1) { inset: 0; background: none; border: 2px solid currentColor; border-radius: 50%; }
  .rglyph--globe i:nth-child(2) { top: 50%; left: 0; width: 20px; height: 2px; transform: translateY(-50%); }
  .rglyph--globe i:nth-child(3) {
    left: 50%; top: 0; width: 10px; height: 20px; background: none;
    border: 2px solid currentColor; border-radius: 50%; transform: translateX(-50%);
  }

  /* speech */
  .rglyph--speech { width: 20px; height: 18px; }
  .rglyph--speech i:nth-child(1) {
    left: 0; top: 0; width: 20px; height: 14px; background: none;
    border: 2px solid currentColor; border-radius: 6px;
  }
  .rglyph--speech i:nth-child(2) {
    left: 4px; bottom: 0; width: 6px; height: 6px;
    clip-path: polygon(0 0, 100% 0, 0 100%);
  }
  .rglyph--speech i:nth-child(3) { display: none; }

  /* rss - for the feed categories LMS may report */
  .rglyph--rss { width: 18px; height: 18px; }
  .rglyph--rss i:nth-child(1) { left: 0; bottom: 0; width: 5px; height: 5px; border-radius: 50%; }
  .rglyph--rss i:nth-child(2) {
    left: 0; bottom: 0; width: 11px; height: 11px; background: none;
    border: 2px solid currentColor; border-radius: 0 0 0 100%;
    border-top-color: transparent; border-right-color: transparent;
    transform: rotate(-90deg); transform-origin: left bottom;
  }
  .rglyph--rss i:nth-child(3) {
    left: 0; bottom: 0; width: 17px; height: 17px; background: none;
    border: 2px solid currentColor; border-radius: 0 0 0 100%;
    border-top-color: transparent; border-right-color: transparent;
    transform: rotate(-90deg); transform-origin: left bottom;
  }
</style>
