<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Our Bluetooth mark (design/marks/bluetooth.svg), drawn rather than a
  picture of it, so that each theme draws it in its own --accent-bluetooth
  (ADR-0171; design/source/28/<id>-bluetooth.svg). The PNG it replaces was
  the same vector at 256 px.
-->
<script>
  let { size = 18, opacity = 1 } = $props();
</script>

<svg class="btmark" viewBox="0 0 64 64" style:width="{size}px" style:height="{size}px" style:opacity aria-hidden="true">
  <g>
    <rect x="10" y="8" width="22" height="48" rx="5"></rect>
    <line x1="18" y1="49" x2="24" y2="49"></line>
    <path d="M41 24.5a10 10 0 0 1 0 15"></path>
    <path d="M48 17.5a20 20 0 0 1 0 29"></path>
  </g>
</svg>

<style>
  .btmark {
    display: block;
    flex-shrink: 0;
  }
  g {
    fill: none;
    stroke: var(--accent-bluetooth);
    stroke-width: 4.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
