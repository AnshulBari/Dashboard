import { Link, useOutletContext, useParams } from 'react-router-dom'
import {
  Activity, ArrowLeft, Award, CircleDot, Gauge, ShieldCheck,
  Sparkles, Target, TrendingUp, Zap,
} from 'lucide-react'
import { usePlayer } from '@/hooks/useQueries'
import ErrorCard from '@/components/ui/ErrorCard'
import { Skeleton } from '@/components/ui/Skeleton'
import PlayerPortrait from '@/components/ui/PlayerPortrait'

interface PageContext { format: string }

function display(value: number | null | undefined, digits = 0) {
  if (value == null) return '—'
  return digits ? value.toFixed(digits) : value.toLocaleString()
}

function StatTile({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className={`profile-stat ${accent ? 'profile-stat-accent' : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export default function PlayerDetail() {
  const { id = '' } = useParams()
  const { format } = useOutletContext<PageContext>()
  const requestedFormat = format
  const player = usePlayer(id, requestedFormat)

  if (player.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-36" />
        <Skeleton className="h-[320px] w-full rounded-[24px]" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-72 rounded-[20px]" />
          <Skeleton className="h-72 rounded-[20px]" />
        </div>
      </div>
    )
  }

  if (player.isError || !player.data) {
    return (
      <div className="card-solid">
        <ErrorCard
          title="Player profile unavailable"
          message="The player record could not be loaded."
          onRetry={() => player.refetch()}
        />
      </div>
    )
  }

  const data = player.data
  const activeFormat = data.format || requestedFormat || 'International'
  const hasBatting = data.matches != null || data.runs != null || data.innings != null
  const hasBowling = Boolean(data.bowling && (
    data.bowling.matches != null || data.bowling.wickets != null || data.bowling.overs != null
  ))

  return (
    <div className="space-y-4">
      <Link to={`/players${requestedFormat ? `?format=${requestedFormat}` : ''}`} className="btn-ghost -ml-2 w-fit gap-2">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to players
      </Link>

      <section className="player-profile-hero">
        <div className="profile-hero-grid">
          <div className="profile-identity">
            <PlayerPortrait name={data.name} fullName={data.full_name} imageUrl={data.image_url} size="hero" className="profile-avatar" showStatus />
            <div className="min-w-0">
              <p className="panel-kicker flex items-center gap-2"><CircleDot className="h-3 w-3" /> Player intelligence</p>
              <h1>{data.full_name || data.name}</h1>
              {data.full_name && data.full_name !== data.name && <p className="profile-known-as">Known as {data.name}</p>}
              <div className="profile-tags">
                <span>{data.role || 'Player'}</span>
                {data.team_name && <span>{data.team_name}</span>}
                {data.country && <span>{data.country}</span>}
                <span className="active">{activeFormat}</span>
              </div>
            </div>
          </div>

          <div className="profile-ratings">
            <div className="rating-ring rating-ring-primary">
              <strong>{display(data.impact_score, 1)}</strong>
              <span>Impact</span>
            </div>
            <div className="rating-ring">
              <strong>{display(data.batting_average, 1)}</strong>
              <span>Average</span>
            </div>
            <div className="rating-ring">
              <strong>{display(data.strike_rate, 1)}</strong>
              <span>Strike rate</span>
            </div>
          </div>
        </div>

        <div className="profile-hero-stats">
          <div><span>Matches</span><strong>{display(data.matches)}</strong></div>
          <div><span>Innings</span><strong>{display(data.innings)}</strong></div>
          <div><span>Career runs</span><strong>{display(data.runs)}</strong></div>
          <div><span>Highest score</span><strong>{display(data.highest_score)}</strong></div>
        </div>
      </section>

      <div className="profile-layout">
        <div className="space-y-4 lg:col-span-2">
          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Career output</p>
                <h2 className="mt-1 font-display text-sm font-semibold text-white">Batting intelligence</h2>
              </div>
              <TrendingUp className="h-4 w-4 text-brand-400" />
            </div>
            {hasBatting ? (
              <div className="profile-stat-grid">
                <StatTile label="Runs" value={display(data.runs)} accent />
                <StatTile label="Average" value={display(data.batting_average, 2)} />
                <StatTile label="Strike rate" value={display(data.strike_rate, 2)} />
                <StatTile label="Balls faced" value={display(data.balls_faced)} />
                <StatTile label="Not outs" value={display(data.not_outs)} />
                <StatTile label="Fours" value={display(data.fours)} />
                <StatTile label="Sixes" value={display(data.sixes)} />
                <StatTile label="Fifties" value={display(data.fifties)} />
                <StatTile label="Hundreds" value={display(data.hundreds)} />
                <StatTile label="Boundary share" value={data.boundary_pct == null ? '—' : `${data.boundary_pct.toFixed(1)}%`} />
                <StatTile label="Dot-ball share" value={data.dot_ball_pct == null ? '—' : `${data.dot_ball_pct.toFixed(1)}%`} />
                <StatTile label="Best score" value={display(data.highest_score)} />
              </div>
            ) : (
              <div className="profile-no-data">No batting summary is available for {activeFormat}.</div>
            )}
          </section>

          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Tactical split</p>
                <h2 className="mt-1 font-display text-sm font-semibold text-white">Performance by innings phase</h2>
              </div>
              <Target className="h-4 w-4 text-brand-400" />
            </div>
            <div className="phase-grid">
              {[
                { name: 'Powerplay', runs: data.powerplay_runs, rate: data.powerplay_strike_rate, icon: Zap },
                { name: 'Middle overs', runs: data.middle_runs, rate: data.middle_strike_rate, icon: Activity },
                { name: 'Death overs', runs: data.death_runs, rate: data.death_strike_rate, icon: Gauge },
              ].map((phase) => (
                <div className="phase-card" key={phase.name}>
                  <span className="phase-icon"><phase.icon /></span>
                  <div>
                    <h3>{phase.name}</h3>
                    <p><strong>{display(phase.runs)}</strong> runs</p>
                    <p><strong>{display(phase.rate, 1)}</strong> strike rate</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="card-solid overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">Player profile</p>
                <h2 className="mt-1 font-display text-sm font-semibold text-white">Technique</h2>
              </div>
              <ShieldCheck className="h-4 w-4 text-brand-400" />
            </div>
            <dl className="profile-facts">
              <div><dt>Batting style</dt><dd>{data.batting_style || 'Not recorded'}</dd></div>
              <div><dt>Bowling style</dt><dd>{data.bowling_style || 'Not recorded'}</dd></div>
              <div><dt>Role</dt><dd>{data.role || 'Not recorded'}</dd></div>
              <div><dt>Current team</dt><dd>{data.team_name || 'Not recorded'}</dd></div>
              <div><dt>Data format</dt><dd className="text-brand-300">{activeFormat}</dd></div>
            </dl>
          </section>

          {hasBowling && data.bowling && (
            <section className="card-solid overflow-hidden">
              <div className="panel-header">
                <div>
                  <p className="panel-kicker">With the ball</p>
                  <h2 className="mt-1 font-display text-sm font-semibold text-white">Bowling intelligence</h2>
                </div>
                <Award className="h-4 w-4 text-brand-400" />
              </div>
              <div className="bowling-grid">
                <StatTile label="Wickets" value={display(data.bowling.wickets)} accent />
                <StatTile label="Overs" value={display(data.bowling.overs, 1)} />
                <StatTile label="Average" value={display(data.bowling.bowling_average, 2)} />
                <StatTile label="Economy" value={display(data.bowling.economy, 2)} />
                <StatTile label="Strike rate" value={display(data.bowling.strike_rate, 2)} />
                <StatTile label="Dot-ball share" value={data.bowling.dot_ball_pct == null ? '—' : `${data.bowling.dot_ball_pct.toFixed(1)}%`} />
              </div>
            </section>
          )}

          <section className="profile-insight">
            <Sparkles />
            <div>
              <span>Impact model</span>
              <strong>{display(data.impact_score, 1)} / 100</strong>
              <p>Blends sustained performance, recent form, pressure contribution, opposition quality, consistency, and efficiency.</p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
