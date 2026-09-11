import { Link, useOutletContext } from 'react-router-dom'
import { Trophy } from 'lucide-react'
import { useLiveMatches, useMatchList } from '@/hooks/useQueries'
import { SkeletonMatch } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'
import CountryFlag from '@/components/ui/CountryFlag'
import type { LiveMatch, MatchRow } from '@/lib/api'

interface PageContext { format: string }

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

function matchesFormat(match: LiveMatch, format: string) {
  if (format === 'International') return true
  const liveFormat = (match.format || '').trim().toLowerCase()
  const requested = format.trim().toLowerCase()
  if (requested === 't20i') return liveFormat === 't20i' || liveFormat === 't20'
  return liveFormat === requested
}

function isLive(match: LiveMatch) {
  return ['live', 'in progress', 'ongoing'].includes((match.status || '').trim().toLowerCase())
}

function HistoricalMatchCard({ match }: { match: MatchRow }) {
  return (
    <Link
      to={`/matches/${match.id}`}
      className="card-solid block p-4 transition-all duration-200 group hover:bg-white/[0.04]"
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <CountryFlag team={match.team_a} size="sm" />
          <span className="truncate text-sm font-semibold text-gray-200 transition-colors group-hover:text-emerald-400">
            {match.team_a || 'TBD'}
          </span>
          <span className="text-[10px] font-medium text-gray-600">vs</span>
          <CountryFlag team={match.team_b} size="sm" />
          <span className="truncate text-sm font-semibold text-gray-200 transition-colors group-hover:text-emerald-400">
            {match.team_b || 'TBD'}
          </span>
        </div>
        <FormatBadge format={match.format} />
      </div>
      <div className="flex items-center justify-between text-[11px]">
        <div className="flex min-w-0 items-center gap-2 text-gray-500">
          {match.match_date && <span>{match.match_date}</span>}
          {match.venue && (
            <><span>·</span><span className="max-w-[200px] truncate">{match.venue}</span></>
          )}
          {match.competition_name && (
            <><span>·</span><span className="max-w-[150px] truncate">{match.competition_name}</span></>
          )}
        </div>
        <span className="max-w-[240px] truncate font-medium text-emerald-400">{match.result}</span>
      </div>
    </Link>
  )
}

function LiveMatchCard({ match }: { match: LiveMatch }) {
  return (
    <article className="match-card match-card-live p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="live-badge"><span className="live-dot" />Live</span>
        <FormatBadge format={match.format || 'Match'} />
      </div>
      <p className="mb-3 truncate text-[10px] text-gray-500">
        {match.competition || match.venue || 'International cricket'}
      </p>
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <span className="flex min-w-0 items-center gap-2">
            <CountryFlag team={match.team_a} size="sm" />
            <span className="truncate text-sm font-semibold text-gray-100">{match.team_a || 'TBA'}</span>
          </span>
          <strong className="shrink-0 font-mono text-xs text-emerald-400">{match.score_team_a || '—'}</strong>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="flex min-w-0 items-center gap-2">
            <CountryFlag team={match.team_b} size="sm" />
            <span className="truncate text-sm font-semibold text-gray-100">{match.team_b || 'TBA'}</span>
          </span>
          <strong className="shrink-0 font-mono text-xs text-emerald-400">{match.score_team_b || '—'}</strong>
        </div>
      </div>
      <p className="mt-4 border-t border-white/[.06] pt-3 text-[10px] text-gray-400">
        {match.result || match.venue || 'Match update pending'}
      </p>
    </article>
  )
}

export default function Matches() {
  const { format } = useOutletContext<PageContext>()
  const matches = useMatchList({
    format,
    limit: 50,
    full_members_only: true,
    recent_only: true,
    completed_only: true,
  })
  const live = useLiveMatches()
  const liveMatches = (live.data?.data || [])
    .filter(isFullMemberMatch)
    .filter((match) => matchesFormat(match, format))
    .filter(isLive)
  const recentMatches = matches.data?.matches || []

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Trophy className="h-5 w-5 text-emerald-400" />
            Matches
          </h1>
          <p className="page-subtitle">Live and recently concluded Full Member internationals</p>
        </div>
        <p className="page-subtitle">
          {liveMatches.length ? `${liveMatches.length} live · ` : ''}
          {matches.data?.total?.toLocaleString() || '—'} recent · {format === 'International' ? 'T20I + ODI + Test' : format}
        </p>
      </div>

      {(live.isLoading || liveMatches.length > 0) && (
        <section className="space-y-3">
          <div className="section-header">
            <div>
              <p className="panel-kicker">In play now</p>
              <h2 className="mt-1 section-title flex items-center gap-2">
                Live Full Member matches {liveMatches.length > 0 && <span className="live-dot" />}
              </h2>
            </div>
          </div>
          {live.isLoading ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, index) => <SkeletonMatch key={index} />)}
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {liveMatches.map((match) => <LiveMatchCard key={match.match_id} match={match} />)}
            </div>
          )}
        </section>
      )}

      <section className="space-y-3">
        <div className="section-header">
          <div>
            <p className="panel-kicker">Latest results</p>
            <h2 className="mt-1 section-title">Recently concluded matches</h2>
          </div>
          <span className="text-[9px] font-semibold uppercase tracking-wider text-gray-500">12 Test-playing nations</span>
        </div>

        {matches.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 10 }).map((_, index) => <SkeletonMatch key={index} />)}
          </div>
        ) : matches.isError ? (
          <ErrorCard message="Failed to load recent Full Member matches" onRetry={() => matches.refetch()} />
        ) : recentMatches.length > 0 ? (
          <div className="space-y-2">
            {recentMatches.map((match) => <HistoricalMatchCard key={match.id} match={match} />)}
          </div>
        ) : (
          <EmptyState title="No recent matches found" message="No Full Member results are available for this format." />
        )}
      </section>
    </div>
  )
}
