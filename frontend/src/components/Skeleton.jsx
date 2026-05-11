/**
 * Skeleton loading components — shimmer pulse placeholders
 * Used while data is being fetched to avoid layout shift and empty states.
 */

function SkeletonBase({ className = '' }) {
  return (
    <div className={`skeleton-pulse rounded-xl bg-white/5 ${className}`} />
  )
}

/** Generic card-shaped skeleton */
export function SkeletonCard({ className = '' }) {
  return (
    <div className={`glass-card p-6 overflow-hidden ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <SkeletonBase className="w-12 h-12 rounded-xl" />
        <SkeletonBase className="w-24 h-4" />
      </div>
      <SkeletonBase className="w-full h-3 mb-2" />
      <SkeletonBase className="w-3/4 h-3 mb-2" />
      <SkeletonBase className="w-1/2 h-3" />
    </div>
  )
}

/** Single stat counter skeleton (icon + number + label) */
export function SkeletonStat() {
  return (
    <div className="glass-card p-6 flex flex-col justify-center relative overflow-hidden">
      <SkeletonBase className="w-16 h-8 mb-2" />
      <SkeletonBase className="w-24 h-3" />
    </div>
  )
}

/** Leaderboard row skeleton */
export function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 py-2">
      <SkeletonBase className="w-8 h-8 rounded-full" />
      <div className="flex-1 space-y-2">
        <SkeletonBase className="w-40 h-3" />
        <SkeletonBase className="w-24 h-2" />
      </div>
      <SkeletonBase className="w-10 h-3" />
    </div>
  )
}

/** Form field skeleton for PredictionForm loading state */
export function SkeletonField() {
  return (
    <div className="form-group">
      <SkeletonBase className="w-32 h-3 mb-3" />
      <SkeletonBase className="w-full h-11" />
    </div>
  )
}

/** Photo card skeleton for gallery pages */
export function SkeletonPhoto() {
  return (
    <div className="photo-card overflow-hidden">
      <SkeletonBase className="w-full aspect-[4/3] rounded-none" />
      <div className="p-3 space-y-2">
        <SkeletonBase className="w-3/4 h-3" />
        <SkeletonBase className="w-1/2 h-2" />
      </div>
    </div>
  )
}

/** Full-page centered loading indicator */
export function PageLoader({ label = 'Loading…' }) {
  return (
    <div className="page-wrapper flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-white/5" />
        <div className="absolute inset-0 rounded-full border-4 border-t-green-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        <span className="absolute inset-0 flex items-center justify-center text-2xl">🌿</span>
      </div>
      <p className="text-sm font-semibold uppercase tracking-widest text-white/40">{label}</p>
    </div>
  )
}

export default SkeletonBase
