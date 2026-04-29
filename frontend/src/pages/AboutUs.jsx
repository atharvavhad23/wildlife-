import { motion } from 'framer-motion'

export default function AboutUs() {
  return (
    <div className="page-wrapper pb-24">
      <div className="max-w-4xl mx-auto pt-16">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-12"
        >
          <header className="text-center">
            <h1 className="text-5xl font-black text-white mb-6 tracking-tight">
              About the <span className="text-green-400">Project</span>
            </h1>
            <p className="text-white/40 text-xl font-medium leading-relaxed">
              Merging advanced analytics with conservation efforts to protect the 
              rich biodiversity of the Koyna region.
            </p>
          </header>

          <section className="glass-card p-10 space-y-6">
            <h2 className="text-2xl font-bold text-white">Our Mission</h2>
            <p className="text-white/60 leading-relaxed text-lg">
              The Koyna Wildlife Intelligence system was developed to provide researchers, 
              conservationists, and policy-makers with data-driven insights into wildlife 
              population dynamics. By leveraging high-resolution iNaturalist data and 
              environmental stressors, our models predict population density and biodiversity 
              health across critical geographic grids.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
              {[
                { val: '25k+', label: 'Observations' },
                { val: '4', label: 'ML Model Suites' },
                { val: '98%', label: 'Area Coverage' },
              ].map((stat, i) => (
                <div key={i} className="bg-white/5 p-6 rounded-2xl border border-white/5 text-center">
                  <div className="text-3xl font-black text-green-400 mb-1">{stat.val}</div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-white/30">{stat.label}</div>
                </div>
              ))}
            </div>
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="glass-card p-8">
              <h3 className="text-lg font-bold text-white mb-4">Technology Stack</h3>
              <ul className="space-y-3 text-white/50 text-sm">
                <li className="flex gap-2"><span>⚡</span> Distributed Random Forest Classifiers</li>
                <li className="flex gap-2"><span>🌍</span> Spatial Clustering & Heatmapping</li>
                <li className="flex gap-2"><span>📊</span> Predictive Time-Series Analysis</li>
                <li className="flex gap-2"><span>☁️</span> Real-time Environmental Sync</li>
              </ul>
            </div>
            <div className="glass-card p-8">
              <h3 className="text-lg font-bold text-white mb-4">The Region</h3>
              <p className="text-white/50 text-sm leading-relaxed">
                Koyna Wildlife Sanctuary is a UNESCO World Heritage site and a critical 
                habitat for many endangered species. Our project focuses on the 
                intersection of human activity, topography, and seasonal changes 
                within this 400+ km² biosphere.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
