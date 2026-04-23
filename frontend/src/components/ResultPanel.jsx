import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { motion } from 'framer-motion'

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
            {summary && (
              <p style={{ marginTop: 16, color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: 520, margin: '16px auto 0' }}>
                {summary}
              </p>
            )}
          </>
        )}
        
        {/* Action Buttons */}
        <div className="flex justify-center gap-4 mt-6">
          <button 
            onClick={() => {
              const csvContent = "data:text/csv;charset=utf-8," 
                + "Model,Mode,Prediction,Unit,Risk,Trend,Accuracy\n"
                + `${mode === 'density' ? regressionModel : occurrenceModel},${mode},${mode === 'density' ? Number(prediction).toFixed(3) : occurrenceLabel.toUpperCase()},${unit},${riskLevel},${trend},${result?.accuracy || 'N/A'}`;
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", `koyna_${speciesLabel.toLowerCase()}_prediction.csv`);
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }}
            className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs font-bold uppercase tracking-wider text-white transition-all shadow-lg backdrop-blur-sm"
          >
            <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            Export CSV
          </button>
          
          <button 
            onClick={(e) => {
              const text = `Koyna Sanctuary ${speciesLabel} ML Prediction:\nMode: ${mode.toUpperCase()}\nResult: ${mode === 'density' ? Number(prediction).toFixed(3) + ' ' + unit : occurrenceLabel.toUpperCase()}\nTrend: ${trend}\nAccuracy: ${result?.accuracy || 'N/A'}%`;
              navigator.clipboard.writeText(text);
              const btn = e.currentTarget;
              const originalText = btn.innerHTML;
              btn.innerHTML = `<svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Copied!`;
              btn.classList.add('border-green-400/50', 'bg-green-400/10');
              setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('border-green-400/50', 'bg-green-400/10');
              }, 2000);
            }}
            className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs font-bold uppercase tracking-wider text-white transition-all shadow-lg backdrop-blur-sm"
          >
            <svg className="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
            Share Result
          </button>
        </div>
      </div>

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
                  ⚡ Limited to top PCA-ranked features
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
