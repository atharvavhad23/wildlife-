import { motion } from 'framer-motion'

const FAQS = [
  {
    q: "How accurate are the wildlife predictions?",
    a: "Our models achieve an average accuracy of 85-92% when validated against historical ground-truth data. However, predictions are estimates based on available observational density and may vary with sudden environmental shifts."
  },
  {
    q: "Where does the data come from?",
    a: "We primarily consume data from the iNaturalist open-source repository, specifically focusing on verified (Research Grade) observations within the Koyna latitude/longitude boundaries."
  },
  {
    q: "What environmental factors are considered?",
    a: "The prediction engine integrates temperature, humidity, rainfall, vegetation index (NDVI), water availability, and human disturbance metrics (proximity to roads/settlements)."
  },
  {
    q: "Can I use these models for my own research?",
    a: "Currently, this platform is for demonstration and registered researcher access. For API integration or data exports, please contact our administrative team."
  },
  {
    q: "How often is the data updated?",
    a: "Observations are synced every 24 hours. Predictive models are retrained monthly to incorporate seasonal trends and new observation clusters."
  }
]

export default function FAQ() {
  return (
    <div className="page-wrapper pb-24">
      <div className="max-w-3xl mx-auto pt-16">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-12"
        >
          <header className="text-center">
            <h1 className="text-5xl font-black text-white mb-6 tracking-tight">
              Common <span className="text-green-400">Questions</span>
            </h1>
            <p className="text-white/40 text-lg font-medium">
              Everything you need to know about the Koyna Wildlife Intelligence platform.
            </p>
          </header>

          <div className="space-y-4">
            {FAQS.map((faq, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="glass-card p-6 hover:border-green-500/20 transition-all"
              >
                <h3 className="text-lg font-bold text-white mb-3 flex items-start gap-3">
                  <span className="text-green-400 font-black">Q.</span>
                  {faq.q}
                </h3>
                <div className="flex items-start gap-3 text-white/50 leading-relaxed text-sm">
                   <span className="text-white/20 font-black uppercase mt-0.5">Ans.</span>
                   <p>{faq.a}</p>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="bg-white/5 p-8 rounded-3xl border border-dashed border-white/10 text-center">
            <h3 className="text-white font-bold mb-2">Still have questions?</h3>
            <p className="text-white/40 text-sm mb-6">Can't find the answer you're looking for? Please chat to our friendly team.</p>
            <button className="px-6 py-3 bg-white text-black font-black text-xs uppercase tracking-widest rounded-xl hover:bg-green-400 transition-colors">
              Contact Support
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
