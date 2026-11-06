/* Phase 29 theme copies. Run in the project's script runner:
     eval(await readFile('design/source/29/build.js')); await build29();
   Takes the recolour from design/source/28/build.js as it is (same families,
   veil, weave angle, mono, radii) and applies it to Room Correction.dc.html,
   writing <id>-room.dc.html for the five kept themes. The source is never written. */
async function build29() {
  const w = {}; (new Function('window', await readFile('design/source/28/themes.js')))(w);
  const KEPT = ['bauhaus', 'sage', 'velvet', 'ink', 'gauge'];
  const THEMES = w.GX_THEMES.filter(t => KEPT.includes(t.id));
  const b28 = await readFile('design/source/28/build.js');
  const body = b28.slice(b28.indexOf('  const hex2'), b28.indexOf('  const SRC'));
  const recolour = new Function(body + '\nreturn recolour;')();
  const src = await readFile('design/source/29/Room Correction.dc.html');
  for (const T of THEMES) {
    const link = `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=${T.monoGF}&display=swap" />`;
    const t = recolour(src, T).replace('<helmet>', '<helmet>\n' + link);
    await saveFile(`design/source/29/${T.id}-room.dc.html`, t);
  }
  return THEMES.map(t => t.id);
}
