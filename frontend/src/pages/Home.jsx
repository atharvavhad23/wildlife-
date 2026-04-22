import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

const cards = [
  {
    key: 'animals',
    emoji: '🦁',
    title: 'Animals',
    subtitle: 'Mammals & Reptiles',
    features: ['Predator & prey species', 'Spatial distribution maps', 'Temporal sighting patterns', 'Environmental factor analysis'],
    btnText: 'Predict Animal Density →',
    to: '/animals',
    color: 'from-red-500 to-rose-400',
    shadow: 'shadow-[0_0_20px_rgba(239,68,68,0.3)]',
    hoverShadow: 'hover:shadow-[0_0_35px_rgba(239,68,68,0.5)]'
  },
  {
    key: 'birds',
    emoji: '🦅',
    title: 'Birds',
    subtitle: 'Avian Species',
    features: ['200+ bird species tracked', 'Migratory pattern analysis', 'Seasonal variation models', 'Habitat preference mapping'],
    btnText: 'Predict Bird Density →',
    to: '/birds',
    color: 'from-teal-400 to-cyan-400',
    shadow: 'shadow-[0_0_20px_rgba(45,212,191,0.3)]',
    hoverShadow: 'hover:shadow-[0_0_35px_rgba(45,212,191,0.5)]'
  },
  {
    key: 'insects',
    emoji: '🦋',
    title: 'Insects',
    subtitle: 'Invertebrate Species',
    features: ['Pollinator & arthropod trends', 'Micro-habitat density signals', 'Seasonal emergence patterns', 'Taxonomy-aware predictions'],
    btnText: 'Predict Insect Density →',
    to: '/insects',
    color: 'from-amber-400 to-orange-400',
    shadow: 'shadow-[0_0_20px_rgba(251,191,36,0.3)]',
    hoverShadow: 'hover:shadow-[0_0_35px_rgba(251,191,36,0.5)]'
  },
  {
    key: 'plants',
    emoji: '🌿',
    title: 'Plants',
    subtitle: 'Flora & Vegetation',
    features: ['Floral density forecasting', 'Botanical hotspot clustering', 'Species-level drilldown maps', 'Taxonomy-aware vegetation signals'],
    btnText: 'Predict Plant Density →',
    to: '/plants',
    color: 'from-emerald-400 to-green-400',
    shadow: 'shadow-[0_0_20px_rgba(52,211,153,0.3)]',
    hoverShadow: 'hover:shadow-[0_0_35px_rgba(52,211,153,0.5)]'
  },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 80, damping: 15 } }
}

export default function Home() {
  return (
    <div className="page-wrapper overflow-hidden pb-20">
      {/* Hero */}
      <motion.div 
        className="hero pt-20 pb-16 relative"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, type: "spring" }}
          className="inline-flex items-center gap-3 bg-green-500/10 border border-green-500/30 rounded-full px-5 py-2 text-sm font-bold text-green-400 tracking-wider uppercase mb-8 shadow-[0_0_20px_rgba(34,197,94,0.15)]"
        >
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          ML-Powered Conservation Intelligence
        </motion.div>
        
        <motion.h1 
          className="text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-br from-white via-green-100 to-green-400 tracking-tighter leading-[1.1] mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          Wildlife Population<br />Density Forecasting
        </motion.h1>
        
        <motion.p 
          className="text-lg text-white/60 max-w-2xl mx-auto leading-relaxed mb-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          Harness advanced machine learning algorithms to predict and cluster wildlife population densities using taxonomy, climate signals, and spatial geometry.
        </motion.p>

        <motion.div 
          className="flex flex-col sm:flex-row justify-center gap-4 mb-16"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Link to="/dashboard" className="group px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl font-extrabold text-white uppercase tracking-widest shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_35px_rgba(16,185,129,0.5)] transition-all flex items-center justify-center gap-2">
            📊 Intelligence Dashboard <span className="group-hover:translate-x-1 transition-transform">→</span>
          </Link>
          <Link to="/animals/clustering" className="px-8 py-4 bg-white/5 hover:bg-white/10 backdrop-blur-md rounded-xl font-extrabold text-white uppercase tracking-widest border border-white/10 transition-all flex items-center justify-center gap-2">
            🗺 Explore Maps
          </Link>
        </motion.div>

        {/* Stats */}
        <motion.div 
          className="flex flex-wrap justify-center gap-6"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {[
            { num: '12', lbl: 'Custom ML Models' },
            { num: '50+', lbl: 'Engineered Features' },
            { num: '92%+', lbl: 'Peak R² Accuracy' },
            { num: '250K+', lbl: 'Sighting Records' },
          ].map((s, i) => (
            <motion.div variants={itemVariants} className="bg-black/30 backdrop-blur-md border border-white/10 rounded-2xl px-6 py-4 flex items-center gap-4 shadow-xl" key={i}>
              <span className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-teal-400 drop-shadow-md">{s.num}</span>
              <span className="text-xs font-bold uppercase tracking-wider text-white/50 w-min leading-tight text-left">{s.lbl}</span>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      {/* Category cards */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 px-4"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
      >
        {cards.map(card => (
          <motion.div variants={itemVariants} key={card.key}>
            <Link to={card.to} className="block group">
              <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden transition-all duration-300 hover:-translate-y-2 hover:border-white/20 shadow-2xl relative h-full flex flex-col">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r opacity-50 group-hover:opacity-100 transition-opacity" />
                <div className={`p-8 pb-6 border-b border-white/5 relative overflow-hidden`}>
                  <div className={`absolute inset-0 bg-gradient-to-br ${card.color} opacity-[0.03] group-hover:opacity-[0.08] transition-opacity`} />
                  <span className="text-6xl mb-4 block filter drop-shadow-xl group-hover:scale-110 transition-transform duration-300 origin-left">{card.emoji}</span>
                  <h2 className="text-3xl font-black text-white tracking-tight mb-1">{card.title}</h2>
                  <p className="text-sm font-bold uppercase tracking-wider text-white/40">{card.subtitle}</p>
                </div>
                <div className="p-8 pt-6 flex-1 flex flex-col">
                  <ul className="flex flex-col gap-3 mb-8 flex-1">
                    {card.features.map(f => (
                      <li key={f} className="flex items-start gap-3 text-sm font-medium text-white/60">
                        <span className={`flex-shrink-0 w-5 h-5 rounded-full bg-gradient-to-r ${card.color} flex items-center justify-center text-[10px] text-white/90 mt-0.5`}>✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <button className={`w-full py-4 rounded-xl font-black uppercase tracking-widest text-xs text-white bg-gradient-to-r ${card.color} ${card.shadow} ${card.hoverShadow} transition-all`}>
                    {card.btnText}
                  </button>
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* Footer */}
      <motion.div 
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        className="mt-24 text-center border-t border-white/10 pt-8 flex flex-col md:flex-row items-center justify-center gap-4 text-xs font-bold uppercase tracking-widest text-white/30"
      >
        <span>🔬 Powered by Advanced Machine Learning</span>
        <span className="hidden md:inline text-white/10">•</span>
        <span>📊 Based on Historical Sighting Data</span>
        <span className="hidden md:inline text-white/10">•</span>
        <span>📍 Koyna Wildlife Sanctuary, Maharashtra</span>
      </motion.div>
    </div>
  )
}
