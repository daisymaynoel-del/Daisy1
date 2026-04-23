import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Film, CheckSquare, BarChart2,
  TrendingUp, Lightbulb, FileText, Upload, MessageSquare
} from 'lucide-react'
import clsx from 'clsx'

const links = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/chat',        icon: MessageSquare,   label: 'Agent Chat' },
  { to: '/upload',      icon: Upload,          label: 'Upload Content' },
  { to: '/approval',    icon: CheckSquare,     label: 'Approval Queue' },
  { to: '/content',     icon: Film,            label: 'Content Feed' },
  { to: '/analytics',   icon: BarChart2,       label: 'Analytics' },
  { to: '/trends',      icon: TrendingUp,      label: 'Trend Tracker' },
  { to: '/suggestions', icon: Lightbulb,       label: 'Suggestions' },
  { to: '/reports',     icon: FileText,        label: 'Reports' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-white border-r border-charcoal-100 flex flex-col flex-shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-charcoal-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">E</span>
          </div>
          <div>
            <p className="font-bold text-charcoal-900 text-sm leading-none">EASTEND</p>
            <p className="text-charcoal-400 text-xs mt-0.5">Social Agent</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx('sidebar-link', isActive && 'active')
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-charcoal-100">
        <p className="text-xs text-charcoal-400">East London, UK</p>
        <p className="text-xs text-charcoal-300">3 posts/day per platform</p>
      </div>
    </aside>
  )
}
