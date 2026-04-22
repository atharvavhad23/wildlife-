import PredictPage from './PredictPage'

const config = {
  emoji: '🌿',
  title: 'Plants',
  subtitle: 'Predict floral density and analyze botanical distribution across Koyna',
  category: 'Phylum · Family · Locality · Season',
  featuresUrl: '/features/plants/',
  predictUrl: '/predict/plants/',
  unit: 'plant observations per grid cell',
  accentColor: 'linear-gradient(135deg, #10b981, #059669)',
  quickLinks: [
    { to: '/plants/photos', label: 'Photo Gallery', icon: '📸' },
    { to: '/plants/clustering', label: 'Clustering Map', icon: '🗺️' },
  ],
}

export default function Plants() {
  return <PredictPage config={config} />
}
