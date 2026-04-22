import { useState, useEffect, useCallback } from 'react'

// Descriptions for every feature that may appear
const FIELD_META = {
  coordinateUncertaintyInMeters: { name: 'GPS Accuracy', desc: 'Location accuracy in metres (lower = better)', icon: '📍' },
  day:              { name: 'Day of Month',        desc: 'Observation day (1–31)',              icon: '🗓️' },
  month:            { name: 'Month',               desc: 'Observation month (1–12)',            icon: '📅' },
  year:             { name: 'Year',                desc: 'Year when observation was recorded',  icon: '📆' },
  decade:           { name: 'Decade',              desc: 'Decade group derived from year',      icon: '⏰' },
  season_enc:       { name: 'Season Code',         desc: 'Encoded season of observation',       icon: '🌦️' },
  lat_grid:         { name: 'Latitude Grid',       desc: 'North–South grid location',           icon: '🧭' },
  lon_grid:         { name: 'Longitude Grid',      desc: 'East–West grid location',             icon: '🧭' },
  species_richness: { name: 'Species Richness',    desc: 'Number of different species in area', icon: '🌈' },
  phylum_enc:       { name: 'Phylum Code',         desc: 'Broad animal phylum (encoded)',       icon: '🧬' },
  class_enc:        { name: 'Class Code',          desc: 'Animal class (encoded)',              icon: '🏷️' },
  order_enc:        { name: 'Order Code',          desc: 'Animal order (encoded)',              icon: '🦁' },
  family_enc:       { name: 'Family Code',         desc: 'Animal family (encoded)',             icon: '🐾' },
  taxonRank_enc:    { name: 'Taxonomic Rank',      desc: 'How specific the classification is',  icon: '📊' },
  basisOfRecord_enc:{ name: 'Record Type',         desc: 'Type of observation record',          icon: '📋' },
}

const DROPDOWN_FEATURES = ['phylum_enc','class_enc','order_enc','family_enc','taxonRank_enc','basisOfRecord_enc','season_enc']
const SLIDER_FEATURES = ['coordinateUncertaintyInMeters','lat_grid','lon_grid','species_richness']

export function usePrediction(featuresUrl, predictUrl) {
  const [features, setFeatures] = useState({})
  const [values, setValues] = useState({})
  const [loading, setLoading] = useState(false)
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

  const predict = useCallback(async () => {
    setLoading(true)
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
        setResult(data)
      } else {
        setError(data.error || 'Prediction failed.')
      }
    } catch (e) {
      setError('Network error: ' + e.message)
    } finally {
      setLoading(false)
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

  return { features, values, setValue, loading, fetchingFeatures, result, error, predict, reset }
}

// ─── Field Component ─────────────────────────────────────────────────────
function FormField({ name, ranges, value, onChange }) {
  const meta = FIELD_META[name] || { name, desc: '', icon: '📌' }
  const isDropdown = DROPDOWN_FEATURES.includes(name)
  const isSlider = SLIDER_FEATURES.includes(name)
  const span = Math.round(ranges.max - ranges.min)
  const showDropdown = isDropdown && span > 0 && span <= 25

  return (
    <div className="form-group">
      <label className="form-label">
        <span className="lbl-icon">{meta.icon}</span>
        <span className="lbl-text">
          <span className="lbl-name">{meta.name}</span>
          {meta.desc && <span className="lbl-desc">{meta.desc}</span>}
        </span>
      </label>

      {showDropdown ? (
        <select
          className="form-input"
          value={value}
          onChange={e => onChange(name, e.target.value)}
        >
          {Array.from({ length: Math.round(ranges.max - ranges.min) + 1 }, (_, i) => {
            const v = Math.round(ranges.min) + i
            return <option key={v} value={v}>{v}</option>
          })}
        </select>
      ) : (
        <div className="slider-row">
          {isSlider && (
            <input
              type="range"
              min={ranges.min}
              max={ranges.max}
              step={0.1}
              value={value}
              onChange={e => onChange(name, e.target.value)}
            />
          )}
          <input
            type="number"
            className="form-input"
            min={ranges.min}
            max={ranges.max}
            step={0.1}
            value={value}
            onChange={e => onChange(name, e.target.value)}
          />
        </div>
      )}

      <div className="range-hint">
        <span>Range:</span>
        <span>{ranges.min.toFixed(2)} – {ranges.max.toFixed(2)}</span>
      </div>
    </div>
  )
}

// ─── Full Form ───────────────────────────────────────────────────────────
export function PredictionForm({ features, values, setValue, loading, fetchingFeatures, onPredict, onReset, accentColor }) {
  if (fetchingFeatures) {
    return (
      <div className="spinner-wrap">
        <div className="spinner" />
        <span>Loading model features…</span>
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
          />
        ))}
      </div>
      <div className="form-actions">
        <button
          className="btn-predict"
          onClick={onPredict}
          disabled={loading}
          style={accentColor ? { background: accentColor } : {}}
        >
          {loading ? '⏳ Analysing…' : '🔮 Predict Population Density'}
        </button>
        <button className="btn-reset" onClick={onReset}>↺ Reset</button>
      </div>
    </>
  )
}
