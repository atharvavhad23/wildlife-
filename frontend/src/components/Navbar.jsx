import { NavLink } from 'react-router-dom'

export default function Navbar() {
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
        <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span className="nav-icon">🏠</span> Home
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
      </div>
    </nav>
  )
}
