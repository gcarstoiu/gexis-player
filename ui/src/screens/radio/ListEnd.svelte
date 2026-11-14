<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- **A list's end** (design/source/31, `ListEnd`; P17): *End of Jazz ·
     1,240 stations* between two hairlines. -->
<script>
  let { text } = $props();
</script>

<div class="end">
  <span class="end__rule"></span>
  <span class="end__text">{text}</span>
  <span class="end__rule"></span>
</div>

<style>
  .end {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px 14px 6px;
    flex-shrink: 0;
  }
  .end__rule {
    flex: 1;
    height: 1px;
    background: var(--ink-line);
  }
  .end__text {
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    white-space: nowrap;
  }
</style>
