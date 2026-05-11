import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  LineChart, Line, CartesianGrid
} from 'recharts'
import { motion } from 'framer-motion'

function TrendGraph({ currentDensity, outlook, unit }) {
  if (!outlook || typeof currentDensity === 'undefined') return null;

  const data = [
    { year: 'Current', density: Number(Number(currentDensity).toFixed(2)) },
    { year: '+5 Years', density: Number(Number(outlook.projected_density_5yr).toFixed(2)) },
    { year: '+10 Years', density: Number(Number(outlook.projected_density_10yr).toFixed(2)) },
  ];

  const trendColor = outlook.density_change_10yr_pct >= 0 ? '#10b981' : '#f87171';

  return (
    <div className="glass-card p-6 mt-8 max-w-2xl mx-auto">
      <h3 className="text-sm font-bold uppercase tracking-wider text-white/40 mb-2 text-center">Population Projection Trend</h3>
      <p className="text-[11px] text-white/30 mb-6 text-center">
        Visualized prediction of population density ({unit}) over the next decade.
      </p>
      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 600 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 600 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip 
              cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }}
              contentStyle={{ background: '#0a1a0e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: '10px 14px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}
              labelStyle={{ color: '#10b981', fontWeight: 800, marginBottom: 4, fontSize: 11 }}
              itemStyle={{ color: '#fff', fontWeight: 600, fontSize: 12, padding: 0 }}
              formatter={(value) => [`${value}`, 'Density']}
            />
            <Line 
              type="monotone" 
              dataKey="density" 
              stroke={trendColor} 
              strokeWidth={4}
              dot={{ r: 6, fill: '#050d06', stroke: trendColor, strokeWidth: 3 }}
              activeDot={{ r: 8, strokeWidth: 0 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function TrendChip({ trend }) {
  if (!trend) return null
  const raw = String(trend.trend || trend.direction || 'Stable').toLowerCase()
  const dir = raw.includes('increas') ? 'increasing' : raw.includes('decreas') ? 'decreasing' : 'stable'
  
  const colors = {
    increasing: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    decreasing: 'bg-red-500/10 text-red-400 border-red-500/20',
    stable: 'bg-blue-500/10 text-blue-400 border-blue-500/20'
  }
  
  const icon = dir === 'increasing' ? '↑' : dir === 'decreasing' ? '↓' : '→'
  const pct = Number(trend.percentage_change ?? 0)
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${colors[dir]}`}>
      {icon} {dir} ({pct.toFixed(1)}%)
    </span>
  )
}

function OccurrenceModelChip({ trend }) {
  if (!trend?.source) return null
  const label = String(trend.classifier_label || trend.trend || 'stable').toLowerCase()
  const conf = Number(trend.confidence)
  const confText = Number.isFinite(conf) ? `${conf.toFixed(0)}% confidence` : 'confidence n/a'
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border bg-white/5 text-white/50 border-white/10" title="Occurrence trend classifier output">
      RF: {label} ({confText})
    </span>
  )
}

function RiskBadge({ level }) {
  if (!level) return null
  const colors = {
    High: 'bg-red-500/20 text-red-400 border-red-500/30',
    Medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    Low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
  }
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${colors[level] || colors.Medium}`}>⚠ {level} Risk</span>
}

function normalizeMetric(key, value) {
  const v = Number(value ?? 0)
  if (key === 'temperature') return Math.max(0, Math.min(100, (v / 45) * 100))
  if (key === 'humidity') return Math.max(0, Math.min(100, v))
  if (key === 'rainfall') return Math.max(0, Math.min(100, (v / 50) * 100))
  if (key === 'vegetation_index' || key === 'water_availability' || key === 'human_disturbance') {
    return Math.max(0, Math.min(100, v * 100))
  }
  return 0
}

function qualitativeLabel(key, value) {
  const v = Number(value ?? 0)
  if (key === 'human_disturbance') {
    if (v > 0.66) return 'High pressure'
    if (v > 0.33) return 'Moderate pressure'
    return 'Low pressure'
  }
  if (key === 'vegetation_index' || key === 'water_availability') {
    if (v > 0.66) return 'Strong'
    if (v > 0.33) return 'Moderate'
    return 'Low'
  }
  if (key === 'rainfall') {
    if (v > 20) return 'Heavy'
    if (v > 5) return 'Moderate'
    return 'Light'
  }
  if (key === 'humidity') {
    if (v > 75) return 'Humid'
    if (v > 45) return 'Balanced'
    return 'Dry'
  }
  if (key === 'temperature') {
    if (v > 33) return 'Hot'
    if (v > 20) return 'Mild'
    return 'Cool'
  }
  return 'Normal'
}

function EnvSimpleBars({ env }) {
  const rows = [
    { key: 'temperature', label: 'Temperature', color: 'from-orange-500 to-red-500' },
    { key: 'humidity', label: 'Humidity', color: 'from-blue-400 to-cyan-400' },
    { key: 'rainfall', label: 'Rainfall', color: 'from-cyan-500 to-blue-500' },
    { key: 'vegetation_index', label: 'Vegetation cover', color: 'from-green-500 to-emerald-400' },
    { key: 'water_availability', label: 'Water availability', color: 'from-teal-400 to-cyan-300' },
    { key: 'human_disturbance', label: 'Human disturbance', color: 'from-purple-500 to-pink-500' },
  ]

  return (
    <div className="flex flex-col gap-3">
      {rows.map((row, index) => {
        const raw = Number(env?.[row.key] ?? 0)
        const pct = normalizeMetric(row.key, raw)
        return (
          <div key={row.key} className="bg-white/5 p-3 rounded-xl flex flex-col gap-2 transition hover:bg-white/10 border border-white/5">
            <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
              <span className="text-white/70">{row.label}</span>
              <span className="text-white/30">{qualitativeLabel(row.key, raw)}</span>
            </div>
            <div className="h-1.5 rounded-full bg-black/20 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1, ease: "easeOut", delay: index * 0.1 }}
                className={`h-full rounded-full bg-gradient-to-r ${row.color}`}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

const FEATURE_NAME_MAP = {
  coordinateUncertaintyInMeters: 'Location Accuracy',
  lat_grid: 'Geographic Latitude',
  lon_grid: 'Geographic Longitude',
  species_richness: 'Biodiversity Density',
  phylum_enc: 'Phylum Taxonomy',
  class_enc: 'Taxonomic Class',
  order_enc: 'Taxonomic Order',
  family_enc: 'Taxonomic Family',
  taxonRank_enc: 'Classification Rank',
  basisOfRecord_enc: 'Observational Basis',
  season_enc: 'Seasonal Cycle',
}

function FeatureBar({ labels = [], values = [] }) {
  const data = labels.map((l, i) => ({ 
    name: FEATURE_NAME_MAP[l] || l.replace(/_/g, ' '), 
    value: values[i] || 0 
  }))
  const COLORS = ['#43a047', '#4ecdc4', '#26c6da', '#fbbf24', '#f97316']
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
        <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="name" width={130} tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10, fontWeight: 600 }} axisLine={false} tickLine={false} />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.04)' }}
          contentStyle={{ background: '#0a1a0e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 11, padding: '8px 12px' }}
          labelStyle={{ color: '#10b981', fontWeight: 800, marginBottom: 4 }}
          itemStyle={{ color: '#fff', fontWeight: 600 }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function FutureOutlookSection({ outlook, unit }) {
  if (!outlook) return null
  const { endangered_risk: risk, density_change_10yr_pct: change } = outlook
  
  const riskColor = risk.risk_level === 'High' ? 'text-red-400 bg-red-400/10 border-red-400/20' : 
                    risk.risk_level === 'Medium' ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20' : 
                    'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'

  return (
    <div className="mt-10 space-y-4">
      <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/30 text-center">Future Outlook & Conservation Risk</h3>
      
      <div className={`p-5 rounded-2xl border backdrop-blur-xl ${riskColor}`}>
        <div className="flex items-start gap-4">
          <span className="text-3xl mt-1">{risk.is_endangered ? '🚨' : '✅'}</span>
          <div>
            <div className="font-black text-[12px] uppercase tracking-wider mb-1.5">
              Risk Assessment: {risk.risk_level}
            </div>
            <p className="text-sm opacity-80 leading-relaxed font-medium">
              {risk.warning_message}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white/5 border border-white/10 p-5 rounded-2xl flex flex-col gap-1 transition-all hover:bg-white/10">
          <div className="text-[10px] font-black uppercase tracking-widest text-white/30 mb-2">5-Year Projection</div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{outlook.projected_density_5yr}</span>
            <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">{unit}</span>
          </div>
          <div className="mt-2">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border ${outlook.projected_trend_5yr === 'Declining' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'}`}>
              {outlook.projected_trend_5yr}
            </span>
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 p-5 rounded-2xl flex flex-col gap-1 transition-all hover:bg-white/10">
          <div className="text-[10px] font-black uppercase tracking-widest text-white/30 mb-2">10-Year Projection</div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{outlook.projected_density_10yr}</span>
            <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">{unit}</span>
          </div>
          <div className="flex items-center gap-2 mt-2">
             <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border ${outlook.projected_trend_10yr === 'Declining' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'}`}>
              {outlook.projected_trend_10yr}
            </span>
            <span className={`text-[10px] font-black ${change < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              ({change > 0 ? '+' : ''}{change}%)
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ResultPanel({ result, unit, speciesLabel }) {
  const { prediction, environmental_data: env, decision, trend, future_outlook } = result
  const regressionModel = result?.model_info?.winner || result?.model_name || 'Regression Model'
  const occurrenceModel = trend?.source || 'Occurrence Classifier'
  const occurrenceLabel = trend?.classifier_label || 'stable'
  const occurrenceConfidence = Number(trend?.confidence)

  const recommendation = decision?.recommendation || ''
  const recs = recommendation
    ? recommendation.split(/\.\s+/).map(s => s.trim()).filter(Boolean)
    : []
  const riskLevel = decision?.risk_level || 'Medium'
  const status = decision?.status || 'Declining'
  
  const mode = result.mode || 'density'

  return (
    <div className="animate-in space-y-8">
      {/* Primary Result Card */}
      <div className="relative glass-card p-10 overflow-hidden text-center">
        {/* Glow effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[200%] h-[200px] bg-gradient-to-b from-green-500/10 to-transparent opacity-50 blur-3xl pointer-events-none" />
        
        <div className="relative z-10">
          {mode === 'density' ? (
            <>
              <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-white/40 mb-4">Estimated {speciesLabel} Density</h2>
              <div className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40 leading-none mb-4">
                {Number(prediction).toFixed(3)}
              </div>
              <div className="text-xs font-black text-green-400 uppercase tracking-[0.2em]">{unit}</div>
              <p className="mt-8 text-sm text-white/30 max-w-lg mx-auto leading-relaxed">
                Prediction generated using <span className="text-white/60 font-bold italic">{regressionModel}</span> based on multi-dimensional spatial features.
              </p>
            </>
          ) : (
            <>
              <h2 className="text-[11px] font-black uppercase tracking-[0.3em] text-white/40 mb-6">{speciesLabel} Occurrence Trend</h2>
              <div className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40 leading-none mb-8">
                {occurrenceLabel.toUpperCase()}
              </div>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <RiskBadge level={riskLevel} />
                <TrendChip trend={trend} />
                <OccurrenceModelChip trend={trend} />
              </div>
            </>
          )}
        </div>
      </div>

      {mode !== 'density' && (
        <TrendGraph currentDensity={prediction} outlook={future_outlook} unit={unit} />
      )}

      {mode === 'density' && <FutureOutlookSection outlook={future_outlook} unit={unit} />}

      {/* Grid: Diagnostics & Decisions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-white/40 mb-6 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400" /> Model Diagnostics
          </h3>
          <div className="space-y-4">
            {mode === 'density' ? (
              <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                <div className="text-xs font-bold text-white mb-1">Architecture</div>
                <div className="text-sm text-white/50">{regressionModel}</div>
                {result?.accuracy && (
                  <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-green-500/10 text-green-400 text-[10px] font-black uppercase tracking-wider">
                    ✓ {Number(result.accuracy).toFixed(1)}% Accuracy
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                <div className="text-xs font-bold text-white mb-1">Classifier</div>
                <div className="text-sm text-white/50">{occurrenceModel}</div>
                <div className="mt-3 flex items-center gap-2">
                   <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400">Verified {occurrenceLabel.toUpperCase()}</span>
                   <span className="w-1 h-1 rounded-full bg-white/20" />
                   <span className="text-[10px] font-bold text-white/30">{occurrenceConfidence.toFixed(0)}% Confidence</span>
                </div>
              </div>
            )}
            <div className="text-[10px] text-white/20 italic">
              * Model verified against historical ground-truth data from the Koyna wildlife sanctuary repository.
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-white/40 mb-6 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Decision Summary
          </h3>
          {recs.length > 0 ? (
            <ul className="space-y-3">
              {recs.slice(0, 4).map((r, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-white/60 leading-relaxed group">
                  <span className="text-amber-500 group-hover:scale-125 transition-transform">⚡</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-white/50 leading-relaxed italic">
              {recommendation || 'Continuous monitoring is advised. Maintain current habitat protection protocols to ensure ecosystem stability.'}
            </div>
          )}
        </div>
      </div>

      {/* Environmental Context Section */}
      {mode === 'density' && env && Object.keys(env).length > 0 && (
        <div className="space-y-6">
          <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/30 text-center">Environmental Context</h3>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { key: 'temperature', label: 'Temp', icon: '🌡️', fmt: v => `${v?.toFixed(1)}°C` },
              { key: 'humidity', label: 'Humidity', icon: '💧', fmt: v => `${v?.toFixed(1)}%` },
              { key: 'rainfall', label: 'Rain', icon: '🌧️', fmt: v => `${v?.toFixed(0)}mm` },
              { key: 'vegetation_index', label: 'Flora', icon: '🌳', fmt: v => v?.toFixed(2) },
              { key: 'water_availability', label: 'Water', icon: '🌊', fmt: v => v?.toFixed(2) },
              { key: 'human_disturbance', label: 'Impact', icon: '👤', fmt: v => v?.toFixed(2) },
            ].filter(f => env[f.key] !== undefined).map(f => (
              <div className="glass-card p-4 text-center group hover:border-green-500/30 transition-all" key={f.key}>
                <div className="text-xs mb-2 opacity-50 group-hover:scale-110 transition-transform block">{f.icon}</div>
                <div className="text-lg font-black text-white">{f.fmt(env[f.key])}</div>
                <div className="text-[9px] font-bold uppercase tracking-widest text-white/30 mt-1">{f.label}</div>
              </div>
            ))}
          </div>

          <div className="glass-card p-8">
            <h4 className="text-[10px] font-black uppercase tracking-widest text-white/40 mb-6 text-center">Factor Analysis Snapshot</h4>
            <EnvSimpleBars env={env} />
          </div>
        </div>
      )}

      {/* Feature Importance Section */}
      {mode === 'density' && result?.feature_importance?.labels?.length > 0 && (
        <div className="glass-card p-8">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-white/40 mb-6 text-center">Top Prediction Drivers</h3>
          <div className="max-w-2xl mx-auto">
             <FeatureBar labels={result.feature_importance.labels} values={result.feature_importance.values} />
          </div>
        </div>
      )}
    </div>
  )
}
