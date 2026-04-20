import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Inbox from './pages/Inbox'
import History from './pages/History'
import Config from './pages/Config'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout pipelineStatus="idle" lastRunAt={null} />}>
        <Route index element={<Dashboard />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="history" element={<History />} />
        <Route path="config" element={<Config />} />
      </Route>
    </Routes>
  )
}
