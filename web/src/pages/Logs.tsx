import { useState, useEffect, useRef } from 'react'

interface LogLine {
  ts: string
  msg: string
}

export default function Logs() {
  const [lines, setLines] = useState<LogLine[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const autoScrollRef = useRef(true)

  useEffect(() => {
    fetch('/api/logs?n=200')
      .then((r) => r.json())
      .then((data) => setLines(data.lines ?? []))
      .catch(() => setError('Failed to load logs'))
  }, [])

  useEffect(() => {
    const es = new EventSource('/api/logs/stream')
    es.onopen = () => setConnected(true)
    es.onmessage = (e) => {
      try {
        const entry: LogLine = JSON.parse(e.data)
        setLines((prev) => [...prev, entry].slice(-500))
      } catch {
        // ignore malformed
      }
    }
    es.onerror = () => {
      setConnected(false)
      es.close()
    }
    return () => es.close()
  }, [])

  useEffect(() => {
    if (autoScrollRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines])

  function formatTs(ts: string) {
    try {
      return new Date(ts).toLocaleTimeString()
    } catch {
      return ts
    }
  }

  return (
    <div className="flex flex-col h-full space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Logs</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-1.5 text-xs text-gray-500 select-none">
            <input
              type="checkbox"
              checked={autoScrollRef.current}
              onChange={(e) => { autoScrollRef.current = e.target.checked }}
              className="h-3.5 w-3.5"
            />
            Auto-scroll
          </label>
          <span className={`text-xs font-medium ${connected ? 'text-green-600' : 'text-gray-400'}`}>
            {connected ? '● live' : '○ disconnected'}
          </span>
          <button
            onClick={() => setLines([])}
            className="text-xs text-gray-400 hover:text-gray-700"
          >
            Clear
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex-1 overflow-y-auto bg-gray-950 rounded-lg p-3 font-mono text-xs text-green-400 min-h-0">
        {lines.length === 0 ? (
          <span className="text-gray-600">No logs yet. Run the pipeline to see output.</span>
        ) : (
          lines.map((line, i) => (
            <div key={i} className="flex gap-3 leading-5">
              <span className="text-gray-600 shrink-0">{formatTs(line.ts)}</span>
              <span className="text-green-300 whitespace-pre-wrap break-all">{line.msg}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
