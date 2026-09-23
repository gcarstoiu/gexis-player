// Re-render the gexis boot frames from Claude Design's own render/frame.js.
//
// This harness changes three numbers in their wavefront tracks and nothing
// else. Both changes exist because the mark grew at 2d446d5 (tile edge
// 28 -> 115 design px) and the wavefronts were not re-fitted to it.
//
// The geometry everything below is derived from, all in frame.js's own terms:
//
//   T    = 115            tile edge
//   G    = T*6.5/28       = 26.70   gap
//   R    = T*7.5/28       = 30.80   tile corner radius
//   DIA  = (2T+G)*sqrt(2) = 363.0   the diamond the four tiles span
//   RR   = DIA*1.163/2    = 211.1   the radius a wave scale of 1.0 means
//   cy   = 297.8                    mark centre, high on an 800px canvas so
//                                   the wordmark and SOUND fit beneath it
//
//   tile outer radius = (T+G)/2*sqrt(2) + ((T/2 - R)*sqrt(2) + R)
//                     = 100.2 + 68.6 = 168.8
//
// Note that is 168.8, not DIA/2 = 181.5: the tiles are ROUNDED squares, so
// their corners fall short of the ideal diamond's points. 181.5 is the safe
// over-estimate and 168.8 is the truth.
import { createCanvas, GlobalFonts } from '@napi-rs/canvas'
import fs from 'node:fs'

GlobalFonts.registerFromPath('fonts/BricolageGrotesque.ttf', 'BG')
GlobalFonts.registerFromPath('fonts/DMMono-Medium.ttf', 'DMM')

// --- 1. where a wavefront is born -----------------------------------------
// Was 0.52 -> 110px, inside a mark reaching 168.8px, so every ring was drawn
// behind the tiles and cut into arcs for the first quarter of its travel.
// That is what George reported as "small lines in the pictogram with each
// pulse". 0.93 -> 196.3px clears the tiles by 27.5px.
const START = 0.93

// --- 2. where it stops being visible --------------------------------------
// The mark centre is 297.8px from the top of the screen and the rings ran to
// 401px, so 20 of the 50 pulse frames had an arc sliced flat by the top edge
// (George, on the panel, 2026-09-20: "the rings were slightly clipped").
// Fixing 1 made this worse, 16 frames -> 20, by pushing every ring further
// out; the two were traded without the second being measured.
//
// George chose to keep the expansion and let the wave dissipate before it
// reaches the edge, rather than cap the travel and tighten the ripple.
//
// A ring is invisible once its opacity track reaches zero, so each track's
// zero-crossing moves to the frame at which the ring is at 293px - the top
// edge less half the 8.2px stroke. Solving r(p) = RR*(START + (1.9-START) *
// (p-p0)/(p1-p0)) = 293 for each wave's own p0/p1:
const FADE1 = 41.3   // was 74, w1s runs 12 -> 74
const FADE2 = 54.3   // was 86, w2s runs 26 -> 86

// Two outputs, and which one you get depends on the path.
//
//   node render.mjs ../theme/still.png   the single still the boot shows today
//   node render.mjs ../theme             all 100 frames of the animation
//
// The still is frame 100, which is pixel-identical to frame 51: the pulse's
// rest state, so it carries the mark, the wordmark, SOUND and the faded halo
// and no wavefronts. That is the frame George asked for on 2026-09-20 when
// he replaced the animation with a still, and it is also what `swaybg` has
// always shown, so the splash and the wallpaper are now the same file.
//
// The animation is kept renderable on purpose. It is not built today, but
// removing the ability to make it again would make going back a re-import,
// and re-importing is what produced two wrong sets.
const OUT = process.argv[2] ?? '../theme'
const STILL = OUT.endsWith('.png')
const FRAMES = STILL ? [100] : (process.argv[3] ? process.argv[3].split(',').map(Number) : null)

let src = fs.readFileSync('frame.js', 'utf8')
const edits = [
  [/w1s:\s*\[\[0,\.52\],\[12,\.52\]/, `w1s:  [[0,${START}],[12,${START}]`],
  [/w2s:\s*\[\[0,\.52\],\[26,\.52\]/, `w2s:  [[0,${START}],[26,${START}]`],
  [/w1o:\s*\[\[0,0\],\[12,0\],\[20,\.48\],\[74,0\],\[100,0\]\]/,
   `w1o:  [[0,0],[12,0],[20,.48],[${FADE1},0],[100,0]]`],
  [/w2o:\s*\[\[0,0\],\[26,0\],\[34,\.3\],\[86,0\],\[100,0\]\]/,
   `w2o:  [[0,0],[26,0],[34,.3],[${FADE2},0],[100,0]]`],
]
// Every edit must bite. A silently-unmatched pattern would render Claude
// Design's frames unchanged and look like a successful run, which is how
// both wrong sets reached the device.
for (const [pattern, replacement] of edits) {
  const before = src
  src = src.replace(pattern, replacement)
  if (src === before) throw new Error(`pattern did not match, refusing to render: ${pattern}`)
}

const mod = new Function(src + '\n;return { renderFrame };')()
// For a still, create the containing directory if the path names one - and
// nothing at all if it does not, or `still.png` becomes a directory.
const dir = STILL ? (OUT.includes('/') ? OUT.replace(/\/[^/]*$/, '') : null) : OUT
if (dir) fs.mkdirSync(dir, { recursive: true })
for (const n of (FRAMES ?? Array.from({ length: 100 }, (_, i) => i + 1))) {
  const c = mod.renderFrame(n, (w, h) => createCanvas(w, h))
  const path = STILL ? OUT : `${OUT}/boot-${String(n).padStart(4, '0')}.png`
  fs.writeFileSync(path, c.encodeSync('png'))
}
console.log(STILL
  ? `rendered the still (frame 100) to ${OUT}`
  : `rendered ${(FRAMES ?? { length: 100 }).length} frames to ${OUT}/`)
console.log(`  wave start ${START} (${(211.1 * START).toFixed(1)}px, tiles reach 168.8px)`)
console.log(`  fade out at ${FADE1} / ${FADE2} (top edge is 297.8px from the mark centre)`)
