// SPDX-License-Identifier: GPL-3.0-or-later
// What the phone's remote asks of the player (ADR-0164). The routes are the
// mini player's and Home Assistant's: nothing here is new to the core but
// seeking.
import { derived, get } from 'svelte/store';
import {
  active, goTo, hidePeppy, panel, pressKey, requestDashboard, requestIdle, requestStandby, sendTransport, showPeppy,
} from '../../lib/state.js';

//: Which of the panel's views it shows, the dashboard and the idle screen
//: over the rest (the mini player's rule, ADR-0101 as amended 2026-10-21).
export const showing = derived([panel, active], ([$p, $a]) =>
  $p.dashboard?.shown ? 'room'
    : $p.idle ? 'idle'
    : $p.visualiser ? 'meters'
    : $a && $p.lyrics ? 'lyrics'
    : $a && $p.now ? 'playing'
    : 'home');

//: What a player is doing, in the design's three states: *Playing · Lyrion*,
//: *Paused · Spotify*, *Idle* (`/players` and this player alike).
export function said(p) {
  if (p?.transport === 'playing') return p.renderer ? `Playing · ${p.renderer}` : 'Playing';
  if (p?.transport === 'paused') return p.renderer ? `Paused · ${p.renderer}` : 'Paused';
  return 'Idle';
}

//: **One press at a time, in order**: a swipe of three steps is three
//: presses, and the third must not overtake the first.
let chain = Promise.resolve();
export function key(name) {
  chain = chain.then(() => pressKey(name).catch(() => {}));
  return chain;
}

//: **A view wakes the screen** (design: any view button, corner button or
//: pad input). The panel's own routes count as a touch; the visualiser, the
//: dashboard and the idle screen are asked for after standby is off.
async function awake() {
  if (get(panel).standby) await requestStandby(false);
}

export async function view(which, say = () => {}) {
  const p = get(panel);
  try {
    if (which === 'home') await goTo('home');
    else if (which === 'playing') await goTo(p.now ? 'minimise' : 'now');
    else if (which === 'lyrics') await goTo(p.lyrics ? 'track' : 'lyrics');
    else if (which === 'meters') {
      await awake();
      await (p.visualiser ? hidePeppy() : showPeppy());
    } else if (which === 'room') {
      await awake();
      await requestDashboard(!p.dashboard?.shown);
    } else if (which === 'idle') {
      await awake();
      await requestIdle(!p.idle);
    }
  } catch (err) {
    say(err.message);
  }
}

export const standby = (on) => requestStandby(on).catch(() => {});

export async function seek(position) {
  try {
    await sendTransport('seek', { position });
  } catch {
    // The bar goes back to where the player says it is.
  }
}
