import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { usePrediction, PredictionForm } from '../components/PredictionForm'
import ResultPanel from '../components/ResultPanel'

export default function PredictPage({ config }) {
  const { emoji, title, subtitle, category, featuresUrl, predictUrl, accentColor, unit, quickLinks } = config
  const hook = usePrediction(featuresUrl, predictUrl)

  return (
    <div className="page-wrapper predict-page">
      {/* Back */}
      <Link to="/" className="back-link mt-6 inline-flex">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
        </svg>
        Back to Dashboard
      </Link>

      {/* Header */}
      <motion.div
        className="predict-page-header"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="header-icon">{emoji}</div>
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
      </motion.div>

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

      {/* Inline error banner (appears above form) */}
      <AnimatePresence>
        {hook.error && !hook.loading && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-6 flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400"
          >
            <span className="text-lg flex-shrink-0">⚠️</span>
            <div>
              <p className="font-semibold text-sm">Error</p>
              <p className="text-sm opacity-80 mt-0.5">{hook.error}</p>
            </div>
            <button
              onClick={() => hook.reset()}
              className="ml-auto flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Form card */}
      <div className="glass-card" style={{ padding: '32px', position: 'relative' }}>
        <div className="section-heading">⚙️ Model Inputs — {category}</div>
        <PredictionForm
          features={hook.features}
          values={hook.values}
          setValue={hook.setValue}
          loading={hook.loading}
          loadingMode={hook.loadingMode}
          fetchingFeatures={hook.fetchingFeatures}
          onPredict={hook.predict}
          onReset={hook.reset}
          accentColor={accentColor}
          categoryLabel={title}
        />

        {/* Animated overlay while predicting */}
        <AnimatePresence>
          {hook.loading && (
            <motion.div
              key="predict-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm rounded-[var(--radius-lg)] flex flex-col items-center justify-center gap-5 z-20"
            >
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 rounded-full border-4 border-white/5" />
                <div className="absolute inset-0 rounded-full border-4 border-t-green-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                <span className="absolute inset-0 flex items-center justify-center text-2xl">{emoji}</span>
              </div>
              <div className="text-center">
                <p className="text-white font-bold text-sm uppercase tracking-widest">
                  {hook.loadingMode === 'density' ? '🔮 Predicting Density…' : '📈 Classifying Trend…'}
                </p>
                <p className="text-white/40 text-xs mt-1">Analysing ecosystem parameters</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Result */}
      <AnimatePresence>
        {hook.result && !hook.loading && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 80, damping: 18 }}
          >
            <ResultPanel result={hook.result} unit={unit} speciesLabel={title} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
