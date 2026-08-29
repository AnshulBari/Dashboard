import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { BarChart3, Info } from 'lucide-react'
import { usePlatformRankings, useIccRankings } from '@/hooks/useQueries'
import { SkeletonTable } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext {
  format: string
}

const CATEGORIES = [
  { value: 'batting', label: 'Batting' },
  { value: 'bowling', label: 'Bowling' },
  { value: 'allrounder', label: 'All-rounder' },
]

export default function Rankings() {
  const { format: globalFormat } = useOutletContext<PageContext>()
  const [category, setCategory] = useState('batting')
  const [source, setSource] = useState<'platform' | 'icc'>('platform')
  
  const targetFormat = globalFormat === 'All' ? 'T20' : globalFormat

  const platform = usePlatformRankings(targetFormat, category)
  const icc = useIccRankings(targetFormat, category)

  const isLoading = source === 'platform' ? platform.isLoading : icc.isLoading
  const isError = source === 'platform' ? platform.isError : icc.isError
  const refetch = () => source === 'platform' ? platform.refetch() : icc.refetch()
  
  const rankings = source === 'platform' 
    ? (platform.data?.rankings || [])
    : (icc.data?.rankings || [])

  const iccAvailable = icc.data?.provider_available ?? false

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Rankings</h1>
        <p className="page-subtitle">
          Platform-computed player rankings based on historical analytics
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        {/* Source toggle */}
        <div className="flex items-center gap-1 bg-surface-100 rounded-lg p-0.5">
          <button
            onClick={() => setSource('platform')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              source === 'platform'
                ? 'bg-surface-200 text-gray-100 shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Platform
          </button>
          <button
            onClick={() => setSource('icc')}
            disabled={!iccAvailable}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              source === 'icc'
                ? 'bg-surface-200 text-gray-100 shadow-sm'
                : iccAvailable
                  ? 'text-gray-500 hover:text-gray-300'
                  : 'text-gray-600 cursor-not-allowed'
            }`}
          >
            ICC {!iccAvailable && '(N/A)'}
          </button>
        </div>

        {/* Category */}
        <div className="flex items-center gap-1">
          {CATEGORIES.map(c => (
            <button
              key={c.value}
              onClick={() => setCategory(c.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                category === c.value
                  ? 'bg-brand-500/15 text-brand-400 border border-brand-500/25'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-surface-100 border border-transparent'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* ICC Notice */}
      {source === 'icc' && !iccAvailable && (
        <div className="card p-4 mb-4 flex items-start gap-3 border-amber-500/20 bg-amber-500/5">
          <Info className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs font-medium text-amber-300">ICC rankings not available</p>
            <p className="text-[10px] text-gray-500 mt-0.5">
              The CricketData.org free tier does not provide ICC rankings. 
              Set up a paid provider to enable official rankings.
            </p>
          </div>
        </div>
      )}

      {isLoading ? (
        <SkeletonTable rows={15} />
      ) : isError ? (
        <ErrorCard message="Failed to load rankings" onRetry={() => refetch()} />
      ) : rankings.length === 0 ? (
        <EmptyState 
          icon={<BarChart3 className="h-10 w-10 text-gray-600" />}
          title="No rankings available" 
          message={source === 'icc' 
            ? "ICC rankings are not available from the current provider." 
            : "No ranking data available for this selection."
          } 
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th className="w-10">Rank</th>
                  <th>Player</th>
                  <th>Team</th>
                  <th className="text-right">Rating</th>
                  {category === 'batting' && (
                    <>
                      <th className="text-right">Runs</th>
                      <th className="text-right">Avg</th>
                      <th className="text-right">SR</th>
                    </>
                  )}
                  {category === 'bowling' && (
                    <>
                      <th className="text-right">Wkts</th>
                      <th className="text-right">Econ</th>
                      <th className="text-right">Avg</th>
                    </>
                  )}
                  <th className="text-right">Form</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((player) => (
                  <tr key={player.id}>
                    <td>
                      <span className={`text-sm font-bold ${
                        (player.rank || 0) <= 3 ? 'text-brand-400' : 'text-gray-500'
                      }`}>
                        {player.rank}
                      </span>
                    </td>
                    <td className="font-medium text-gray-200">{player.name}</td>
                    <td>
                      <span className="badge-blue text-[10px]">
                        {player.team || player.country || '—'}
                      </span>
                    </td>
                    <td className="text-right">
                      <span className="text-sm font-bold text-gray-100">
                        {player.rating?.toFixed(1) || '—'}
                      </span>
                    </td>
                    {category === 'batting' && (
                      <>
                        <td className="text-right font-mono text-sm text-gray-300">
                          {player.runs?.toLocaleString() || '—'}
                        </td>
                        <td className="text-right font-mono text-sm text-gray-300">
                          {player.batting_average?.toFixed(1) || '—'}
                        </td>
                        <td className="text-right font-mono text-sm text-gray-300">
                          {player.strike_rate?.toFixed(1) || '—'}
                        </td>
                      </>
                    )}
                    {category === 'bowling' && (
                      <>
                        <td className="text-right font-mono text-sm text-gray-300">
                          {player.wickets || '—'}
                        </td>
                        <td className="text-right font-mono text-sm text-gray-300">
                          {player.economy?.toFixed(2) || '—'}
                        </td>
                        <td className="text-right font-mono text-sm text-gray-300">
                          {player.batting_average?.toFixed(1) || '—'}
                        </td>
                      </>
                    )}
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Source Attribution */}
      <div className="mt-4 card p-3">
        <p className="text-[10px] text-gray-500 text-center">
          {source === 'platform' ? (
            <>
              <strong className="text-gray-400">Platform Rating</strong> · 
              Computed using weighted composite of batting average (40%), strike rate (30%), and form score (30%). 
              Minimum 5 innings required.
            </>
          ) : (
            <>
              <strong className="text-gray-400">Official Rankings</strong> · 
              Sourced from external provider. May not be available for all formats/categories.
            </>
          )}
        </p>
      </div>
    </div>
  )
}
