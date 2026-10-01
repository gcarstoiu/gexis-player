// SPDX-License-Identifier: GPL-3.0-or-later
//
// The bar strip's lyrics, worked out exactly as now playing works them out
// (NowPlaying.svelte: `synced`, `sungLines`, `anchor`, `singing`). Kept as
// plain functions here rather than lifted out of NowPlaying, so the panel's
// screen is not touched by the bar's arrival; if one changes, change both.

// An LRC body is `[mm:ss.xx] text` per line; unstamped lines are headers.
const LRC = /^\[(\d+):(\d+(?:\.\d+)?)\]\s?(.*)$/;

/** Every stamped line, in time order. */
export function parseSynced(body) {
  if (!body) return [];
  const out = [];
  for (const line of body.split('\n')) {
    const match = LRC.exec(line.trim());
    if (!match) continue;
    out.push({ at: Number(match[1]) * 60 + Number(match[2]), text: match[3].trim() });
  }
  return out.sort((a, b) => a.at - b.at);
}

/** The lines with words, each remembering where it sat among all of them:
 *  a stamped line with no words is timing, not a lyric. */
export const sungOf = (synced) => synced.map((line, i) => ({ ...line, src: i })).filter((l) => l.text);

/** Which stamped line the clock is on, or -1 before the first. */
export function activeAt(synced, at) {
  let index = -1;
  for (let i = 0; i < synced.length; i += 1) {
    if (synced[i].at <= at) index = i;
    else break;
  }
  return index;
}

/** Which sung line the strip rests on: the last one sung, held through a gap
 *  and after the last word. */
export function anchorOf(sung, active) {
  if (!sung.length) return -1;
  let n = 0;
  for (let i = 0; i < sung.length; i += 1) {
    if (sung[i].src <= active) n = i;
    else break;
  }
  return n;
}
