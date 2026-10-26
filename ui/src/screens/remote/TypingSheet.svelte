<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 C5: the typing sheet (design/source/21, *Typing sheet*), while a
  text field on the player's screen has focus: the phone's own keyboard
  types straight into it, and the sheet carries no field of its own. Done
  puts the keyboard away. It rides above the keyboard, which covers the
  bottom of the page rather than shortening it. A tap on its words brings
  the keyboard back if it was put away another way.
-->
<script>
  let { open = false, ondone = () => {}, onkeyboard = () => {} } = $props();

  let lift = $state(0);
  $effect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const fit = () => (lift = Math.max(0, window.innerHeight - (vv.height + vv.offsetTop)));
    fit();
    vv.addEventListener('resize', fit);
    vv.addEventListener('scroll', fit);
    return () => {
      vv.removeEventListener('resize', fit);
      vv.removeEventListener('scroll', fit);
    };
  });
</script>

<div class="sheet" class:is-open={open} style:--lift={`${lift}px`} aria-hidden={!open} inert={!open}>
  <button class="label" type="button" onclick={onkeyboard}>Typing on the player’s screen</button>
  <button class="done" type="button" onclick={ondone}>Done</button>
</div>

<style>
  .sheet {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 40;
    background: #16232c;
    border-top: 1px solid rgba(233, 238, 242, 0.16);
    border-radius: 20px 20px 0 0;
    padding: 14px 16px 18px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 -10px 32px rgba(0, 0, 0, 0.6);
    transform: translateY(calc(100% + 24px));
    transition: transform 260ms cubic-bezier(0.32, 0.72, 0, 1);
  }
  .sheet.is-open {
    transform: translateY(calc(-1 * var(--lift, 0px)));
  }
  .label {
    flex: 1;
    min-width: 0;
    border: 0;
    padding: 0;
    background: none;
    text-align: left;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
    cursor: text;
  }
  .done {
    height: 50px;
    padding: 0 20px;
    border-radius: 14px;
    border: 0;
    display: grid;
    place-items: center;
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    background: #7ed6bc;
    color: #0d151c;
    cursor: pointer;
    flex-shrink: 0;
  }
  .done:active {
    transform: scale(0.96);
  }
</style>
