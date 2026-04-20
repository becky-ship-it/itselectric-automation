import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePipeline } from './usePipeline'

vi.mock('../api/client', () => ({
  getPipelineStatus: vi.fn().mockResolvedValue({
    status: 'idle',
    last_run_at: '2026-04-20T00:00:00Z',
    run_id: null,
  }),
  runPipeline: vi.fn().mockResolvedValue({ run_id: 'run-1' }),
}))

class FakeEventSource {
  static instances: FakeEventSource[] = []
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  closed = false

  url: string
  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }
  close() {
    this.closed = true
  }
  emit(data: string) {
    this.onmessage?.({ data })
  }
  error() {
    this.onerror?.()
  }
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
})

describe('usePipeline', () => {
  it('starts idle', () => {
    const { result } = renderHook(() => usePipeline())
    expect(result.current.status).toBe('idle')
    expect(result.current.logs).toEqual([])
  })

  it('transitions to running when run() is called', async () => {
    const { result } = renderHook(() => usePipeline())
    await act(() => result.current.run())
    expect(FakeEventSource.instances).toHaveLength(1)
    expect(FakeEventSource.instances[0].url).toContain('run-1')
  })

  it('accumulates log messages from SSE', async () => {
    const { result } = renderHook(() => usePipeline())
    await act(() => result.current.run())
    act(() => FakeEventSource.instances[0].emit('processing msg 1'))
    expect(result.current.logs).toContain('processing msg 1')
  })

  it('returns to idle and calls onComplete when [done] received', async () => {
    const onComplete = vi.fn()
    const { result } = renderHook(() => usePipeline())
    await act(() => result.current.run({ onComplete }))
    act(() => FakeEventSource.instances[0].emit('[done]'))
    expect(result.current.status).toBe('idle')
    expect(FakeEventSource.instances[0].closed).toBe(true)
    expect(onComplete).toHaveBeenCalledOnce()
  })

  it('returns to idle on EventSource error', async () => {
    const { result } = renderHook(() => usePipeline())
    await act(() => result.current.run())
    act(() => FakeEventSource.instances[0].error())
    expect(result.current.status).toBe('idle')
    expect(FakeEventSource.instances[0].closed).toBe(true)
  })
})
