// SPDX-License-Identifier: GPL-3.0-or-later
// Fonts are bundled, never fetched: the panel may have no internet.
import '@fontsource-variable/nunito-sans/wght.css';
import '@fontsource/ibm-plex-mono/300.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/600.css';
import '@fontsource/ibm-plex-mono/700.css';
import './styles/tokens.css';
import { mount } from 'svelte';
import App from './App.svelte';

export default mount(App, { target: document.getElementById('app') });
