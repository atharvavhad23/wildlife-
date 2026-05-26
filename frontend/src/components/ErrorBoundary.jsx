import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || 'Unexpected error' }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled UI error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, message: '' })
    window.location.reload()
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="page-wrapper min-h-[60vh] flex items-center justify-center">
        <div className="glass-card p-8 max-w-xl w-full text-center border border-red-500/30">
          <h2 className="text-xl font-bold text-red-300 mb-3">Something went wrong</h2>
          <p className="text-sm text-white/60 mb-6">
            {this.state.message || 'An unexpected UI error occurred.'}
          </p>
          <button
            onClick={this.handleRetry}
            className="px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider bg-red-500/15 text-red-200 border border-red-400/30 hover:bg-red-500/25 transition-all"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }
}
