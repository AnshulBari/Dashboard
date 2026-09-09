import { useEffect, useMemo, useState } from 'react'

const PLAYER_PORTRAITS: Record<string, string> = {
  'babar azam': 'babar-azam.jpg',
  'ben stokes': 'ben-stokes.jpg',
  'harry brook': 'harry-brook.jpg',
  'jasprit bumrah': 'jasprit-bumrah.jpg',
  'joe root': 'joe-root.jpg',
  'jofra archer': 'jofra-archer.jpg',
  'jos buttler': 'jos-buttler.jpg',
  'kagiso rabada': 'kagiso-rabada.jpg',
  'kane williamson': 'kane-williamson.jpg',
  'kl rahul': 'kl-rahul.jpg',
  'mitchell marsh': 'mitchell-marsh.jpg',
  'ms dhoni': 'ms-dhoni.jpg',
  'pat cummins': 'pat-cummins.jpg',
  'quinton de kock': 'quinton-de-kock.jpg',
  'rashid khan': 'rashid-khan.jpg',
  'ravindra jadeja': 'ravindra-jadeja.jpg',
  'rishabh pant': 'rishabh-pant.jpg',
  'rohit sharma': 'rohit-sharma.jpg',
  'shakib al hasan': 'shakib-al-hasan.jpg',
  'shubman gill': 'shubman-gill.jpg',
  'sikandar raza': 'sikandar-raza.jpg',
  'steve smith': 'steve-smith.jpg',
  'temba bavuma': 'temba-bavuma.png',
  'towhid hridoy': 'towhid-hridoy.jpg',
  'tawhid hridoy': 'towhid-hridoy.jpg',
  'travis head': 'travis-head.jpg',
  'virat kohli': 'virat-kohli.jpg',
  'will jacks': 'will-jacks.jpg',
}

type PortraitSize = 'xs' | 'sm' | 'md' | 'hero' | 'spotlight'

const PORTRAIT_SIZE_CLASS: Record<PortraitSize, string> = {
  xs: 'player-portrait-xs',
  sm: 'player-portrait-sm',
  md: 'player-portrait-md',
  hero: 'player-portrait-hero',
  spotlight: 'player-portrait-spotlight',
}

interface PlayerPortraitProps {
  name: string | null | undefined
  fullName?: string | null
  imageUrl?: string | null
  size?: PortraitSize
  className?: string
  showStatus?: boolean
}

function normalize(name: string) {
  return name.trim().toLowerCase().replace(/[.'’]/g, '').replace(/\s+/g, ' ')
}

function initials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (words.length > 1) return words.slice(0, 2).map((word) => word[0]).join('').toUpperCase()
  return name.slice(0, 2).toUpperCase() || '?'
}

export function playerPortraitUrl(name?: string | null, fullName?: string | null) {
  const candidates = [fullName, name].filter((value): value is string => Boolean(value))
  for (const candidate of candidates) {
    const file = PLAYER_PORTRAITS[normalize(candidate)]
    if (file) return `/assets/players/${file}`
  }
  return null
}

export default function PlayerPortrait({ name, fullName, imageUrl, size = 'md', className = '', showStatus = false }: PlayerPortraitProps) {
  const label = fullName || name || 'Unknown player'
  const localUrl = playerPortraitUrl(name, fullName)
  const sources = useMemo(
    () => Array.from(new Set([localUrl, imageUrl].filter((value): value is string => Boolean(value)))),
    [localUrl, imageUrl],
  )
  const sourceKey = sources.join('|')
  const [failedSources, setFailedSources] = useState<string[]>([])

  useEffect(() => setFailedSources([]), [sourceKey])

  const src = sources.find((source) => !failedSources.includes(source))
  const classes = `player-portrait ${PORTRAIT_SIZE_CLASS[size]} ${src ? '' : 'player-portrait-fallback'} ${className}`.trim()

  return (
    <span className={classes} title={label} aria-label={label}>
      {src ? (
        <img
          src={src}
          alt={label}
          loading={size === 'hero' || size === 'spotlight' ? 'eager' : 'lazy'}
          draggable={false}
          onError={() => setFailedSources((failed) => failed.includes(src) ? failed : [...failed, src])}
        />
      ) : <span>{initials(label)}</span>}
      {showStatus && <i aria-hidden="true" />}
    </span>
  )
}
