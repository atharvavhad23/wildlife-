import { useState, useEffect, useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, AreaChart, Area
} from 'recharts'

const CLUSTER_COLORS = [
  '#43a047','#4ecdc4','#fbbf24','#f97316','#a78bfa',
  '#f472b6','#34d399','#60a5fa','#fb7185','#a3e635',
]

const DatasetIcon = ({ ds }) => {
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
      heatScript.setAttribute('data-heat', 'true')
      heatScript.onload = () => resolve(window.L)
      heatScript.onerror = () => reject(new Error('Failed to load Leaflet Heat script'))
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
    script.onload = loadHeat; script.onerror = () => reject(new Error('Failed to load Leaflet script'))
    document.body.appendChild(script)
  })
  return leafletAssetsPromise
}

// Convex Hull Helper (Monotone Chain algorithm)
function getConvexHull(points) {
  if (points.length < 3) return points
  points.sort((a, b) => a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1])
  const upper = []
  for (const p of points) {
    while (upper.length >= 2 && crossProduct(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop()
    upper.push(p)
  }
  const lower = []
  for (let i = points.length - 1; i >= 0; i--) {
    const p = points[i]
    while (lower.length >= 2 && crossProduct(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop()
    lower.push(p)
  }
  upper.pop()
  lower.pop()
  return upper.concat(lower)
}
function crossProduct(a, b, c) {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
}

export default function ClusteringMap() {
  const location = useLocation()
  const initialCategory = location.pathname.split('/')[1] || 'animals'
  
  const [category, setCategory] = useState(initialCategory)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [nClusters, setNClusters] = useState(8)
  const [layerType, setLayerType] = useState('hulls') // Default to hulls for "defined" look
  const [selectedCluster, setSelectedCluster] = useState(null)
  const [comparisonCluster, setComparisonCluster] = useState(null) // Feature 11: Comparison
  const [clusterDetails, setClusterDetails] = useState(null)
  const [compDetails, setCompDetails] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [photosA, setPhotosA] = useState([]) // Primary cluster photos
  const [photosB, setPhotosB] = useState([]) // Comparison cluster photos
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [loadingPhotosA, setLoadingPhotosA] = useState(false)
  const [loadingPhotosB, setLoadingPhotosB] = useState(false)
  const [error, setError] = useState(null)
  const [mapInstance, setMapInstance] = useState(null)
  const [showDiversity, setShowDiversity] = useState(false) // Feature 12: Diversity Hotspots

  useEffect(() => {
    setCategory(location.pathname.split('/')[1] || 'animals')
  }, [location.pathname])

  const loadData = async (cat, n) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/cluster-heatmap/?dataset=${cat}&clusters=${n}`)
      const d = await res.json()
      if (d.error) throw new Error(d.error)
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
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
      
      // Fetch Cluster Photos
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
      if (!data || !data.points) return
      try {
        const L = await ensureLeafletAssets()
        const mapEl = document.getElementById('map-container')
        if (!mapEl) return
        mapEl.innerHTML = ''
        map = L.map(mapEl, { zoomControl: false }).setView([17.5, 73.8], 10)
        setMapInstance(map)
        L.control.zoom({ position: 'bottomright' }).addTo(map)
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          attribution: 'Esri'
        }).addTo(map)

        const clusterGroups = {}
        data.points.forEach(([lat, lon, cid]) => {
          if (!clusterGroups[cid]) clusterGroups[cid] = []
          clusterGroups[cid].push([lat, lon])
        })

        const bounds = []
        Object.entries(clusterGroups).forEach(([cid, pts]) => {
          const color = CLUSTER_COLORS[cid % CLUSTER_COLORS.length]
          
          // Show Hulls for "Defined" clusters
          if (layerType === 'hulls' || layerType === 'both') {
            const hullPts = getConvexHull(pts)
            if (hullPts.length > 2) {
              const poly = L.polygon(hullPts, {
                color, weight: 2, fillColor: color, fillOpacity: 0.15, dashArray: '5, 5'
              }).addTo(map)
              poly.on('click', () => setSelectedCluster(cid))
              poly.bindTooltip(`Cluster ${cid} Boundary`, { sticky: true })
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

        // Diversity Hotspot Overlay (Shannon-like visualization)
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
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-black">
      {/* Sidebar */}
      <div className="w-[420px] flex flex-col glass-panel border-r border-white/5 z-20 overflow-hidden">
        <div className="p-6 border-b border-white/5 bg-black/20">
          <div className="flex items-center gap-3 mb-5">
            <span className="text-3xl"><DatasetIcon ds={category} /></span>
            <div>
              <h1 className="text-lg font-bold capitalize">Defined {category} Clusters</h1>
              <p className="text-[9px] uppercase tracking-widest text-muted font-bold">Spatial Boundaries & Diversity</p>
            </div>
          </div>

          <div className="flex gap-1 p-1 bg-white/5 rounded-lg mb-5">
            {['animals', 'birds', 'insects', 'plants'].map(cat => (
              <button key={cat} onClick={() => { setCategory(cat); setSelectedCluster(null); setComparisonCluster(null); }}
                className={`flex-1 py-1.5 text-[9px] font-bold uppercase rounded transition-all ${category === cat ? 'bg-green-500 text-white' : 'text-muted hover:bg-white/5'}`}>
                {cat}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-[9px] font-bold uppercase text-muted mb-1">Defined Limits</div>
              <select value={layerType} onChange={e => setLayerType(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-[10px] text-primary outline-none">
                <option value="hulls">Convex Hulls (Defined)</option>
                <option value="markers">Observation Points</option>
                <option value="both">Both Layers</option>
              </select>
            </div>
            <div>
              <div className="text-[9px] font-bold uppercase text-muted mb-1">Diversity View</div>
              <button onClick={() => setShowDiversity(!showDiversity)} className={`w-full py-1 rounded text-[10px] font-bold border transition-all ${showDiversity ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400' : 'bg-white/5 border-white/10 text-muted'}`}>
                {showDiversity ? 'ON: Hotspots' : 'OFF: Hotspots'}
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
          {selectedCluster !== null ? (
            <div className="animate-in">
              <div className="flex justify-between items-center mb-4">
                <button onClick={() => { setSelectedCluster(null); setComparisonCluster(null); }} className="text-[10px] font-bold uppercase text-muted hover:text-primary">← Reset</button>
                <button onClick={() => setComparisonCluster(comparisonCluster ? null : (selectedCluster + 1) % nClusters)} 
                  className={`text-[9px] font-bold uppercase px-3 py-1 rounded border transition-all ${comparisonCluster !== null ? 'bg-amber-500 text-black border-amber-500' : 'border-white/20 text-secondary hover:bg-white/5'}`}>
                  {comparisonCluster !== null ? 'End Comparison' : '⚖️ Compare Cluster'}
                </button>
              </div>

              <div className={`grid gap-4 ${comparisonCluster !== null ? 'grid-cols-2' : 'grid-cols-1'}`}>
                {/* Cluster A */}
                <div className="space-y-4">
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
                </div>
                
                {/* Cluster B (Comparison) */}
                {comparisonCluster !== null && (
                  <div className="space-y-4 border-l border-white/10 pl-4">
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
            <div className="space-y-4">
              <div className="text-[10px] font-bold uppercase text-muted mb-2">Regional Hubs</div>
              {Array.from({length: nClusters}).map((_, i) => (
                <div key={i} onClick={() => setSelectedCluster(i)} className="p-3 bg-white/5 rounded-xl border border-white/5 hover:border-green-500/30 cursor-pointer transition-all flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs" style={{ backgroundColor: `${CLUSTER_COLORS[i % CLUSTER_COLORS.length]}22`, color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}>{i}</div>
                  <div className="flex-1 text-xs font-bold">Region {i}</div>
                  <div className="text-[10px] text-muted">Explore →</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div id="map-container" className="flex-1 relative z-10 bg-[#0a0a0a]" />

      {loading && (
        <div className="absolute inset-0 z-30 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center">
          <div className="spinner !w-10 !h-10 border-t-green-500 mb-4" />
          <div className="text-sm font-bold uppercase tracking-widest text-green-400">Defining Boundaries...</div>
        </div>
      )}
    </div>
  )
}

function ClusterDetailView({ id, details, category, timeline, loading, photos, loadingPhotos, color }) {
  if (loading) return <div className="py-8 text-center"><div className="spinner !w-5 !h-5 mx-auto mb-2" /></div>
  return (
    <div className="animate-in">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
        <h2 className="text-sm font-bold">Region {id}</h2>
      </div>
      
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-white/5 p-2 rounded text-center">
          <div className="text-[14px] font-bold text-primary">{details?.species_count}</div>
          <div className="text-[8px] text-muted uppercase">Species</div>
        </div>
        <div className="bg-white/5 p-2 rounded text-center">
          <div className="text-[14px] font-bold text-primary">{details?.total_obs}</div>
          <div className="text-[8px] text-muted uppercase">Obs</div>
        </div>
      </div>

      {timeline.length > 0 && (
        <div className="h-[80px] w-full mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeline}><Area type="monotone" dataKey="count" stroke={color} fill={color} fillOpacity={0.1} /></AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Visual Evidence - Gallery */}
      <div className="mb-4">
        <div className="text-[8px] font-bold uppercase text-muted mb-2 flex items-center justify-between">
          <span>Visual Evidence</span>
          {loadingPhotos && <div className="spinner !w-2 !h-2 border-t-green-500" />}
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
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-1">
                  <div className="text-[6px] text-white font-bold truncate">{p.common_name || p.species}</div>
                </div>
              </div>
            ))}
          </div>
        ) : !loadingPhotos && (
          <div className="text-[8px] text-muted text-center py-4 bg-white/5 rounded-lg border border-dashed border-white/10 italic">
            No visual evidence in cluster
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        <div className="text-[8px] font-bold uppercase text-muted mb-1">Key Species</div>
        {details?.species?.slice(0, 8).map(s => (
          <Link key={s.scientificName} to={`/${category}/species?species=${encodeURIComponent(s.scientificName)}`} className="block p-1.5 bg-white/5 rounded text-[10px] hover:bg-white/10 transition-all italic truncate">
            {s.scientificName}
          </Link>
        ))}
      </div>
    </div>
  )
}
