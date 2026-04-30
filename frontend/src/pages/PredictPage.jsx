import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { usePrediction, PredictionForm } from '../components/PredictionForm'
import ResultPanel from '../components/ResultPanel'

export default function PredictPage({ config }) {
  const { emoji, title, subtitle, category, featuresUrl, predictUrl, accentColor, unit, quickLinks } = config
  const hook = usePrediction(featuresUrl, predictUrl)

  return (
    <div className="page-wrapper pb-32">
      {/* Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12 mt-8">
        <Link to="/models" className="group flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.2em] text-white/40 hover:text-green-400 transition-all">
          <span className="p-2 rounded-xl bg-white/5 border border-white/5 group-hover:border-green-500/30 group-hover:bg-white/10 transition-all">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
            </svg>
          </span>
          Back to Hub
        </Link>

        {quickLinks && (
          <div className="flex flex-wrap gap-2">
            {quickLinks.map(ql => (
              <Link 
                key={ql.to} 
                to={ql.to} 
                className="px-5 py-2.5 rounded-2xl bg-white/10 border border-white/10 hover:border-green-500/40 hover:bg-white/15 text-[10px] font-black uppercase tracking-[0.15em] text-white hover:text-green-400 transition-all flex items-center gap-2.5 shadow-xl hover:scale-105 active:scale-95"
              >
                <span className="text-sm">{ql.icon}</span> {ql.label}
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-16"
      >
        <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center text-4xl shadow-inner border border-white/5 mx-auto mb-6">
          {emoji}
        </div>
        <h1 className="text-4xl md:text-5xl font-black text-white mb-2 tracking-tight">{title} <span className="text-white/20">Forecasting</span></h1>
        <p className="text-white/40 text-sm font-medium tracking-wide max-w-xl mx-auto leading-relaxed">
          {subtitle}
        </p>
      </motion.div>

      {/* Error Banner */}
      <AnimatePresence>
        {hook.error && !hook.loading && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-8 max-w-3xl mx-auto flex items-start gap-3 p-5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 shadow-lg"
          >
            <span className="text-xl flex-shrink-0">⚠️</span>
            <div className="flex-1">
              <p className="font-black text-xs uppercase tracking-widest mb-1">Intelligence Error</p>
              <p className="text-sm font-medium opacity-80">{hook.error}</p>
            </div>
            <button
              onClick={() => hook.reset()}
              className="px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-[10px] font-black uppercase tracking-widest transition-all"
            >
              Clear
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Section */}
      <div className="max-w-4xl mx-auto">
        <div className="glass-card overflow-hidden relative border-white/10">
          {/* Form Header */}
          <div className="px-8 py-4 border-b border-white/5 bg-white/3 flex items-center justify-between">
            <span className="text-[10px] font-black uppercase tracking-widest text-white/40">⚙️ Model Parameters</span>
            <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-400 text-[9px] font-black uppercase tracking-wider border border-green-500/20">Ready</span>
          </div>

          <div className="p-8 md:p-12">
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
          </div>

          {/* Predicting Overlay */}
          <AnimatePresence>
            {hook.loading && (
              <motion.div
                key="predict-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-[#0a1a0e]/80 backdrop-blur-md z-20 flex flex-col items-center justify-center gap-6"
              >
                <div className="relative w-20 h-20">
                  <div className="absolute inset-0 rounded-full border-4 border-white/5" />
                  <div className="absolute inset-0 rounded-full border-4 border-t-green-500 border-r-transparent border-b-transparent border-l-transparent animate-spin shadow-[0_0_20px_rgba(34,197,94,0.3)]" />
                  <span className="absolute inset-0 flex items-center justify-center text-3xl animate-pulse">{emoji}</span>
                </div>
                <div className="text-center">
                  <h3 className="text-white font-black text-xs uppercase tracking-[0.3em] mb-2">
                    {hook.loadingMode === 'density' ? 'Synthesizing Density...' : 'Calculating Trends...'}
                  </h3>
                  <div className="flex items-center justify-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-green-400 animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1 h-1 rounded-full bg-green-400 animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1 h-1 rounded-full bg-green-400 animate-bounce" />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Result Section */}
      <div className="max-w-5xl mx-auto mt-12">
        <AnimatePresence>
          {hook.result && !hook.loading && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ type: 'spring', stiffness: 60, damping: 20 }}
            >
              <ResultPanel result={hook.result} unit={unit} speciesLabel={title} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
