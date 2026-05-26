import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { SkeletonPhoto } from '../components/Skeleton'

const CONFIG = {
  animals: { emoji: '🦁', label: 'Animals', apiUrl: '/photos/animals/' },
  birds: { emoji: '🦅', label: 'Birds', apiUrl: '/photos/birds/' },
  insects: { emoji: '🦋', label: 'Insects', apiUrl: '/photos/insects/' },
  plants: { emoji: '🌿', label: 'Plants', apiUrl: '/photos/plants/' },
}

function PhotoCard({ photo }) {
  const rawSrc = photo.thumbnailUrl || photo.imageUrl || photo.image_url || ''
  const initialSrc = rawSrc.startsWith('/media/') || rawSrc.startsWith('/static/')
    ? rawSrc
    : rawSrc
      ? `/photo-proxy/?url=${encodeURIComponent(rawSrc)}`
      : '/images/no-image.jpg'

  const [src, setSrc] = useState(initialSrc)
  useEffect(() => setSrc(initialSrc), [initialSrc])

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="group relative bg-white/5 rounded-2xl overflow-hidden border border-white/5 hover:border-white/20 transition-all hover:-translate-y-1">
      <div className="aspect-[4/3] bg-white/3 overflow-hidden relative">
        <img
          src={src || '/images/no-image.jpg'}
          alt={photo.title || 'Observation photo'}
          loading="lazy"
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
          onError={(e) => {
            e.currentTarget.src = '/images/no-image.jpg'
            setSrc('/images/no-image.jpg')
          }}
        />
      </div>
      <div className="p-4">
        <h3 className="text-sm font-bold text-white truncate mb-1" title={photo.title}>{photo.title}</h3>
        <p className="text-[10px] font-bold text-white/30 uppercase tracking-wider mb-2">{photo.subtitle}</p>
        {photo.eventDate && <div className="text-[10px] text-white/40 mb-3 font-medium">{photo.eventDate}</div>}
      </div>
    </motion.div>
  )
}

export default function PhotosGallery() {
  const { species } = useParams()
  const navigate = useNavigate()
  const cfg = CONFIG[species] || CONFIG.animals
  const PAGE = 24

  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')

  const loadPhotos = useCallback(async (off = 0, reset = false) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${cfg.apiUrl}?offset=${off}&limit=${PAGE}`)
      if (!res.ok) throw new Error(`Request failed (${res.status})`)
      const data = await res.json()
      const incoming = data.photos || []
      setPhotos((prev) => (reset ? incoming : [...prev, ...incoming]))
      setOffset(data.nextOffset || off + incoming.length)
      setHasMore(Boolean(data.hasMore))
      setTotal(Number(data.total || 0))
    } catch (e) {
      setError(`Failed to load photos: ${e?.message || 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }, [cfg.apiUrl])

  useEffect(() => {
    setPhotos([])
    setOffset(0)
    setHasMore(true)
    loadPhotos(0, true)
  }, [species, loadPhotos])

  return (
    <div className="page-wrapper min-h-screen pb-20">
      <div className="mb-12">
        <button onClick={() => navigate(-1)} className="back-link !mb-8 border-none bg-transparent cursor-pointer">Back</button>
        <div className="flex flex-col md:flex-row md:items-end gap-6">
          <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center text-5xl shadow-inner border border-white/5">{cfg.emoji}</div>
          <div className="flex-1">
            <h1 className="text-4xl font-black text-white mb-2">{cfg.label} Evidence</h1>
            <p className="text-white/30 text-sm font-medium tracking-wide">
              {total > 0 ? <><span className="text-green-400">{total.toLocaleString()}</span> verified observations from the Koyna biosphere</> : 'Loading observations...'}
            </p>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center gap-3 text-red-400 text-sm font-bold">
            <span>⚠</span> {error}
            <button onClick={() => loadPhotos(0, true)} className="ml-auto px-3 py-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-[10px] uppercase tracking-wider">Retry</button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {photos.map((p, i) => <PhotoCard key={`${p.occurrenceUrl || 'no-url'}-${i}`} photo={p} />)}
        {loading && Array.from({ length: 8 }).map((_, i) => <SkeletonPhoto key={i} />)}
      </div>

      {hasMore && photos.length > 0 && (
        <div className="mt-16 flex flex-col items-center gap-4">
          <button onClick={() => loadPhotos(offset)} disabled={loading} className="group relative px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-xs font-black uppercase tracking-[0.2em] text-white/60 hover:text-white transition-all disabled:opacity-50">
            {loading ? 'Loading...' : 'Load More Observations'}
            <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 text-[9px] text-white/20 whitespace-nowrap">
              Showing {photos.length} of {total.toLocaleString()} records
            </div>
          </button>
        </div>
      )}

      {!loading && photos.length === 0 && !error && (
        <div className="py-32 text-center">
          <div className="text-5xl mb-6 opacity-20">🍃</div>
          <h2 className="text-xl font-bold text-white mb-2">No images available</h2>
          <p className="text-white/30 text-sm">Try another species category or check back later.</p>
        </div>
      )}
    </div>
  )
}
