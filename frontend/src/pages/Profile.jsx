import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'



export default function Profile() {
  const { user, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    toast.success('Signed out successfully')
    navigate('/auth')
  }

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : '??'

  const memberSince = user?.metadata?.creationTime
    ? new Date(user.metadata.creationTime).toLocaleDateString('en-IN', { year: 'numeric', month: 'long' })
    : 'N/A'

  const lastSignIn = user?.metadata?.lastSignInTime
    ? new Date(user.metadata.lastSignInTime).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : 'N/A'

  return (
    <div className="page-wrapper pb-24">
      {/* Back */}
      <Link to="/" className="back-link mt-6 inline-flex">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
        </svg>
        Back to Dashboard
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="max-w-2xl mx-auto mt-8"
      >
        {/* Avatar card */}
        <div className="glass-card p-8 text-center mb-6 relative overflow-hidden">
          {/* Background glow */}
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 via-transparent to-teal-500/5 pointer-events-none" />

          {/* Avatar */}
          <div className="relative inline-block mb-5">
            <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-4xl font-black shadow-[0_0_40px_rgba(16,185,129,0.4)] mx-auto">
              {initials}
            </div>
            <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-green-400 border-2 border-[#0a1a0e] flex items-center justify-center">
              <span className="text-[8px]">✓</span>
            </div>
          </div>

          <h1 className="text-3xl font-extrabold text-white tracking-tight mb-1">Your Profile</h1>
          <p className="text-white/40 text-sm mb-5">Wildlife Prediction System Account</p>

          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-bold uppercase tracking-widest">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Active Analyst
          </div>
        </div>

        {/* Account info */}
        <div className="glass-card p-6 mb-6">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/40 mb-5">Account Details</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <span className="text-sm text-white/50 font-medium">Email Address</span>
              <span className="text-sm font-semibold text-white">{user?.email || 'Guest User'}</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <span className="text-sm text-white/50 font-medium">Member Since</span>
              <span className="text-sm font-semibold text-white">{memberSince}</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <span className="text-sm text-white/50 font-medium">Last Sign In</span>
              <span className="text-sm font-semibold text-white">{lastSignIn}</span>
            </div>
            <div className="flex items-center justify-between py-3">
              <span className="text-sm text-white/50 font-medium">Email Verified</span>
              <span className={`text-sm font-bold ${user?.emailVerified ? 'text-green-400' : 'text-amber-400'}`}>
                {user?.emailVerified ? '✓ Verified' : '⚠ Unverified'}
              </span>
            </div>
          </div>
        </div>

        {/* Logout */}
        <div className="glass-card p-6">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/40 mb-4">Danger Zone</h2>
          <p className="text-sm text-white/40 mb-5 leading-relaxed">
            Signing out will end your current session. You will need to sign in again to access the platform.
          </p>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-6 py-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 hover:border-red-500/50 text-red-400 hover:text-red-300 font-semibold text-sm transition-all active:scale-95"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out of Account
          </button>
        </div>
      </motion.div>
    </div>
  )
}
