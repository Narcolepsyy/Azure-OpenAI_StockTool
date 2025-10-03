/**
 * Custom hook for WebSocket connection management
 */

import { useRef, useCallback, useState, useEffect } from 'react'
import { apiBase } from '../lib/api'

export interface Quote {
  symbol: string
  current_price: number
  change: number
  percent_change: number
  high: number
  low: number
  open: number
  previous_close: number
  timestamp?: number
  datetime?: string
  error?: string
  name?: string
  currency?: string
  market_cap?: number
  pe_ratio?: number
  volume?: number
}

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected'

interface WebSocketMessage {
  type: string
  data?: Quote
  symbols?: string[]
  message?: string
}

interface UseWebSocketReturn {
  wsStatus: WebSocketStatus
  quotes: Record<string, Quote>
  lastUpdated: Record<string, number>
  connect: () => void
  disconnect: () => void
  subscribe: (symbols: string[]) => void
}

export const useWebSocket = (watchlist: string[], user: any): UseWebSocketReturn => {
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>('disconnected')
  const [quotes, setQuotes] = useState<Record<string, Quote>>({})
  const [lastUpdated, setLastUpdated] = useState<Record<string, number>>({})
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number>()

  const connect = useCallback(() => {
    if (!user) {
      if (import.meta.env.DEV) {
        console.log('Cannot connect WebSocket: user not logged in')
      }
      return
    }

    // Don't reconnect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      if (import.meta.env.DEV) {
        console.log('WebSocket already connected, skipping reconnection')
      }
      return
    }

    // Close existing connection if any
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      if (import.meta.env.DEV) {
        console.log('Closing existing WebSocket connection')
      }
      wsRef.current.close()
      wsRef.current = null
    }

    // Determine WebSocket URL
    const base = apiBase()
    let backendBase = base
    
    // Ensure we're using the backend server
    if (backendBase.includes('localhost:5173') || backendBase.includes('5173')) {
      if (import.meta.env.DEV) {
        console.warn('[WebSocket] apiBase() returned frontend URL, forcing backend URL')
      }
      backendBase = 'http://127.0.0.1:8000'
    }
    
    const protocol = backendBase.startsWith('https') ? 'wss:' : 'ws:'
    const host = backendBase.replace(/^https?:\/\//, '')
    const wsUrl = `${protocol}//${host}/dashboard/ws`
    
    if (import.meta.env.DEV) {
      console.log('[WebSocket] Connecting to:', wsUrl)
    }
    
    setWsStatus('connecting')
    
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (import.meta.env.DEV) {
          console.log('WebSocket connected successfully')
        }
        setWsStatus('connected')
        
        // Subscribe to watchlist symbols
        ws.send(JSON.stringify({
          action: 'subscribe',
          symbols: watchlist
        }))
        if (import.meta.env.DEV) {
          console.log('Subscribed to symbols:', watchlist)
        }
      }

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          
          if (data.type === 'quote_update' && data.data) {
            const quote = data.data
            setQuotes(prev => ({
              ...prev,
              [quote.symbol]: quote
            }))
            setLastUpdated(prev => ({
              ...prev,
              [quote.symbol]: Date.now()
            }))
          } else if (data.type === 'subscribed') {
            if (import.meta.env.DEV) {
              console.log('Subscribed to:', data.symbols)
            }
          } else if (data.type === 'error') {
            if (import.meta.env.DEV) {
              console.error('WebSocket error:', data.message)
            }
          }
        } catch (error) {
          if (import.meta.env.DEV) {
            console.error('Error parsing WebSocket message:', error)
          }
        }
      }

      ws.onerror = (error) => {
        if (import.meta.env.DEV) {
          console.error('WebSocket error:', error)
        }
        setWsStatus('disconnected')
      }

      ws.onclose = (event) => {
        if (import.meta.env.DEV) {
          console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason)
        }
        setWsStatus('disconnected')
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (import.meta.env.DEV) {
            console.log('Attempting to reconnect...')
          }
          connect()
        }, 3000)
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Error creating WebSocket connection:', error)
      }
      setWsStatus('disconnected')
    }
  }, [user, watchlist])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setWsStatus('disconnected')
  }, [])

  const subscribe = useCallback((symbols: string[]) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        symbols
      }))
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    wsStatus,
    quotes,
    lastUpdated,
    connect,
    disconnect,
    subscribe,
  }
}
