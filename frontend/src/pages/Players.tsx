import { useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { Users, Search } from 'lucide-react'
import { usePlayerList } from '@/hooks/useQueries'
import { Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
interface PageContext { format: string }

export default function Players() {
  const { format } = useOutletContext<PageContext>()
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('form_score')

  const players = usePlayerList({
    format: format === 'All' ? undefined : format,
    sort_by: sortBy,
    limit: 50,
  })

  const playerList = players.data?.players || []
  const filtered = search
    ? playerList.filter(p => p.name?.toLowerCase().includes(search.toLowerCase()))
    : playerList

  return (
    <div className="space-y-5">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <Users className="h-5 w-5 text-emerald-400" />
          Players
        </h1>
        <p className="page-subtitle">
          {players.data?.total?.toLocaleString() || '—'} players · {format === 'All' ? 'All formats' : format}
        </p>
      </div>

      {/* Search + Sort */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search players..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-input pl-10"
          />
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="form-select w-full sm:w-40"
        >
          <option value="form_score">Form Score</option>
          <option value="batting_average">Batting Average</option>
          <option value="strike_rate">Strike Rate</option>
          <option value="career_runs">Career Runs</option>
          <option value="career_wickets">Wickets</option>
        </select>
      </div>

      {/* Player Grid */}
      {players.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="card-solid p-4 space-y-3">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ))}
        </div>
      ) : players.isError ? (
        <ErrorCard message="Failed to load players" onRetry={() => players.refetch()} />
      ) : filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((player) => (
            <Link
              key={player.id}
              to={`/players/${player.id}`}
              className="card-solid p-4 hover:bg-white/[0.04] transition-all duration-200 group"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500/20 to-blue-500/20 flex items-center justify-center text-sm font-bold text-gray-300 border border-white/10">
                    {player.name?.charAt(0) || '?'}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-200 truncate group-hover:text-emerald-400 transition-colors">
                      {player.name}
                    </p>
                    <p className="text-[11px] text-gray-500 truncate">
                      {player.team_name || player.country || '—'}
                    </p>
                  </div>
                </div>
                {player.form_score != null && (
                  <span className={`inline-flex items-center justify-center w-9 h-9 rounded-full text-xs font-bold ${
                    player.form_score >= 70 ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
                    player.form_score >= 50 ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30' :
                    'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                  }`}>
                    {player.form_score.toFixed(0)}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2 mt-3">
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">Avg</p>
                  <p className="text-xs font-semibold text-gray-300">{player.batting_average?.toFixed(1) || '—'}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">SR</p>
                  <p className="text-xs font-semibold text-gray-300">{player.strike_rate?.toFixed(1) || '—'}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">Runs</p>
                  <p className="text-xs font-semibold text-gray-300">{player.career_runs?.toLocaleString() || '—'}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No players found" message="Try adjusting your search or format filter." />
      )}
    </div>
  )
}
