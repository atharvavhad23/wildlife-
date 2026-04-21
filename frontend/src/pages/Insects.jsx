import PredictPage from './PredictPage'

const config = {
  emoji: '🦋',
  title: 'Insects',
  subtitle: 'Predict invertebrate species density across Koyna micro-habitats',
  category: 'Location · Taxonomy · Phenology',
  featuresUrl: '/features/insects/',
  predictUrl: '/predict/insects/',
  unit: 'insects per km²',
  accentColor: 'linear-gradient(135deg, #f59e0b, #f97316)',
  quickLinks: [
    { to: '/insects/photos', label: 'Photo Gallery', icon: '📸' },
    { to: '/insects/clustering', label: 'Clustering Map', icon: '🗺️' },
  ],
}

export default function Insects() {
  return <PredictPage config={config} />
}
