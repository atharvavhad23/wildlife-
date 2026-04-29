import { useState, useEffect, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { SkeletonPhoto } from '../components/Skeleton'

const CONFIG = {
  animals: {
    emoji: '🦁', label: 'Animals', apiUrl: '/photos/animals/',
    accent: 'bg-red-500', back: '/animals',
  },
  birds: {
    emoji: '🦅', label: 'Birds', apiUrl: '/photos/birds/',
    accent: 'bg-cyan-500', back: '/birds',
  },
  insects: {
    emoji: '🦋', label: 'Insects', apiUrl: '/photos/insects/',
    accent: 'bg-amber-500', back: '/insects',
  },
  plants: {
    emoji: '🌿', label: 'Plants', apiUrl: '/photos/plants/',
    accent: 'bg-emerald-500', back: '/plants',
  },
}

function PhotoCard({ photo }) {
  const src = photo.thumbnailUrl
    ? `/photo-proxy/?url=${encodeURIComponent(photo.thumbnailUrl)}`
    : null

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="group relative bg-white/5 rounded-2xl overflow-hidden border border-white/5 hover:border-white/20 transition-all hover:-translate-y-1 hover:shadow-2xl hover:shadow-black/50"
    >
      <div className="aspect-[4/3] bg-white/3 overflow-hidden relative">
        {src ? (
          <img 
            src={src} 
            alt={photo.title} 
            loading="lazy" 
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl grayscale opacity-20">🌿</div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </div>

      <div className="p-4">
        <h3 className="text-sm font-bold text-white truncate mb-1" title={photo.title}>
          {photo.title}
        </h3>
        <p className="text-[10px] font-bold text-white/30 uppercase tracking-wider mb-2">
          {photo.subtitle}
        </p>
        
        {photo.eventDate && (
          <div className="flex items-center gap-1.5 text-[10px] text-white/40 mb-3 font-medium">
            <span>🗓️</span> {photo.eventDate}
          </div>
        )}

        {photo.occurrenceUrl && (
          <a
            href={photo.occurrenceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.1em] text-green-400 hover:text-green-300 transition-colors"
          >
            Observation ↗
          </a>
        )}
      </div>
    </motion.div>
  )
}

export default function PhotosGallery() {
  const { species } = useParams()
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
  }, [species])

  return (
    <div className="page-wrapper min-h-screen pb-20">
      {/* Header Section */}
      <div className="mb-12">
        <Link to={cfg.back} className="back-link !mb-8">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          Back to Predictor
        </Link>
        
        <div className="flex flex-col md:flex-row md:items-end gap-6">
          <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center text-5xl shadow-inner border border-white/5">
            {cfg.emoji}
          </div>
          <div className="flex-1">
            <h1 className="text-4xl font-black text-white mb-2">{cfg.label} Evidence</h1>
            <p className="text-white/30 text-sm font-medium tracking-wide">
              {total > 0 ? (
                <><span className="text-green-400">{total.toLocaleString()}</span> verified observations from the Koyna biosphere</>
              ) : 'Accessing iNaturalist visual repository…'}
            </p>
          </div>
        </div>
      </div>

      {/* Error State */}
      <AnimatePresence>
        {error && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center gap-3 text-red-400 text-sm font-bold"
          >
            <span>⚠️</span> {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Photo Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {photos.map((p, i) => <PhotoCard key={`${p.occurrenceUrl}-${i}`} photo={p} />)}

        {/* Skeleton loading state */}
        {loading && Array.from({ length: 8 }).map((_, i) => (
          <SkeletonPhoto key={i} />
        ))}
      </div>

      {/* Load More Action */}
      {hasMore && photos.length > 0 && (
        <div className="mt-16 flex flex-col items-center gap-4">
          <button
            onClick={() => loadPhotos(offset)}
            disabled={loading}
            className="group relative px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-xs font-black uppercase tracking-[0.2em] text-white/60 hover:text-white transition-all disabled:opacity-50"
          >
            {loading ? '⏳ Accessing Next Page…' : 'Load More Observations'}
            {/* Progress indicator */}
            <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 text-[9px] text-white/20 whitespace-nowrap">
              Showing {photos.length} of {total.toLocaleString()} records
            </div>
          </button>
        </div>
      )}

      {/* End of results */}
      {!hasMore && photos.length > 0 && (
        <div className="mt-20 text-center">
          <div className="w-10 h-1 border-t border-white/10 mx-auto mb-6" />
          <p className="text-[11px] font-black uppercase tracking-widest text-white/20">
            End of visual evidence for {cfg.label} ✓
          </p>
        </div>
      )}

      {/* Empty State */}
      {!loading && photos.length === 0 && !error && (
        <div className="py-32 text-center">
          <div className="text-5xl mb-6 opacity-20">🍃</div>
          <h2 className="text-xl font-bold text-white mb-2">No observations found</h2>
          <p className="text-white/30 text-sm">Try another species category or check back later.</p>
        </div>
      )}
    </div>
  )
}
