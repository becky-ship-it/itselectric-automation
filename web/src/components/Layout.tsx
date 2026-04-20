import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import StatusStrip from './StatusStrip'

interface Props {
  pipelineStatus: 'idle' | 'running'
  lastRunAt: string | null
}

export default function Layout({ pipelineStatus, lastRunAt }: Props) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <StatusStrip status={pipelineStatus} lastRunAt={lastRunAt} />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
