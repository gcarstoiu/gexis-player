// SPDX-License-Identifier: GPL-3.0-or-later
//: **The player's theme** (ADR-0171): the setting, as one of themeRule.js's
//: themes, or null for Deep Teal. The page wears it as `data-theme`
//: (App.svelte); a script that hands a colour to a style passes it through
//: `tone(colour, $theme)`.
import { derived } from 'svelte/store';
import { settingValues } from './settings.js';
import { themeNamed } from './themeRule.js';

export const theme = derived(settingValues, ($values) => themeNamed($values.theme));
