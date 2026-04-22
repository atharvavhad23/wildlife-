import { NavLink } from 'react-router-dom'
import { signOut } from 'firebase/auth'
import { auth } from '../lib/firebase'

export default function Navbar() {
  const logout = async () => {
    if (!auth) return
    try {
      await signOut(auth)
    } catch {
      // Keep UI responsive even if logout fails once.
    }
  }

  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-brand">
        <span className="brand-emoji">🌿</span>
        <span>Wildlife Prediction</span>
        <span style={{ fontSize: '0.7rem', fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>
          Koyna
        </span>
      </NavLink>

      <div className="navbar-links">
        <NavLink to="/home" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">🏠</span> Home
        </NavLink>
        <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">📊</span> Dashboard
        </NavLink>
        <NavLink to="/animals" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">🦁</span> Animals
        </NavLink>
        <NavLink to="/birds" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">🦅</span> Birds
        </NavLink>
        <NavLink to="/insects" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">🦋</span> Insects
        </NavLink>
        <NavLink to="/plants" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">🌿</span> Plants
        </NavLink>
        <button type="button" className="nav-link" onClick={logout}>Logout</button>
      </div>
    </nav>
  )
}
