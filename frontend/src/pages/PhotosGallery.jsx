import { useState, useEffect, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'

const CONFIG = {
  animals: {
    emoji: '🦁', label: 'Animals', apiUrl: '/photos/animals/',
    accent: '#ff6b6b', back: '/animals',
  },
  birds: {
    emoji: '🦅', label: 'Birds', apiUrl: '/photos/birds/',
    accent: '#4ecdc4', back: '/birds',
  },
  insects: {
    emoji: '🦋', label: 'Insects', apiUrl: '/photos/insects/',
    accent: '#f59e0b', back: '/insects',
  },
  plants: {
    emoji: '🌿', label: 'Plants', apiUrl: '/photos/plants/',
    accent: '#10b981', back: '/plants',
  },
}

function PhotoCard({ photo }) {
  const src = photo.thumbnailUrl
    ? `/photo-proxy/?url=${encodeURIComponent(photo.thumbnailUrl)}`
    : null

  return (
    <div className="photo-card">
      <div className="photo-img-wrap">
        {src
          ? <img src={src} alt={photo.title} loading="lazy" />
          : <span className="photo-placeholder">🌿</span>
        }
      </div>
      <div className="photo-info">
        <div className="photo-title" title={photo.title}>{photo.title}</div>
        <div className="photo-sub">{photo.subtitle}</div>
        {photo.eventDate && (
          <div className="photo-sub" style={{ marginTop: 3 }}>📅 {photo.eventDate}</div>
        )}
        {photo.occurrenceUrl && (
          <a
            href={photo.occurrenceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="photo-link"
          >
            View observation ↗
          </a>
        )}
      </div>
    </div>
  )
}

export default function PhotosGallery() {
  const { species } = useParams()   // 'animals' | 'birds' | 'insects'
  const cfg = CONFIG[species] || CONFIG.animals

  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState(null)
  const PAGE = 24

  const loadPhotos = useCallback(async (off = 0, reset = false) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${cfg.apiUrl}?offset=${off}&limit=${PAGE}`)
      const data = await res.json()
      const incoming = data.photos || []
      setPhotos(prev => reset ? incoming : [...prev, ...incoming])
      setOffset(data.nextOffset || off + incoming.length)
      setHasMore(data.hasMore || false)
      setTotal(data.total || 0)
    } catch (e) {
      setError('Failed to load photos: ' + e.message)
    } finally {
      setLoading(false)
    }
  }, [cfg.apiUrl])

  useEffect(() => {
    setPhotos([])
    setOffset(0)
    setHasMore(true)
    loadPhotos(0, true)
  }, [species])   // eslint-disable-line

  return (
    <div className="page-wrapper">
      {/* Header */}
      <div className="gallery-header">
      <Link to={cfg.back} className="back-link">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back to {cfg.label} Prediction
      </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8 }}>
          <span style={{ fontSize: '3rem' }}>{cfg.emoji}</span>
          <div>
            <h1 style={{ fontSize: '2rem', marginBottom: 4 }}>{cfg.label} Photo Gallery</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              {total > 0 ? `${total.toLocaleString()} verified iNaturalist observations` : 'Loading…'}
            </p>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="error-box" style={{ marginBottom: 24 }}>
          <span>⚠️</span><span>{error}</span>
        </div>
      )}

      {/* Grid */}
      <div className="gallery-grid">
        {photos.map((p, i) => <PhotoCard key={`${p.occurrenceUrl}-${i}`} photo={p} />)}

        {/* Skeleton placeholders while loading first batch */}
        {loading && photos.length === 0 &&
          Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="photo-card" style={{ opacity: 0.4 }}>
              <div className="photo-img-wrap" style={{ background: 'rgba(255,255,255,0.04)' }}>
                <span className="photo-placeholder">🌿</span>
              </div>
              <div className="photo-info">
                <div style={{ height: 14, background: 'rgba(255,255,255,0.06)', borderRadius: 4, marginBottom: 8 }} />
                <div style={{ height: 10, background: 'rgba(255,255,255,0.04)', borderRadius: 4, width: '60%' }} />
              </div>
            </div>
          ))
        }
      </div>

      {/* Load more */}
      {hasMore && photos.length > 0 && (
        <button
          className="load-more-btn"
          onClick={() => loadPhotos(offset)}
          disabled={loading}
        >
          {loading ? '⏳ Loading…' : `Load more photos (${photos.length} / ${total})`}
        </button>
      )}

      {!hasMore && photos.length > 0 && (
        <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 32, fontSize: '0.875rem' }}>
          All {total.toLocaleString()} observations loaded ✓
        </p>
      )}
    </div>
  )
}
