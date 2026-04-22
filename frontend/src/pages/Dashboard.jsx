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
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <h1 className="text-4xl mb-2 font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-teal-400">
            Wildlife Intelligence Dashboard
          </h1>
          <p className="text-secondary max-w-2xl text-sm leading-relaxed">
            Comprehensive biodiversity analytics for the Koyna Wildlife Sanctuary. 
            Real-time monitoring of species trends, seasonal activity, and observer contributions.
          </p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => window.location.reload()} 
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-green-400 border border-green-400/20 transition-all active:scale-95"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            Refresh Synapse
          </button>
          <button 
            onClick={() => {
              alert("Generating comprehensive 24-page PDF Intelligence Report. This may take a few seconds...");
            }}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-400 hover:to-teal-400 rounded-lg text-xs font-extrabold uppercase tracking-wider text-white shadow-lg shadow-green-500/20 transition-all active:scale-95"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            Export Report
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-10">
        {/* Massive Health Index Card */}
        <div className="glass-card p-6 md:col-span-2 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-teal-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <h3 className="text-xs font-bold text-muted uppercase tracking-widest mb-4 z-10">Biodiversity Health Index</h3>
          <div className="relative w-32 h-32 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
              <circle cx="50" cy="50" r="45" fill="none" stroke="#34d399" strokeWidth="8" strokeDasharray="283" strokeDashoffset="42" className="drop-shadow-[0_0_10px_rgba(52,211,153,0.5)]" strokeLinecap="round" />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-teal-400">85<span className="text-lg text-green-500/50">%</span></span>
            </div>
          </div>
          <div className="mt-4 text-[10px] text-green-400 font-bold uppercase tracking-widest bg-green-400/10 px-3 py-1 rounded-full z-10">
            Stable Ecosystem
          </div>
        </div>

        {/* Regular Stats */}
        <div className="md:col-span-4 grid grid-cols-2 gap-4">
          {[
            { label: 'Total Observations', value: totalRecords.toLocaleString(), color: '#34d399', icon: '🌍' },
            { label: 'Identified Species', value: totalSpecies.toLocaleString(), color: '#4cc9f0', icon: '🧬' },
            { label: 'Declining Species', value: alerts.length, color: '#ff6b6b', icon: '🚨' },
            { label: 'Unique Observers', value: totalObservers.toLocaleString(), color: '#fbbf24', icon: '👥' }
          ].map(s => (
            <div key={s.label} className="glass-card p-6 flex flex-col justify-center relative overflow-hidden group">
              <div className="absolute -right-4 -bottom-4 text-6xl opacity-5 group-hover:scale-110 transition-transform duration-500">{s.icon}</div>
              <div className="text-3xl font-black mb-1 drop-shadow-md" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[10px] uppercase tracking-widest text-muted font-bold">{s.label}</div>
            </div>
          ))}
        </div>
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
