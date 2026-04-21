import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

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
      existing.addEventListener('error', () => reject(new Error('Failed to load Leaflet script')))
      return
    }

    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.async = true
    script.setAttribute('data-leaflet', 'true')
    script.onload = () => resolve(window.L)
    script.onerror = () => reject(new Error('Failed to load Leaflet script'))
    document.body.appendChild(script)
  })

  return leafletAssetsPromise
}

function InfoItem({ label, value }) {
  return (
    <div className="glass-card" style={{ padding: 16 }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>{label}</div>
      <div style={{ marginTop: 4, color: 'var(--text-primary)', fontWeight: 600 }}>{value || 'Unknown'}</div>
    </div>
  )
}

function PhotoCard({ photo }) {
  const src = photo.thumbnailUrl ? `/photo-proxy/?url=${encodeURIComponent(photo.thumbnailUrl)}` : null

  return (
    <div className="photo-card">
      <div className="photo-img-wrap">
        {src ? <img src={src} alt={photo.title} loading="lazy" /> : <span className="photo-placeholder">🌿</span>}
      </div>
      <div className="photo-info">
        <div className="photo-title" title={photo.title}>{photo.title}</div>
        <div className="photo-sub">{photo.subtitle}</div>
        {photo.eventDate && <div className="photo-sub" style={{ marginTop: 3 }}>📅 {photo.eventDate}</div>}
      </div>
    </div>
  )
}

export default function SpeciesDetail() {
  const [searchParams] = useSearchParams()
  const species = (searchParams.get('species') || '').trim()

  const [detail, setDetail] = useState(null)
  const [photos, setPhotos] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const title = useMemo(() => detail?.scientificName || species || 'Species Detail', [detail, species])

  useEffect(() => {
    let active = true

    const load = async () => {
      if (!species) {
        setError('Missing species parameter in URL.')
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const category = window.location.pathname.split('/')[1] || 'animals'
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

    return () => {
      active = false
    }
  }, [species])

  useEffect(() => {
    let map = null
    let mounted = true

    const setupMap = async () => {
      if (!detail || !detail.locations || detail.locations.length === 0) return
      try {
        const L = await ensureLeafletAssets()
        if (!mounted) return

        const mapEl = document.getElementById('species-map')
        if (!mapEl) return

        mapEl.innerHTML = ''
        map = L.map(mapEl)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 18,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        const points = detail.locations
          .filter((p) => Number.isFinite(p.latitude) && Number.isFinite(p.longitude))
          .map((p) => [p.latitude, p.longitude])

        if (points.length === 0) return

        points.slice(0, 300).forEach(([lat, lon]) => {
          L.circleMarker([lat, lon], {
            radius: 4,
            color: '#4ecdc4',
            fillColor: '#4ecdc4',
            fillOpacity: 0.65,
            weight: 1,
          }).addTo(map)
        })

        if (points.length > 1) map.fitBounds(points, { padding: [20, 20] })
        else map.setView(points[0], 9)
      } catch {
        // Keep page usable even if map asset fails.
      }
    }

    setupMap()

    return () => {
      mounted = false
      if (map) map.remove()
    }
  }, [detail])

  const loadMorePhotos = async () => {
    if (!hasMore || loadingMore || !species) return
    setLoadingMore(true)
    try {
      const category = window.location.pathname.split('/')[1] || 'animals'
      const res = await fetch(`/api/${category}/species-photos/?species=${encodeURIComponent(species)}&offset=${offset}&limit=24`)
      const data = await res.json()
      setPhotos((prev) => [...prev, ...(data.photos || [])])
      setOffset(data.nextOffset || offset)
      setHasMore(Boolean(data.hasMore))
    } finally {
      setLoadingMore(false)
    }
  }

  const category = window.location.pathname.split('/')[1] || 'animals'

  return (
    <div className="page-wrapper">
      <div style={{ padding: '40px 0 24px' }}>
        <Link to={`/${category}/clustering`} className="back-link">← Back to Clustering Map</Link>
        <h1 style={{ fontSize: '2.2rem', marginTop: 6 }}>{title}</h1>
        {detail?.class && detail?.family && (
          <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>{detail.class} • {detail.family}</p>
        )}
      </div>

      {loading && (
        <div className="spinner-wrap" style={{ marginTop: 40 }}>
          <div className="spinner" />
          <span>Loading species profile…</span>
        </div>
      )}

      {error && <div className="error-box"><span>⚠️</span><span>{error}</span></div>}

      {!loading && detail && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 14 }}>
            <InfoItem label="Kingdom" value={detail.kingdom} />
            <InfoItem label="Phylum" value={detail.phylum} />
            <InfoItem label="Class" value={detail.class} />
            <InfoItem label="Order" value={detail.order} />
            <InfoItem label="Family" value={detail.family} />
            <InfoItem label="Genus" value={detail.genus} />
            <InfoItem label="Observations" value={detail.observationCount} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 18, marginTop: 22 }}>
            <div className="glass-card" style={{ padding: 18 }}>
              <div className="section-heading">🧭 Geographic Range</div>
              <div id="species-map" style={{ height: 360, borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }} />
            </div>

            <div className="glass-card" style={{ padding: 18 }}>
              <div className="section-heading">ℹ️ Species Information</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div className="glass-card" style={{ padding: 12 }}><strong>Common Name:</strong> {detail.species || 'N/A'}</div>
                <div className="glass-card" style={{ padding: 12 }}><strong>Scientific Name:</strong> {detail.scientificName}</div>
                <div className="glass-card" style={{ padding: 12 }}><strong>Date Range:</strong> {detail?.dateRange?.earliest || 'N/A'} → {detail?.dateRange?.latest || 'N/A'}</div>
                <div className="glass-card" style={{ padding: 12 }}><strong>Center:</strong> Lat {Number(detail?.geographicRange?.centerLat || 0).toFixed(3)}, Lon {Number(detail?.geographicRange?.centerLon || 0).toFixed(3)}</div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 24 }}>
            <div className="section-heading">📸 Species Gallery</div>
            <div className="gallery-grid">
              {photos.map((p, i) => <PhotoCard key={`${p.occurrenceUrl}-${i}`} photo={p} />)}
            </div>
            {hasMore && (
              <button className="load-more-btn" onClick={loadMorePhotos} disabled={loadingMore}>
                {loadingMore ? '⏳ Loading…' : 'Load more photos'}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
