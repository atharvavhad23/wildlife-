import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import { onAuthStateChanged } from 'firebase/auth'
import { PageTransition } from './components/PageTransition'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Animals from './pages/Animals'
import Birds from './pages/Birds'
import Insects from './pages/Insects'
import PhotosGallery from './pages/PhotosGallery'
import ClusteringMap from './pages/ClusteringMap'
import SpeciesDetail from './pages/SpeciesDetail'
import Dashboard from './pages/Dashboard'
import Plants from './pages/Plants'
import Auth from './pages/Auth'
import Profile from './pages/Profile'
import { auth, firebaseConfigured } from './lib/firebase'

function RequireAuth({ user, authReady, children }) {
  if (!authReady) {
    return <div className="page-wrapper" style={{ paddingTop: 64 }}>Checking authentication...</div>
  }
  if (!user) {
    return <Navigate to="/auth" replace />
  }
  return children
}

function NotFound() {
  return (
    <div className="page-wrapper" style={{ textAlign: 'center', paddingTop: 100 }}>
      <div style={{ fontSize: '5rem', marginBottom: 20 }}>🌿</div>
      <h2 style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>Page not found</h2>
      <a href="/" style={{ color: 'var(--green-300)' }}>← Back to Home</a>
    </div>
  )
}

function AnimatedRoutes({ user, authReady }) {
  const location = useLocation()
  
  // A helper component to wrap elements in PageTransition
  const withTransition = (Element) => (
    <PageTransition>
      <Element />
    </PageTransition>
  )

  const withAuth = (Element) => (
    <RequireAuth user={user} authReady={authReady}>
      {withTransition(Element)}
    </RequireAuth>
  )

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/auth" element={user ? <Navigate to="/" replace /> : withTransition(Auth)} />
        <Route path="/" element={withAuth(Dashboard)} />
        <Route path="/home" element={withAuth(Home)} />
        <Route path="/dashboard" element={withAuth(Dashboard)} />
        <Route path="/animals" element={withAuth(Animals)} />
        <Route path="/birds" element={withAuth(Birds)} />
        <Route path="/insects" element={withAuth(Insects)} />
        <Route path="/:species/photos" element={withAuth(PhotosGallery)} />
        <Route path="/animals/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/animals/species" element={withAuth(SpeciesDetail)} />
        <Route path="/birds/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/birds/species" element={withAuth(SpeciesDetail)} />
        <Route path="/insects/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/insects/species" element={withAuth(SpeciesDetail)} />
        <Route path="/plants" element={withAuth(Plants)} />
        <Route path="/plants/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/plants/species" element={withAuth(SpeciesDetail)} />
        <Route path="/profile" element={withAuth(Profile)} />
        <Route path="*" element={withAuth(NotFound)} />
      </Routes>
    </AnimatePresence>
  )
}

export default function App() {
  const location = useLocation()
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

  // ── Sync Document Title ──
  useEffect(() => {
    const path = location.pathname;
    let title = "Koyna Wildlife Intelligence";
    if (path === '/') title = "Dashboard | Koyna Intelligence";
    else if (path === '/home') title = "Species Selection | Koyna Intelligence";
    else if (path.includes('animals')) title = "Animals Prediction | Koyna";
    else if (path.includes('birds')) title = "Birds Prediction | Koyna";
    else if (path.includes('insects')) title = "Insects Prediction | Koyna";
    else if (path.includes('plants')) title = "Plants Prediction | Koyna";
    else if (path === '/auth') title = "Platform Access | Koyna";
    else if (path === '/profile') title = "Your Profile | Koyna";
    
    document.title = title;
  }, [location])

  const showNavbar = location.pathname !== '/auth'

  return (
    <>
      {showNavbar && <Navbar />}
      <AnimatedRoutes user={user} authReady={authReady} />
    </>
  )
}
