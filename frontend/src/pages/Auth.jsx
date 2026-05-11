import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUserWithEmailAndPassword, sendEmailVerification, signInWithEmailAndPassword, sendPasswordResetEmail } from 'firebase/auth'
import { auth, firebaseConfigured } from '../lib/firebase'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Eye, 
  EyeOff, 
  Mail, 
  Lock, 
  CheckCircle, 
  ArrowRight, 
  ArrowLeft, 
  ShieldCheck, 
  Zap 
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

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

function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase()
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

export default function Auth() {
  const navigate = useNavigate()
  const toast = useToast()
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
    const normalizedEmail = normalizeEmail(email)
    if (!normalizedEmail) {
      setError('Please enter your email first.')
      return
    }
    if (!isValidEmail(normalizedEmail)) {
      setError('Please enter a valid email address.')
      return
    }
    setLoading(true)
    try {
      await postJson('/auth/send-otp/', { email: normalizedEmail, purpose })
      setOtpSent(true)
      setOtpVerified(false)
      setEmail(normalizedEmail)
      setMessage('OTP sent to your email.')
      toast.success('OTP sent — check your inbox')
    } catch (e) {
      setError(e.message)
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async () => {
    clearStatus()
    const normalizedEmail = normalizeEmail(email)
    if (!isValidEmail(normalizedEmail)) {
      setError('Please enter a valid email address.')
      return
    }
    if (!otp.trim()) {
      setError('Please enter the OTP code.')
      return
    }
    setLoading(true)
    try {
      await postJson('/auth/verify-otp/', { email: normalizedEmail, otp: otp.trim(), purpose })
      setOtpVerified(true)
      setMessage('OTP verified successfully.')
      toast.success('Email verified ✓')
    } catch (e) {
      setError(e.message)
      toast.error(e.message)
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

    if (mode === 'reset') {
      if (!email.trim()) {
        setError('Please enter your email to reset your password.')
        return
      }
      setLoading(true)
      try {
        await sendPasswordResetEmail(auth, email)
        setMessage('Password reset email sent! Check your inbox.')
        toast.success('Reset email sent — check your inbox')
      } catch (e) {
        setError(e.message)
        toast.error(e.message)
      } finally {
        setLoading(false)
      }
      return
    }

    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.')
      return
    }

    const normalizedEmail = email.trim().toLowerCase()

    if (!isValidEmail(normalizedEmail)) {
      setError('Please enter a valid email address.')
      return
    }
    if (mode === 'signup' && !otpVerified) {
      setError('Please verify your email with OTP first.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'signup') {
        const cred = await createUserWithEmailAndPassword(auth, normalizedEmail, password)
        await sendEmailVerification(cred.user)
        setMessage('Signup successful. Redirecting...')
        toast.success('Account created! Welcome to Koyna Intelligence')
      } else {
        await signInWithEmailAndPassword(auth, normalizedEmail, password)
        toast.success('Welcome back! Signed in successfully')
      }
      setEmail(normalizedEmail)
      setTimeout(() => navigate('/'), 1000)
    } catch (e) {
      setError(e.message)
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen w-full flex bg-[#050d06] overflow-hidden relative">
      {/* Left Decorative Panel (Hidden on Mobile) */}
      <div className="hidden lg:flex flex-1 relative items-center justify-center border-r border-white/5 overflow-hidden">
        {/* Animated Neon Blobs */}
        <motion.div 
          animate={{ scale: [1, 1.2, 1], rotate: [0, 90, 0] }} 
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }} 
          className="absolute -top-[20%] -left-[10%] w-[800px] h-[800px] bg-green-500/20 rounded-full blur-[140px]" 
        />
        <motion.div 
          animate={{ scale: [1, 1.5, 1], rotate: [0, -90, 0] }} 
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }} 
          className="absolute -bottom-[20%] -right-[10%] w-[600px] h-[600px] bg-teal-500/15 rounded-full blur-[120px]" 
        />
        
        <div className="relative z-10 p-16 max-w-2xl">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.8, ease: "easeOut" }}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-green-400 text-xs font-bold uppercase tracking-widest mb-8">
              <Zap size={14} fill="currentColor" /> Platform Access
            </div>
            <h2 className="text-6xl font-extrabold text-white mb-6 tracking-tighter leading-[1.1]">
              Wildlife Intelligence <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-emerald-400 to-teal-400">At Your Fingertips.</span>
            </h2>
            <p className="text-lg text-white/50 leading-relaxed font-medium max-w-lg">
              Access hyper-localized biodiversity predictions, deep spatial clustering maps, and academic-grade machine learning insights for the Koyna Sanctuary.
            </p>
          </motion.div>
        </div>
      </div>

      {/* Right Auth Panel */}
      <div className="w-full lg:w-[500px] xl:w-[600px] flex flex-col justify-center px-6 py-12 lg:px-16 relative z-10 bg-black/40 backdrop-blur-xl shadow-2xl">
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="w-full max-w-[420px] mx-auto"
        >
          <div className="mb-10">
            <h1 className="text-4xl lg:text-5xl font-extrabold text-white mb-3 tracking-tight">
              {mode === 'signup' ? 'Create Account' : mode === 'reset' ? 'Reset Password' : 'Welcome Back'}
            </h1>
            <p className="text-white/50 text-sm font-medium">
              {mode === 'signup' ? 'Sign up to start monitoring wildlife.' : mode === 'reset' ? 'Enter your email to receive a secure recovery link.' : 'Sign in to your dashboard to continue.'}
            </p>
          </div>

          <div className="flex p-1.5 mb-10 bg-white/5 rounded-xl border border-white/5 relative shadow-inner">
            <button 
              type="button"
              className={`flex-1 py-2.5 text-xs font-black uppercase tracking-widest rounded-lg transition-all z-10 ${mode === 'login' ? 'text-white' : 'text-white/40 hover:text-white/80'}`}
              onClick={() => handleModeSwitch('login')}
            >
              Sign In
            </button>
            <button 
              type="button"
              className={`flex-1 py-2.5 text-xs font-black uppercase tracking-widest rounded-lg transition-all z-10 ${mode === 'signup' ? 'text-white' : 'text-white/40 hover:text-white/80'}`}
              onClick={() => handleModeSwitch('signup')}
            >
              Sign Up
            </button>
            {/* Animated background pill */}
            <motion.div 
              className="absolute top-1.5 bottom-1.5 w-[calc(50%-6px)] bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg shadow-[0_0_20px_rgba(16,185,129,0.3)]"
              animate={{ left: mode === 'signup' ? 'calc(50% + 4px)' : '6px', opacity: mode === 'reset' ? 0 : 1 }}
              transition={{ type: 'spring', bounce: 0.2, duration: 0.5 }}
            />
          </div>

          <form onSubmit={submit} className="flex flex-col gap-6">
            <div className="group">
              <label className="block text-xs font-bold uppercase tracking-wider text-white/50 mb-2 group-focus-within:text-green-400 transition-colors">Email Address</label>
              <input 
                className="w-full bg-black/50 border border-white/10 rounded-xl px-5 py-4 text-white placeholder-white/20 focus:outline-none focus:border-green-500/50 focus:ring-1 focus:ring-green-500/50 transition-all shadow-inner text-sm" 
                type="email" 
                placeholder="you@example.com" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                required
              />
            </div>

            <AnimatePresence>
              {mode !== 'reset' && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden group"
                >
                  <div className="flex justify-between items-end mb-2 pt-1">
                    <label className="block text-xs font-bold uppercase tracking-wider text-white/50 group-focus-within:text-green-400 transition-colors">Password</label>
                    {mode === 'login' && (
                      <button type="button" onClick={() => handleModeSwitch('reset')} className="text-[10px] font-bold uppercase tracking-wider text-green-400 hover:text-green-300 transition-colors">
                        Forgot Password?
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <input 
                      className="w-full bg-black/50 border border-white/10 rounded-xl pl-5 pr-12 py-4 text-white placeholder-white/20 focus:outline-none focus:border-green-500/50 focus:ring-1 focus:ring-green-500/50 transition-all shadow-inner text-sm tracking-widest" 
                      type={showPassword ? "text" : "password"} 
                      placeholder="••••••••" 
                      value={password} 
                      onChange={(e) => setPassword(e.target.value)} 
                      required={mode !== 'reset'}
                    />
                    <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 p-1 text-white/30 hover:text-white transition-colors"
                      aria-label="Toggle password visibility"
                    >
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {mode === 'signup' && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden group"
                >
                  <label className="block text-xs font-bold uppercase tracking-wider text-white/50 mb-2 group-focus-within:text-green-400 transition-colors pt-2">Email Verification</label>
                  <div className="flex gap-3">
                    <input 
                      className="flex-1 bg-black/50 border border-white/10 rounded-xl px-5 py-4 text-white placeholder-white/20 focus:outline-none focus:border-green-500/50 focus:ring-1 focus:ring-green-500/50 transition-all shadow-inner text-sm tracking-widest text-center" 
                      type="text" 
                      placeholder="6-DIGIT OTP" 
                      value={otp} 
                      onChange={(e) => setOtp(e.target.value)} 
                      disabled={otpVerified}
                    />
                    {!otpSent ? (
                      <button type="button" className="btn-predict px-6 py-0 shrink-0 text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg h-auto min-h-[52px]" onClick={sendOtp} disabled={loading || !email}>
                        Send OTP
                      </button>
                    ) : !otpVerified ? (
                      <button type="button" className="btn-predict px-6 py-0 shrink-0 text-xs font-bold uppercase tracking-wider rounded-xl shadow-lg h-auto min-h-[52px]" onClick={verifyOtp} disabled={loading || !otp}>
                        Verify
                      </button>
                    ) : (
                      <div className="flex items-center justify-center px-6 bg-green-500/20 text-green-400 rounded-xl border border-green-500/30 shrink-0 h-auto min-h-[52px] font-bold text-xs uppercase tracking-wider shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                        <CheckCircle size={16} className="mr-1.5" />
                        Verified
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <button 
              type="submit" 
              className="w-full bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white font-extrabold uppercase tracking-widest py-4 rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] transition-all active:scale-[0.98] mt-6 flex items-center justify-center border border-green-400/30 group"
              disabled={loading}
            >
              {loading ? (
                <div className="animate-spin h-5 w-5 border-2 border-white/20 border-t-white rounded-full" />
              ) : mode === 'signup' ? (
                <>Create Account <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" /></>
              ) : mode === 'reset' ? (
                <>Send Reset Link <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" /></>
              ) : (
                <>Secure Sign In <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" /></>
              )}
            </button>

            <AnimatePresence>
              {mode === 'reset' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center mt-2">
                  <button type="button" onClick={() => handleModeSwitch('login')} className="flex items-center justify-center gap-2 mx-auto text-[11px] font-bold uppercase tracking-widest text-white/40 hover:text-white transition-colors">
                    <ArrowLeft size={12} /> Back to Sign In
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </form>

          <AnimatePresence>
            {message && (
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-8 p-4 bg-green-500/10 border border-green-500/20 rounded-xl text-green-400 text-sm font-semibold text-center shadow-lg">
                {message}
              </motion.div>
            )}
            {error && (
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-8 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm font-semibold text-center shadow-lg">
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {!firebaseConfigured && (
            <div className="mt-8 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl text-yellow-500 text-xs font-bold uppercase tracking-wider text-center">
              Firebase configuration missing. Check .env variables.
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
