import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createUserWithEmailAndPassword, sendEmailVerification, signInWithEmailAndPassword } from 'firebase/auth'
import { auth, firebaseConfigured } from '../lib/firebase'

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

  const sendOtp = async () => {
    clearStatus()
    if (!email.trim()) {
      setError('Enter email first.')
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
      setError('Enter OTP code.')
      return
    }
    setLoading(true)
    try {
      await postJson('/auth/verify-otp/', { email, otp, purpose })
      setOtpVerified(true)
      setMessage('OTP verified. You can continue now.')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const submit = async () => {
    clearStatus()
    if (!firebaseConfigured || !auth) {
      setError('Firebase is not configured. Set frontend env values first.')
      return
    }
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.')
      return
    }
    if (!otpVerified) {
      setError('Please verify OTP first.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'signup') {
        const cred = await createUserWithEmailAndPassword(auth, email, password)
        await sendEmailVerification(cred.user)
        setMessage('Signup successful. Verification mail sent.')
      } else {
        await signInWithEmailAndPassword(auth, email, password)
      }
      navigate('/')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-wrapper" style={{ maxWidth: 520, paddingTop: 48 }}>
      <div className="glass-card" style={{ padding: 28 }}>
        <h1 style={{ fontSize: '1.8rem', marginBottom: 6 }}>Project Authentication</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 18 }}>
          {mode === 'signup' ? 'Create account' : 'Sign in'} with Firebase + email OTP.
        </p>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button className="quick-link-btn" onClick={() => { setMode('login'); setOtpVerified(false); setOtpSent(false) }}>
            Login
          </button>
          <button className="quick-link-btn" onClick={() => { setMode('signup'); setOtpVerified(false); setOtpSent(false) }}>
            Signup
          </button>
        </div>

        <div style={{ display: 'grid', gap: 10 }}>
          <input className="form-input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="form-input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="form-input" type="text" placeholder="6-digit OTP" value={otp} onChange={(e) => setOtp(e.target.value)} />
            <button className="btn-reset" onClick={sendOtp} disabled={loading}>Send OTP</button>
            <button className="btn-reset" onClick={verifyOtp} disabled={loading || !otpSent}>Verify OTP</button>
          </div>

          <button className="btn-predict" onClick={submit} disabled={loading}>
            {loading ? 'Please wait...' : mode === 'signup' ? 'Create Account' : 'Login'}
          </button>

          {message && <div style={{ color: '#66bb6a', fontSize: '0.9rem' }}>{message}</div>}
          {error && <div style={{ color: '#ff8e8e', fontSize: '0.9rem' }}>{error}</div>}

          {!firebaseConfigured && (
            <div style={{ marginTop: 8, color: 'var(--amber-400)', fontSize: '0.85rem' }}>
              Firebase config missing. Add VITE_FIREBASE_* values in frontend env.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
