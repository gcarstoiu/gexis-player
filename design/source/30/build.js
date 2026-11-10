/* Phase 30 theme copies. Run in the project's script runner:
     eval(await readFile('design/source/30/build.js')); await build30();
   Applies Phase 28's recolour (design/source/28/build.js, unchanged) to
   Room Correction.dc.html and RoomChart.dc.html, writing <id>-room.dc.html and
   <id>-RoomChart.dc.html for the five kept themes. Each themed page imports its
   own themed chart. The sources are never written. */
async function build30() {
  const w = {}; (new Function('window', await readFile('design/source/28/themes.js')))(w);
  const KEPT = ['bauhaus', 'sage', 'velvet', 'ink', 'gauge'];
  const THEMES = w.GX_THEMES.filter(t => KEPT.includes(t.id));
  const b28 = await readFile('design/source/28/build.js');
  const recolour = new Function(b28.slice(b28.indexOf('  const hex2'), b28.indexOf('  const SRC')) + '\nreturn recolour;')();
  const page = await readFile('design/source/30/Room Correction.dc.html');
  const chart = await readFile('design/source/30/RoomChart.dc.html');
  for (const T of THEMES) {
    const link = `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=${T.monoGF}&display=swap" />`;
    const a = recolour(page, T).replace('<helmet>', '<helmet>\n' + link).split('name="RoomChart"').join(`name="${T.id}-RoomChart"`);
    const b = recolour(chart, T).replace('<helmet>', '<helmet>\n' + link);
    await saveFile(`design/source/30/${T.id}-room.dc.html`, a);
    await saveFile(`design/source/30/${T.id}-RoomChart.dc.html`, b);
  }
  return THEMES.map(t => t.id);
}
