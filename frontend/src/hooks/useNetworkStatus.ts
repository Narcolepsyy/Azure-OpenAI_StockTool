/**
 * Custom hook for managing network connection status
 */

import { useState, useEffect } from 'react'
import { apiBase, authHeaders } from '../lib/api'
import type { ConnectionQuality } from '../types'

export const useNetworkStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [connectionQuality, setConnectionQuality] = useState<ConnectionQuality>('good')

  useEffect(() => {
    let connectionCheckInterval: number | null = null
    
    const handleOnline = () => {
      setIsOnline(true)
      setConnectionQuality('good')
    }
    
    const handleOffline = () => {
      setIsOnline(false)
      setConnectionQuality('offline')
    }
    
    const checkConnectionQuality = async () => {
      if (!isOnline) return
      
      try {
        const start = Date.now()
        const timeoutController = new AbortController()
        const timeoutId = window.setTimeout(() => timeoutController.abort(), 5000)
        
        const response = await fetch(`${apiBase()}/chat/models`, { 
          method: 'HEAD',
          cache: 'no-cache',
          headers: authHeaders(),
          signal: timeoutController.signal
        })
        
        clearTimeout(timeoutId)
        const responseTime = Date.now() - start
        
        if (response.ok || response.status === 401) {
          setConnectionQuality(responseTime > 3000 ? 'poor' : 'good')
        } else {
          setConnectionQuality('poor')
        }
      } catch (error) {
        console.warn('Connection quality check failed:', error)
        setConnectionQuality('poor')
      }
    }
    
    // Set up event listeners
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    // Initial connection state
    setIsOnline(navigator.onLine)
    
    // Start periodic checks every 30 seconds when online
    if (navigator.onLine) {
      checkConnectionQuality() // Initial check
      connectionCheckInterval = window.setInterval(checkConnectionQuality, 30000)
    }
    
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      if (connectionCheckInterval) {
        window.clearInterval(connectionCheckInterval)
      }
    }
  }, [isOnline])

  return { isOnline, connectionQuality }
}