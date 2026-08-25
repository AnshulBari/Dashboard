import { Radio, WifiOff } from 'lucide-react'

export default function Live() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Live Match Centre</h1>
        <p className="page-subtitle">
          Real-time match data from legitimate cricket APIs
        </p>
      </div>

      <div className="card p-12 text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Radio className="h-8 w-8 text-gray-300" />
        </div>
        <h3 className="text-lg font-semibold text-gray-600 mb-2">No Live Matches</h3>
        <p className="text-sm text-gray-400 max-w-md mx-auto">
          When matches are in progress, live scores, run rates, win probability,
          and recent deliveries will appear here.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-gray-400">
          <WifiOff className="h-3 w-3" />
          <span>Live data depends on external API availability</span>
        </div>
      </div>
    </div>
  )
}
