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
    <div className="dash-card" style={{ marginTop: 24, maxWidth: 600, margin: '24px auto 0' }}>
      <div className="dash-card-title">Population Projection Trend</div>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: 20 }}>
        Visualized prediction of population density ({unit}) over the next decade.
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: '#a7d7a9', fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#a7d7a9', fontSize: 12 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
          <Tooltip 
            cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }}
            contentStyle={{ background: '#0d2818', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
            labelStyle={{ color: '#a7d7a9', marginBottom: 4 }}
            itemStyle={{ color: '#fff', fontWeight: 'bold' }}
            formatter={(value) => [`${value}`, 'Density']}
          />
          <Line 
            type="monotone" 
            dataKey="density" 
            stroke={trendColor} 
            strokeWidth={3}
            dot={{ r: 5, fill: '#0d2818', stroke: trendColor, strokeWidth: 2 }}
            activeDot={{ r: 7 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function TrendChip({ trend }) {
  if (!trend) return null
  const raw = String(trend.trend || trend.direction || 'Stable').toLowerCase()
  const dir = raw.includes('increas') ? 'increasing' : raw.includes('decreas') ? 'decreasing' : 'stable'
  const cls = dir === 'increasing' ? 'up' : dir === 'decreasing' ? 'down' : 'stable'
  const icon = dir === 'increasing' ? '↑' : dir === 'decreasing' ? '↓' : '→'
  const pct = Number(trend.percentage_change ?? 0)
  return <span className={`trend-chip ${cls}`}>{icon} {dir} ({pct.toFixed(2)}%)</span>
}

function OccurrenceModelChip({ trend }) {
  if (!trend?.source) return null
  const label = String(trend.classifier_label || trend.trend || 'stable').toLowerCase()
  const conf = Number(trend.confidence)
  const confText = Number.isFinite(conf) ? `${conf.toFixed(1)}% confidence` : 'confidence n/a'
  return (
    <span className="trend-chip stable" title="Occurrence trend classifier output">
      RF occurrence: {label} ({confText})
    </span>
  )
}

function RiskBadge({ level }) {
  if (!level) return null
  return <span className={`risk-badge ${level}`}>⚠ {level} Risk</span>
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
          <div key={row.key} className="glass p-3 rounded-lg flex flex-col gap-2 transition hover:bg-white/10">
            <div className="flex justify-between items-center text-xs">
              <span className="font-medium text-text-primary">{row.label}</span>
              <span className="text-text-muted">{qualitativeLabel(row.key, raw)}</span>
            </div>
            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
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

// ─── Feature importance bar ───────────────────────────────────────────────
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
        <XAxis type="number" tick={{ fill: '#6b9f6e', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="name" width={130} tick={{ fill: '#a7d7a9', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.04)' }}
          contentStyle={{ background: '#0d2818', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: '#a7d7a9' }}
          itemStyle={{ color: '#66bb6a' }}
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
    <div className="mt-8 space-y-4">
      <div className="section-heading">🔮 Future Outlook & Conservation Risk</div>
      
      <div className={`p-4 rounded-xl border backdrop-blur-md ${riskColor}`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">{risk.is_endangered ? '🚨' : '✅'}</span>
          <div>
            <div className="font-bold text-sm uppercase tracking-wider mb-1">
              Endangered Risk: {risk.risk_level}
            </div>
            <p className="text-sm opacity-90 leading-relaxed">
              {risk.warning_message}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass p-4 rounded-xl flex flex-col gap-1">
          <div className="text-[10px] uppercase tracking-widest text-text-muted mb-1">5-Year Projection</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-text-primary">{outlook.projected_density_5yr}</span>
            <span className="text-xs text-text-muted">{unit}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 ${outlook.projected_trend_5yr === 'Declining' ? 'text-red-400' : 'text-emerald-400'}`}>
              {outlook.projected_trend_5yr}
            </span>
          </div>
        </div>

        <div className="glass p-4 rounded-xl flex flex-col gap-1">
          <div className="text-[10px] uppercase tracking-widest text-text-muted mb-1">10-Year Projection</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-text-primary">{outlook.projected_density_10yr}</span>
            <span className="text-xs text-text-muted">{unit}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
             <span className={`text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 ${outlook.projected_trend_10yr === 'Declining' ? 'text-red-400' : 'text-emerald-400'}`}>
              {outlook.projected_trend_10yr}
            </span>
            <span className={`text-[10px] font-bold ${change < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
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
  const summary = `Risk is ${riskLevel.toLowerCase()} and ecosystem status is ${status.toLowerCase()}. ${recommendation}`
  
  const mode = result.mode || 'density'

  return (
    <div className="result-panel">
      {/* Dynamic Results Header based on Mode */}
      <div className="result-top">
        {mode === 'density' ? (
          <>
            <div className="result-label">Estimated {speciesLabel} Population Density</div>
            <div className="result-value-big">{Number(prediction).toFixed(3)}</div>
            <div className="result-unit">{unit}</div>
            <p style={{ marginTop: 16, color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: 520, margin: '16px auto 0' }}>
              This regression model predicts the precise expected population density based on the inputted parameters.
            </p>
          </>
        ) : (
          <>
            <div className="result-label">{speciesLabel} Occurrence Trend</div>
            <div className="result-value-big" style={{ fontSize: '2.5rem', marginBottom: 10 }}>{occurrenceLabel.toUpperCase()}</div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              <RiskBadge level={riskLevel} />
              <TrendChip trend={trend} />
              <OccurrenceModelChip trend={trend} />
            </div>
          </>
        )}
      </div>

      {mode !== 'density' && (
        <TrendGraph currentDensity={prediction} outlook={future_outlook} unit={unit} />
      )}

      {mode === 'density' && <FutureOutlookSection outlook={future_outlook} unit={unit} />}

      {/* Env data cards */}
      <div className="dashboard-grid" style={{ marginTop: 24 }}>
        <div className="dash-card">
          <div className="dash-card-title">Model Diagnostics</div>
          <div className="rec-list" style={{ marginTop: 8 }}>
            {mode === 'density' ? (
              <div>
                <strong>Density Model:</strong> {regressionModel} 
                <br/>
                <span style={{ fontSize: '0.85em', color: '#fbbf24' }}>
                  {result?.accuracy ? ` ✓ Accuracy: ${Number(result.accuracy).toFixed(1)}%` : ''} 
                  {result?.accuracy ? ' | ' : ''} 
                  ⚡ Universal Feature Integrated
                </span>
              </div>
            ) : (
              <div>
                <strong>Classification Model:</strong> {occurrenceModel}
                <br/>
                <span style={{ fontSize: '0.85em', color: '#10b981' }}>
                  ✓ Output: {occurrenceLabel.toUpperCase()} 
                  {Number.isFinite(occurrenceConfidence) ? ` | ${occurrenceConfidence.toFixed(1)}% confidence` : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {mode === 'density' && env && Object.keys(env).length > 0 && (
        <>
          <div className="section-heading" style={{ marginTop: 28 }}>
            🌍 Environmental Context
          </div>
          <div className="env-grid">
            {[
              { key: 'temperature', label: 'Temperature', fmt: v => `${v?.toFixed(1)}°C` },
              { key: 'humidity', label: 'Humidity', fmt: v => `${v?.toFixed(1)}%` },
              { key: 'rainfall', label: 'Rainfall', fmt: v => `${v?.toFixed(0)} mm` },
              { key: 'vegetation_index', label: 'Vegetation', fmt: v => v?.toFixed(3) },
              { key: 'water_availability', label: 'Water Avail.', fmt: v => v?.toFixed(3) },
              { key: 'human_disturbance', label: 'Human Disturb.', fmt: v => v?.toFixed(3) },
            ].filter(f => env[f.key] !== undefined).map(f => (
              <div className="env-card" key={f.key}>
                <div className="env-val">{f.fmt(env[f.key])}</div>
                <div className="env-label">{f.label}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Charts row */}
      {mode === 'density' && env && (
        <div className="dashboard-grid" style={{ marginTop: 28 }}>
          <div className="dash-card">
            <div className="dash-card-title">Environmental Snapshot (Easy View)</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: 10 }}>
              Higher bars mean stronger presence of that factor.
            </p>
            <EnvSimpleBars env={env} />
          </div>
          <div className="dash-card">
            <div className="dash-card-title">Decision Summary</div>
            {recs.length > 0 ? (
              <ul className="rec-list">
                {recs.slice(0, 5).map((r, i) => <li key={i}>💡 {r}</li>)}
              </ul>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Recommendation: {recommendation || 'Continue monitoring and keep habitat conditions stable.'}
              </p>
            )}
          </div>
        </div>
      )}

      {mode === 'density' && result?.feature_importance?.labels?.length > 0 && (
        <div className="dashboard-grid" style={{ marginTop: 18 }}>
          <div className="dash-card">
            <div className="dash-card-title">Top Drivers (Feature Importance)</div>
            <FeatureBar labels={result.feature_importance.labels} values={result.feature_importance.values} />
          </div>
        </div>
      )}
    </div>
  )
}
