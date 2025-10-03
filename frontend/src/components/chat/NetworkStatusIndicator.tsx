/**
 * Network status indicator component
 */

import React from 'react'
import type { NetworkStatusProps } from '../../types'

const NetworkStatusIndicator: React.FC<NetworkStatusProps> = ({
  isOnline,
  connectionQuality
}) => {
  // Only show for offline - ignore slow connection to reduce clutter
  if (isOnline) return null
  
  return (
    <div className="px-2 py-1 rounded border text-xs bg-red-900/50 border-red-600 text-red-300 flex items-center gap-1.5">
      <span>🔴</span>
      <span className="font-medium">Offline</span>
    </div>
  )
}

export { NetworkStatusIndicator }