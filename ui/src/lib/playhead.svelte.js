// SPDX-License-Identifier: GPL-3.0-or-later
//
// The playing position, advanced locally between broadcasts. Shared by now
// playing and the mini strip, which show the same track.
//
// Position is published at a rate that differs by source, so the position
// advances locally and re-anchors only when the published values change —
// every broadcast repeats the last position, including volume-only ones.
import { untrack } from 'svelte';

/** `read()` returns the current metadata. Call during component setup. */
export function playhead(read) {
  let anchor = $state({ position: null, duration: null, playing: false, at: 0 });
  let now = $state(performance.now());

  $effect(() => {
    const metadata = read();
    const position = metadata?.position ?? null;
    const duration = metadata?.duration ?? null;
    const playing = metadata?.transport === 'playing';
    const a = untrack(() => anchor);
    if (position !== a.position || duration !== a.duration || playing !== a.playing) {
      const at = performance.now();
      anchor = { position, duration, playing, at };
      now = at;
    }
  });

  $effect(() => {
    if (!anchor.playing || anchor.position === null) return;
    const id = setInterval(() => (now = performance.now()), 500);
    return () => clearInterval(id);
  });

  const hasPosition = () => anchor.position !== null && !!anchor.duration;
  const elapsed = () => {
    if (!hasPosition()) return 0;
    const moved = anchor.playing ? (now - anchor.at) / 1000 : 0;
    return Math.min(anchor.position + moved, anchor.duration);
  };

  return {
    get hasPosition() {
      return hasPosition();
    },
    get duration() {
      return anchor.duration;
    },
    get elapsed() {
      return elapsed();
    },
    get percent() {
      return hasPosition() ? (elapsed() / anchor.duration) * 100 : 0;
    },
  };
}

export const mmss = (s) => {
  s = Math.max(0, Math.floor(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};
