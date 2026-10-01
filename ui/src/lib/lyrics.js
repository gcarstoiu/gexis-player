// SPDX-License-Identifier: GPL-3.0-or-later
//
// Synced lyrics, followed: shared by the panel's Now Playing and the bar's
// strip (one copy since 2026-10-01).
//
// **A stamped line with no words is timing, not a lyric.** LRC bodies use
// them for the run-in, for instrumental breaks and for the outro, and
// following them literally leaves the screen blank in the middle of a song
// and again at the end - which reads as a fault rather than as silence
// (George, on the panel, 2026-09-20). So the words are kept apart from the
// timing (`sungOf`), each remembering where it sat so the clock can still be
// followed, and the screen rests on the last line sung (`anchorOf`).

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
