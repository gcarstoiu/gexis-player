// SPDX-License-Identifier: GPL-3.0-or-later
//
// Play/pause that flips its icon on press (George, 2026-09-16, amending
// ADR-0037 §4): Bluetooth reports a pause about 4.5 s late (measured), and a
// button that seems not to have heard reads as broken. Only the icon is
// ahead of the renderer, and if it has not confirmed within CONFIRM_MS the
// icon goes back to the reported state. Shared by now playing and the mini
// strip, so both buttons behave the same.
import { untrack } from 'svelte';
import { sendTransport } from './state.js';

const CONFIRM_MS = 8000;

/** `transport()` and `active()` read the current values. Call during
 *  component setup. */
export function playToggle(transport, active) {
  let pressed = $state(null); // 'playing' | 'paused': what the last press asked for
  let timer;

  function forget() {
    clearTimeout(timer);
    pressed = null;
  }
  $effect(() => {
    if (pressed !== null && transport() === pressed) untrack(forget);
  });
  $effect(() => {
    active();
    untrack(forget);
  });

  const shows = () => pressed ?? (transport() === 'playing' ? 'playing' : 'paused');

  async function toggle() {
    const want = shows() === 'playing' ? 'paused' : 'playing';
    clearTimeout(timer);
    pressed = want;
    timer = setTimeout(forget, CONFIRM_MS);
    try {
      await sendTransport(want === 'playing' ? 'play' : 'pause');
    } catch (err) {
      forget();
      console.info('transport:', err.message);
    }
  }

  return {
    get shows() {
      return shows();
    },
    toggle,
  };
}
