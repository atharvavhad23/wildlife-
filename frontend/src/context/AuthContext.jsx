import { createContext, useContext, useEffect, useState } from 'react'
import { onAuthStateChanged, signOut } from 'firebase/auth'
import { auth, firebaseConfigured } from '../lib/firebase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    if (!firebaseConfigured || !auth) {
      setAuthReady(true)
      return
    }
    const unsubscribe = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser)
      setAuthReady(true)
    })
    return () => unsubscribe()
  }, [])

  const logout = async () => {
    if (!auth) return
    try {
      await signOut(auth)
    } catch {
      // ignore
    }
  }

  return (
    <AuthContext.Provider value={{ user, authReady, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
