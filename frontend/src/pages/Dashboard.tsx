import { useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import {
  ArrowUpRight, ChevronRight, CircleDot,
  MapPin, Radio, Shield, Sparkles, Trophy, Users, WifiOff,
} from 'lucide-react'
import {
  useLiveMatches, useMatchList, usePlayerList, useTeamList, useVenueList,
} from '@/hooks/useQueries'
import { Skeleton, SkeletonCard, SkeletonMatch } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import ErrorCard from '@/components/ui/ErrorCard'
import FormatBadge from '@/components/ui/FormatBadge'
import CountryFlag from '@/components/ui/CountryFlag'
import PlayerPortrait from '@/components/ui/PlayerPortrait'
import type { LiveMatch, MatchRow, PlayerRow, VenueRow } from '@/lib/api'

interface DashboardContext { format: string }
type PlayerTab = 'impact' | 'batting' | 'bowling'

const playerTabs: { key: PlayerTab; label: string; sort: string; metric: string }[] = [
  { key: 'impact', label: 'Impact', sort: 'impact_score', metric: 'IMPACT' },
  { key: 'batting', label: 'Batting', sort: 'career_runs', metric: 'RUNS' },
  { key: 'bowling', label: 'Bowling', sort: 'career_wickets', metric: 'WKTS' },
]

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
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  }).format(parsed)
}

function metricValue(player: PlayerRow, tab: PlayerTab) {
  if (tab === 'batting') return player.career_runs?.toLocaleString() ?? '—'
  if (tab === 'bowling') return player.career_wickets?.toLocaleString() ?? '—'
  return player.impact_score?.toFixed(1) ?? '—'
}

function PerformerRow({ player, index, tab, format }: { player: PlayerRow; index: number; tab: PlayerTab; format: string }) {
  return (
    <Link to={`/players/${player.id}${format === 'International' ? '' : `?format=${format}`}`} className="performer-row group">
      <div className="performer-rank">{String(index + 1).padStart(2, '0')}</div>
      <PlayerPortrait name={player.name} fullName={player.full_name} imageUrl={player.image_url} size="sm" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] font-semibold text-gray-100 transition group-hover:text-brand-300">
          {player.full_name || player.name}
        </p>
        <p className="mt-0.5 truncate text-[9px] text-gray-500">
          {player.team_name || player.country || player.role || 'Independent'}
        </p>
      </div>
      <div className="text-right">
        <p className="font-display text-sm font-bold text-white">{metricValue(player, tab)}</p>
        <p className="text-[7px] font-bold tracking-[.14em] text-gray-600">
          {playerTabs.find((item) => item.key === tab)?.metric}
        </p>
      </div>
    </Link>
  )
}

function ResultCard({ match }: { match: MatchRow }) {
  return (
    <Link to={`/matches/${match.id}`} className="result-card group">
      <div className="mb-4 flex items-center justify-between">
        <FormatBadge format={match.format} />
        <span className="text-[8px] font-semibold text-gray-500">{match.match_date || 'Date unavailable'}</span>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2"><CountryFlag team={match.team_a} size="sm" /><span className="truncate text-[11px] font-semibold text-white">{match.team_a || 'TBD'}</span></span>
          <strong className="shrink-0 font-mono text-[10px] text-white">{match.score_team_a || '—'}</strong>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2"><CountryFlag team={match.team_b} size="sm" /><span className="truncate text-[11px] font-semibold text-white">{match.team_b || 'TBD'}</span></span>
          <strong className="shrink-0 font-mono text-[10px] text-white">{match.score_team_b || '—'}</strong>
        </div>
      </div>
      <p className="mt-4 line-clamp-1 border-t border-white/[.06] pt-3 text-[9px] font-medium text-brand-300">
        {match.result || 'Result pending'}
      </p>
    </Link>
  )
}

