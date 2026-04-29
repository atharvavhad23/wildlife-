import { useState, useEffect, useRef } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

const NAV_ITEMS = [
  { to: '/home',    label: 'Home',      icon: '🏠' },
  { to: '/',        label: 'Dashboard', icon: '📊', end: true },
  { to: '/animals', label: 'Animals',   icon: '🦁' },
  { to: '/birds',   label: 'Birds',     icon: '🦅' },
  { to: '/insects', label: 'Insects',   icon: '🦋' },
  { to: '/plants',  label: 'Plants',    icon: '🌿' },
]

function UserDropdown({ user, onLogout, onClose }) {
  const dropRef = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : '??'

  return (
    <motion.div
      ref={dropRef}
      initial={{ opacity: 0, y: -8, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="absolute right-0 top-full mt-3 w-64 bg-[#0a1a0e]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50"
    >
      {/* Email header */}
      <div className="px-4 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-sm font-black">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-0.5">Signed in as</div>
            <div className="text-sm font-semibold text-white truncate">{user?.email || 'Unknown'}</div>
          </div>
        </div>
        <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-[10px] font-bold uppercase tracking-wider text-green-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Active Analyst
        </div>
      </div>

      {/* Links */}
      <div className="p-2">
        <NavLink
          to="/profile"
          onClick={onClose}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/60 hover:text-white hover:bg-white/5 transition-all"
        >
          <span className="text-base">👤</span> View Profile
        </NavLink>
      </div>

      {/* Logout */}
      <div className="p-2 border-t border-white/5">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all text-left"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sign out
        </button>
      </div>
    </motion.div>
  )
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dropOpen, setDropOpen] = useState(false)

  // Scroll shadow
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false) }, [])

  const handleLogout = async () => {
    setDropOpen(false)
    setMobileOpen(false)
    await logout()
    toast.success('Signed out successfully')
    navigate('/auth')
  }

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : '??'

  return (
    <>
      <nav
        className={`navbar transition-shadow duration-300 ${scrolled ? 'shadow-[0_4px_24px_rgba(0,0,0,0.5)]' : ''}`}
        style={{ height: 'var(--navbar-h)' }}
      >
        {/* Brand */}
        <NavLink to="/" className="navbar-brand gap-2">
          <span className="brand-emoji">🌿</span>
          <span className="hidden sm:inline">Wildlife Intelligence</span>
          <span className="inline sm:hidden font-bold">Koyna</span>
          <span className="text-[10px] font-normal text-white/30 hidden md:inline">Koyna WLS</span>
        </NavLink>

        {/* Desktop nav links */}
        <div className="navbar-links hidden md:flex">
          {NAV_ITEMS.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `nav-link relative group${isActive ? ' active' : ''}`
              }
            >
              {({ isActive }) => (
                <>
                  <span className="nav-icon">{icon}</span>
                  {label}
                  {isActive && (
                    <motion.span
                      layoutId="nav-indicator"
                      className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-green-400 to-emerald-400"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>

        {/* Right side: avatar + hamburger */}
        <div className="flex items-center gap-3">
          {/* User avatar button (desktop) */}
          {user && (
            <div className="relative hidden md:block">
              <button
                onClick={() => setDropOpen(v => !v)}
                className="w-9 h-9 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-sm font-black hover:scale-105 transition-transform focus:outline-none focus:ring-2 focus:ring-green-500/60"
                aria-label="User menu"
                aria-expanded={dropOpen}
              >
                {initials}
              </button>
              <AnimatePresence>
                {dropOpen && (
                  <UserDropdown
                    user={user}
                    onLogout={handleLogout}
                    onClose={() => setDropOpen(false)}
                  />
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Hamburger (mobile) */}
          <button
            className="md:hidden flex flex-col justify-center items-center w-10 h-10 gap-1.5 rounded-xl hover:bg-white/5 transition-colors"
            onClick={() => setMobileOpen(v => !v)}
            aria-label="Toggle navigation"
            aria-expanded={mobileOpen}
          >
            <motion.span
              animate={mobileOpen ? { rotate: 45, y: 7 } : { rotate: 0, y: 0 }}
              className="block w-5 h-0.5 bg-white/70 rounded-full origin-center"
              transition={{ duration: 0.2 }}
            />
            <motion.span
              animate={mobileOpen ? { opacity: 0, scaleX: 0 } : { opacity: 1, scaleX: 1 }}
              className="block w-5 h-0.5 bg-white/70 rounded-full"
              transition={{ duration: 0.2 }}
            />
            <motion.span
              animate={mobileOpen ? { rotate: -45, y: -7 } : { rotate: 0, y: 0 }}
              className="block w-5 h-0.5 bg-white/70 rounded-full origin-center"
              transition={{ duration: 0.2 }}
            />
          </button>
        </div>
      </nav>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            key="mobile-drawer"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="md:hidden fixed top-[64px] left-0 right-0 z-[90] bg-[#0a1a0e]/97 backdrop-blur-xl border-b border-white/10 shadow-2xl"
          >
            <div className="flex flex-col p-4 gap-1">
              {NAV_ITEMS.map(({ to, label, icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                      isActive
                        ? 'bg-green-500/15 text-green-300 border border-green-500/20'
                        : 'text-white/60 hover:text-white hover:bg-white/5'
                    }`
                  }
                >
                  <span className="text-lg">{icon}</span>
                  {label}
                </NavLink>
              ))}

              {/* Mobile user section */}
              {user && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <NavLink
                    to="/profile"
                    onClick={() => setMobileOpen(false)}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold text-white/60 hover:text-white hover:bg-white/5 transition-all"
                  >
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-xs font-black">
                      {initials}
                    </div>
                    <div>
                      <div className="text-white font-semibold text-sm">Profile</div>
                      <div className="text-white/30 text-xs truncate max-w-[180px]">{user.email}</div>
                    </div>
                  </NavLink>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold text-red-400 hover:bg-red-500/10 transition-all"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
