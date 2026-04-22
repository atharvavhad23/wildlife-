import { auth } from '../lib/firebase'
import { Link } from 'react-router-dom'
import { signOut } from 'firebase/auth'

export default function Profile() {
  const user = auth?.currentUser;

  const handleLogout = async () => {
    if (!auth) return
    try {
      await signOut(auth)
    } catch {
      // ignore
    }
  }

  return (
    <div className="page-wrapper">
      <Link to="/" className="back-link">← Back to Dashboard</Link>
      
      <div className="glass-card" style={{ padding: '48px', maxWidth: '600px', margin: '40px auto', textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', marginBottom: '20px' }}>👤</div>
        <h1 style={{ fontSize: '2rem', marginBottom: '8px', color: 'var(--green-300)' }}>Your Profile</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
          Wildlife Prediction System Account
        </p>

        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '24px', marginBottom: '32px', textAlign: 'left' }}>
          <div style={{ marginBottom: '16px' }}>
            <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Email Address</span>
            <span style={{ fontSize: '1.2rem', fontWeight: 600, color: 'white' }}>{user?.email || 'Guest User'}</span>
          </div>
          <div>
            <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Account Status</span>
            <span style={{ display: 'inline-block', padding: '4px 10px', background: 'rgba(46,204,113,0.15)', color: '#4ecdc4', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 700 }}>
              Active Analyst
            </span>
          </div>
        </div>

        <button 
          onClick={handleLogout}
          style={{
            padding: '12px 32px',
            background: 'rgba(255,107,107,0.1)',
            border: '1px solid rgba(255,107,107,0.3)',
            color: '#ff6b6b',
            borderRadius: '8px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={e => e.currentTarget.style.background = 'rgba(255,107,107,0.2)'}
          onMouseOut={e => e.currentTarget.style.background = 'rgba(255,107,107,0.1)'}
        >
          Logout from account
        </button>
      </div>
    </div>
  )
}
