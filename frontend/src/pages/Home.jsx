import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'

const FEATURES = [
  {
    icon: '🎯',
    title: 'High Precision Modeling',
    desc: 'Utilizing Random Forest and Gradient Boosting architectures to achieve up to 92% prediction accuracy.'
  },
  {
    icon: '🌍',
    title: 'Spatial Intelligence',
    desc: 'Dynamic clustering and heatmapping of wildlife sightings across 400+ square kilometers of sanctuary terrain.'
  },
  {
    icon: '🌩️',
    title: 'Environmental Sync',
    desc: 'Real-time integration of climate data including NDVI, precipitation, and anthropogenic disturbance factors.'
  },
  {
    icon: '📊',
    title: 'Conservation Metrics',
    desc: 'Automated health index calculations to identify vulnerable species and habitat degradation hotspots.'
  }
]

export default function Home() {
  const { user } = useAuth()

  return (
    <div className="page-wrapper overflow-hidden pb-32">
      {/* Hero Section */}
      <section className="relative pt-20 pb-32 text-center">
        {/* Abstract Background Glows */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-green-500/10 blur-[120px] rounded-full pointer-events-none" />
        
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="relative z-10"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-green-400 mb-8 shadow-2xl">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Empowering Conservation with AI
          </div>

          <h1 className="text-6xl md:text-8xl font-black text-white tracking-tighter leading-[0.9] mb-8">
            Protecting <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">Koyna's</span><br />
            Wild Future.
          </h1>

          <p className="text-lg md:text-xl text-white/40 max-w-2xl mx-auto leading-relaxed mb-12 font-medium">
            The world's most advanced machine learning platform for 
            predicting wildlife population dynamics and biodiversity health 
            within the UNESCO World Heritage site.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              to={user ? "/models" : "/auth"}
              className="px-10 py-5 bg-white text-black font-black uppercase tracking-widest text-xs rounded-2xl hover:bg-green-400 transition-all shadow-[0_20px_50px_rgba(255,255,255,0.1)] active:scale-95"
            >
              Access Prediction Models
            </Link>
            <Link
              to="/about"
              className="px-10 py-5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-white font-black uppercase tracking-widest text-xs transition-all active:scale-95"
            >
              Learn More
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Feature Grid */}
      <section className="max-w-6xl mx-auto px-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {FEATURES.map((f, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="glass-card p-8 group hover:border-green-500/30 transition-all"
          >
            <div className="text-4xl mb-6 group-hover:scale-110 transition-transform">{f.icon}</div>
            <h3 className="text-white font-black uppercase tracking-wider text-sm mb-3">{f.title}</h3>
            <p className="text-white/40 text-xs leading-relaxed font-medium">{f.desc}</p>
          </motion.div>
        ))}
      </section>

      {/* How it Works / Trust Section */}
      <section className="mt-40 max-w-5xl mx-auto px-6">
        <div className="glass-card p-12 md:p-20 overflow-hidden relative">
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-green-500/10 blur-[100px] rounded-full" />
          
          <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-5xl font-black text-white leading-tight mb-8">
                Data-Driven<br />
                <span className="text-white/40 font-medium">Decisions for</span><br />
                Conservationists.
              </h2>
              <div className="space-y-6">
                {[
                  { t: 'Verified Sources', d: 'Models trained on Research Grade iNaturalist observations.' },
                  { t: 'Open Intelligence', d: 'Accessible insights for researchers and policy makers.' },
                  { t: 'Global Standards', d: 'Aligned with IUCN Red List and conservation protocols.' },
                ].map((item, i) => (
                  <div key={i} className="flex gap-4">
                    <span className="text-green-400 font-bold">✓</span>
                    <div>
                      <div className="text-white text-sm font-bold">{item.t}</div>
                      <div className="text-white/30 text-xs">{item.d}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-black/40 rounded-3xl p-8 border border-white/5 shadow-inner">
               <div className="flex items-center gap-4 mb-6">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
               </div>
               <div className="space-y-4">
                  <div className="h-4 bg-white/10 rounded-full w-3/4 animate-pulse" />
                  <div className="h-4 bg-white/5 rounded-full w-full animate-pulse" />
                  <div className="h-20 bg-green-500/5 rounded-2xl border border-green-500/10 flex items-center justify-center">
                     <span className="text-[10px] font-black uppercase tracking-widest text-green-400">Processing Spatial Grid...</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="h-8 bg-white/5 rounded-lg" />
                    <div className="h-8 bg-white/5 rounded-lg" />
                    <div className="h-8 bg-white/5 rounded-lg" />
                  </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mt-40 text-center px-6">
        <h2 className="text-3xl font-black text-white mb-6 uppercase tracking-tighter">Ready to explore the biodiversity?</h2>
        <Link
          to="/models"
          className="inline-flex items-center gap-3 px-10 py-5 bg-green-500 rounded-2xl text-black font-black uppercase tracking-widest text-xs hover:bg-green-400 transition-all shadow-[0_20px_50px_rgba(34,197,94,0.2)] group"
        >
          Start Predicting
          <span className="group-hover:translate-x-1 transition-transform">→</span>
        </Link>
      </section>
    </div>
  )
}
