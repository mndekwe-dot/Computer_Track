import { Component } from 'react'

/**
 * Last line of defence. Without this, one bad render leaves a guard staring at
 * a white screen with a queue of students in front of them and no idea what to
 * do. A crash here must always end with a way back to the console.
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Kept in the console for whoever supports the deployment. Swap this for a
    // real error reporting service if you deploy campus-wide.
    console.error('Unhandled UI error:', error, info?.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div className="empty-state" style={{ padding: '60px 24px' }}>
        <h2>Something broke on this screen</h2>
        <p style={{ maxWidth: 460, margin: '10px auto 20px' }}>
          The gate register itself is fine - nothing you recorded has been lost, and any scans
          waiting to sync are still saved on this device. Reload to carry on.
        </p>
        <div className="row-actions" style={{ justifyContent: 'center' }}>
          <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
            Reload the app
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => {
              this.setState({ error: null })
              window.location.assign('/console')
            }}
          >
            Back to the gate console
          </button>
        </div>
        <details style={{ marginTop: 26, textAlign: 'left', maxWidth: 560, margin: '26px auto 0' }}>
          <summary style={{ cursor: 'pointer', fontSize: 13 }}>Technical details</summary>
          <pre
            className="mono"
            style={{
              marginTop: 10,
              padding: 12,
              background: 'var(--surface-muted)',
              borderRadius: 8,
              overflowX: 'auto',
              fontSize: 12,
            }}
          >
            {error.message}
          </pre>
        </details>
      </div>
    )
  }
}
