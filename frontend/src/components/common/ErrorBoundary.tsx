/**
 * Error Boundary Component
 * Catches and handles React component errors gracefully
 */

import React from 'react'
import { Button } from '../ui'

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console in development
    if (import.meta.env.DEV) {
      console.error('Error boundary caught an error:', error, errorInfo)
    }
    
    // In production, you could send this to an error tracking service like Sentry
    // Example: Sentry.captureException(error, { extra: errorInfo })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-4 bg-red-50 border border-red-200 rounded-lg">
          <h3 className="text-lg font-semibold text-red-800 mb-1">Something went wrong</h3>
          <p className="text-sm text-red-600 text-center mb-3">
            An error occurred while rendering this component
          </p>
          {import.meta.env.DEV && this.state.error && (
            <pre className="text-xs text-red-700 bg-red-100 p-2 rounded mb-3 max-w-md overflow-auto">
              {this.state.error.message}
            </pre>
          )}
          <Button
            onClick={this.handleReset}
            variant="danger"
            size="sm"
          >
            Try again
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
