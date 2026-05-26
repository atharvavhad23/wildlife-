import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { SkeletonPhoto } from '../components/Skeleton'

function PhotoCard({ photo }) {
  const rawSrc = photo.thumbnailUrl || photo.imageUrl || photo.image_url || ''
  const proxied = rawSrc && !rawSrc.startsWith('/media/') && !rawSrc.startsWith('/static/')
    ? `/photo-proxy/?url=${encodeURIComponent(rawSrc)}`
    : rawSrc
  const [src, setSrc] = useState(proxied || '/images/no-image.jpg')

  useEffect(() => {
    setSrc(proxied || '/images/no-image.jpg')
  }, [proxied])

  return (
    <div className="photo-card group">
      <div className="photo-img-wrap relative">
        <img
          src={src || '/images/no-image.jpg'}
          alt={photo.title || 'Species photo'}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-[1.06] transition-transform duration-500"
          onError={(e) => {
            e.currentTarget.src = '/images/no-image.jpg'
            setSrc('/images/no-image.jpg')
          }}
        />
      </div>
      <div className="photo-info">
        <div className="photo-title" title={photo.title}>{photo.title}</div>
        <div className="photo-sub">{photo.subtitle}</div>
      </div>
    </div>
  )
}

function InfoItem({ label, value }) {
  return (
    <div className="glass-card p-4">
      <div className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-1.5">{label}</div>
      <div className="text-sm font-semibold text-white">{value || 'Unknown'}</div>
    </div>
  )
}

export default function SpeciesDetail() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const species = (searchParams.get('species') || '').trim()
  const category = window.location.pathname.split('/')[1] || 'animals'
  const listMode = !species

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState(null)
  const [photos, setPhotos] = useState([])
  const [speciesList, setSpeciesList] = useState([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const title = useMemo(
    () => (listMode ? `${category[0].toUpperCase()}${category.slice(1)} Species` : (detail?.scientificName || species || 'Species Detail')),
    [category, detail, species, listMode],
  )

  useEffect(() => {
    let active = true

    const load = async () => {
      setLoading(true)
      setError('')
      try {
        if (listMode) {
          const listRes = await fetch(`/api/${category}/species/?offset=0&limit=24`)
          if (!listRes.ok) throw new Error(`Failed to load species list (${listRes.status})`)
          const listData = await listRes.json()
          if (!active) return
          setSpeciesList(listData.species || [])
          setOffset(listData.nextOffset || (listData.species || []).length)
          setHasMore(Boolean(listData.hasMore))
          setDetail(null)
          setPhotos([])
          return
        }

        const [dRes, pRes] = await Promise.all([
          fetch(`/api/${category}/species/?species=${encodeURIComponent(species)}`),
          fetch(`/api/${category}/species-photos/?species=${encodeURIComponent(species)}&offset=0&limit=24`),
        ])
        if (!dRes.ok) throw new Error(`Failed to load species details (${dRes.status})`)
        if (!pRes.ok) throw new Error(`Failed to load species photos (${pRes.status})`)

        const d = await dRes.json()
        const p = await pRes.json()
        if (!active) return
        if (d.error) throw new Error(d.error)
        setDetail(d)
        setPhotos(p.photos || [])
        setOffset(p.nextOffset || (p.photos || []).length)
        setHasMore(Boolean(p.hasMore))
        setSpeciesList([])
      } catch (e) {
        if (!active) return
        setError(e?.message || 'Failed to load species data.')
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [species, category, listMode])

  const loadMore = async () => {
    if (!hasMore || loadingMore) return
    setLoadingMore(true)
    try {
      const url = listMode
        ? `/api/${category}/species/?offset=${offset}&limit=24`
        : `/api/${category}/species-photos/?species=${encodeURIComponent(species)}&offset=${offset}&limit=24`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to load more (${res.status})`)
      const data = await res.json()
      if (listMode) {
        setSpeciesList((prev) => [...prev, ...(data.species || [])])
      } else {
        setPhotos((prev) => [...prev, ...(data.photos || [])])
      }
      setOffset(data.nextOffset || offset)
      setHasMore(Boolean(data.hasMore))
    } catch (e) {
      setError(e?.message || 'Failed to load more.')
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <div className="page-wrapper pb-20">
      <button onClick={() => navigate(-1)} className="back-link mt-6 inline-flex border-none bg-transparent cursor-pointer">
        Back
      </button>

      <div className="pt-6 pb-8">
        <motion.h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-green-300 tracking-tight mb-2" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          {title}
        </motion.h1>
      </div>

      {loading && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <SkeletonPhoto key={i} />)}
        </div>
      )}

      {!loading && error && (
        <div className="flex items-start gap-3 p-5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {!loading && !error && listMode && (
        <>
          {speciesList.length > 0 ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {speciesList.map((item, idx) => (
                  <Link key={`${item.scientificName}-${idx}`} to={`/${category}/species?species=${encodeURIComponent(item.scientificName)}`} className="glass-card p-5 hover:border-green-500/40 transition-all">
                    <div className="text-sm font-bold text-white mb-1">{item.scientificName}</div>
                    <div className="text-xs text-white/50 italic mb-2">{item.species}</div>
                    <div className="text-[11px] text-green-300 font-semibold">{Number(item.observationCount || 0).toLocaleString()} observations</div>
                  </Link>
                ))}
              </div>
              {hasMore && (
                <button className="load-more-btn" onClick={loadMore} disabled={loadingMore}>
                  {loadingMore ? 'Loading species...' : 'Load more species'}
                </button>
              )}
            </>
          ) : (
            <div className="text-center py-16 text-white/20">
              <p className="text-sm font-medium">No species records available.</p>
            </div>
          )}
        </>
      )}

      {!loading && !error && !listMode && detail && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-8">
            <InfoItem label="Kingdom" value={detail.kingdom} />
            <InfoItem label="Phylum" value={detail.phylum} />
            <InfoItem label="Class" value={detail.class} />
            <InfoItem label="Order" value={detail.order} />
            <InfoItem label="Family" value={detail.family} />
            <InfoItem label="Genus" value={detail.genus} />
            <InfoItem label="Records" value={detail.observationCount?.toLocaleString()} />
          </div>
          {photos.length > 0 ? (
            <div className="gallery-grid">
              {photos.map((p, i) => <PhotoCard key={`${p.occurrenceUrl}-${i}`} photo={p} />)}
            </div>
          ) : (
            <div className="text-center py-16 text-white/20">
              <p className="text-sm font-medium">No photos available for this species yet.</p>
            </div>
          )}
          {hasMore && (
            <button className="load-more-btn" onClick={loadMore} disabled={loadingMore}>
              {loadingMore ? 'Loading...' : 'Load more photos'}
            </button>
          )}
        </>
      )}
    </div>
  )
}
