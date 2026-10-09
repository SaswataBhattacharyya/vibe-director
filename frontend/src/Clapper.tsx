import { useEffect, useState } from 'react';

/** The PR22 mascot geometry, kept as a neutral hello animation for real navigation. */
export default function Clapper({ route }: { route: string }) {
  const [replay, setReplay] = useState(0);
  useEffect(() => setReplay(value => value + 1), [route]);

  return <button
    className="clapper-replay"
    type="button"
    aria-label="Replay Clapper hello"
    title="Replay Clapper hello"
    onClick={() => setReplay(value => value + 1)}
  >
    <svg key={replay} className="mascot is-playing" data-pose="neutral" viewBox="0 0 320 300" role="img" aria-label="Clapperboard mascot, hello moment">
      <ellipse cx="162" cy="274" rx="105" ry="9" className="mascot-shadow" />
      <g className="body-group" transform="rotate(0 160 180)">
        <rect x="65" y="108" width="190" height="153" rx="13" className="mascot-body" />
        <path d="M65 108h190v43H65z" className="mascot-top" />
        <path d="M73 108h18l34 43h-18zM121 108h18l34 43h-18zM169 108h18l34 43h-18zM217 108h18l20 26v17h-6z" className="mascot-stripe" />
        <path d="M65 151h190" className="mascot-seam" />
        <g className="eye-group">
          <ellipse cx="120" cy="199" rx="18" ry="20" className="mascot-eye" />
          <g className="gaze"><circle className="pupil" cx="120" cy="199" r="8" /><circle cx="117" cy="195" r="2.7" className="mascot-glint" /></g>
          <ellipse cx="200" cy="199" rx="18" ry="20" className="mascot-eye" />
          <g className="gaze"><circle className="pupil" cx="200" cy="199" r="8" /><circle cx="197" cy="195" r="2.7" className="mascot-glint" /></g>
        </g>
        <g className="lid-group" transform="rotate(-8 64 113)">
          <path d="M53 72L256 41l9 49L62 121z" className="mascot-lid" />
          <path d="M78 68l18-3 24 47-18 3zM129 60l18-3 24 47-18 3zM180 52l18-3 24 47-18 3zM231 44l18-3 16 31v18l-5 1z" className="mascot-stripe" />
        </g>
        <circle cx="65" cy="110" r="9" className="mascot-print" />
      </g>
    </svg>
  </button>;
}
