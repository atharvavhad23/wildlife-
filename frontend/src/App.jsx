import { BrowserRouter, Routes, Route } from 'react-router-dom'
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

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/animals" element={<Animals />} />
        <Route path="/birds" element={<Birds />} />
        <Route path="/insects" element={<Insects />} />
        <Route path="/:species/photos" element={<PhotosGallery />} />
        <Route path="/animals/clustering" element={<ClusteringMap />} />
        <Route path="/animals/species" element={<SpeciesDetail />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