function LiveTile({ match }: { match: LiveMatch }) {
  const isLive = match.status?.toLowerCase() === 'live'
  return (
    <div className="live-tile">
      <div className="flex items-center justify-between">
        <span className={isLive ? 'live-badge' : 'badge'}>{isLive && <span className="live-dot" />}{isLive ? 'Live' : 'Upcoming'}</span>
        <span className="text-[8px] text-gray-500">{match.format || 'Match'}</span>
      </div>
      <div className="mt-4 space-y-2.5">
        <div className="flex items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2"><CountryFlag team={match.team_a} size="sm" /><span className="truncate text-[11px] font-semibold text-gray-200">{match.team_a || 'TBA'}</span></span>
          {isLive && <span className="shrink-0 font-mono text-[11px] font-bold text-white">{match.score_team_a || '—'}</span>}
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2"><CountryFlag team={match.team_b} size="sm" /><span className="truncate text-[11px] font-semibold text-gray-200">{match.team_b || 'TBA'}</span></span>
          {isLive && <span className="shrink-0 font-mono text-[11px] font-bold text-white">{match.score_team_b || '—'}</span>}
        </div>
      </div>
      <p className="mt-3 border-t border-white/[.06] pt-2 text-[8px] text-gray-500">
        {isLive ? (match.result || match.venue || 'Match update pending') : `${fixtureTime(match.start_time)}${match.venue ? ` · ${match.venue}` : ''}`}
      </p>
    </div>
  )
}

function VenueConditions({ venue }: { venue: VenueRow }) {
  const first = venue.avg_first_innings_score
  const second = venue.avg_second_innings_score
  const difference = first != null && second != null ? Math.round(first - second) : null
  const read = difference == null
    ? 'Scoring pattern unavailable'
    : Math.abs(difference) < 10
      ? 'Scoring stays balanced across innings'
      : difference > 0
        ? `Scoring falls by ${difference} runs later`
        : `Scoring improves by ${Math.abs(difference)} runs later`

  return (
    <Link to={`/venues/${venue.id}`} className="conditions-row group">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-semibold text-gray-100 group-hover:text-brand-300">{venue.name}</p>
          <p className="mt-0.5 text-[8px] text-gray-500">Last match {venue.last_match_date || 'date unavailable'}</p>
        </div>
        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-gray-600 transition group-hover:text-brand-400" />
      </div>
      <div className="conditions-metrics">
        <div><span>1st inns avg</span><strong>{first == null ? '—' : Math.round(first)}</strong></div>
        <div><span>2nd inns avg</span><strong>{second == null ? '—' : Math.round(second)}</strong></div>
      </div>
      <p className="conditions-read">{read}</p>
    </Link>
  )
}

