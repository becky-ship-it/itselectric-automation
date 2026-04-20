import { useState } from 'react'
import { usePipeline } from '../hooks/usePipeline'
import { useContactCounts } from '../hooks/useContacts'

interface StatCardProps {
  label: string
  value: number
  color: string
}

function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div className={`rounded-lg p-5 text-white ${color}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-sm opacity-80 mt-1">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0)
  const pipeline = usePipeline()
  const counts = useContactCounts(refreshKey)

  function handleRun() {
    pipeline.run({
      onComplete: () => setRefreshKey((k) => k + 1),
    })
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <button
          onClick={handleRun}
          disabled={pipeline.status === 'running'}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {pipeline.status === 'running' ? 'Running…' : 'Run Pipeline'}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StatCard label="Pending" value={counts.pending} color="bg-yellow-500" />
        <StatCard label="Unparsed" value={counts.unparsed} color="bg-gray-500" />
      </div>

      {pipeline.logs.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-900 p-4">
          <div className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wide">
            Pipeline log
          </div>
          <div className="font-mono text-xs text-gray-200 space-y-0.5 max-h-64 overflow-y-auto">
            {pipeline.logs.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}

      {pipeline.status === 'idle' && pipeline.logs.length === 0 && (
        <p className="text-sm text-gray-500">
          Click "Run Pipeline" to fetch and process new emails.
        </p>
      )}
    </div>
  )
}
