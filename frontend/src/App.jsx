import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { PageTransition } from './components/PageTransition'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Animals from './pages/Animals'
import Birds from './pages/Birds'
import Insects from './pages/Insects'
import PhotosGallery from './pages/PhotosGallery'
import ClusteringMap from './pages/ClusteringMap'
import SpeciesDetail from './pages/SpeciesDetail'

function NotFound() {
  return (
    <div className="page-wrapper" style={{ textAlign: 'center', paddingTop: 100 }}>
      <div style={{ fontSize: '5rem', marginBottom: 20 }}>🌿</div>
      <h2 style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>Page not found</h2>
      <a href="/" style={{ color: 'var(--green-300)' }}>← Back to Home</a>
    </div>
  )
}

function AnimatedRoutes() {
  const location = useLocation()
  
  // A helper component to wrap elements in PageTransition
  const withTransition = (Element) => (
    <PageTransition>
      <Element />
    </PageTransition>
  )

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={withTransition(Home)} />
        <Route path="/animals" element={withTransition(Animals)} />
        <Route path="/birds" element={withTransition(Birds)} />
        <Route path="/insects" element={withTransition(Insects)} />
        <Route path="/:species/photos" element={withTransition(PhotosGallery)} />
        <Route path="/animals/clustering" element={withTransition(ClusteringMap)} />
        <Route path="/animals/species" element={withTransition(SpeciesDetail)} />
        <Route path="/birds/clustering" element={withTransition(ClusteringMap)} />
        <Route path="/birds/species" element={withTransition(SpeciesDetail)} />
        <Route path="/insects/clustering" element={withTransition(ClusteringMap)} />
        <Route path="/insects/species" element={withTransition(SpeciesDetail)} />
        <Route path="*" element={withTransition(NotFound)} />
      </Routes>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <>
      <Navbar />
      <AnimatedRoutes />
    </>
  )
}
