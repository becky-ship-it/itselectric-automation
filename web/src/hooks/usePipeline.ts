import { useState, useCallback, useRef } from 'react'
import { getPipelineStatus, runPipeline } from '../api/client'

export interface PipelineState {
  status: 'idle' | 'running'
  lastRunAt: string | null
  logs: string[]
  run: (opts?: { fixture?: boolean; onComplete?: () => void }) => void
}

export function usePipeline(): PipelineState {
  const [status, setStatus] = useState<'idle' | 'running'>('idle')
  const [lastRunAt, setLastRunAt] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)

  const run = useCallback(
    async (opts?: { fixture?: boolean; onComplete?: () => void }) => {
      setLogs([])
      setStatus('running')
      try {
        const { run_id } = await runPipeline({ fixture: opts?.fixture })
        const es = new EventSource(`/api/pipeline/stream/${run_id}`)
        esRef.current = es
        es.onmessage = (e) => {
          if (e.data === '[done]') {
            es.close()
            setStatus('idle')
            getPipelineStatus().then((s) => setLastRunAt(s.last_run_at))
            opts?.onComplete?.()
            return
          }
          setLogs((prev) => [...prev, e.data])
        }
        es.onerror = () => {
          es.close()
          setStatus('idle')
        }
      } catch (err) {
        setStatus('idle')
        setLogs((prev) => [...prev, `Error: ${err}`])
      }
    },
    []
  )

  return { status, lastRunAt, logs, run }
}
