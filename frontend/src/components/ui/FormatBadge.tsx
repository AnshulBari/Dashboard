const FORMAT_STYLES: Record<string, string> = {
  T20: 'badge-t20',
  T20I: 'badge-t20i',
  ODI: 'badge-odi',
  Test: 'badge-test',
}

interface FormatBadgeProps {
  format: string
  className?: string
}

export default function FormatBadge({ format, className = '' }: FormatBadgeProps) {
  const style = FORMAT_STYLES[format] || 'badge-gray'
  return (
    <span className={`${style} ${className}`}>
      {format}
    </span>
  )
}
