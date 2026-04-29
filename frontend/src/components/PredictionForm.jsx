import { useState, useEffect, useCallback } from 'react'
import { SkeletonField } from './Skeleton'

// Descriptions for every feature that may appear
const FIELD_META = {
  coordinateUncertaintyInMeters: { name: 'Location Accuracy', desc: 'Precision of geographic coordinates (lower is better)', icon: '📍' },
  day:              { name: 'Day',               desc: 'Observation day (1–31)',              icon: '🗓️' },
  month:            { name: 'Month',               desc: 'Observation month (1–12)',            icon: '📅' },
  year:             { name: 'Year',                desc: 'Observation year',                    icon: '📆' },
  decade:           { name: 'Decade',              desc: 'Temporal decade classification',      icon: '⏰' },
  season_enc:       { name: 'Seasonal Cycle',      desc: 'Observed season (Pre-monsoon, etc.)', icon: '🌦️' },
  lat_grid:         { name: 'Geographic Latitude', desc: 'North–South spatial grid',           icon: '🧭' },
  lon_grid:         { name: 'Geographic Longitude',desc: 'East–West spatial grid',              icon: '🧭' },
  species_richness: { name: 'Biodiversity Density',desc: 'Unique species per spatial node',      icon: '🌈' },
  phylum_enc:       { name: 'Phylum Taxonomy',     desc: 'Broad taxonomic phylum classification',icon: '🧬' },
  class_enc:        { name: 'Taxonomic Class',     desc: 'Class-level biological category',      icon: '🏷️' },
  order_enc:        { name: 'Taxonomic Order',     desc: 'Order-level biological category',      icon: '🦁' },
  family_enc:       { name: 'Taxonomic Family',    desc: 'Family-level biological category',     icon: '🐾' },
  taxonRank_enc:    { name: 'Classification Rank', desc: 'Specificness of taxonomic ID',         icon: '📊' },
  basisOfRecord_enc:{ name: 'Observational Basis', desc: 'Method used for data collection',     icon: '📋' },
}

const FEATURE_VALUE_MAPS = {
  phylum_enc: { 0: 'Chordata', 1: 'Arthropoda', 2: 'Tracheophyta', 3: 'Mollusca' },
  class_enc: { 0: 'Mammalia', 1: 'Aves', 2: 'Insecta', 3: 'Magnoliopsida', 4: 'Reptilia', 5: 'Amphibia' },
  season_enc: { 0: 'Summer', 1: 'Monsoon', 2: 'Winter', 3: 'Spring' },
  basisOfRecord_enc: { 0: 'Human Observation', 1: 'Machine Observation', 2: 'Preserved Specimen' },
  taxonRank_enc: { 0: 'Species', 1: 'Genus', 2: 'Family', 3: 'Order' }
}

const DROPDOWN_FEATURES = ['phylum_enc','class_enc','order_enc','family_enc','taxonRank_enc','basisOfRecord_enc','season_enc']
const SLIDER_FEATURES = ['coordinateUncertaintyInMeters','lat_grid','lon_grid','species_richness']
const INTEGER_FEATURES = [
  'day', 'month', 'year', 'decade', 'species_richness',
  'phylum_enc', 'class_enc', 'order_enc', 'family_enc', 'taxonRank_enc', 'basisOfRecord_enc', 'season_enc'
]

export function usePrediction(featuresUrl, predictUrl) {
  const [features, setFeatures] = useState({})
  const [values, setValues] = useState({})
  const [loading, setLoading] = useState(false)
  const [loadingMode, setLoadingMode] = useState(null)
  const [fetchingFeatures, setFetchingFeatures] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Load features
  useEffect(() => {
    setFetchingFeatures(true)
    fetch(featuresUrl)
      .then(r => r.json())
      .then(data => {
        if (data?.error) {
          throw new Error(data.error)
        }

        const sanitizedEntries = Object.entries(data).filter(([, v]) => (
          v &&
          typeof v === 'object' &&
          Number.isFinite(v.min) &&
          Number.isFinite(v.max) &&
          Number.isFinite(v.mean)
        ))

        if (sanitizedEntries.length === 0) {
          throw new Error('No feature metadata available for this model.')
        }

        const cleanFeatures = Object.fromEntries(sanitizedEntries)
        setFeatures(cleanFeatures)
        // Pre-fill with means
        const defaults = {}
        Object.entries(cleanFeatures).forEach(([k, v]) => {
          defaults[k] = Math.round(v.mean * 10) / 10
        })
        setValues(defaults)
      })
      .catch((err) => setError(err?.message || 'Failed to load model features.'))
      .finally(() => setFetchingFeatures(false))
  }, [featuresUrl])

  const setValue = useCallback((key, val) => {
    setValues(prev => ({ ...prev, [key]: val }))
  }, [])

  const predict = useCallback(async (mode = 'density') => {
    setLoading(true)
    setLoadingMode(mode)
    setError(null)
    setResult(null)
    try {
      const payload = {}
      Object.keys(features).forEach(k => { payload[k] = parseFloat(values[k]) })

      const res = await fetch(predictUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (data.status === 'success') {
        setResult({ ...data, mode })
      } else {
        setError(data.error || 'Prediction failed.')
      }
    } catch (e) {
      setError('Network error: ' + e.message)
    } finally {
      setLoading(false)
      setLoadingMode(null)
    }
  }, [features, values, predictUrl])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    const defaults = {}
    Object.entries(features).forEach(([k, v]) => {
      defaults[k] = Math.round(v.mean * 10) / 10
    })
    setValues(defaults)
  }, [features])

  return { features, values, setValue, loading, loadingMode, fetchingFeatures, result, error, predict, reset }
}

