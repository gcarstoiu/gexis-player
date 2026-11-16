// SPDX-License-Identifier: GPL-3.0-or-later
// The phone's radio glyphs, as design/source/31's phone artboards (H01-H24)
// draw them: stroked paths on a 24-unit box, round caps and joins.

export const RADIO = {
  search: 'M15.3 15.3l5.2 5.2',
  pin: 'M12 21s-6.4-6-6.4-11a6.4 6.4 0 0 1 12.8 0c0 5-6.4 11-6.4 11z',
  globe: 'M3.6 12h16.8',
  speech: 'M5 5.5h14a1.8 1.8 0 0 1 1.8 1.8v8a1.8 1.8 0 0 1-1.8 1.8H11l-4.4 3.4V17.1H5a1.8 1.8 0 0 1-1.8-1.8v-8A1.8 1.8 0 0 1 5 5.5z',
  link: ['M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1', 'M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1'],
  back: 'M14.5 5.5 8 12l6.5 6.5',
  chevron: 'M9.5 5.5 16 12l-6.5 6.5',
  clear: 'M6.5 6.5l11 11M17.5 6.5l-11 11',
  grip: 'M5 8h14M5 12h14M5 16h14',
  minus: 'M6.5 12h11',
  bars: 'M6 19v-6M10 19V7M14 19v-9M18 19v-4',
  spinner: 'M12 3.5a8.5 8.5 0 1 1-8.5 8.5',
  warn: ['M12 4 2.8 19.5h18.4L12 4z', 'M12 10v4.2'],
  cloudOff: ['M7 18.5h10.2a3.8 3.8 0 0 0 .9-7.5 6 6 0 0 0-10.3-3.3M5 9.6A4.5 4.5 0 0 0 7 18.5', 'M3.5 3.5l17 17'],
  remote: 'M10.5 13h3M10.5 16h3',
};
