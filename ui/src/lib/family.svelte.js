// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0109: which family of layouts this screen gets. Chromium's scale
// factor makes a Standard screen 1280 logical px wide and a bar 400 logical
// px tall; the family follows from the shape that leaves - Standard for
// aspect 1.5-1.8, Bar for 3-5. The boundary sits between the two (2.4), so
// a screen just outside either range still lands in the nearer one.

const BAR_FROM = 2.4;

function measure() {
  if (typeof window === 'undefined') return { width: 1280, height: 800 };
  return { width: window.innerWidth || 1280, height: window.innerHeight || 800 };
}

let size = $state(measure());
if (typeof window !== 'undefined') {
  window.addEventListener('resize', () => (size = measure()));
}

export const screen = {
  get width() { return size.width; },
  get height() { return size.height; },
  get family() { return size.width / size.height >= BAR_FROM ? 'bar' : 'standard'; },
};
