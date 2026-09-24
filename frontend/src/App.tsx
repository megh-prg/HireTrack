import { useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api'
import Applications from './pages/Applications'
import DSA from './pages/DSA'
import FollowUps from './pages/FollowUps'
import Jobs from './pages/Jobs'
import Matching from './pages/Matching'
import Prep from './pages/Prep'
import ProgressPage from './pages/Progress'
import Recruiters from './pages/Recruiters'
import Settings from './pages/Settings'
import Sources from './pages/Sources'
import Today from './pages/Today'

// The job-search pipeline, in the order you work through it.
const NAV = [
  { to: '/', label: 'Today', icon: '⌂' },
  { to: '/jobs', label: 'Jobs', icon: '1' },
  { to: '/matching', label: 'Matching', icon: '2' },
  { to: '/applications', label: 'Applications', icon: '3' },
  { to: '/recruiters', label: 'Recruiters', icon: '4' },
  { to: '/dsa', label: 'DSA', icon: '5' },
  { to: '/prep', label: 'Interview Prep', icon: '6' },
  { to: '/followups', label: 'Follow-ups', icon: '7' },
  { to: '/progress', label: 'Progress', icon: '8' },
]

type Theme = 'light' | 'dark' | 'system'

function readTheme(): Theme {
  try {
    return (localStorage.getItem('hiretrack-theme') as Theme) || 'system'
  } catch {
    return 'system'
  }
}

function Shell() {
  const location = useLocation()
  const [dueCount, setDueCount] = useState(0)
  const [theme, setTheme] = useState<Theme>(readTheme)

  useEffect(() => {
    api.followups
      .list(0)
      .then((items) => setDueCount(items.filter((i) => i.kind === 'application' || i.kind === 'recruiter').length))
      .catch(() => setDueCount(0))
  }, [location.pathname])

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    try {
      localStorage.setItem('hiretrack-theme', theme)
    } catch {
      /* storage unavailable */
    }
  }, [theme])

  const nextTheme: Record<Theme, Theme> = { system: 'light', light: 'dark', dark: 'system' }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          HireTrack<small>Job search & interview prep</small>
        </div>
        <nav className="nav" aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'}>
              <span className="step">{item.icon}</span>
              {item.label}
              {item.to === '/followups' && dueCount > 0 && <span className="badge">{dueCount}</span>}
            </NavLink>
          ))}
          <div className="nav-sep" />
          <NavLink to="/sources">
            <span className="step">↻</span>Job sources
          </NavLink>
          <NavLink to="/settings">
            <span className="step">⚙</span>Profile & goals
          </NavLink>
        </nav>
        <div className="sidebar-foot">
          <button className="theme-toggle" onClick={() => setTheme(nextTheme[theme])}>
            Theme: {theme}
          </button>
        </div>
      </aside>
      <nav className="mobile-nav" aria-label="Main">
        {[...NAV, { to: '/sources', label: 'Sources' }, { to: '/settings', label: 'Profile' }].map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<Today />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/matching" element={<Matching />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/recruiters" element={<Recruiters />} />
          <Route path="/dsa" element={<DSA />} />
          <Route path="/prep" element={<Prep />} />
          <Route path="/followups" element={<FollowUps />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  )
}
