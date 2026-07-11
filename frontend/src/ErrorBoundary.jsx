import React from 'react'

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('React Error Boundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px 20px', maxWidth: 800, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
          <h2 style={{ color: '#E11D48', marginBottom: 16 }}>Something went wrong.</h2>
          <div style={{ background: '#FEE2E2', padding: 20, borderRadius: 8, color: '#991B1B', marginBottom: 24, fontSize: 14 }}>
            <strong>Error:</strong> {this.state.error?.toString()}
          </div>
          <p style={{ fontSize: 14, color: '#4B5563' }}>
            Please copy this error message or take a screenshot so we can fix it!
          </p>
        </div>
      )
    }

    return this.props.children
  }
}
