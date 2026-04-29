import { Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'
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
import PredictHub from './pages/PredictHub'
import AboutUs from './pages/AboutUs'
import FAQ from './pages/FAQ'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import ToastContainer from './components/Toast'
import { PageLoader } from './components/Skeleton'

function RequireAuth({ children }) {
  const { user, authReady } = useAuth()
  if (!authReady) return <PageLoader label="Checking authentication…" />
  if (!user) return <Navigate to="/auth" replace />
  return children
}

function NotFound() {
  return (
    <div className="page-wrapper flex flex-col items-center justify-center min-h-[60vh] text-center gap-6">
      <div className="text-8xl">🌿</div>
      <div>
        <h2 className="text-2xl font-bold text-white/60 mb-3">Page not found</h2>
        <p className="text-white/30 text-sm mb-6">The page you're looking for doesn't exist.</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-xl border border-green-500/30 font-semibold text-sm transition-all"
        >
          ← Back to Home
        </Link>
      </div>
    </div>
  )
}

function AnimatedRoutes() {
  const location = useLocation()
  const { user } = useAuth()

  const withTransition = (Element) => (
    <PageTransition>
      <Element />
    </PageTransition>
  )

  const withAuth = (Element) => (
    <RequireAuth>
      {withTransition(Element)}
    </RequireAuth>
  )

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/auth" element={user ? <Navigate to="/" replace /> : withTransition(Auth)} />
        <Route path="/" element={withTransition(Home)} />
        <Route path="/about" element={withTransition(AboutUs)} />
        <Route path="/faq" element={withTransition(FAQ)} />
        <Route path="/dashboard" element={withAuth(Dashboard)} />
        <Route path="/models" element={withAuth(PredictHub)} />
        <Route path="/animals" element={withAuth(Animals)} />
        <Route path="/birds" element={withAuth(Birds)} />
        <Route path="/insects" element={withAuth(Insects)} />
        <Route path="/plants" element={withAuth(Plants)} />
        <Route path="/:species/photos" element={withAuth(PhotosGallery)} />
        <Route path="/animals/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/animals/species" element={withAuth(SpeciesDetail)} />
        <Route path="/birds/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/birds/species" element={withAuth(SpeciesDetail)} />
        <Route path="/insects/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/insects/species" element={withAuth(SpeciesDetail)} />
        <Route path="/plants/clustering" element={withAuth(ClusteringMap)} />
        <Route path="/plants/species" element={withAuth(SpeciesDetail)} />
        <Route path="/profile" element={withAuth(Profile)} />
        <Route path="*" element={withTransition(NotFound)} />
      </Routes>
    </AnimatePresence>
  )
}

function AppShell() {
  const location = useLocation()
  const showNavbar = location.pathname !== '/auth'

  // ── Sync Document Title ──
  useEffect(() => {
    const path = location.pathname
    let title = 'Koyna Wildlife Intelligence'
    if (path === '/' || path === '/dashboard') title = 'Dashboard | Koyna Intelligence'
    else if (path === '/home') title = 'Species Selection | Koyna Intelligence'
    else if (path.includes('animals')) title = 'Animals Prediction | Koyna'
    else if (path.includes('birds')) title = 'Birds Prediction | Koyna'
    else if (path.includes('insects')) title = 'Insects Prediction | Koyna'
    else if (path.includes('plants')) title = 'Plants Prediction | Koyna'
    else if (path === '/auth') title = 'Platform Access | Koyna'
    else if (path === '/profile') title = 'Your Profile | Koyna'
    document.title = title
  }, [location])

  return (
    <>
      {showNavbar && <Navbar />}
      <AnimatedRoutes />
      <ToastContainer />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppShell />
      </ToastProvider>
    </AuthProvider>
  )
}
