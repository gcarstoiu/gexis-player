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
    // localhost when the daemon runs here instead. Every path the core
    // serves (wsserver.py's routes); `/state` and `/touchpad` are WebSockets.
    proxy: {
      '/state': {
        target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090',
        ws: true,
        changeOrigin: true,
      },
      '/renderer': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/volume': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/idle': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/library': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/renderers': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/surface': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/settings': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/transport': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/menus': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/radio': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/panel': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/peppy': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      // Before `/touch`: a key is a prefix, and the first that matches wins.
      '/touchpad': {
        target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090',
        ws: true,
        changeOrigin: true,
      },
      '/touch': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/screen-new': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/screen': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/setup': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/notices': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/network': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/report': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/hardware-report': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/bluetooth': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/skins': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/plugins': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
      '/enrichment': { target: process.env.GEXIS_CORE ?? 'http://gexis.local:8090' },
    },
  },
});
