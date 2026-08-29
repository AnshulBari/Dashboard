import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  icon?: React.ReactNode
  title?: string
  message?: string
  action?: React.ReactNode
  className?: string
}

export default function EmptyState({ 
  icon,
  title = 'No data available',
  message = 'There is no data to display for this selection.',
  action,
  className = '' 
}: EmptyStateProps) {
  return (
    <div className={`empty-state ${className}`}>
      {icon || <Inbox className="h-10 w-10 text-gray-600 mb-3" />}
      <h3 className="text-sm font-semibold text-gray-300 mb-1">{title}</h3>
      <p className="text-xs text-gray-500 max-w-xs">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
