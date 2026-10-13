import type { Accessory } from '../agents'

export type Mood = 'idle' | 'working' | 'talking' | 'done' | 'away'

interface Props {
  color: string
  accessory: Accessory
  mood?: Mood
  size?: number
}

/** A little Labubu agent. Each role wears its own accessory; mood drives the animation. */
export default function Labubu({ color, accessory, mood = 'idle', size = 84 }: Props) {
  return (
    <svg className={`labubu mood-${mood}`} width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
      <ellipse className="lb-shadow" cx="50" cy="95" rx="24" ry="4" />
      <g className="lb-body">
        {/* ears */}
        <path d="M30 34 L22 6 L42 28 Z" fill={color} />
        <path d="M70 34 L78 6 L58 28 Z" fill={color} />
        <path d="M30 30 L26 14 L37 27 Z" fill="#ffe3f0" opacity=".7" />
        <path d="M70 30 L74 14 L63 27 Z" fill="#ffe3f0" opacity=".7" />
        {/* head + face */}
        <ellipse cx="50" cy="56" rx="34" ry="33" fill={color} />
        <ellipse cx="50" cy="61" rx="24" ry="20" fill="#ffe8f3" />
        <g className="lb-eyes">
          <ellipse cx="40" cy="56" rx="5" ry="6" fill="#0b0b0d" />
          <ellipse cx="60" cy="56" rx="5" ry="6" fill="#0b0b0d" />
          <circle cx="41.6" cy="54" r="1.6" fill="#fff" />
          <circle cx="61.6" cy="54" r="1.6" fill="#fff" />
        </g>
        <ellipse cx="33" cy="66" rx="4" ry="2.4" fill={color} opacity=".45" />
        <ellipse cx="67" cy="66" rx="4" ry="2.4" fill={color} opacity=".45" />
        {/* the famous toothy grin */}
        <path className="lb-mouth" d="M38 69 Q50 79 62 69" stroke="#0b0b0d" strokeWidth="2.4" fill="#fff" strokeLinejoin="round" />
        <path d="M42 70.5 L44 74.5 L46 72 M48 72.8 L50 76.5 L52 72.8 M54 72 L56 74.5 L58 70.5"
          stroke="#0b0b0d" strokeWidth="1.3" fill="none" strokeLinejoin="round" />
        <Gear accessory={accessory} color={color} />
      </g>
    </svg>
  )
}

function Gear({ accessory, color }: { accessory: Accessory; color: string }) {
  switch (accessory) {
    case 'crown':
      return (
        <g>
          <path d="M34 26 L36 12 L43 20 L50 8 L57 20 L64 12 L66 26 Z" fill="#ffd1e8" stroke="#0b0b0d" strokeWidth="1.6" />
          <circle cx="50" cy="19" r="2.2" fill={color} />
        </g>
      )
    case 'box':
      return (
        <g>
          <rect x="62" y="74" width="22" height="18" rx="2" fill="#2a1520" stroke="#ffb3da" strokeWidth="1.6" />
          <path d="M62 80 H84 M73 74 V80" stroke="#ffb3da" strokeWidth="1.4" />
        </g>
      )
    case 'glasses':
      return (
        <g fill="none" stroke="#0b0b0d" strokeWidth="2">
          <circle cx="40" cy="56" r="9" />
          <circle cx="60" cy="56" r="9" />
          <path d="M49 56 H51 M31 54 L24 51 M69 54 L76 51" />
        </g>
      )
    case 'hardhat':
      return (
        <g>
          <path d="M24 36 Q50 4 76 36 Z" fill="#ffd1e8" stroke="#0b0b0d" strokeWidth="1.6" />
          <rect x="20" y="34" width="60" height="6" rx="3" fill="#ffd1e8" stroke="#0b0b0d" strokeWidth="1.6" />
          <path d="M50 12 V34" stroke="#0b0b0d" strokeWidth="1.4" />
        </g>
      )
    case 'headset':
      return (
        <g fill="none" stroke="#0b0b0d" strokeWidth="2.6">
          <path d="M18 58 Q18 20 50 20 Q82 20 82 58" />
          <rect x="12" y="52" width="10" height="16" rx="4" fill="#ffd1e8" />
          <rect x="78" y="52" width="10" height="16" rx="4" fill="#ffd1e8" />
          <path d="M17 68 Q22 82 38 78" strokeWidth="2" />
          <circle cx="39" cy="78" r="2.6" fill="#0b0b0d" />
        </g>
      )
  }
}
