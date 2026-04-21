import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'

function TrendChip({ trend }) {
  if (!trend) return null
  const raw = String(trend.trend || trend.direction || 'Stable').toLowerCase()
  const dir = raw.includes('increas') ? 'increasing' : raw.includes('decreas') ? 'decreasing' : 'stable'
  const cls = dir === 'increasing' ? 'up' : dir === 'decreasing' ? 'down' : 'stable'
  const icon = dir === 'increasing' ? '↑' : dir === 'decreasing' ? '↓' : '→'
  const pct = Number(trend.percentage_change ?? 0)
  return <span className={`trend-chip ${cls}`}>{icon} {dir} ({pct.toFixed(2)}%)</span>
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
    { key: 'temperature', label: 'Temperature' },
    { key: 'humidity', label: 'Humidity' },
    { key: 'rainfall', label: 'Rainfall' },
    { key: 'vegetation_index', label: 'Vegetation cover' },
    { key: 'water_availability', label: 'Water availability' },
    { key: 'human_disturbance', label: 'Human disturbance' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {rows.map((row) => {
        const raw = Number(env?.[row.key] ?? 0)
        const pct = normalizeMetric(row.key, raw)
        return (
          <div key={row.key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
              <span style={{ color: 'var(--text-secondary)' }}>{row.label}</span>
              <span style={{ color: 'var(--text-muted)' }}>{qualitativeLabel(row.key, raw)}</span>
            </div>
            <div style={{ height: 9, borderRadius: 99, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,#43a047,#66bb6a)' }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Feature importance bar ───────────────────────────────────────────────
function FeatureBar({ labels = [], values = [] }) {
  const data = labels.map((l, i) => ({ name: l.replace(/_/g, ' '), value: values[i] || 0 }))
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

export default function ResultPanel({ result, unit, speciesLabel }) {
  const { prediction, environmental_data: env, decision, trend } = result

  const recommendation = decision?.recommendation || ''
  const recs = recommendation
    ? recommendation.split(/\.\s+/).map(s => s.trim()).filter(Boolean)
    : []
  const riskLevel = decision?.risk_level || 'Medium'
  const status = decision?.status || 'Declining'
  const summary = `Risk is ${riskLevel.toLowerCase()} and ecosystem status is ${status.toLowerCase()}. ${recommendation}`

  return (
    <div className="result-panel">
      {/* Big number */}
      <div className="result-top">
        <div className="result-label">Estimated {speciesLabel} Population Density</div>
        <div className="result-value-big">{Number(prediction).toFixed(3)}</div>
        <div className="result-unit">{unit}</div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16, flexWrap: 'wrap' }}>
          <RiskBadge level={riskLevel} />
          <TrendChip trend={trend} />
        </div>
        {summary && (
          <p style={{ marginTop: 16, color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: 520, margin: '16px auto 0' }}>
            {summary}
          </p>
        )}
      </div>

      {/* Env data cards */}
      {env && Object.keys(env).length > 0 && (
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
      {env && (
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

      {result?.feature_importance?.labels?.length > 0 && (
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
