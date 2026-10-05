// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0101 as amended 2026-10-05: the phone's Lyrics toggle, between App
// and whichever Now Playing the screen family draws (NowPlaying.svelte, or
// BarNowPlaying.svelte on a bar).
import { writable } from 'svelte/store';

//: An ask from the phone: `{ on: true }` for the lyrics, `{ on: false }` for
//: the Track tab. Now Playing applies it and clears it, so a screen that
//: mounts later does not apply it again.
export const lyricsAsk = writable(null);

//: Whether Now Playing has its lyrics up - App reports it to the core only
//: while Now Playing is what the glass shows.
export const lyricsShown = writable(false);
