import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { ArrowLeft, TrendingUp, Target } from 'lucide-react'
import { playerApi } from '../services/api'

interface PlayerData {
  id: string
  name: string
  full_name: string | null
  role: string | null
  country: string | null
  team_name: string | null
  batting_style: string | null
  bowling_style: string | null
  form_score: number | null
  matches: number | null
  innings: number | null
  runs: number | null
  batting_average: number | null
  strike_rate: number | null
  highest_score: number | null
  fours: number | null
  sixes: number | null
  fifties: number | null
  hundreds: number | null
  balls_faced: number | null
  not_outs: number | null
  boundary_pct: number | null
  dot_ball_pct: number | null
  powerplay_runs: number | null
  powerplay_strike_rate: number | null
  middle_runs: number | null
  middle_strike_rate: number | null
  death_runs: number | null
  death_strike_rate: number | null
  bowling?: {
    matches: number | null
    innings: number | null
    overs: number | null
    wickets: number | null
    runs_conceded: number | null
    bowling_average: number | null
    strike_rate: number | null
    economy: number | null
    dot_ball_pct: number | null
  } | null
}

function StatBox({ label, value, subtitle }: { label: string; value: string | number; subtitle?: string }) {
  return (
    <div className="text-center p-3 rounded-lg bg-surface-50">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs font-medium text-gray-500 mt-1">{label}</p>
      {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
    </div>
  )
}

export default function PlayerDetail() {
  const { id } = useParams()
  const [player, setPlayer] = useState<PlayerData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    async function load() {
      try {
        const data = await playerApi.get(id!) as PlayerData
        setPlayer(data)
      } catch (err) {
        setError('Failed to load player data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500">Loading player...</div>
    )
  }

  if (error || !player) {
    return (
      <div className="text-center py-12 text-gray-500">{error || 'Player not found'}</div>
    )
  }

  const battingAvg = player.batting_average ?? 0
  const strikeRate = player.strike_rate ?? 0
  const formScore = player.form_score ?? 0
  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => window.history.back()}
        className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Players
      </button>

      {/* Player Header */}
      <div className="card p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{player.name}</h1>
            {player.full_name && player.full_name !== player.name && (
              <p className="text-sm text-gray-500 mt-1">{player.full_name}</p>
            )}
            <div className="flex items-center gap-3 mt-2">
              <span className="badge-blue">{player.role || 'Unknown'}</span>
              {player.team_name && <span className="badge-green">{player.team_name}</span>}
              {player.batting_style && <span className="text-xs text-gray-400">{player.batting_style}</span>}
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-brand-50 border-4 border-brand-500 flex items-center justify-center">
                <span className="text-2xl font-bold text-brand-700">{formScore.toFixed(1)}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Form Score</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-surface-50 border-2 border-surface-300 flex items-center justify-center">
                <span className="text-xl font-bold text-gray-700">{battingAvg.toFixed(1)}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Average</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-surface-50 border-2 border-surface-300 flex items-center justify-center">
                <span className="text-xl font-bold text-gray-700">{strikeRate.toFixed(1)}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Strike Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Career Batting Stats */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Career Batting</h2>
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
          <StatBox label="Matches" value={player.matches ?? '-'} />
          <StatBox label="Innings" value={player.innings ?? '-'} />
          <StatBox label="Runs" value={(player.runs ?? 0).toLocaleString()} />
          <StatBox label="Average" value={player.batting_average?.toFixed(1) ?? '-'} />
          <StatBox label="Strike Rate" value={player.strike_rate?.toFixed(1) ?? '-'} />
          <StatBox label="Highest" value={player.highest_score ?? '-'} />
          <StatBox label="Fours" value={player.fours ?? '-'} />
          <StatBox label="Sixes" value={player.sixes ?? '-'} />
          <StatBox label="50s" value={player.fifties ?? '-'} />
          <StatBox label="100s" value={player.hundreds ?? '-'} />
          <StatBox label="Boundary %" value={player.boundary_pct != null ? `${player.boundary_pct.toFixed(1)}%` : '-'} />
          <StatBox label="Dot Ball %" value={player.dot_ball_pct != null ? `${player.dot_ball_pct.toFixed(1)}%` : '-'} />
        </div>
      </div>

      {/* Phase Performance */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-gray-900">Phase Performance</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { name: 'Powerplay', runs: player.powerplay_runs, sr: player.powerplay_strike_rate },
            { name: 'Middle Overs', runs: player.middle_runs, sr: player.middle_strike_rate },
            { name: 'Death Overs', runs: player.death_runs, sr: player.death_strike_rate },
          ].map((phase) => (
            <div key={phase.name} className="p-4 rounded-lg bg-surface-50 border border-surface-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">{phase.name}</h3>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-xs text-gray-500">Runs</p>
                  <p className="text-sm font-bold text-gray-900">{phase.runs ?? '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Strike Rate</p>
                  <p className="text-sm font-bold text-gray-900">{phase.sr?.toFixed(1) ?? '-'}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bowling Stats (if applicable) */}
      {player.bowling && (
        <div className="card p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Career Bowling</h2>
          <div className="grid grid-cols-4 md:grid-cols-5 gap-3">
            <StatBox label="Matches" value={player.bowling.matches ?? '-'} />
            <StatBox label="Wickets" value={player.bowling.wickets ?? '-'} />
            <StatBox label="Average" value={player.bowling.bowling_average?.toFixed(1) ?? '-'} />
            <StatBox label="Economy" value={player.bowling.economy?.toFixed(2) ?? '-'} />
            <StatBox label="Strike Rate" value={player.bowling.strike_rate?.toFixed(1) ?? '-'} />
          </div>
        </div>
      )}

      {/* Form Score Explanation */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-gray-900">Form Score</h2>
        </div>
        <p className="text-sm text-gray-600 mb-3">
          The Form Score is a weighted composite metric (0-100) based on recent performance, consistency,
          opposition strength, venue performance, match situation, and efficiency.
        </p>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-brand-50 border-4 border-brand-500 flex items-center justify-center">
              <span className="text-xl font-bold text-brand-700">{formScore.toFixed(1)}</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Overall</p>
          </div>
          <div className="text-sm text-gray-500">
            Weighted across: Recent Performance (35%), Consistency (20%), Opposition Strength (15%),
            Venue Performance (10%), Match Situation (10%), Efficiency (10%)
          </div>
        </div>
      </div>
    </div>
  )
}
