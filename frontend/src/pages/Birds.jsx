import PredictPage from './PredictPage'

const config = {
  emoji: '🦅',
  title: 'Birds',
  subtitle: 'Predict avian species population density across Koyna grid cells',
  category: 'Location · Taxonomy · Season',
  featuresUrl: '/features/birds/',
  predictUrl: '/predict/birds/',
  unit: 'birds per km²',
  accentColor: 'linear-gradient(135deg, #4ecdc4, #26c6da)',
  quickLinks: [
    { to: '/birds/photos', label: 'Photo Gallery', icon: '📸' },
  ],
}

export default function Birds() {
  return <PredictPage config={config} />
}
