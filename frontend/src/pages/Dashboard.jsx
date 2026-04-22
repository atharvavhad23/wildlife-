import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts'

const COLORS = ['#34d399', '#4cc9f0', '#f72585', '#fbbf24', '#f97316', '#a78bfa']

const DatasetCard = ({ title, icon, stats, color }) => {
  if (!stats) return null
  return (
    <Link to={`/${title.toLowerCase()}/clustering`} className="glass-card p-6 hover:-translate-y-1 transition-all">
      <div className="flex items-center justify-between mb-4">
        <span className="text-4xl">{icon}</span>
        <div className="text-right">
          <h3 style={{ color }} className="text-xl font-bold uppercase tracking-tight">{title}</h3>
          <p className="text-xs text-muted">Koyna WLS Dataset</p>
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-secondary">Observations</span>
          <span className="font-bold text-primary">{stats.total?.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-secondary">Unique Species</span>
          <span className="font-bold text-primary">{stats.species?.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-secondary">Families</span>
          <span className="font-bold text-primary">{stats.families}</span>
        </div>
        <div className="w-full bg-white/5 h-1.5 rounded-full mt-4 overflow-hidden">
          <div 
            className="h-full rounded-full" 
            style={{ 
              backgroundColor: color, 
              width: '100%',
              opacity: 0.8
            }} 
          />
        </div>
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const [statsData, setStatsData] = useState(null)
  const [seasonal, setSeasonal] = useState([])
  const [alerts, setAlerts] = useState([])
  const [observers, setObservers] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeDs, setActiveDs] = useState('animals')

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [statsRes, seasonalRes, alertsRes, observersRes] = await Promise.all([
          fetch('/api/dashboard-stats/'),
          fetch(`/api/seasonal-activity/?dataset=${activeDs}`),
          fetch(`/api/conservation-alerts/?dataset=${activeDs}`),
          fetch(`/api/top-observers/?dataset=${activeDs}`)
        ])
        
        if (!statsRes.ok || !seasonalRes.ok || !alertsRes.ok || !observersRes.ok) {
           throw new Error("One or more dashboard API calls failed");
        }
        
        const stats = await statsRes.json()
        const seasonalData = await seasonalRes.json()
        const alertsData = await alertsRes.json()
        const observersData = await observersRes.json()

        console.log("Dashboard Stats:", stats);
        console.log("Initial Seasonal Data:", seasonalData);
        
        if (stats.error) console.error("Stats Error:", stats.error);

        setStatsData(stats)
        setSeasonal(seasonalData.seasonal || [])
        setAlerts(alertsData.alerts || [])
        setObservers(observersData.observers || [])
      } catch (e) {
        console.error('Dashboard Init Error:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [activeDs])

  if (loading && !statsData) {
    return (
      <div className="page-wrapper flex flex-col items-center justify-center min-h-[60vh]">
        <div className="spinner mb-4" />
        <p className="text-secondary">Gathering wildlife intelligence...</p>
      </div>
    )
  }

  const data = statsData?.datasets || {}
  const totalRecords = statsData?.totalRecords || 0
  const totalSpecies = Object.values(data).reduce((acc, curr) => acc + curr.species, 0)
  const totalObservers = statsData?.totalObservers || 0

  return (
    <div className="page-wrapper pt-12">
      <div className="mb-12">
        <h1 className="text-4xl mb-2">Wildlife Intelligence Dashboard</h1>
        <p className="text-secondary max-w-2xl">
          Comprehensive biodiversity analytics for the Koyna Wildlife Sanctuary. 
          Real-time monitoring of species trends, seasonal activity, and observer contributions.
        </p>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {[
          { label: 'Total Observations', value: totalRecords.toLocaleString(), color: '#34d399' },
          { label: 'Identified Species', value: totalSpecies.toLocaleString(), color: '#4cc9f0' },
          { label: 'Declining species', value: alerts.length, color: '#ff6b6b' },
          { label: 'Unique Observers', value: totalObservers.toLocaleString(), color: '#fbbf24' }
        ].map(s => (
          <div key={s.label} className="glass-card p-6 text-center">
            <div className="text-2xl font-bold mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted font-bold">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Dataset Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12">
        <DatasetCard title="Animals" icon="🐾" stats={data?.animals} color="#34d399" />
        <DatasetCard title="Birds" icon="🦅" stats={data?.birds} color="#4cc9f0" />
        <DatasetCard title="Insects" icon="🦋" stats={data?.insects} color="#f72585" />
        <DatasetCard title="Plants" icon="🌿" stats={data?.plants} color="#fbbf24" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Charts */}
        <div className="lg:col-span-2 space-y-8">
          <div className="glass-card p-8">
            <div className="flex items-center justify-between mb-8">
              <h3 className="section-heading !border-0 !mb-0 !p-0">🌡️ Seasonal Observation Trends</h3>
              <div className="flex gap-2">
                {['animals', 'birds', 'insects', 'plants'].map(ds => (
                  <button 
                    key={ds}
                    onClick={() => setActiveDs(ds)}
                    className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${activeDs === ds ? 'bg-green-500 text-white' : 'bg-white/5 text-muted hover:bg-white/10'}`}
                  >
                    {ds.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={seasonal}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={activeDs === 'animals' ? '#34d399' : activeDs === 'birds' ? '#4cc9f0' : activeDs === 'insects' ? '#f72585' : '#fbbf24'} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={activeDs === 'animals' ? '#34d399' : activeDs === 'birds' ? '#4cc9f0' : activeDs === 'insects' ? '#f72585' : '#fbbf24'} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis 
                    dataKey="name" 
                    stroke="rgba(255,255,255,0.3)" 
                    fontSize={12} 
                    tickLine={false} 
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.3)" 
                    fontSize={12} 
                    tickLine={false} 
                    axisLine={false}
                    tickFormatter={(v) => v > 1000 ? `${(v/1000).toFixed(1)}k` : v}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(10, 26, 14, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="count" 
                    stroke={activeDs === 'animals' ? '#34d399' : activeDs === 'birds' ? '#4cc9f0' : activeDs === 'insects' ? '#f72585' : '#fbbf24'} 
                    strokeWidth={3}
                    fillOpacity={1} 
                    fill="url(#colorCount)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-card p-6">
              <h3 className="text-sm font-bold text-muted uppercase tracking-wider mb-6">🏆 Top Contributors</h3>
              <div className="space-y-4">
                {observers.slice(0, 5).map((o, i) => (
                  <div key={o.name} className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-xs font-bold text-secondary">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-bold text-primary truncate">{o.name}</div>
                      <div className="text-[10px] text-muted uppercase">{o.species} species recorded</div>
                    </div>
                    <div className="text-sm font-bold text-green-400">{o.observations}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card p-6">
              <h3 className="text-sm font-bold text-muted uppercase tracking-wider mb-6">🧬 Taxonomic Groups</h3>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={Object.entries(data?.[activeDs]?.classBreakdown || {}).map(([name, value]) => ({ name, value }))}
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {Object.entries(data?.[activeDs]?.classBreakdown || {}).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'rgba(10, 26, 14, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Alerts & Status */}
        <div className="space-y-8">
          <div className="glass-card p-6 border-l-4 border-l-red-500/50">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-2xl">🚨</span>
              <h3 className="text-sm font-bold text-muted uppercase tracking-wider">Conservation Alerts</h3>
            </div>
            
            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
              {alerts.length > 0 ? alerts.slice(0, 10).map((a) => (
                <div key={a.species} className="p-4 bg-white/5 rounded-xl border border-white/5 hover:border-red-500/30 transition-all group">
                  <div className="flex justify-between items-start mb-2">
                    <div className="text-sm font-bold italic text-primary group-hover:text-red-400 transition-colors">{a.species}</div>
                    <div className="text-xs font-bold text-red-500">-{a.dropPercent}%</div>
                  </div>
                  <div className="text-[10px] text-muted uppercase mb-3">{a.class} • {a.order}</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-white/10 h-1 rounded-full overflow-hidden">
                      <div className="bg-red-500 h-full" style={{ width: `${a.dropPercent}%` }} />
                    </div>
                    <span className="text-[10px] text-muted">{a.recentObs} obs</span>
                  </div>
                </div>
              )) : (
                <div className="text-center py-12 text-muted text-sm italic">
                  No active conservation alerts for this group.
                </div>
              )}
            </div>
          </div>

          <div className="glass-card p-6">
            <h3 className="text-sm font-bold text-muted uppercase tracking-wider mb-6">📍 Geographic Focus</h3>
            <div className="space-y-4">
              {Object.entries(data || {}).map(([key, v]) => (
                <div key={key} className="flex items-center justify-between">
                  <div className="text-sm text-secondary capitalize">{key} hotspot</div>
                  <div className="text-xs font-bold text-primary bg-white/5 px-2 py-1 rounded">{v.topLocality || 'Koyna Region'}</div>
                </div>
              ))}
            </div>
            <Link 
              to="/animals/clustering" 
              className="mt-8 block text-center py-3 bg-white/5 hover:bg-white/10 rounded-xl text-xs font-bold uppercase tracking-widest text-secondary transition-all"
            >
              Explore Spatial Maps →
            </Link>
          </div>
        </div>
      </div>

      <div className="footer mt-20 opacity-50">
        <p>Data synchronized with iNaturalist and GBIF biodiversity networks.</p>
        <p>© 2024 Koyna Wildlife Conservation Portal</p>
      </div>
    </div>
  )
}
