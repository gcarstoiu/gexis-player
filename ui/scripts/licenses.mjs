// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0099: the licences of what is bundled into the panel's screens go with
// them, into dist/licenses/ - the Svelte runtime, Vite's module-preload helper,
// the two fonts (OFL-1.1 asks for its text with every copy), and uqr, which
// draws the setup screen's QR codes (ADR-0104).
import { copyFileSync, mkdirSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const BUNDLED = ['svelte', 'vite', '@fontsource-variable/nunito-sans', '@fontsource/ibm-plex-mono', 'uqr'];
const out = join('dist', 'licenses');

for (const name of BUNDLED) {
  const dir = join('node_modules', name);
  const found = readdirSync(dir).filter((f) => /^(licen[cs]e|copying|notice)/i.test(f));
  if (!found.length) throw new Error(`${name} has no licence file to ship`);
  const target = join(out, name.replace('/', '__'));
  mkdirSync(target, { recursive: true });
  for (const file of found) copyFileSync(join(dir, file), join(target, file));
}
console.log(`licenses: ${BUNDLED.length} packages into ${out}`);
