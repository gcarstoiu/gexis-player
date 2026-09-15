// SPDX-License-Identifier: GPL-3.0-or-later
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    // Everything hashed under assets/, so the daemon serves exactly two
    // things: `/` (index.html) and `/assets/*`. Keeping the built output
    // to one directory is what lets wsserver.py's static route stay
    // narrow enough not to shadow `/state` or the command routes
    // (ADR-0028).
    assetsDir: 'assets',
    // The panel's Chromium is pinned by the image (ADR-0023), so there is
    // exactly one browser to target locally. A remote browser is the
    // looser constraint - this is recent enough for both without
    // transpiling down to something nobody runs.
    target: 'es2022',
    emptyOutDir: true,
  },
  server: {
    // `npm run dev` against a real daemon: the UI is served by Vite but
    // talks to gexis-core on the device. Overridable so it can point at
    // localhost when the daemon runs here instead.
    proxy: {
      '/state': {
        target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090',
        ws: true,
        changeOrigin: true,
      },
      '/renderer': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/volume': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/idle': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
    },
  },
});
