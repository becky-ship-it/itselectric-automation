interface Props {
  status: 'idle' | 'running'
  lastRunAt: string | null
}

export default function StatusStrip({ status, lastRunAt }: Props) {
  if (status === 'idle' && !lastRunAt) return null
  return (
    <div
      className={`text-xs px-4 py-1 text-white ${
        status === 'running' ? 'bg-blue-600 animate-pulse' : 'bg-gray-700'
      }`}
    >
      {status === 'running'
        ? 'Pipeline running…'
        : `Last run: ${lastRunAt ? new Date(lastRunAt).toLocaleString() : 'never'}`}
    </div>
  )
}