export default function Dashboard() {
  const { format } = useOutletContext<DashboardContext>()
  const [playerTab, setPlayerTab] = useState<PlayerTab>('impact')
  const formatParam = format
  const activePlayerTab = playerTabs.find((tab) => tab.key === playerTab)!
  const fullMembersOnly = format !== 'T20'

  const players = usePlayerList({
    format: formatParam, sort_by: activePlayerTab.sort, limit: 10,
    full_members_only: fullMembersOnly, recent_only: true,
  })
  const teams = useTeamList({
    format: formatParam, sort_by: 'win_rate', limit: 12,
    full_members_only: fullMembersOnly, recent_only: true,
  })
  const matches = useMatchList({
    format: formatParam, limit: 6, full_members_only: fullMembersOnly,
    recent_only: true, completed_only: true,
  })
  const venues = useVenueList({ format: formatParam, limit: 8, full_members_only: fullMembersOnly, recent_only: true })
  const live = useLiveMatches()

  const playerList = players.data?.players || []
  const filteredPlayers = playerList.filter((player) => {
    if (playerTab === 'bowling') return (player.career_wickets || 0) > 0
    if (playerTab === 'batting') return (player.career_runs || 0) > 0
    return player.impact_score != null
  })
  const matchList = matches.data?.matches || []
  const teamList = teams.data?.teams || []
  const venueList = (venues.data?.venues || []).filter((venue) => (venue.total_matches || 0) > 0)
  const providerMatches = (live.data?.data || []).filter(isFullMemberMatch)
  const liveMatches = providerMatches.filter((match) => match.status?.toLowerCase() === 'live')
  const upcomingMatches = providerMatches
    .filter((match) => ['upcoming', 'scheduled'].includes(match.status?.toLowerCase() || ''))
    .sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''))
  const liveCenterMatches = liveMatches.length ? liveMatches : upcomingMatches
  const liveAvailable = live.data?.provider_available ?? false
  const featuredPlayer = filteredPlayers[0] || playerList[0]
  return (
    <div className="dashboard-stage">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow"><Sparkles /> Live intelligence workspace</div>
          <h1>Matchday command center</h1>
          <p>{format === 'International' ? 'T20I, ODI and Test intelligence' : `${format} intelligence`} from ball-by-ball history and live match signals.</p>
        </div>
        <div className="dashboard-meta">
          <span><i className="signal-dot" /> Systems operational</span>
          <strong>4.13M</strong>
          <small>deliveries analyzed</small>
        </div>
      </div>

      <div className="dashboard-grid">
        <aside className="dashboard-left space-y-4">
          <section className="card-solid overflow-hidden">
            <div className="panel-header block">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="panel-kicker">18-month leaderboard</p>
                  <h2 className="mt-1 font-display text-sm font-semibold text-white">Recent performers</h2>
                </div>
                <Link to="/players" className="section-link">See all</Link>
              </div>
              <div className="tabs">
                {playerTabs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setPlayerTab(tab.key)}
                    className={`tab flex-1 ${playerTab === tab.key ? 'tab-active' : 'tab-inactive'}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="performer-list">
              {players.isLoading ? (
                Array.from({ length: 6 }).map((_, index) => (
                  <div className="flex gap-3 px-4 py-3" key={index}>
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1 space-y-2"><Skeleton className="h-3 w-3/4" /><Skeleton className="h-2 w-1/2" /></div>
                  </div>
                ))
              ) : players.isError ? (
                <ErrorCard message="Player leaderboard is unavailable." onRetry={() => players.refetch()} />
              ) : filteredPlayers.length ? (
                filteredPlayers.slice(0, 7).map((player, index) => (
                  <PerformerRow key={player.id} player={player} index={index} tab={playerTab} format={format} />
                ))
              ) : (
                <EmptyState title="No player data" message="Choose another format or metric." />
              )}
            </div>
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Full Member momentum</p>
                <h2 className="mt-1 font-display text-sm font-semibold text-white">Recent team strength</h2>
              </div>
              <Link to="/teams" className="section-link">See all</Link>
            </div>
            <div className="p-3">
              {teams.isLoading ? <SkeletonCard /> : teamList.slice(0, 4).map((team, index) => (
                <Link to={`/teams/${team.id}`} key={team.id} className="strength-row group">
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <p className="truncate text-[10px] font-semibold text-gray-200 group-hover:text-brand-300">{team.name}</p>
                      <strong>{team.win_rate?.toFixed(0) || '—'}%</strong>
                    </div>
                    <div className="strength-track"><i style={{ width: `${Math.min(team.win_rate || 0, 100)}%` }} /></div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </aside>

        <div className="dashboard-center space-y-4">
          <section className="spotlight-card">
            <div className="spotlight-shade" />
            <div className="spotlight-topline">
              <span><CircleDot /> Intelligence spotlight</span>
              <FormatBadge format={format === 'International' ? 'INTL' : format} />
            </div>
            <div className="spotlight-content">
              <div className="spotlight-copy">
                <p className="panel-kicker">Featured performer</p>
                <h2>{featuredPlayer?.full_name || featuredPlayer?.name || 'Cricket Intelligence'}</h2>
                <p>{featuredPlayer?.team_name || featuredPlayer?.country || 'Historical performance model'}</p>
                {featuredPlayer && (
                  <Link to={`/players/${featuredPlayer.id}${format === 'International' ? '' : `?format=${format}`}`} className="btn-primary mt-5 gap-2">
                    Open player intelligence <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                )}
              </div>
              <PlayerPortrait
                name={featuredPlayer?.name || 'Cricket Intelligence'}
                fullName={featuredPlayer?.full_name}
                imageUrl={featuredPlayer?.image_url}
                size="spotlight"
                className="spotlight-monogram"
                showStatus
              />
            </div>
            <div className="spotlight-stats">
              <div><strong>{featuredPlayer?.impact_score?.toFixed(1) || '—'}</strong><span>Impact</span></div>
              <div><strong>{featuredPlayer?.career_runs?.toLocaleString() || '—'}</strong><span>Runs</span></div>
              <div><strong>{featuredPlayer?.batting_average?.toFixed(1) || '—'}</strong><span>Average</span></div>
              <div><strong>{featuredPlayer?.strike_rate?.toFixed(1) || '—'}</strong><span>Strike rate</span></div>
            </div>
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Latest outcomes</p>
                <h2 className="mt-1 font-display text-sm font-semibold text-white">Recent match center</h2>
              </div>
              <Link to="/matches" className="section-link flex items-center gap-1">All matches <ChevronRight className="h-3 w-3" /></Link>
            </div>
            <div className="result-grid">
              {matches.isLoading ? (
                Array.from({ length: 3 }).map((_, index) => <SkeletonCard key={index} />)
              ) : matches.isError ? (
                <ErrorCard message="Recent matches are unavailable." onRetry={() => matches.refetch()} />
              ) : matchList.length ? (
                matchList.map((match) => <ResultCard key={match.id} match={match} />)
              ) : (
                <EmptyState title="No recent matches" message="No results for this format." />
              )}
            </div>
          </section>

          <section className="data-ribbon">
            <div><Users /><span><strong>{players.data?.total?.toLocaleString() || '—'}</strong> players</span></div>
            <div><Shield /><span><strong>{teams.data?.total?.toLocaleString() || '—'}</strong> teams</span></div>
            <div><Trophy /><span><strong>{matches.data?.total?.toLocaleString() || '—'}</strong> matches</span></div>
            <div><MapPin /><span><strong>{venues.data?.total?.toLocaleString() || '—'}</strong> venues</span></div>
          </section>
        </div>

        <aside className="dashboard-right space-y-4">
          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">{liveMatches.length ? 'In play now' : 'Next on the calendar'}</p>
                <h2 className="mt-1 flex items-center gap-2 font-display text-sm font-semibold text-white">
                  Live center {liveMatches.length > 0 && <span className="live-dot" />}
                </h2>
              </div>
              <Link to="/live" className="section-link">Open</Link>
            </div>
            <div className="space-y-2 p-3">
              {live.isLoading ? <><SkeletonMatch /><SkeletonMatch /></> : liveCenterMatches.length ? (
                liveCenterMatches.map((match) => <LiveTile key={match.match_id} match={match} />)
              ) : (
                <div className="offline-tile">
                  <span className="offline-icon">{liveAvailable ? <Radio /> : <WifiOff />}</span>
                  <h3>{liveAvailable ? 'No upcoming fixtures' : 'Schedule feed unavailable'}</h3>
                  <p>{liveAvailable ? 'There are no Full Member matches currently listed.' : 'Connect CricketData.org to load live and upcoming matches.'}</p>
                  <Link to="/live">View live center <ChevronRight /></Link>
                </div>
              )}
            </div>
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">{fullMembersOnly ? 'Latest full-member venues' : 'Latest T20 venues'}</p>
                <h2 className="mt-1 font-display text-sm font-semibold text-white">Scoring conditions</h2>
              </div>
              <Link to="/venues" className="section-link">See all</Link>
            </div>
            <div className="p-3">
              {venues.isLoading ? <SkeletonCard /> : venueList.slice(0, 3).map((venue) => (
                <VenueConditions venue={venue} key={venue.id} />
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
