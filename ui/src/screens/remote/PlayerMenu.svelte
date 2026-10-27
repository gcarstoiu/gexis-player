<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the player menu (design/source/21, *Player menu*), from the
  picker: *Gexis players*, this one first with its check, then the others on
  the network (`/players`, ADR-0136), each with what it is doing. Another
  opens its own page in the same tab (C1), which closes everything here.
-->
<script>
  import mark from '../../assets/gexis-mark.svg';
  import { said } from './commands.js';
  import { FILLED } from './icons.js';

  let { open = false, me = null, others = [], here = null, onclose = () => {} } = $props();
</script>

{#if open}
  <div class="scrim" role="presentation" onclick={onclose}></div>
  <div class="menu" role="dialog" aria-label="Gexis players">
    <div class="head">Gexis players</div>
    <div class="row is-current">
      <img src={mark} alt="" />
      <span class="text">
        <span class="name">{here?.name ?? me?.name ?? 'This player'}</span>
        <span class="state">{here?.state ?? said(me)}</span>
      </span>
      <svg class="check" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.check} /></svg>
    </div>
    {#each others as p (p.url)}
      <a class="row" href={p.url}>
        <img src={mark} alt="" />
        <span class="text">
          <span class="name">{p.name}</span>
          <span class="state">{said(p)}</span>
        </span>
      </a>
    {/each}
  </div>
{/if}

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 30;
    background: rgba(4, 8, 10, 0.45);
  }
  .menu {
    position: absolute;
    z-index: 31;
    left: 16px;
    right: 16px;
    top: calc(72px + env(safe-area-inset-top, 0px));
    background: #16232c;
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 18px;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
    padding: 8px 0;
    max-height: calc(100% - 96px);
    overflow-y: auto;
  }
  .head {
    padding: 8px 18px 6px;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 64px;
    padding: 0 18px;
    color: #e9eef2;
    text-decoration: none;
    cursor: pointer;
  }
  .row.is-current {
    background: rgba(233, 238, 242, 0.05);
    cursor: default;
  }
  img {
    width: 30px;
    height: 30px;
    display: block;
    flex-shrink: 0;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .name {
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .state {
    font-size: 13px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .check {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    fill: #7ed6bc;
  }
</style>
