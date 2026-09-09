const FLAG_CODES: Record<string, string> = {
  afghanistan: 'af',
  australia: 'au',
  bangladesh: 'bd',
  england: 'gb-eng',
  india: 'in',
  ireland: 'ie',
  'new zealand': 'nz',
  pakistan: 'pk',
  'south africa': 'za',
  'sri lanka': 'lk',
  'west indies': 'wi',
  zimbabwe: 'zw',
  'united states': 'us',
  'united states of america': 'us',
  usa: 'us',
  canada: 'ca',
  netherlands: 'nl',
  scotland: 'gb-sct',
  namibia: 'na',
  nepal: 'np',
  'united arab emirates': 'ae',
  uae: 'ae',
  oman: 'om',
  'papua new guinea': 'pg',
  png: 'pg',
  'hong kong': 'hk',
  kenya: 'ke',
  uganda: 'ug',
  jersey: 'je',
  guernsey: 'gg',
}

type FlagSize = 'sm' | 'md' | 'lg'

const FLAG_SIZE_CLASS: Record<FlagSize, string> = {
  sm: 'country-flag-sm',
  md: 'country-flag-md',
  lg: 'country-flag-lg',
}

interface CountryFlagProps {
  team: string | null | undefined
  size?: FlagSize
  className?: string
}

function normalizedTeamName(team: string) {
  return team
    .trim()
    .toLowerCase()
    .replace(/\s+(men|women|xi|a)$/i, '')
    .replace(/\s+/g, ' ')
}

function initials(team: string) {
  const words = team.trim().split(/\s+/).filter(Boolean)
  if (words.length > 1) return words.slice(0, 2).map((word) => word[0]).join('').toUpperCase()
  return team.slice(0, 2).toUpperCase() || '?'
}

export default function CountryFlag({ team, size = 'md', className = '' }: CountryFlagProps) {
  const label = team || 'Unknown team'
  const code = team ? FLAG_CODES[normalizedTeamName(team)] : undefined
  const classes = `country-flag ${FLAG_SIZE_CLASS[size]} ${className}`.trim()

  if (!code) {
    return <span className={`${classes} country-flag-fallback`} aria-label={label}>{initials(label)}</span>
  }

  return (
    <span className={classes} title={label}>
      <img src={`/assets/flags/${code}.svg`} alt={`${label} flag`} loading="lazy" draggable={false} />
    </span>
  )
}
