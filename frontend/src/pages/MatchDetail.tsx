import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, MapPin, Trophy } from 'lucide-react'
import { useMatch, useMatchScorecard } from '@/hooks/useQueries'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'
import CountryFlag from '@/components/ui/CountryFlag'
import PlayerPortrait from '@/components/ui/PlayerPortrait'
import { Skeleton } from '@/components/ui/Skeleton'

export default function MatchDetail() {
  const { id = '' } = useParams()
  const match = useMatch(id)
  const scorecard = useMatchScorecard(id)
  const [activeInnings, setActiveInnings] = useState(0)
  const detail = match.data
  const innings = scorecard.data?.innings || []
  const selected = innings[Math.min(activeInnings, Math.max(innings.length - 1, 0))]

  if (match.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="h-72 w-full rounded-[24px]" />
        <Skeleton className="h-96 w-full rounded-[20px]" />
      </div>
    )
  }

  if (match.isError || !detail) {
    return <ErrorCard title="Match unavailable" message="This match record could not be loaded." onRetry={() => match.refetch()} />
  }

  return (
    <div className="space-y-4">
      <Link to="/matches" className="btn-ghost -ml-2 w-fit gap-2">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to matches
      </Link>

      <section className="match-hero">
        <div className="match-hero-top">
          <FormatBadge format={detail.format} />
          <span>{detail.competition_name || 'Historical match'}</span>
        </div>
        <div className="match-versus">
          <div>
            <CountryFlag team={detail.team_a} size="lg" />
            <h1>{detail.team_a || 'TBD'}</h1>
          </div>
          <span className="match-vs-disc">VS</span>
          <div>
            <CountryFlag team={detail.team_b} size="lg" />
            <h1>{detail.team_b || 'TBD'}</h1>
          </div>
        </div>
        <p className="match-result">{detail.result || 'Result unavailable'}</p>
        <div className="match-meta">
          <span><CalendarDays /> {detail.match_date || 'Date unavailable'}</span>
          <span><MapPin /> {detail.venue || 'Venue unavailable'}</span>
          {detail.winner && <span><Trophy /> {detail.winner}</span>}
        </div>
      </section>

      {scorecard.isLoading ? (
        <Skeleton className="h-96 w-full rounded-[20px]" />
      ) : scorecard.isError ? (
        <div className="card-solid"><ErrorCard title="Scorecard unavailable" message="The match summary is available, but its detailed scorecard could not be loaded." onRetry={() => scorecard.refetch()} /></div>
      ) : innings.length === 0 ? (
        <div className="card-solid"><EmptyState title="No scorecard data" message="A ball-by-ball scorecard has not been generated for this match." /></div>
      ) : (
        <section className="card-solid overflow-hidden">
          <div className="panel-header flex-wrap gap-3">
            <div>
              <p className="panel-kicker">Full scorecard</p>
              <h2 className="mt-1 font-display text-sm font-semibold text-white">Innings breakdown</h2>
            </div>
            <div className="tabs max-w-full overflow-x-auto">
              {innings.map((item, index) => (
                <button key={item.innings_number} onClick={() => setActiveInnings(index)} className={`tab inline-flex items-center gap-1.5 whitespace-nowrap ${index === activeInnings ? 'tab-active' : 'tab-inactive'}`}>
                  <CountryFlag team={item.team} size="sm" /> {item.team || `Innings ${item.innings_number}`} · {item.runs ?? '—'}/{item.wickets ?? '—'}
                </button>
              ))}
            </div>
          </div>

          {selected && (
            <>
              <div className="innings-scoreline">
                <div><span>Score</span><strong>{selected.runs ?? '—'}/{selected.wickets ?? '—'}</strong></div>
                <div><span>Overs</span><strong>{selected.overs ?? '—'}</strong></div>
                <div><span>Extras</span><strong>{selected.extras ?? '—'}</strong></div>
                <div><span>Batting side</span><strong className="flex items-center gap-2"><CountryFlag team={selected.team} size="sm" />{selected.team || '—'}</strong></div>
              </div>

              <div className="scorecard-block">
                <h3>Batting</h3>
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead><tr><th>Batter</th><th>Dismissal</th><th className="text-right">R</th><th className="text-right">B</th><th className="text-right">4s</th><th className="text-right">6s</th><th className="text-right">SR</th></tr></thead>
                    <tbody>
                      {selected.batting.map((player) => (
                        <tr key={player.player_id || player.player_name}>
                          <td>
                            <span className="flex items-center gap-2">
                              <PlayerPortrait name={player.player_name} imageUrl={player.image_url} size="xs" />
                              {player.player_id ? <Link className="font-semibold text-gray-100 hover:text-brand-300" to={`/players/${player.player_id}`}>{player.player_name}</Link> : player.player_name}
                            </span>
                          </td>
                          <td className="max-w-[260px] truncate text-gray-500">{player.dismissal || 'not out'}</td>
                          <td className="text-right font-mono font-bold text-white">{player.runs ?? '—'}</td>
                          <td className="text-right font-mono">{player.balls ?? '—'}</td>
                          <td className="text-right font-mono">{player.fours ?? '—'}</td>
                          <td className="text-right font-mono">{player.sixes ?? '—'}</td>
                          <td className="text-right font-mono text-brand-300">{player.strike_rate?.toFixed(1) || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="scorecard-block border-t border-white/[.07]">
                <h3>Bowling</h3>
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead><tr><th>Bowler</th><th className="text-right">O</th><th className="text-right">M</th><th className="text-right">R</th><th className="text-right">W</th><th className="text-right">Econ</th></tr></thead>
                    <tbody>
                      {selected.bowling.map((player) => (
                        <tr key={player.player_id || player.player_name}>
                          <td>
                            <span className="flex items-center gap-2">
                              <PlayerPortrait name={player.player_name} imageUrl={player.image_url} size="xs" />
                              {player.player_id ? <Link className="font-semibold text-gray-100 hover:text-brand-300" to={`/players/${player.player_id}`}>{player.player_name}</Link> : player.player_name}
                            </span>
                          </td>
                          <td className="text-right font-mono">{player.overs ?? '—'}</td>
                          <td className="text-right font-mono">{player.maidens ?? '—'}</td>
                          <td className="text-right font-mono">{player.runs ?? '—'}</td>
                          <td className="text-right font-mono font-bold text-white">{player.wickets ?? '—'}</td>
                          <td className="text-right font-mono text-brand-300">{player.economy?.toFixed(2) || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  )
}
