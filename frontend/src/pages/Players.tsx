import { useOutletContext } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Users } from 'lucide-react'
import { usePlayerList } from '@/hooks/useQueries'
import { SkeletonTable } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext {
  format: string
}

export default function Players() {
  const { format } = useOutletContext<PageContext>()
  const { data, isLoading, isError, refetch } = usePlayerList({ 
    format: format === 'All' ? 'T20' : format, 
    limit: 50 
  })

  const players = data?.players || []

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Players</h1>
        <p className="page-subtitle">
          Player intelligence · {format === 'All' ? 'T20' : format}
        </p>
      </div>

      {isLoading ? (
        <SkeletonTable rows={10} />
      ) : isError ? (
        <ErrorCard message="Failed to load players" onRetry={() => refetch()} />
      ) : players.length === 0 ? (
        <EmptyState 
          icon={<Users className="h-10 w-10 text-gray-600" />}
          title="No players found" 
          message="No player data available for this selection." 
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th className="w-8">#</th>
                  <th>Player</th>
                  <th>Team</th>
                  <th>Role</th>
                  <th className="text-right">Form</th>
                  <th className="text-right">Runs</th>
                  <th className="text-right">Avg</th>
                  <th className="text-right">SR</th>
                  <th className="text-right">Wkts</th>
                </tr>
              </thead>
              <tbody>
                {players.map((player, idx) => (
                  <tr key={player.id}>
                    <td className="text-gray-600 text-xs">{idx + 1}</td>
                    <td>
                      <Link 
                        to={`/players/${player.id}`}
                        className="font-medium text-gray-200 hover:text-brand-400 transition-colors"
                      >
                        {player.name}
                      </Link>
                    </td>
                    <td>
                      <span className="badge-blue text-[10px]">
                        {player.team_name || '—'}
                      </span>
                    </td>
                    <td className="text-xs text-gray-400 capitalize">{player.role || '—'}</td>
                    <td className="text-right">
                      {player.form_score != null ? (
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-[11px] font-bold ${
                          player.form_score >= 70 ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
                          player.form_score >= 50 ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30' :
                          'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        }`}>
                          {player.form_score.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>
                    <td className="text-right font-mono text-sm text-gray-300">
                      {player.career_runs?.toLocaleString() || '—'}
                    </td>
                    <td className="text-right font-mono text-sm text-gray-300">
                      {player.batting_average?.toFixed(1) || '—'}
                    </td>
                    <td className="text-right font-mono text-sm text-gray-300">
                      {player.strike_rate?.toFixed(1) || '—'}
                    </td>
                    <td className="text-right font-mono text-sm text-gray-300">
                      {player.career_wickets || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
