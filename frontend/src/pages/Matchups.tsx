import { useOutletContext } from 'react-router-dom'
import { Swords } from 'lucide-react'
import { useMatchupList } from '@/hooks/useQueries'
import { SkeletonTable } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext {
  format: string
}

export default function Matchups() {
  const { format } = useOutletContext<PageContext>()
  const { data, isLoading, isError, refetch } = useMatchupList({ 
    format: format === 'All' ? 'T20' : format, 
    limit: 25 
  })

  const matchups = data?.matchups || []

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Matchups</h1>
        <p className="page-subtitle">
          Batter vs bowler analytics · {format === 'All' ? 'T20' : format}
        </p>
      </div>

      <div className="card">
        <div className="px-4 py-3 border-b border-surface-200/50">
          <div className="flex items-center gap-2">
            <Swords className="h-4 w-4 text-brand-400" />
            <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Head-to-Head Matchups
            </h2>
          </div>
          <p className="text-[10px] text-gray-500 mt-0.5">
            Minimum 10 balls for statistical significance · Ranked by total runs scored
          </p>
        </div>

        {isLoading ? (
          <SkeletonTable rows={10} />
        ) : isError ? (
          <div className="p-4">
            <ErrorCard message="Failed to load matchups" onRetry={() => refetch()} />
          </div>
        ) : matchups.length === 0 ? (
          <div className="p-4">
            <EmptyState 
              icon={<Swords className="h-10 w-10 text-gray-600" />}
              title="No matchup data" 
              message="No batter-bowler matchup data available for this format." 
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Batter</th>
                  <th>Bowler</th>
                  <th className="text-right">Balls</th>
                  <th className="text-right">Runs</th>
                  <th className="text-right">Wkts</th>
                  <th className="text-right">SR</th>
                  <th className="text-right">Avg</th>
                  <th className="text-right">Dots</th>
                  <th className="text-right">4s</th>
                  <th className="text-right">6s</th>
                </tr>
              </thead>
              <tbody>
                {matchups.map((m, idx) => (
                  <tr key={idx}>
                    <td className="font-medium text-gray-200">{m.batter_name}</td>
                    <td className="text-gray-400">{m.bowler_name}</td>
                    <td className="text-right font-mono text-gray-300">{m.total_balls}</td>
                    <td className="text-right font-mono font-bold text-gray-100">{m.total_runs}</td>
                    <td className="text-right font-mono text-gray-300">{m.total_wickets}</td>
                    <td className="text-right font-mono text-gray-300">
                      {m.strike_rate?.toFixed(1) || '—'}
                    </td>
                    <td className="text-right font-mono text-gray-300">
                      {m.batting_average?.toFixed(1) || '—'}
                    </td>
                    <td className="text-right font-mono text-gray-300">{m.dot_balls}</td>
                    <td className="text-right font-mono text-gray-300">{m.boundaries}</td>
                    <td className="text-right font-mono text-gray-300">{m.sixes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
