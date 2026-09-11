import { Link, useParams, useSearchParams } from 'react-router-dom'
import { CalendarDays, ChevronRight, MapPin, Shield, Target, Trophy, Users } from 'lucide-react'

import CountryFlag from '@/components/ui/CountryFlag'
import ErrorCard from '@/components/ui/ErrorCard'
import FormatBadge from '@/components/ui/FormatBadge'
import PlayerPortrait from '@/components/ui/PlayerPortrait'
import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton'
import { useCompetitionDashboard } from '@/hooks/useQueries'
import type { MatchRow, TournamentPlayerStats } from '@/lib/api'


function number(value: number | null | undefined, digits = 0) {
  if (value == null) return '—'
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function MatchCard({ match }: { match: MatchRow }) {
  return (
    <Link to={`/matches/${match.id}`} className="tournament-match group">
      <div className="flex items-center justify-between text-[9px] uppercase tracking-[.13em] text-gray-500">
        <span>{match.match_date || 'Date unavailable'}</span>
        <span>{match.venue || 'Venue unavailable'}</span>
      </div>
      <div className="mt-4 space-y-3">
        <div className="flex items-center gap-3">
          <CountryFlag team={match.team_a} size="sm" />
          <strong className="flex-1 truncate text-xs text-gray-100">{match.team_a}</strong>
          <span className="font-display text-sm font-bold text-white">{match.score_team_a || '—'}</span>
        </div>
        <div className="flex items-center gap-3">
          <CountryFlag team={match.team_b} size="sm" />
          <strong className="flex-1 truncate text-xs text-gray-100">{match.team_b}</strong>
          <span className="font-display text-sm font-bold text-white">{match.score_team_b || '—'}</span>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-white/[.07] pt-3">
        <span className="truncate text-[9px] font-semibold text-brand-300">{match.result}</span>
        <ChevronRight className="h-3.5 w-3.5 text-gray-600 transition group-hover:translate-x-0.5 group-hover:text-brand-300" />
      </div>
    </Link>
  )
}

function PlayerLeader({ player, index, bowling = false }: {
  player: TournamentPlayerStats
  index: number
  bowling?: boolean
}) {
  const primary = bowling ? `${number(player.wickets)} wickets` : `${number(player.runs)} runs`
  const secondary = bowling
    ? `${number(player.average, 1)} avg · ${number(player.economy, 1)} econ`
    : `${number(player.average, 1)} avg · ${number(player.strike_rate, 1)} SR`
  return (
    <Link to={`/players/${player.id}`} className="tournament-leader group">
      <span className="w-5 text-[8px] font-bold text-gray-600">{String(index + 1).padStart(2, '0')}</span>
      <PlayerPortrait name={player.name} fullName={player.full_name} imageUrl={player.image_url} size="sm" />
      <span className="min-w-0 flex-1">
        <strong className="block truncate text-xs text-gray-100 group-hover:text-brand-300">{player.full_name || player.name}</strong>
        <small className="mt-0.5 block truncate text-[9px] text-gray-500">{player.country || secondary}</small>
      </span>
      <span className="text-right">
        <strong className="block font-display text-xs text-white">{primary}</strong>
        <small className="block text-[8px] text-gray-500">{secondary}</small>
      </span>
    </Link>
  )
}

export default function CompetitionDetail() {
  const { id = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const seasonId = searchParams.get('season') || undefined
  const query = useCompetitionDashboard(id, seasonId)

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-56 w-full" />
        <div className="grid gap-4 lg:grid-cols-3"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
      </div>
    )
  }
  if (query.isError || !query.data) {
    return <ErrorCard message="Tournament intelligence is unavailable." onRetry={() => query.refetch()} />
  }

  const data = query.data
  const overview = data.overview
  const selectSeason = (nextSeason: string) => {
    const params = new URLSearchParams(searchParams)
    params.set('season', nextSeason)
    setSearchParams(params)
  }

  return (
    <div className="tournament-page space-y-4">
      <section className="tournament-hero">
        <div className="tournament-hero-grid" aria-hidden="true" />
        <div className="relative z-10 flex flex-col gap-8 p-6 md:flex-row md:items-end md:justify-between md:p-9">
          <div>
            <p className="eyebrow"><Trophy /> Tournament intelligence</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <h1 className="font-display text-3xl font-bold tracking-[-.05em] text-white md:text-5xl">
                {data.competition.name}
              </h1>
              <FormatBadge format={data.competition.format || ''} />
            </div>
            <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-400">
              <CalendarDays className="h-3.5 w-3.5 text-brand-400" />
              {data.season.name} edition
              <span className="text-gray-700">/</span>
              {data.season.first_match_date || 'Unknown start'} to {data.season.last_match_date || 'Unknown finish'}
            </p>
          </div>
          <div className="flex items-end gap-5">
            {data.champion && (
              <div className="text-right">
                <p className="text-[8px] font-bold uppercase tracking-[.18em] text-brand-400">Champion</p>
                <div className="mt-2 flex items-center justify-end gap-2">
                  <CountryFlag team={data.champion.name} />
                  <strong className="font-display text-xl text-white">{data.champion.name}</strong>
                </div>
              </div>
            )}
            <label className="season-control">
              <span>Edition</span>
              <select value={data.season.id} onChange={(event) => selectSeason(event.target.value)}>
                {data.seasons.filter((season) => season.matches > 0).map((season) => (
                  <option value={season.id} key={season.id}>{season.name}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className="tournament-metrics">
          <div><strong>{number(overview.matches)}</strong><span>Tournament matches</span></div>
          <div><strong>{number(overview.teams)}</strong><span>Teams</span></div>
          <div><strong>{number(overview.runs)}</strong><span>Runs</span></div>
          <div><strong>{number(overview.wickets)}</strong><span>Wickets</span></div>
          <div><strong>{number(overview.avg_first_innings, 1)}</strong><span>1st inns avg</span></div>
          <div><strong>{number(overview.highest_total)}</strong><span>Highest total</span></div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-8">
          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div><p className="panel-kicker">Tournament table</p><h2 className="mt-1 font-display text-base font-semibold text-white">Team performance</h2></div>
              <span className="section-link">{data.teams.length} teams</span>
            </div>
            <div className="overflow-x-auto">
              <table className="tournament-table">
                <thead><tr><th>#</th><th>Team</th><th>P</th><th>W</th><th>L</th><th>NR</th><th>Win%</th></tr></thead>
                <tbody>{data.teams.map((team, index) => (
                  <tr key={team.id}>
                    <td>{String(index + 1).padStart(2, '0')}</td>
                    <td><Link to={`/teams/${team.id}`}><CountryFlag team={team.name} size="sm" /><strong>{team.name}</strong></Link></td>
                    <td>{team.matches}</td><td className="text-brand-300">{team.wins}</td><td>{team.losses}</td><td>{team.no_results + team.ties}</td><td>{number(team.win_rate, 1)}%</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div><p className="panel-kicker">Edition results</p><h2 className="mt-1 font-display text-base font-semibold text-white">Match center</h2></div>
              <span className="section-link">
                {number(overview.scorecards_indexed ?? data.matches.length)} of {number(overview.matches)} scorecards indexed
              </span>
            </div>
            <div className="grid gap-2 p-3 md:grid-cols-2">
              {data.matches.map((match) => <MatchCard match={match} key={match.id} />)}
            </div>
          </section>
        </div>

        <aside className="space-y-4 xl:col-span-4">
          <section className="card-solid overflow-hidden">
            <div className="panel-header"><div><p className="panel-kicker">Batting leaders</p><h2 className="mt-1 flex items-center gap-2 font-display text-base font-semibold text-white"><Target className="h-4 w-4 text-brand-400" />Most runs</h2></div></div>
            <div className="divide-y divide-white/[.05]">{data.top_batters.map((player, index) => <PlayerLeader player={player} index={index} key={player.id} />)}</div>
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header"><div><p className="panel-kicker">Bowling leaders</p><h2 className="mt-1 flex items-center gap-2 font-display text-base font-semibold text-white"><Shield className="h-4 w-4 text-brand-400" />Most wickets</h2></div></div>
            <div className="divide-y divide-white/[.05]">{data.top_bowlers.map((player, index) => <PlayerLeader player={player} index={index} bowling key={player.id} />)}</div>
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header"><div><p className="panel-kicker">Ground map</p><h2 className="mt-1 flex items-center gap-2 font-display text-base font-semibold text-white"><MapPin className="h-4 w-4 text-brand-400" />Venue conditions</h2></div><span className="section-link"><Users className="h-3 w-3" /> {overview.venues}</span></div>
            <div className="divide-y divide-white/[.05]">{data.venues.map((venue, index) => (
              <Link to={`/venues/${venue.id}`} className="tournament-venue" key={venue.id}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <span className="min-w-0 flex-1"><strong>{venue.name}</strong><small>{venue.city || venue.country || 'Location unavailable'}</small></span>
                <span className="text-right"><strong>{venue.matches}</strong><small>matches</small></span>
              </Link>
            ))}</div>
          </section>
        </aside>
      </div>
    </div>
  )
}
