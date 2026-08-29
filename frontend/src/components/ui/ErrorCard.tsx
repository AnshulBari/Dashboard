import { AlertTriangle, RefreshCw } from 'lucide-react'

interface ErrorCardProps {
  title?: string
  message?: string
  onRetry?: () => void
  className?: string
}

export default function ErrorCard({ 
  title = 'Something went wrong', 
  message = 'Failed to load data. Please try again.',
  onRetry,
  className = '' 
}: ErrorCardProps) {
  return (
    <div className={`error-state ${className}`}>
      <AlertTriangle className="h-8 w-8 text-amber-500/60 mb-3" />
      <h3 className="text-sm font-semibold text-gray-300 mb-1">{title}</h3>
      <p className="text-xs text-gray-500 max-w-xs">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 btn-ghost text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Try again
        </button>
      )}
    </div>
  )
}
