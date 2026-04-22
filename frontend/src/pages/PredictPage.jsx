import { Link } from 'react-router-dom'
import { usePrediction, PredictionForm } from '../components/PredictionForm'
import ResultPanel from '../components/ResultPanel'

export default function PredictPage({ config }) {
  const { emoji, title, subtitle, category, featuresUrl, predictUrl, accentColor, unit, quickLinks } = config

  const hook = usePrediction(featuresUrl, predictUrl)

  return (
    <div className="page-wrapper predict-page">
      {/* Back */}
      <Link to="/" className="back-link">← Back to Home</Link>

      {/* Header */}
      <div className="predict-page-header">
        <div className="header-icon">{emoji}</div>
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
      </div>

      {/* Quick links */}
      {quickLinks && (
        <div className="quick-links">
          {quickLinks.map(ql => (
            <Link key={ql.to} to={ql.to} className="quick-link-btn">
              {ql.icon} {ql.label}
            </Link>
          ))}
        </div>
      )}

      {/* Form card */}
      <div className="glass-card" style={{ padding: '32px' }}>
        <div className="section-heading">⚙️ Model Inputs — {category}</div>
        <PredictionForm
          features={hook.features}
          values={hook.values}
          setValue={hook.setValue}
          loading={hook.loading}
          fetchingFeatures={hook.fetchingFeatures}
          onPredict={hook.predict}
          onReset={hook.reset}
          accentColor={accentColor}
          categoryLabel={title}
        />
      </div>

      {/* Loading */}
      {hook.loading && (
        <div className="spinner-wrap" style={{ marginTop: 32 }}>
          <div className="spinner" />
          <span>Analysing ecosystem data…</span>
        </div>
      )}

      {/* Error */}
      {hook.error && !hook.loading && (
        <div className="error-box">
          <span>⚠️</span>
          <span>{hook.error}</span>
        </div>
      )}

      {/* Result */}
      {hook.result && !hook.loading && (
        <ResultPanel
          result={hook.result}
          unit={unit}
          speciesLabel={title}
        />
      )}
    </div>
  )
}
