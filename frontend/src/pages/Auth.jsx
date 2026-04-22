import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUserWithEmailAndPassword, sendEmailVerification, signInWithEmailAndPassword } from 'firebase/auth'
import { auth, firebaseConfigured } from '../lib/firebase'
import { motion, AnimatePresence } from 'framer-motion'

async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Request failed')
  return data
}

export default function Auth() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [otpVerified, setOtpVerified] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const purpose = useMemo(() => mode, [mode])

  const clearStatus = () => {
    setMessage('')
    setError('')
  }

  const handleModeSwitch = (newMode) => {
    setMode(newMode)
    clearStatus()
    setOtpSent(false)
    setOtpVerified(false)
  }

  const sendOtp = async () => {
    clearStatus()
    if (!email.trim()) {
      setError('Please enter your email first.')
      return
    }
    setLoading(true)
    try {
      await postJson('/auth/send-otp/', { email, purpose })
      setOtpSent(true)
      setOtpVerified(false)
      setMessage('OTP sent to your email.')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async () => {
    clearStatus()
    if (!otp.trim()) {
      setError('Please enter the OTP code.')
      return
    }
    setLoading(true)
    try {
      await postJson('/auth/verify-otp/', { email, otp, purpose })
      setOtpVerified(true)
      setMessage('OTP verified successfully.')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    clearStatus()
    if (!firebaseConfigured || !auth) {
      setError('Firebase is not configured. Set frontend env values first.')
      return
    }
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.')
      return
    }
    if (mode === 'signup' && !otpVerified) {
      setError('Please verify your email with OTP first.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'signup') {
        const cred = await createUserWithEmailAndPassword(auth, email, password)
        await sendEmailVerification(cred.user)
        setMessage('Signup successful. Redirecting...')
      } else {
        await signInWithEmailAndPassword(auth, email, password)
      }
      setTimeout(() => navigate('/'), 1000)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-wrapper flex items-center justify-center min-h-[80vh] px-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 w-full max-w-md relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand-primary to-brand-light" />
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            {mode === 'signup' ? 'Create Account' : 'Welcome Back'}
          </h1>
          <p className="text-text-muted text-sm">
            {mode === 'signup' ? 'Sign up to start monitoring wildlife.' : 'Sign in to your account to continue.'}
          </p>
        </div>

        <div className="flex p-1 mb-8 bg-white/5 rounded-lg border border-white/5">
          <button 
            type="button"
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'login' ? 'bg-white/10 text-white shadow-sm' : 'text-text-muted hover:text-white'}`}
            onClick={() => handleModeSwitch('login')}
          >
            Sign In
          </button>
          <button 
            type="button"
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'signup' ? 'bg-white/10 text-white shadow-sm' : 'text-text-muted hover:text-white'}`}
            onClick={() => handleModeSwitch('signup')}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-5">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Email Address</label>
            <input 
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand/50 transition-all" 
              type="email" 
              placeholder="you@example.com" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Password</label>
            <div className="relative">
              <input 
                className="w-full bg-white/5 border border-white/10 rounded-lg pl-4 pr-12 py-3 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand/50 transition-all" 
                type={showPassword ? "text" : "password"} 
                placeholder="••••••••" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required
              />
              <button 
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-white transition-colors"
                aria-label="Toggle password visibility"
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                )}
              </button>
            </div>
          </div>

          <AnimatePresence>
            {mode === 'signup' && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <label className="block text-xs font-medium text-text-secondary mb-1 mt-1">Email Verification</label>
                <div className="flex gap-2">
                  <input 
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand/50 transition-all" 
                    type="text" 
                    placeholder="6-digit OTP" 
                    value={otp} 
                    onChange={(e) => setOtp(e.target.value)} 
                    disabled={otpVerified}
                  />
                  {!otpSent ? (
                    <button type="button" className="btn-predict px-4 py-0 shrink-0 text-sm whitespace-nowrap h-full min-h-[46px]" onClick={sendOtp} disabled={loading || !email}>
                      Send OTP
                    </button>
                  ) : !otpVerified ? (
                    <button type="button" className="btn-predict px-4 py-0 shrink-0 text-sm whitespace-nowrap h-full min-h-[46px]" onClick={verifyOtp} disabled={loading || !otp}>
                      Verify
                    </button>
                  ) : (
                    <div className="flex items-center justify-center px-4 bg-[#10B981]/20 text-[#10B981] rounded-lg border border-[#10B981]/30 shrink-0 h-[46px]">
                      <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
                      Verified
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <button 
            type="submit" 
            className="w-full bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-white font-semibold py-3 rounded-lg shadow-[0_0_15px_rgba(34,197,94,0.3)] transition-all active:scale-[0.98] mt-2 flex items-center justify-center"
            disabled={loading}
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            ) : mode === 'signup' ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <AnimatePresence>
          {message && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-6 p-3 bg-[#10B981]/10 border border-[#10B981]/20 rounded-lg text-[#10B981] text-sm text-center">
              {message}
            </motion.div>
          )}
          {error && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm text-center">
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {!firebaseConfigured && (
          <div className="mt-6 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-400 text-xs text-center">
            Firebase configuration is missing. Please add VITE_FIREBASE_* variables to your frontend environment.
          </div>
        )}
      </motion.div>
    </div>
  )
}
