<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- **No favourites yet** (design/source/31, `FavouritesEmpty`; P06): a
     dashed plate in the tiles' place, and how to add one. -->
<script>
  import HeartIcon from '../../lib/HeartIcon.svelte';
</script>

<div class="empty">
  <span class="empty__disc"><HeartIcon size={30} ink="var(--favourite)" /></span>
  <div class="empty__text">
    <span class="empty__head">No favourites yet</span>
    <span class="empty__note">Tap the heart on any station to keep it here, in your own order. Next and Previous then step through them, like a radio’s presets.</span>
  </div>
</div>

<style>
  .empty {
    height: 196px;
    box-sizing: border-box;
    border-radius: var(--r-xl);
    border: 1.5px dashed var(--favourites-empty-line);
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 0 36px;
  }
  .empty__disc {
    width: 72px;
    height: 72px;
    border-radius: var(--r-circle);
    box-sizing: border-box;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--c-favourite-rgb), 0.14);
    border: 1px solid rgba(var(--c-favourite-rgb), 0.3);
  }
  .empty__text {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .empty__head {
    font-size: 24px;
    font-weight: 700;
  }
  .empty__note {
    font-size: 17px;
    line-height: 1.45;
    color: var(--ink-muted);
    max-width: 640px;
  }
</style>
