/**
 * Input component with consistent styling
 */

import React from 'react'
import clsx from 'clsx'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(({
  className,
  label,
  error,
  helperText,
  id,
  ...props
}, ref) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`

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
      <input
        ref={ref}
        id={inputId}
        className={clsx(
          'w-full px-3 py-2 bg-gray-700 border rounded-md text-white placeholder-gray-400',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          'focus:bg-gray-700',
          'transition-colors duration-200',
          'autofill:bg-gray-700 autofill:text-white',
          '[&:-webkit-autofill]:bg-gray-700 [&:-webkit-autofill]:text-white',
          '[&:-webkit-autofill]:[-webkit-text-fill-color:white]',
          '[&:-webkit-autofill]:[-webkit-box-shadow:0_0_0px_1000px_rgb(55,65,81)_inset]',
          error 
            ? 'border-red-500 focus:ring-red-500' 
            : 'border-gray-600',
          className
        )}
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

Input.displayName = 'Input'

export { Input }