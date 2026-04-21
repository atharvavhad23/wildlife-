import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const CLUSTER_COLORS = [
  '#43a047','#4ecdc4','#fbbf24','#f97316','#a78bfa',
  '#f472b6','#34d399','#60a5fa','#fb7185','#a3e635',
]

function ClusterBadge({ id }) {
  return (
    <span style={{
      display: 'inline-block',
      width: 12, height: 12,
      borderRadius: '50%',
      background: CLUSTER_COLORS[id % CLUSTER_COLORS.length],
      marginRight: 6, flexShrink: 0,
    }} />
  )
}

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

export default function ClusteringMap() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [nClusters, setNClusters] = useState(8)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [mapReady, setMapReady] = useState(false)

  useEffect(() => {
    let map = null
    let mounted = true

    const renderMap = async () => {
      if (!data || !data.clusters || Object.keys(data.clusters).length === 0) return
      try {
        const L = await ensureLeafletAssets()
        if (!mounted) return

        const ids = Object.keys(data.clusters)
        const points = ids
          .map((id) => ({ id, ...data.clusters[id] }))
          .filter((c) => Number.isFinite(c.center_lat) && Number.isFinite(c.center_lon))

        if (points.length === 0) return

        const mapEl = document.getElementById('cluster-map')
        if (!mapEl) return

        mapEl.innerHTML = ''
        map = L.map(mapEl, { zoomControl: true })
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 18,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        const bounds = []
        points.forEach((c) => {
          bounds.push([c.center_lat, c.center_lon])
          const color = CLUSTER_COLORS[Number(c.id) % CLUSTER_COLORS.length]
          const radius = Math.min(18, Math.max(8, Math.sqrt((c.animal_count || 0) / 40)))

          L.circleMarker([c.center_lat, c.center_lon], {
            radius,
            color,
            fillColor: color,
            fillOpacity: 0.75,
            weight: 2,
          })
            .addTo(map)
            .bindPopup(
              `<b>Cluster ${c.id}</b><br/>${(c.animal_count || 0).toLocaleString()} observations<br/>${c.species_count || 0} species`
            )
        })

        if (bounds.length > 1) {
          map.fitBounds(bounds, { padding: [30, 30] })
        } else {
          map.setView(bounds[0], 8)
        }

        setMapReady(true)
      } catch (e) {
        setError(e.message)
      }
    }

    renderMap()

    return () => {
      mounted = false
      if (map) {
        map.remove()
      }
    }
  }, [data])

  const load = async (n) => {
    setLoading(true)
    setError(null)
    setSelected(null)
    try {
      const res = await fetch(`/api/animals/clustering/?clusters=${n}`)
      const d = await res.json()
      if (d.error) throw new Error(d.error)
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(nClusters) }, [nClusters])

  const clusters = data?.clusters || {}
  const clusterIds = Object.keys(clusters).map(Number)

  return (
    <div className="page-wrapper">
      {/* Header */}
      <div style={{ padding: '48px 0 32px' }}>
        <Link to="/animals" className="back-link">← Back to Animals</Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8 }}>
          <span style={{ fontSize: '3rem' }}>🗺️</span>
          <div>
            <h1 style={{ fontSize: '2rem', marginBottom: 4 }}>Animals Clustering Map</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              K-means geographic + taxonomic clustering of all animal observations
            </p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="glass-card" style={{ padding: '20px 28px', marginBottom: 28, display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 600 }}>
          Number of clusters:
          <input
            type="range" min={3} max={15} step={1}
            value={nClusters}
            onChange={e => setNClusters(Number(e.target.value))}
            style={{ width: 140 }}
          />
          <span style={{ color: 'var(--green-300)', fontWeight: 700, minWidth: 20 }}>{nClusters}</span>
        </label>
        {data && (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 'auto' }}>
            {data.total_species?.toLocaleString()} total observations
          </span>
        )}
      </div>

      {/* Error */}
      {error && <div className="error-box"><span>⚠️</span><span>{error}</span></div>}

      {/* Loading */}
      {loading && (
        <div className="spinner-wrap" style={{ marginTop: 40 }}>
          <div className="spinner" />
          <span>Running K-means clustering…</span>
        </div>
      )}

      {/* Cluster grid */}
      {!loading && data && (
        <>
          <div className="glass-card" style={{ padding: '16px', marginBottom: 20 }}>
            <div className="section-heading" style={{ marginBottom: 10 }}>🧭 Geographic Cluster Map</div>
            <div id="cluster-map" style={{ width: '100%', height: 380, borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)' }} />
            {!mapReady && <p style={{ color: 'var(--text-muted)', marginTop: 10, fontSize: '0.85rem' }}>Preparing map…</p>}
          </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px,1fr))', gap: 20 }}>
          {clusterIds.map(id => {
            const c = clusters[id]
            const isSelected = selected === id
            const color = CLUSTER_COLORS[id % CLUSTER_COLORS.length]
            return (
              <div
                key={id}
                className="glass-card"
                style={{
                  padding: '24px',
                  cursor: 'pointer',
                  borderColor: isSelected ? color : undefined,
                  boxShadow: isSelected ? `0 0 24px ${color}40` : undefined,
                  transition: 'all 0.2s ease',
                }}
                onClick={() => setSelected(isSelected ? null : id)}
              >
                {/* Cluster header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: `${color}22`, border: `2px solid ${color}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.85rem', fontWeight: 700, color,
                  }}>{id}</div>
                  <div>
                    <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Cluster {id}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {c.animal_count?.toLocaleString()} obs · {c.species_count} species
                    </div>
                  </div>
                  <div style={{ marginLeft: 'auto', fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'right' }}>
                    <div>Lat {c.center_lat?.toFixed(2)}</div>
                    <div>Lon {c.center_lon?.toFixed(2)}</div>
                  </div>
                </div>

                {/* Species list */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {(c.species || []).slice(0, isSelected ? 10 : 4).map((sp, i) => (
                    <a
                      key={i}
                      href={`/animals/species?species=${encodeURIComponent(sp)}`}
                      onClick={e => e.stopPropagation()}
                      style={{
                        display: 'flex', alignItems: 'center',
                        fontSize: '0.82rem', color: 'var(--text-secondary)',
                        padding: '6px 10px', borderRadius: 6,
                        background: 'rgba(255,255,255,0.03)',
                        transition: 'background 0.15s',
                        textDecoration: 'none',
                      }}
                      onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.07)'}
                      onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                    >
                      <ClusterBadge id={id} />
                      {sp}
                    </a>
                  ))}
                  {!isSelected && c.species?.length > 4 && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', paddingLeft: 18 }}>
                      +{c.species.length - 4} more • click to expand
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        </>
      )}

      {/* Legend */}
      {!loading && data && (
        <div className="glass-card" style={{ padding: '20px 28px', marginTop: 32 }}>
          <div className="section-heading">📊 Cluster Legend</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {clusterIds.map(id => (
              <div key={id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <ClusterBadge id={id} />
                Cluster {id} ({clusters[id]?.animal_count?.toLocaleString()} obs)
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
