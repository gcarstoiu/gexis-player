<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The station directory cannot be reached** (design/source/31,
  `DirectoryBanner`; P04, P05). `kept`: the lists show what was seen in the
  last day. `none`: nothing is kept, browsing is dimmed, the favourites
  still play. *Try again* asks once more.
-->
<script>
  import Icon from './Icon.svelte';

  let { kind = 'kept', busy = false, onretry } = $props();
</script>

<div class="banner" role="status">
  <span class="banner__glyph"><Icon name="cloud-off" size={26} /></span>
  <span class="banner__text">
    {kind === 'none'
      ? 'Can’t reach the station directory, and nothing from the last day is kept. Your favourites still play.'
      : 'Can’t reach the station directory. Lists show what was seen in the last day.'}
  </span>
  <button class="banner__retry" type="button" disabled={busy} onclick={onretry}>
    <Icon name="retry" size={18} width={2.4} />Try again
  </button>
</div>

<style>
  .banner {
    height: 60px;
    box-sizing: border-box;
    border-radius: var(--r-lg);
    background: var(--directory-ground);
    border: 1px solid var(--directory-line);
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 10px 0 18px;
    flex-shrink: 0;
  }
  .banner__glyph {
    color: var(--accent-warn);
    display: flex;
  }
  .banner__text {
    flex: 1;
    min-width: 0;
    font-size: 17px;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .banner__retry {
    height: 44px;
    padding: 0 16px;
    border-radius: var(--r-pill);
    border: 1px solid var(--c-warn-50);
    background: transparent;
    color: var(--accent-warn);
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .banner__retry:active {
    transform: scale(0.96);
  }
  .banner__retry:disabled {
    opacity: 0.6;
  }
</style>
