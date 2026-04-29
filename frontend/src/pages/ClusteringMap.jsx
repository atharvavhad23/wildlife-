import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, ResponsiveContainer
} from 'recharts'

const CLUSTER_COLORS = [
  '#43a047','#4ecdc4','#fbbf24','#f97316','#a78bfa',
  '#f472b6','#34d399','#60a5fa','#fb7185','#a3e635',
]

function DatasetIcon({ ds }) {
  if (ds === 'animals') return '🐾'
  if (ds === 'birds') return '🦅'
  if (ds === 'insects') return '🦋'
  return '🍃'
}

let leafletAssetsPromise = null
function ensureLeafletAssets() {
  if (window.L && window.L.heatLayer) return Promise.resolve(window.L)
  if (leafletAssetsPromise) return leafletAssetsPromise

  leafletAssetsPromise = new Promise((resolve, reject) => {
    const loadHeat = () => {
      if (window.L && window.L.heatLayer) return resolve(window.L)
      const heatScript = document.createElement('script')
      heatScript.src = 'https://unpkg.com/leaflet.heat/dist/leaflet-heat.js'
      heatScript.async = true
      heatScript.onload = () => resolve(window.L)
      heatScript.onerror = () => reject(new Error('Failed to load Leaflet Heat'))
      document.body.appendChild(heatScript)
    }
    if (!document.querySelector('link[data-leaflet="true"]')) {
      const css = document.createElement('link')
      css.rel = 'stylesheet'; css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      css.setAttribute('data-leaflet', 'true'); document.head.appendChild(css)
    }
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.async = true; script.setAttribute('data-leaflet', 'true')
    script.onload = loadHeat; script.onerror = () => reject(new Error('Failed to load Leaflet'))
    document.body.appendChild(script)
  })
  return leafletAssetsPromise
}

