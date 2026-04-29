import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { PawPrint, Bird, Bug, Leaf, ArrowRight } from 'lucide-react'

const CATEGORIES = [
  { 
    id: 'animals', 
    title: 'Animals & Reptiles', 
    icon: PawPrint, 
    desc: 'Mammal and reptile population density forecasting across spatial grids.',
    color: 'from-red-500/20 to-rose-500/10 border-red-500/20 text-red-300'
  },
  { 
    id: 'birds', 
    title: 'Avian Species', 
    icon: Bird, 
    desc: 'Bird distribution patterns and micro-habitat density analysis.',
    color: 'from-teal-500/20 to-cyan-500/10 border-teal-500/20 text-teal-300'
  },
  { 
    id: 'insects', 
    title: 'Invertebrates', 
    icon: Bug, 
    desc: 'Insect population trends and biodiversity richness indicators.',
    color: 'from-amber-500/20 to-orange-500/10 border-amber-500/20 text-amber-300'
  },
  { 
    id: 'plants', 
    title: 'Flora & Vegetation', 
    icon: Leaf, 
    desc: 'Plant species prevalence and environmental factor correlations.',
    color: 'from-emerald-500/20 to-green-500/10 border-emerald-500/20 text-emerald-300'
  },
]

export default function PredictHub() {
  return (
    <div className="page-wrapper pb-24">
      <div className="max-w-6xl mx-auto pt-12">
        <header className="mb-12 text-center">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-5xl font-black text-white mb-4 tracking-tight"
          >
            Wildlife Prediction <span className="text-green-400">Models</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-white/40 text-lg max-w-2xl mx-auto leading-relaxed"
          >
            Select a category to access specialized machine learning models trained on 
            verified iNaturalist observation data from the Koyna biosphere.
          </motion.p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {CATEGORIES.map((cat, i) => (
            <motion.div
              key={cat.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
            >
              <Link
                to={`/${cat.id}`}
                className={`group relative flex flex-col p-8 rounded-3xl border backdrop-blur-xl bg-gradient-to-br transition-all hover:-translate-y-2 hover:shadow-2xl hover:shadow-black/40 ${cat.color}`}
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center text-4xl group-hover:scale-110 transition-transform">
                    <cat.icon size={32} />
                  </div>
                  <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-widest">
                    Available
                  </div>
                </div>
                
                <h2 className="text-2xl font-black text-white mb-2 group-hover:text-green-400 transition-colors">
                  {cat.title}
                </h2>
                <p className="text-white/50 text-sm leading-relaxed mb-8">
                  {cat.desc}
                </p>

                <div className="mt-auto flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] opacity-40 group-hover:opacity-100 group-hover:translate-x-2 transition-all">
                  Launch Predictor <ArrowRight size={14} />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
