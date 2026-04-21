import PredictPage from './PredictPage'

const config = {
  emoji: '🦁',
  title: 'Animals',
  subtitle: 'Predict mammal & reptile population density across Koyna grid cells',
  category: 'Location · Taxonomy · Environment',
  featuresUrl: '/features/animals/',
  predictUrl: '/predict/animals/',
  unit: 'animals per km²',
  accentColor: 'linear-gradient(135deg, #ff6b6b, #e84393)',
  quickLinks: [
    { to: '/animals/photos', label: 'Photo Gallery', icon: '📸' },
    { to: '/animals/clustering', label: 'Clustering Map', icon: '🗺️' },
  ],
}

export default function Animals() {
  return <PredictPage config={config} />
}