function getConvexHull(points) {
  if (points.length < 3) return points
  points.sort((a, b) => a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1])
  const upper = []; for (const p of points) { while (upper.length >= 2 && crossProduct(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop(); upper.push(p) }
  const lower = []; for (let i = points.length - 1; i >= 0; i--) { const p = points[i]; while (lower.length >= 2 && crossProduct(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop(); lower.push(p) }
  upper.pop(); lower.pop()
  return upper.concat(lower)
}
function crossProduct(a, b, c) { return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) }

function ClusterDetailView({ id, details, category, timeline, loading, photos, loadingPhotos, color }) {
  if (loading) return (
    <div className="py-8 flex items-center justify-center">
      <div className="w-6 h-6 rounded-full border-2 border-t-green-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
    </div>
  )

  return (
    <div className="animate-in">
      {/* Cluster header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
        <h2 className="text-sm font-bold text-white">Region {id}</h2>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-white/5 rounded-xl p-3 text-center border border-white/5">
          <div className="text-lg font-black text-white">{details?.species_count ?? '—'}</div>
          <div className="text-[9px] font-bold uppercase tracking-wider text-white/30 mt-0.5">Species</div>
        </div>
        <div className="bg-white/5 rounded-xl p-3 text-center border border-white/5">
          <div className="text-lg font-black text-white">{details?.total_obs?.toLocaleString() ?? '—'}</div>
          <div className="text-[9px] font-bold uppercase tracking-wider text-white/30 mt-0.5">Observations</div>
        </div>
      </div>

      {/* Mini timeline chart */}
      {timeline.length > 0 && (
        <div className="h-[70px] w-full mb-4 bg-white/3 rounded-xl overflow-hidden">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeline} margin={{ top: 4, right: 4, bottom: 0, left: -32 }}>
              <Area type="monotone" dataKey="count" stroke={color} fill={color} fillOpacity={0.12} strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Photo evidence */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[9px] font-bold uppercase tracking-wider text-white/30">Visual Evidence</span>
          {loadingPhotos && (
            <div className="w-3 h-3 rounded-full border border-t-green-400 border-transparent animate-spin" />
          )}
        </div>
        {photos.length > 0 ? (
          <div className="grid grid-cols-3 gap-1.5">
            {photos.slice(0, 6).map((p, idx) => (
              <div key={idx} className="aspect-square bg-white/5 rounded-lg overflow-hidden group relative">
                <img
                  src={`/photo-proxy/?url=${encodeURIComponent(p.url)}`}
                  alt={p.species}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-1.5">
                  <div className="text-[8px] text-white font-semibold truncate leading-tight">{p.common_name || p.species}</div>
                </div>
              </div>
            ))}
          </div>
        ) : !loadingPhotos && (
          <div className="text-[9px] text-white/20 text-center py-4 bg-white/3 rounded-lg border border-dashed border-white/10 italic">
            No visual evidence in this cluster
          </div>
        )}
      </div>

      {/* Key species list */}
      <div>
        <div className="text-[9px] font-bold uppercase tracking-wider text-white/30 mb-2">Key Species</div>
        <div className="space-y-1">
          {details?.species?.slice(0, 8).map(s => (
            <Link
              key={s.scientificName}
              to={`/${category}/species?species=${encodeURIComponent(s.scientificName)}`}
              className="block p-2 bg-white/5 hover:bg-white/10 rounded-lg text-[11px] text-white/70 hover:text-white italic truncate transition-all border border-white/5 hover:border-white/10"
            >
              {s.scientificName}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function ClusteringMap() {
  const location = useLocation()
  const navigate = useNavigate()
  const initialCategory = location.pathname.split('/')[1] || 'animals'

  const [category, setCategory] = useState(initialCategory)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [nClusters, setNClusters] = useState(8)
  const [layerType, setLayerType] = useState('hulls')
  const [selectedCluster, setSelectedCluster] = useState(null)
  const [comparisonCluster, setComparisonCluster] = useState(null)
  const [clusterDetails, setClusterDetails] = useState(null)
  const [compDetails, setCompDetails] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [photosA, setPhotosA] = useState([])
  const [photosB, setPhotosB] = useState([])
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [loadingPhotosA, setLoadingPhotosA] = useState(false)
  const [loadingPhotosB, setLoadingPhotosB] = useState(false)
  const [showDiversity, setShowDiversity] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setCategory(location.pathname.split('/')[1] || 'animals')
  }, [location.pathname])

  const loadData = async (cat, n) => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`/api/cluster-heatmap/?dataset=${cat}&clusters=${n}`)
      const d = await res.json()
      if (d.error) throw new Error(d.error)
      setData(d)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { loadData(category, nClusters) }, [category, nClusters])

  const fetchDetails = async (id, setFn) => {
    try {
      const res = await fetch(`/api/cluster-details/?dataset=${category}&clusters=${nClusters}&cluster_id=${id}`)
      const d = await res.json()
      setFn(d.clusters[id])
      const isPrimary = setFn === setClusterDetails
      const setPhotoFn = isPrimary ? setPhotosA : setPhotosB
      const setLoadingPhotoFn = isPrimary ? setLoadingPhotosA : setLoadingPhotosB
      if (isPrimary) {
        const tRes = await fetch(`/api/cluster-timeline/?dataset=${category}&clusters=${nClusters}&cluster_id=${id}`)
        const tD = await tRes.json()
        setTimeline(tD.timeline)
      }
      setLoadingPhotoFn(true)
      fetch(`/api/cluster-photos/?dataset=${category}&clusters=${nClusters}&cluster_id=${id}`)
        .then(r => r.json())
        .then(data => setPhotoFn(data.photos || []))
        .finally(() => setLoadingPhotoFn(false))
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    if (selectedCluster !== null) {
      setLoadingDetails(true)
      fetchDetails(selectedCluster, setClusterDetails).finally(() => setLoadingDetails(false))
    }
  }, [selectedCluster])

  useEffect(() => {
    if (comparisonCluster !== null) fetchDetails(comparisonCluster, setCompDetails)
  }, [comparisonCluster])

  useEffect(() => {
    let map = null
    const initMap = async () => {
      if (!data?.points) return
      try {
        const L = await ensureLeafletAssets()
        const mapEl = document.getElementById('map-container')
        if (!mapEl) return
        mapEl.innerHTML = ''
        map = L.map(mapEl, { zoomControl: false }).setView([17.5, 73.8], 10)
        L.control.zoom({ position: 'bottomright' }).addTo(map)
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: 'Esri' }).addTo(map)

        const clusterGroups = {}
        data.points.forEach(([lat, lon, cid]) => {
          if (!clusterGroups[cid]) clusterGroups[cid] = []
          clusterGroups[cid].push([lat, lon])
        })

        const bounds = []
        Object.entries(clusterGroups).forEach(([cid, pts]) => {
          const color = CLUSTER_COLORS[cid % CLUSTER_COLORS.length]
          if (layerType === 'hulls' || layerType === 'both') {
            const hullPts = getConvexHull(pts)
            if (hullPts.length > 2) {
              const poly = L.polygon(hullPts, { color, weight: 2, fillColor: color, fillOpacity: 0.15, dashArray: '5, 5' }).addTo(map)
              poly.on('click', () => setSelectedCluster(cid))
              poly.bindTooltip(`Cluster ${cid}`, { sticky: true })
            }
          }
          if (layerType === 'markers' || layerType === 'both') {
            pts.slice(0, 100).forEach(p => {
              L.circleMarker(p, { radius: 3, fillColor: color, color: '#fff', weight: 0.5, fillOpacity: 0.7 })
                .addTo(map).on('click', () => setSelectedCluster(cid))
            })
          }
          pts.forEach(p => bounds.push(p))
        })

        if (showDiversity) {
          const heatPts = data.points.map(p => [p[0], p[1], 0.8])
          L.heatLayer(heatPts, { radius: 35, blur: 25, gradient: { 0.4: 'blue', 0.6: 'cyan', 0.8: 'yellow', 1.0: 'red' } }).addTo(map)
        }

        if (bounds.length > 0) map.fitBounds(bounds, { padding: [50, 50] })
      } catch (e) { console.error(e) }
    }
    initMap()
    return () => { if (map) map.remove() }
  }, [data, layerType, showDiversity])

  return (
    <div className="flex overflow-hidden bg-black" style={{ height: 'calc(100vh - var(--navbar-h))' }}>
      {/* Sidebar */}
      <div className="w-[380px] xl:w-[420px] flex flex-col glass-panel border-r border-white/5 z-20 overflow-hidden flex-shrink-0">
        {/* Sidebar header */}
        <div className="p-5 border-b border-white/5 bg-black/20">
          <button onClick={() => navigate(-1)} className="back-link !mb-5 border-none bg-transparent cursor-pointer">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
            </svg>
            Back
          </button>

          <div className="flex items-center gap-3 mb-5">
            <span className="text-3xl"><DatasetIcon ds={category} /></span>
            <div>
              <h1 className="text-base font-bold capitalize text-white">{category} Cluster Map</h1>
              <p className="text-[9px] uppercase tracking-widest text-white/30 font-bold">Spatial Boundaries & Diversity</p>
            </div>
          </div>

          {/* Dataset tabs */}
          <div className="flex gap-1 p-1 bg-white/5 rounded-xl mb-4">
            {['animals', 'birds', 'insects', 'plants'].map(cat => (
              <button
                key={cat}
                onClick={() => { setCategory(cat); setSelectedCluster(null); setComparisonCluster(null) }}
                className={`flex-1 py-1.5 text-[9px] font-bold uppercase tracking-wider rounded-lg transition-all ${category === cat ? 'bg-green-500 text-white shadow' : 'text-white/30 hover:text-white/60 hover:bg-white/5'}`}
              >
                {cat.slice(0, 3)}
              </button>
            ))}
          </div>

          {/* Controls grid */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <div className="text-[9px] font-bold uppercase tracking-wider text-white/30 mb-1.5">Layer Mode</div>
              <select
                value={layerType}
                onChange={e => setLayerType(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-[11px] text-white outline-none focus:border-green-500/50"
              >
                <option value="hulls"   style={{ background: '#0a1a0e' }}>Convex Hulls</option>
                <option value="markers" style={{ background: '#0a1a0e' }}>Observation Points</option>
                <option value="both"    style={{ background: '#0a1a0e' }}>Both Layers</option>
              </select>
            </div>
            <div>
              <div className="text-[9px] font-bold uppercase tracking-wider text-white/30 mb-1.5">Diversity Heatmap</div>
              <button
                onClick={() => setShowDiversity(!showDiversity)}
                className={`w-full py-1.5 rounded-lg text-[11px] font-bold border transition-all ${showDiversity ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400' : 'bg-white/5 border-white/10 text-white/40 hover:text-white/70'}`}
              >
                {showDiversity ? '🔥 ON' : '💤 OFF'}
              </button>
            </div>
          </div>

          {/* Cluster count slider */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <div className="text-[9px] font-bold uppercase tracking-wider text-white/30">Cluster Count</div>
              <div className="text-[11px] font-black text-green-400">{nClusters}</div>
            </div>
            <input
              type="range"
              min={3} max={15} step={1}
              value={nClusters}
              onChange={e => { setNClusters(Number(e.target.value)); setSelectedCluster(null) }}
              className="w-full"
            />
            <div className="flex justify-between text-[8px] text-white/20 mt-0.5">
              <span>3</span><span>15</span>
            </div>
          </div>
        </div>

        {/* Sidebar body */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          {selectedCluster !== null ? (
            <div className="animate-in">
              {/* Cluster actions bar */}
              <div className="flex items-center justify-between mb-4">
                <button
                  onClick={() => { setSelectedCluster(null); setComparisonCluster(null) }}
                  className="text-[10px] font-bold uppercase tracking-wider text-white/40 hover:text-white transition-colors flex items-center gap-1"
                >
                  ← All Clusters
                </button>
                <button
                  onClick={() => setComparisonCluster(comparisonCluster !== null ? null : (Number(selectedCluster) + 1) % nClusters)}
                  className={`text-[9px] font-bold uppercase px-3 py-1 rounded-lg border transition-all ${comparisonCluster !== null ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'border-white/15 text-white/30 hover:bg-white/5 hover:text-white/60'}`}
                >
                  {comparisonCluster !== null ? 'End Compare' : '⚖ Compare'}
                </button>
              </div>

              <div className={`grid gap-4 ${comparisonCluster !== null ? 'grid-cols-2' : 'grid-cols-1'}`}>
                <ClusterDetailView
                  id={selectedCluster}
                  details={clusterDetails}
                  category={category}
                  timeline={timeline}
                  loading={loadingDetails}
                  photos={photosA}
                  loadingPhotos={loadingPhotosA}
                  color={CLUSTER_COLORS[selectedCluster % CLUSTER_COLORS.length]}
                />
                {comparisonCluster !== null && (
                  <div className="border-l border-white/10 pl-4">
                    <ClusterDetailView
                      id={comparisonCluster}
                      details={compDetails}
                      category={category}
                      timeline={[]}
                      loading={!compDetails}
                      photos={photosB}
                      loadingPhotos={loadingPhotosB}
                      color={CLUSTER_COLORS[comparisonCluster % CLUSTER_COLORS.length]}
                    />
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-[9px] font-bold uppercase tracking-wider text-white/30 mb-3">Regional Hubs</div>
              {/* Empty state */}
              {!loading && (
                <div className="mb-4 p-3 rounded-xl bg-white/3 border border-dashed border-white/10 text-center">
                  <div className="text-xl mb-1">🗺</div>
                  <p className="text-[10px] text-white/30">Click a cluster on the map or select below</p>
                </div>
              )}
              <div className="space-y-2">
                {Array.from({ length: nClusters }).map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedCluster(i)}
                    className="w-full p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 hover:border-green-500/20 transition-all flex items-center gap-3 text-left group"
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs flex-shrink-0"
                      style={{ backgroundColor: `${CLUSTER_COLORS[i % CLUSTER_COLORS.length]}20`, color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}
                    >
                      {i}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold text-white/70 group-hover:text-white transition-colors">Region {i}</div>
                      <div className="text-[9px] text-white/25 mt-0.5">Click to explore →</div>
                    </div>
                    <svg className="w-3 h-3 text-white/20 group-hover:text-white/50 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative z-10 bg-[#0a0a0a]">
        <div id="map-container" className="w-full h-full" />

        {/* Error overlay */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-20">
            <div className="text-center p-8 glass-card max-w-sm">
              <div className="text-4xl mb-4">⚠️</div>
              <p className="text-red-400 font-semibold mb-2">Failed to load cluster data</p>
              <p className="text-white/40 text-sm mb-5">{error}</p>
              <button
                onClick={() => loadData(category, nClusters)}
                className="px-5 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-xl border border-green-500/30 text-sm font-bold transition-all"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 z-20 bg-black/70 backdrop-blur-sm flex flex-col items-center justify-center gap-4">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-3 border-white/5" />
              <div className="absolute inset-0 rounded-full border-4 border-t-green-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold uppercase tracking-widest text-green-400">Defining Boundaries…</div>
              <div className="text-xs text-white/30 mt-1">{nClusters} clusters · {category}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
