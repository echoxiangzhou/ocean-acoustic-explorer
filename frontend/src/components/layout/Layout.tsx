import { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import './Layout.css'

const NAV_ITEMS = [
  { path: '/overview', label: 'A 全球声场', icon: '🌍' },
  { path: '/profiles', label: 'B 声速剖面', icon: '📊' },
  { path: '/analysis', label: 'C 精细分析', icon: '🔬' },
  { path: '/trends', label: 'D 趋势分析', icon: '📈' },
  { path: '/scenarios', label: 'E 场景模拟', icon: '⚡' },
]

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-layout">
      <header className="top-bar">
        <div className="logo">OceanAcoustic Explorer</div>
        <nav className="nav-tabs">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="main-content">{children}</main>
    </div>
  )
}
