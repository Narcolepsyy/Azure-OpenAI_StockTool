/**
 * Loading spinner component
 */

import React from 'react'
import { Loader2 } from 'lucide-react'
import clsx from 'clsx'

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  label?: string
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className,
  label
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }

  return (
    <div className={clsx('flex items-center justify-center', className)}>
      <Loader2 className={clsx('animate-spin text-blue-500', sizeClasses[size])} />
      {label && (
        <span className="ml-2 text-sm text-gray-400">{label}</span>
      )}
    </div>
  )
}

export { LoadingSpinner }