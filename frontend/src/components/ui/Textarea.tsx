/**
 * Textarea component with auto-resize functionality
 */

import React, { useEffect, useRef } from 'react'
import clsx from 'clsx'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  helperText?: string
  autoResize?: boolean
  maxHeight?: number
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({
  className,
  label,
  error,
  helperText,
  autoResize = false,
  maxHeight = 200,
  id,
  ...props
}, ref) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const inputId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`

  // Auto-resize functionality
  useEffect(() => {
    if (!autoResize) return
    
    const textarea = textareaRef.current || (ref as React.RefObject<HTMLTextAreaElement>)?.current
    if (!textarea) return

    const handleResize = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`
    }

    textarea.addEventListener('input', handleResize)
    handleResize() // Initial resize

    return () => {
      textarea.removeEventListener('input', handleResize)
    }
  }, [autoResize, maxHeight, ref, props.value])

  return (
    <div className="space-y-1">
      {label && (
        <label 
          htmlFor={inputId} 
          className="block text-sm font-medium text-gray-300"
        >
          {label}
        </label>
      )}
      <textarea
        ref={ref || textareaRef}
        id={inputId}
        className={clsx(
          'w-full px-3 py-2 bg-gray-700 border rounded-md text-white placeholder-gray-400',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          'transition-colors duration-200',
          autoResize && 'resize-none overflow-hidden',
          error 
            ? 'border-red-500 focus:ring-red-500' 
            : 'border-gray-600',
          className
        )}
        style={autoResize ? { maxHeight } : undefined}
        {...props}
      />
      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-sm text-gray-400">{helperText}</p>
      )}
    </div>
  )
})

Textarea.displayName = 'Textarea'

export { Textarea }