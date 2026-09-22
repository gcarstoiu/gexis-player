import type { CSSProperties } from 'react';

export type LogoLetter = 'g' | 'e' | 'i' | 's';

export interface BootScreenProps {
  /** Which letter the travel settles on — the property being booted.
   *  Default 's', the player. The travel order is always g e i s; only which
   *  tile HOLDS changes. */
  lands?: LogoLetter;
  /** Mono sub-label under the wordmark. Defaults to the property's name;
   *  pass null for the mark and wordmark alone. */
  label?: string | null;
  /** Width of the MARK in px — not the screen. Everything else, including
   *  the wordmark (≈ 2.7× this) and the wavefront radii, derives from it.
   *  Default 114, which is what the device frames use at 1280×800. */
  size?: number;
  /** Which property's flourish runs during the pulse. Defaults to `lands`;
   *  pass null for none (the only safe override). */
  flourish?: LogoLetter | null;
  /** Intro length in seconds — plays once. Default 2. Below about 1.2 s the
   *  travel is too fast to read as a sweep. */
  intro?: number;
  /** Pulse length in seconds — loops for ever, starting when the intro ends.
   *  Default 2. */
  pulse?: number;
  style?: CSSProperties;
}

export function BootScreen(props: BootScreenProps): JSX.Element;
