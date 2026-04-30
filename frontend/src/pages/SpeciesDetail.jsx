import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { SkeletonPhoto } from '../components/Skeleton'

let leafletAssetsPromise = null
function ensureLeafletAssets() {
  if (window.L) return Promise.resolve(window.L)
  if (leafletAssetsPromise) return leafletAssetsPromise

  leafletAssetsPromise = new Promise((resolve, reject) => {
    if (!document.querySelector('link[data-leaflet="true"]')) {
      const css = document.createElement('link')
      css.rel = 'stylesheet'
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      css.setAttribute('data-leaflet', 'true')
      document.head.appendChild(css)
    }
    const existing = document.querySelector('script[data-leaflet="true"]')
    if (existing) {
      existing.addEventListener('load', () => resolve(window.L))
      existing.addEventListener('error', () => reject(new Error('Failed to load Leaflet')))
      return
    }
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.async = true
    script.setAttribute('data-leaflet', 'true')
    script.onload = () => resolve(window.L)
    script.onerror = () => reject(new Error('Failed to load Leaflet'))
    document.body.appendChild(script)
  })
  return leafletAssetsPromise
}

function InfoItem({ label, value }) {
  return (
    <div className="glass-card p-4 hover:-translate-y-0.5 transition-transform">
      <div className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-1.5">{label}</div>
      <div className="text-sm font-semibold text-white">{value || 'Unknown'}</div>
    </div>
  )
}

function PhotoCard({ photo }) {
  const src = photo.thumbnailUrl ? `/photo-proxy/?url=${encodeURIComponent(photo.thumbnailUrl)}` : null
  return (
    <div className="photo-card group">
      <div className="photo-img-wrap relative">
        {src
          ? <img src={src} alt={photo.title} loading="lazy" className="w-full h-full object-cover group-hover:scale-[1.06] transition-transform duration-500" />
          : <span className="photo-placeholder">🌿</span>
        }
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
          <div className="text-white text-xs font-semibold truncate">{photo.title}</div>
          {photo.subtitle && <div className="text-white/60 text-[10px] italic truncate">{photo.subtitle}</div>}
        </div>
      </div>
      <div className="photo-info">
        <div className="photo-title" title={photo.title}>{photo.title}</div>
        <div className="photo-sub">{photo.subtitle}</div>
        {photo.eventDate && <div className="photo-sub mt-1">📅 {photo.eventDate}</div>}
      </div>
    </div>
  )
}

