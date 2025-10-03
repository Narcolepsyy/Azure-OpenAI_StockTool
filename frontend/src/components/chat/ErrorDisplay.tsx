/**
 * Error display component with retry functionality
 */

import React from 'react'
import { Button } from '../ui'
import type { ErrorDisplayProps } from '../../types'

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  onDismiss,
  canRetry = true
}) => {
  const isNetworkError = error.includes('🌐') || error.includes('Connection failed') || error.includes('Unable to reach server')
  const isTimeoutError = error.includes('⏱️') || error.includes('timed out')

  return (
    <div className="max-w-3xl mx-auto px-4 mb-2">
      <div className="bg-red-900/50 border border-red-600 rounded-xl p-2 text-sm text-red-300">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-xs">❌</span>
            <span className="truncate text-xs">{error}</span>
          </div>
          
          <div className="flex gap-1 flex-shrink-0">
            {canRetry && onRetry && (
              <Button
                onClick={onRetry}
                variant="secondary"
                size="sm"
                className="w-6 h-6 text-xs"
                title="Retry request"
              >
                ↻
              </Button>
            )}
            {onDismiss && (
              <Button
                onClick={onDismiss}
                variant="ghost"
                size="sm"
                className="w-6 h-6 text-xs"
                title="Dismiss error"
              >
                ×
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export { ErrorDisplay }