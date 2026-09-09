import { Radio, WifiOff } from 'lucide-react'
import { useLiveMatches } from '@/hooks/useQueries'
import { SkeletonMatch } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import ErrorCard from '@/components/ui/ErrorCard'
import FormatBadge from '@/components/ui/FormatBadge'
import CountryFlag from '@/components/ui/CountryFlag'
import type { LiveMatch } from '@/lib/api'

const FULL_MEMBER_TEAMS = new Set([
  'afghanistan', 'australia', 'bangladesh', 'england', 'india', 'ireland',
  'new zealand', 'pakistan', 'south africa', 'sri lanka', 'west indies', 'zimbabwe',
])

function fullMemberName(team: string | null) {
  return (team || '').trim().toLowerCase().replace(/\s+(men|women|xi|a)$/i, '')
}

function isFullMemberMatch(match: LiveMatch) {
  return FULL_MEMBER_TEAMS.has(fullMemberName(match.team_a))
    && FULL_MEMBER_TEAMS.has(fullMemberName(match.team_b))
}

function fixtureTime(value: string | null) {
  if (!value) return 'Start time to be confirmed'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  }).format(parsed)
}

function statusLabel(status: string | null) {
  const normalized = status?.toLowerCase()
  if (normalized === 'live') return 'LIVE'
  if (normalized === 'upcoming' || normalized === 'scheduled') return 'UPCOMING'
  return 'FINAL'
}

function LiveMatchCard({ match }: { match: LiveMatch }) {
  const isLive = match.status?.toLowerCase() === 'live'
  return (
    <article className={`match-card p-5 ${isLive ? 'match-card-live' : ''}`}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <FormatBadge format={match.format || 'Match'} />
        <span className={isLive ? 'live-badge' : 'badge'}>
          {isLive && <span className="live-dot" />}{statusLabel(match.status)}
        </span>
      </div>
      <p className="mb-3 truncate text-[10px] text-gray-500">
        {match.competition || match.venue || 'International cricket'}
      </p>
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <span className="flex min-w-0 items-center gap-2"><CountryFlag team={match.team_a} size="sm" /><span className="truncate text-sm font-semibold text-gray-100">{match.team_a || 'TBA'}</span></span>
          {isLive && <p className="shrink-0 font-mono text-xs font-bold text-emerald-400">{match.score_team_a || '—'}</p>}
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="flex min-w-0 items-center gap-2"><CountryFlag team={match.team_b} size="sm" /><span className="truncate text-sm font-semibold text-gray-100">{match.team_b || 'TBA'}</span></span>
          {isLive && <p className="shrink-0 font-mono text-xs font-bold text-emerald-400">{match.score_team_b || '—'}</p>}
        </div>
      </div>
      <p className="mt-4 border-t border-white/[.06] pt-3 text-[10px] text-gray-400">
        {isLive
          ? (match.result || match.venue || 'Match update pending')
          : `${fixtureTime(match.start_time)}${match.venue ? ` · ${match.venue}` : ''}`}
      </p>
    </article>
  )
}

export default function Live() {
  const live = useLiveMatches()
  const providerMatches = (live.data?.data || []).filter(isFullMemberMatch)
  const liveMatches = providerMatches.filter((match) => match.status?.toLowerCase() === 'live')
  const upcomingMatches = providerMatches
    .filter((match) => ['upcoming', 'scheduled'].includes(match.status?.toLowerCase() || ''))
    .sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''))
  const displayedMatches = liveMatches.length ? liveMatches : upcomingMatches
  const liveAvailable = live.data?.provider_available ?? false

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <Radio className="h-5 w-5 text-emerald-400" />
          Live Center
        </h1>
        <p className="page-subtitle">
          Live Full Member scores, followed by the next scheduled international fixtures
        </p>
      </div>

      {/* Status banner */}
      <div className={`card-solid p-4 flex items-center gap-3 ${liveAvailable ? 'border-emerald-500/20' : 'border-amber-500/20'}`}>
        {liveAvailable ? (
          <>
            <span className={liveMatches.length ? 'live-badge' : 'badge'}>{liveMatches.length > 0 && <span className="live-dot" />}{liveMatches.length ? 'Live' : 'Upcoming'}</span>
            <span className="text-sm text-gray-300">Provider connected · Auto-refresh every 30s</span>
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-amber-400" />
            <span className="text-sm text-gray-400">
              Live and upcoming schedule provider is offline
            </span>
          </>
        )}
      </div>

      {/* Live matches */}
      {live.isError ? (
        <ErrorCard message="The live provider could not be reached" onRetry={() => live.refetch()} />
      ) : live.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <SkeletonMatch key={i} />)}
        </div>
      ) : displayedMatches.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedMatches.map((match) => <LiveMatchCard key={match.match_id} match={match} />)}
        </div>
      ) : (
        <EmptyState
          icon={<Radio className="h-10 w-10 text-gray-600" />}
          title={liveAvailable ? 'No live or upcoming matches' : 'Schedule feed unavailable'}
          message={liveAvailable ? 'No Full Member fixtures are currently listed.' : 'Connect CricketData.org to load live scores and upcoming fixtures.'}
        />
      )}

      {/* Data source footer */}
      <div className="text-center py-4">
        <p className="text-[10px] text-gray-600">
          Live scores and fixture schedule: CricketData.org
        </p>
      </div>
    </div>
  )
}