export default function SpeciesDetail() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const species = (searchParams.get('species') || '').trim()

  const [detail, setDetail] = useState(null)
  const [photos, setPhotos] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const title = useMemo(() => detail?.scientificName || species || 'Species Detail', [detail, species])
  const category = window.location.pathname.split('/')[1] || 'animals'

  useEffect(() => {
    let active = true
    const load = async () => {
      if (!species) { setError('Missing species parameter in URL.'); setLoading(false); return }
      setLoading(true); setError(null)
      try {
        const [detailRes, photosRes] = await Promise.all([
          fetch(`/api/${category}/species/?species=${encodeURIComponent(species)}`),
          fetch(`/api/${category}/species-photos/?species=${encodeURIComponent(species)}&offset=0&limit=24`),
        ])
        const detailData = await detailRes.json()
        const photosData = await photosRes.json()
        if (!active) return
        if (detailData.error) throw new Error(detailData.error)
        setDetail(detailData)
        setPhotos(photosData.photos || [])
        setOffset(photosData.nextOffset || (photosData.photos || []).length)
        setHasMore(Boolean(photosData.hasMore))
      } catch (e) {
        if (!active) return
        setError(e.message)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [species])

  useEffect(() => {
    let map = null; let mounted = true
    const setupMap = async () => {
      if (!detail?.locations?.length) return
      try {
        const L = await ensureLeafletAssets()
        if (!mounted) return
        const mapEl = document.getElementById('species-map')
        if (!mapEl) return
        mapEl.innerHTML = ''
        map = L.map(mapEl)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '© OpenStreetMap' }).addTo(map)
        const points = detail.locations.filter(p => Number.isFinite(p.latitude) && Number.isFinite(p.longitude)).map(p => [p.latitude, p.longitude])
        if (!points.length) return
        points.slice(0, 300).forEach(([lat, lon]) => {
          L.circleMarker([lat, lon], { radius: 4, color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.65, weight: 1 }).addTo(map)
        })
        if (points.length > 1) map.fitBounds(points, { padding: [20, 20] })
        else map.setView(points[0], 9)
      } catch { /* keep page usable */ }
    }
    setupMap()
    return () => { mounted = false; if (map) map.remove() }
  }, [detail])

  const loadMorePhotos = async () => {
    if (!hasMore || loadingMore || !species) return
    setLoadingMore(true)
    try {
      const res = await fetch(`/api/${category}/species-photos/?species=${encodeURIComponent(species)}&offset=${offset}&limit=24`)
      const data = await res.json()
      setPhotos(prev => [...prev, ...(data.photos || [])])
      setOffset(data.nextOffset || offset)
      setHasMore(Boolean(data.hasMore))
    } finally { setLoadingMore(false) }
  }

  return (
    <div className="page-wrapper pb-20">
      {/* Back */}
      <button onClick={() => navigate(-1)} className="back-link mt-6 inline-flex border-none bg-transparent cursor-pointer">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
        </svg>
        Back
      </button>

      {/* Species header */}
      <div className="pt-6 pb-8">
        <motion.h1
          className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-green-300 tracking-tight mb-2"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {title}
        </motion.h1>
        {detail?.class && detail?.family && (
          <p className="text-white/40 text-sm font-medium">{detail.class} • {detail.family}</p>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="glass-card p-4">
                <div className="skeleton-pulse h-2 w-16 rounded mb-2" />
                <div className="skeleton-pulse h-4 w-24 rounded" />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => <SkeletonPhoto key={i} />)}
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-start gap-3 p-5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
          <span className="text-lg">⚠️</span>
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {/* Content */}
      {!loading && detail && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          {/* Info grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-8">
            <InfoItem label="Kingdom"  value={detail.kingdom} />
            <InfoItem label="Phylum"   value={detail.phylum} />
            <InfoItem label="Class"    value={detail.class} />
            <InfoItem label="Order"    value={detail.order} />
            <InfoItem label="Family"   value={detail.family} />
            <InfoItem label="Genus"    value={detail.genus} />
            <InfoItem label="Records"  value={detail.observationCount?.toLocaleString()} />
          </div>

          {/* Map + Species info */}
          <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-5 mb-8">
            <div className="glass-card p-5">
              <div className="section-heading">🧭 Geographic Range</div>
              <div id="species-map" className="w-full h-[360px] rounded-xl border border-white/8 overflow-hidden" />
            </div>

            <div className="glass-card p-5">
              <div className="section-heading">ℹ️ Species Information</div>
              <div className="flex flex-col gap-3">
                {[
                  { label: 'Common Name',    value: detail.species || 'N/A' },
                  { label: 'Scientific Name', value: detail.scientificName },
                  { label: 'Date Range',     value: `${detail?.dateRange?.earliest || 'N/A'} → ${detail?.dateRange?.latest || 'N/A'}` },
                  { label: 'Center Coords',  value: `Lat ${Number(detail?.geographicRange?.centerLat || 0).toFixed(3)}, Lon ${Number(detail?.geographicRange?.centerLon || 0).toFixed(3)}` },
                ].map(({ label, value }) => (
                  <div key={label} className="glass p-3 rounded-xl">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/30 block mb-0.5">{label}</span>
                    <span className="text-sm font-semibold text-white">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Gallery */}
          <div>
            <div className="section-heading">📸 Species Gallery</div>
            {photos.length > 0 ? (
              <div className="gallery-grid">
                {photos.map((p, i) => <PhotoCard key={`${p.occurrenceUrl}-${i}`} photo={p} />)}
              </div>
            ) : (
              <div className="text-center py-16 text-white/20">
                <div className="text-5xl mb-4">📷</div>
                <p className="text-sm font-medium">No photos available for this species yet.</p>
              </div>
            )}

            {hasMore && (
              <button
                className="load-more-btn"
                onClick={loadMorePhotos}
                disabled={loadingMore}
              >
                {loadingMore ? '⏳ Loading…' : 'Load more photos'}
              </button>
            )}
          </div>
        </motion.div>
      )}
    </div>
  )
}