// ─── Field Component ─────────────────────────────────────────────────────
function FormField({ name, ranges, value, onChange, categoryLabel = 'Animals' }) {
  const meta = FIELD_META[name] || { name, desc: '', icon: '📌' }
  const isDropdown = DROPDOWN_FEATURES.includes(name) || !!ranges.options
  const isSlider = SLIDER_FEATURES.includes(name)
  const isInteger = INTEGER_FEATURES.includes(name)
  const span = Math.round(ranges.max - ranges.min)
  const showDropdown = isDropdown && (ranges.options || (span > 0 && span <= 200))

  let desc = meta.desc;
  let icon = meta.icon;

  if (desc) {
    const cat = categoryLabel.toLowerCase();
    if (cat === 'plants') {
      desc = desc.replace(/Broad animal/gi, 'Broad botanical').replace(/Animal/gi, 'Plant');
    } else if (cat === 'birds') {
      desc = desc.replace(/Broad animal/gi, 'Broad avian').replace(/Animal/gi, 'Bird');
    } else if (cat === 'insects') {
      desc = desc.replace(/Broad animal/gi, 'Broad invertebrate').replace(/Animal/gi, 'Insect');
    }
  }

  if (name.includes('_enc')) {
    const cat = categoryLabel.toLowerCase();
    if (cat === 'plants') {
      if (name === 'phylum_enc') icon = '🌿';
      if (name === 'class_enc') icon = '🌱';
      if (name === 'order_enc') icon = '🌲';
      if (name === 'family_enc') icon = '🍃';
    } else if (cat === 'birds') {
      if (name === 'phylum_enc') icon = '🦅';
      if (name === 'class_enc') icon = '🕊️';
      if (name === 'order_enc') icon = '🪶';
      if (name === 'family_enc') icon = '🪹';
    } else if (cat === 'insects') {
      if (name === 'phylum_enc') icon = '🦋';
      if (name === 'class_enc') icon = '🐛';
      if (name === 'order_enc') icon = '🐞';
      if (name === 'family_enc') icon = '🐜';
    }
  }

  return (
    <div className="form-group">
      <label className="form-label">
        <span className="lbl-icon">{icon}</span>
        <span className="lbl-text">
          <span className="lbl-name">{meta.name}</span>
          {desc && <span className="lbl-desc">{desc}</span>}
        </span>
      </label>

      {showDropdown ? (
        <select
          className="form-input"
          value={value}
          onChange={e => onChange(name, e.target.value)}
          style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: '#fff' }}
        >
          {ranges.options ? ranges.options.map((opt, i) => (
            <option key={i} value={i} style={{ background: '#1a2e20', color: '#fff' }}>{opt}</option>
          )) : Array.from({ length: Math.round(ranges.max - ranges.min) + 1 }, (_, i) => {
            const v = Math.round(ranges.min) + i;
            const map = FEATURE_VALUE_MAPS[name];
            const label = map && map[v] ? map[v] : v;
            return <option key={v} value={v} style={{ background: '#1a2e20', color: '#fff' }}>{label}</option>
          })}
        </select>
      ) : (
        <div className="slider-row">
          {isSlider && (
            <input
              type="range"
              min={ranges.min}
              max={ranges.max}
              step={isInteger ? 1 : 0.1}
              value={value}
              onChange={e => onChange(name, e.target.value)}
            />
          )}
          <input
            type="number"
            className="form-input"
            min={ranges.min}
            max={ranges.max}
            step={isInteger ? 1 : 0.1}
            value={value}
            onChange={e => onChange(name, e.target.value)}
          />
        </div>
      )}

      {!name.includes('_enc') && (
        <div className="range-hint">
          <span>Range:</span>
          <span>
            {isInteger ? Math.round(ranges.min) : ranges.min.toFixed(2)} –{' '}
            {isInteger ? Math.round(ranges.max) : ranges.max.toFixed(2)}
          </span>
        </div>
      )}
    </div>
  )
}

// ─── Full Form ───────────────────────────────────────────────────────────
export function PredictionForm({ features, values, setValue, loading, loadingMode, fetchingFeatures, onPredict, onReset, accentColor, categoryLabel = 'Animals' }) {
  if (fetchingFeatures) {
    return (
      <div className="form-grid">
        {Array.from({ length: 6 }).map((_, i) => <SkeletonField key={i} />)}
      </div>
    )
  }

  return (
    <>
      <div className="form-grid">
        {Object.entries(features).map(([name, ranges]) => (
          <FormField
            key={name}
            name={name}
            ranges={ranges}
            value={values[name] ?? ranges.mean}
            onChange={setValue}
            categoryLabel={categoryLabel}
          />
        ))}
      </div>
      <div className="form-actions">
        <button
          onClick={() => onPredict('density')}
          disabled={loading}
          className="flex-1 min-w-[180px] flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-extrabold uppercase tracking-widest text-sm text-white bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 shadow-lg shadow-green-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
        >
          {loadingMode === 'density' ? (
            <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Analysing…</>
          ) : '🔮 Predict Density'}
        </button>
        <button
          onClick={() => onPredict('trend')}
          disabled={loading}
          className="flex-1 min-w-[180px] flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-extrabold uppercase tracking-widest text-sm text-white bg-gradient-to-r from-teal-600 to-cyan-500 hover:from-teal-500 hover:to-cyan-400 shadow-lg shadow-teal-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98]"
        >
          {loadingMode === 'trend' ? (
            <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Analysing…</>
          ) : '📈 Classify Trend'}
        </button>
        <button
          onClick={onReset}
          className="w-full flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-bold uppercase tracking-widest text-xs text-white/40 hover:text-white/70 bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 transition-all"
        >
          ↺ Reset to Defaults
        </button>
      </div>
    </>
  )
}
