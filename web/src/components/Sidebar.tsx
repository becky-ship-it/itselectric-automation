import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/inbox', label: 'Inbox' },
  { to: '/history', label: 'History' },
  { to: '/config', label: 'Config' },
  { to: '/logs', label: 'Logs' },
]

export default function Sidebar() {
  return (
    <nav className="w-48 shrink-0 bg-gray-900 text-white flex flex-col h-full p-4 gap-1">
      <div className="mb-5 px-2">
        <img src="/logo.svg" alt="it's electric" className="w-full max-w-[140px]" style={{ filter: 'brightness(0) invert(1)' }} />
      </div>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `px-3 py-2 rounded text-sm font-medium transition-colors ${
              isActive
                ? 'bg-gray-700 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
