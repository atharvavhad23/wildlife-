import { Link } from 'react-router-dom'

const cards = [
  {
    key: 'animals',
    emoji: '🦁',
    title: 'Animals',
    subtitle: 'Mammals & Reptiles',
    features: ['Predator & prey species', 'Spatial distribution maps', 'Temporal sighting patterns', 'Environmental factor analysis'],
    btnText: 'Predict Animal Density →',
    to: '/animals',
  },
  {
    key: 'birds',
    emoji: '🦅',
    title: 'Birds',
    subtitle: 'Avian Species',
    features: ['200+ bird species tracked', 'Migratory pattern analysis', 'Seasonal variation models', 'Habitat preference mapping'],
    btnText: 'Predict Bird Density →',
    to: '/birds',
  },
  {
    key: 'insects',
    emoji: '🦋',
    title: 'Insects',
    subtitle: 'Invertebrate Species',
    features: ['Pollinator & arthropod trends', 'Micro-habitat density signals', 'Seasonal emergence patterns', 'Taxonomy-aware predictions'],
    btnText: 'Predict Insect Density →',
    to: '/insects',
  },
]

export default function Home() {
  return (
    <div className="page-wrapper">
      {/* Hero */}
      <div className="hero">
        <div className="hero-badge">
          <span>🔬</span>
          ML-Powered Conservation Intelligence
        </div>
        <h1>Wildlife Population<br />Density Forecasting</h1>
        <p>
          Use advanced machine learning to predict wildlife population density
          across the Koyna Wildlife Sanctuary based on environmental,
          taxonomic, and temporal factors.
        </p>

        {/* Stats */}
        <div className="stats-row">
          {[
            { num: '3', lbl: 'Prediction Models' },
            { num: '13+', lbl: 'Feature Inputs' },
            { num: '89%+', lbl: 'Model Accuracy' },
            { num: '500K+', lbl: 'Observations' },
          ].map(s => (
            <div className="stat-pill" key={s.lbl}>
              <span className="stat-num">{s.num}</span>
              <span className="stat-lbl">{s.lbl}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Category cards */}
      <div className="category-grid">
        {cards.map(card => (
          <Link key={card.key} to={card.to} className={`cat-card ${card.key}`}>
            <div className="cat-card-header">
              <span className="cat-emoji">{card.emoji}</span>
              <h2>{card.title}</h2>
              <p>{card.subtitle}</p>
            </div>
            <div className="cat-card-body">
              <ul className="cat-features">
                {card.features.map(f => <li key={f}>{f}</li>)}
              </ul>
              <button className="cat-btn">{card.btnText}</button>
            </div>
          </Link>
        ))}
      </div>

      {/* Footer */}
      <div className="footer">
        🔬 Powered by Advanced Machine Learning &nbsp;·&nbsp;
        📊 Based on Historical Sighting Data &nbsp;·&nbsp;
        📍 Koyna Wildlife Sanctuary, Maharashtra
      </div>
    </div>
  )
}
