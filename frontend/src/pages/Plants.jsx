import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { usePrediction, PredictionForm } from '../components/PredictionForm'
import ResultPanel from '../components/ResultPanel'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

// ─── Model Comparison Badge ────────────────────────────────────────────────
function ModelBadge({ name, isWinner }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
        isWinner
          ? 'bg-green-500/20 text-green-400 border border-green-500/40'
          : 'bg-white/5 text-muted border border-white/10'
      }`}
    >
      {isWinner && '🏆 '}
      {name}
    </span>
  )
}

// ─── Metric Row ────────────────────────────────────────────────────────────
function MetricRow({ label, value, unit = '', highlight = false }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
      <span className="text-xs text-secondary">{label}</span>
      <span className={`text-xs font-bold ${highlight ? 'text-green-400' : 'text-primary'}`}>
        {value}{unit}
      </span>
    </div>
  )
}

// ─── Model Comparison Panel ────────────────────────────────────────────────
function ModelComparisonPanel() {
  const [info, setInfo]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/plants/model-info/')
      .then(r => r.json())
      .then(d => { setInfo(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="glass-card p-6 animate-pulse">
        <div className="h-4 bg-white/10 rounded w-1/2 mb-4" />
        <div className="h-3 bg-white/5 rounded w-full mb-2" />
        <div className="h-3 bg-white/5 rounded w-3/4" />
      </div>
    )
  }

  if (!info || !info.trained) {
    return (
      <div className="glass-card p-6 border-l-4 border-l-amber-500/60">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="font-bold text-amber-400 mb-1">Models Not Trained Yet</h3>
            <p className="text-sm text-secondary mb-4">
              Run the training scripts to enable predictions and model comparison:
            </p>
            <div className="bg-black/40 rounded-lg p-3 font-mono text-xs text-green-300 space-y-1">
              <div>cd d:\Wildlife_Conserve</div>
              <div>.venv\Scripts\python.exe prepare_plants_data.py</div>
              <div>.venv\Scripts\python.exe train_plants_model.py</div>
            </div>
            <p className="text-xs text-muted mt-3">
              This will train Linear Regression &amp; XGBoost, compare them, and save the winner as the production model.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const reg  = info.regression || {}
  const comp = reg.comparison  || {}
  const models = Object.entries(comp)

  // Chart data for side-by-side comparison
  const chartData = models.map(([name, metrics]) => ({
    name: name.length > 12 ? name.slice(0, 12) + '…' : name,
    fullName: name,
    r2: parseFloat((metrics.r2 || 0).toFixed(4)),
    within25: parseFloat((metrics.within_25pct || 0).toFixed(1)),
    isWinner: name === reg.winner,
  }))

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-bold uppercase tracking-widest text-muted">
          🤖 Model Comparison
        </h2>
        <ModelBadge name={reg.winner || 'Unknown'} isWinner />
      </div>

      {/* Metrics for winning model */}
      <div className="mb-5">
        <div className="text-[10px] font-bold uppercase text-muted mb-2">Winner Metrics</div>
        <MetricRow label="R² Score"              value={(reg.r2      || 0).toFixed(4)} highlight />
        <MetricRow label="Cross-Val R² (5-fold)" value={(reg.cv_r2   || 0).toFixed(4)} />
        <MetricRow label="MAE (log space)"        value={(reg.mae     || 0).toFixed(4)} />
        <MetricRow label="Within ±25% Accuracy"  value={(reg.within_25pct || 0).toFixed(1)} unit="%" />
      </div>

      {/* Side-by-side R² chart */}
      {chartData.length > 1 && (
        <>
          <div className="text-[10px] font-bold uppercase text-muted mb-3">R² Comparison</div>
          <div className="h-[120px] w-full mb-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.5)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.5)' }} axisLine={false} tickLine={false} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'rgba(10,26,14,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                  formatter={(v, _, props) => [v.toFixed(4), `R² — ${props.payload.fullName}`]}
                />
                <Bar dataKey="r2" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.isWinner ? '#34d399' : '#4cc9f0'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* All models table */}
          <div className="text-[10px] font-bold uppercase text-muted mb-2">All Models</div>
          <div className="space-y-1.5">
            {models.map(([name, m]) => (
              <div
                key={name}
                className={`flex items-center justify-between p-2 rounded-lg text-xs ${
                  name === reg.winner ? 'bg-green-500/10 border border-green-500/20' : 'bg-white/5'
                }`}
              >
                <div className="flex items-center gap-2">
                  {name === reg.winner && <span>🏆</span>}
                  <span className="font-bold truncate max-w-[130px]">{name}</span>
                </div>
                <div className="flex gap-3 text-[10px] text-muted font-mono">
                  <span>R²: {(m.r2||0).toFixed(3)}</span>
                  <span>±25%: {(m.within_25pct||0).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Clustering info */}
      {info.clustering?.n_clusters > 0 && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <div className="text-[10px] font-bold uppercase text-muted mb-2">🗺️ K-Means Clustering</div>
          <MetricRow label="Optimal k (elbow method)" value={info.clustering.n_clusters} />
          <MetricRow label="Inertia" value={info.clustering.inertia.toFixed(0)} />
        </div>
      )}
    </div>
  )
}

// ─── Main Plants Page ──────────────────────────────────────────────────────
export default function Plants() {
  const config = {
    emoji:       '🌿',
    title:       'Plants',
    subtitle:    'Predict floral density and analyze botanical distribution across Koyna',
    category:    'Phylum · Family · Locality · Season',
    featuresUrl: '/features/plants/',
    predictUrl:  '/predict/plants/',
    unit:        'plant observations per grid cell',
    accentColor: 'linear-gradient(135deg, #10b981, #059669)',
    quickLinks: [
      { to: '/plants/photos',      label: 'Photo Gallery',   icon: '📸' },
      { to: '/plants/clustering',  label: 'Clustering Map',  icon: '🗺️' },
    ],
  }

  const hook = usePrediction(config.featuresUrl, config.predictUrl)

  return (
    <div className="page-wrapper predict-page">
      <Link to="/" className="back-link">← Back to Home</Link>

      {/* Header */}
      <div className="predict-page-header">
        <div className="header-icon">{config.emoji}</div>
        <div>
          <h1>{config.title}</h1>
          <p>{config.subtitle}</p>
        </div>
      </div>

      {/* Quick Links */}
      <div className="quick-links">
        {config.quickLinks.map(ql => (
          <Link key={ql.to} to={ql.to} className="quick-link-btn">
            {ql.icon} {ql.label}
          </Link>
        ))}
      </div>

      {/* Two-column layout: Form + Model Comparison */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, alignItems: 'start' }}>
        {/* Prediction Form */}
        <div className="glass-card" style={{ padding: '32px' }}>
          <div className="section-heading">⚙️ Model Inputs — {config.category}</div>
          <PredictionForm
            features={hook.features}
            values={hook.values}
            setValue={hook.setValue}
            loading={hook.loading}
            fetchingFeatures={hook.fetchingFeatures}
            onPredict={hook.predict}
            onReset={hook.reset}
            accentColor={config.accentColor}
          />
        </div>

        {/* Model Comparison Panel */}
        <ModelComparisonPanel />
      </div>

      {/* Loading */}
      {hook.loading && (
        <div className="spinner-wrap" style={{ marginTop: 32 }}>
          <div className="spinner" />
          <span>Analysing botanical ecosystem data…</span>
        </div>
      )}

      {/* Error */}
      {hook.error && !hook.loading && (
        <div className="error-box">
          <span>⚠️</span>
          <span>{hook.error}</span>
        </div>
      )}

      {/* Result Panel — also shows model_info if returned */}
      {hook.result && !hook.loading && (
        <>
          <ResultPanel
            result={hook.result}
            unit={config.unit}
            speciesLabel={config.title}
          />
          {hook.result.model_info && (
            <div className="glass-card p-6 mt-6">
              <div className="section-heading">📊 Model Used for This Prediction</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                {[
                  { label: 'Winner',         value: hook.result.model_info.winner },
                  { label: 'R²',             value: (hook.result.model_info.r2||0).toFixed(4) },
                  { label: 'CV-R² (5-fold)', value: (hook.result.model_info.cv_r2||0).toFixed(4) },
                  { label: 'Within ±25%',    value: `${(hook.result.model_info.within_25pct||0).toFixed(1)}%` },
                ].map(item => (
                  <div key={item.label} className="bg-white/5 rounded-xl p-4 text-center">
                    <div className="text-lg font-bold text-green-400">{item.value}</div>
                    <div className="text-[10px] text-muted uppercase tracking-widest mt-1">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
