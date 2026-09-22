import type { CSSProperties } from 'react';

export type LogoLetter = 'g' | 'e' | 'i' | 's';

export interface LogoProps {
  /** Width of the rotated mark in px. Letters are dropped below 28. Default 96. */
  size?: number;
  /** The property signing itself: that tile keeps its hue, the other three
   *  drop to slate. Unset means the master mark, every tile lit.
   *  g gazette · e engine room · i inbox · s sound. */
  lead?: LogoLetter | null;
  /** Set the word "gexis" beside the mark. Default false — the mark alone. */
  wordmark?: boolean;
  /** Mono sub-label under the wordmark, e.g. "sound". Needs wordmark. */
  sublabel?: string | null;
  /** Flatten the mark to one colour — a CSS colour or token reference. For
   *  single-colour grounds, print and embossing. Overrides lead. */
  mono?: string | null;
  style?: CSSProperties;
}

export function Logo(props: LogoProps): JSX.Element;
