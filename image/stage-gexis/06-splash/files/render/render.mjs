// Re-render the gexis boot frames from Claude Design's own render/frame.js.
// The only thing this harness changes is the wavefronts' start radius, via
// RING_START; everything else is their renderer, unmodified.
import { createCanvas, GlobalFonts } from '@napi-rs/canvas'
import fs from 'node:fs'

GlobalFonts.registerFromPath('fonts/BricolageGrotesque.ttf', 'BG')
GlobalFonts.registerFromPath('fonts/DMMono-Medium.ttf', 'DMM')

const RING_START = parseFloat(process.argv[2] ?? '0.52')
const OUT = process.argv[3] ?? 'out'
const FRAMES = process.argv[4] ? process.argv[4].split(',').map(Number) : null

let src = fs.readFileSync('frame.js', 'utf8')
// the one edit: where each wavefront is born. 0.52 puts it at 109.8px, inside
// a mark whose tiles reach 181.5px, so it is clipped for the first quarter of
// its travel (the defect c77d4e3 fixed for the previous, smaller mark).
const before = src
src = src.replace(/w1s:\s*\[\[0,\.52\],\[12,\.52\]/, `w1s:  [[0,${RING_START}],[12,${RING_START}]`)
src = src.replace(/w2s:\s*\[\[0,\.52\],\[26,\.52\]/, `w2s:  [[0,${RING_START}],[26,${RING_START}]`)
if (RING_START !== 0.52 && src === before) throw new Error('ring start not patched — the tracks did not match')

const mod = new Function(src + '\n;return { renderFrame };')()
fs.mkdirSync(OUT, { recursive: true })
const mk = (w, h) => createCanvas(w, h)
for (const n of (FRAMES ?? Array.from({ length: 100 }, (_, i) => i + 1))) {
  const c = mod.renderFrame(n, mk)
  fs.writeFileSync(`${OUT}/boot-${String(n).padStart(4, '0')}.png`, c.encodeSync('png'))
}
console.log(`rendered ${(FRAMES ?? {length:100}).length} frames to ${OUT}/ with ring start ${RING_START}`)
