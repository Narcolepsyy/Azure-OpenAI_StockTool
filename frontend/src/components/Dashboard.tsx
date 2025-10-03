/**
 * Real-time Stock Dashboard using Finnhub WebSocket
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../hooks'
import { getToken, apiBase } from '../lib/api'

interface Quote {
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
  name?: string  // For yfinance data
  currency?: string
  market_cap?: number
  pe_ratio?: number
  volume?: number
}

interface NewsArticle {
  title: string
  publisher: string
  link: string
  published: string
  thumbnail?: string
}

interface TrendData {
  symbol: string
  period: string
  period_change_percent: number
  trend: 'strong_uptrend' | 'uptrend' | 'neutral' | 'downtrend' | 'strong_downtrend'
  sma_20: number
  sma_50?: number
  latest_price: number
}

interface MarketIndex {
  name: string
  symbol: string
  price: number
  change: number
  changePercent: number
}

interface CompanyProfile {
  symbol: string
  name: string
  country?: string
  currency?: string
  exchange?: string
  industry?: string
  market_cap?: number
  logo?: string
  weburl?: string
}

interface SearchResult {
  symbol: string
  description: string
  type: string
  displaySymbol: string
  region?: string
  currency?: string
  matchScore?: string
}

interface DashboardProps {
  onStockSelect?: (symbol: string) => void
}

interface USMarketMover {
  ticker: string
  price: number
  change_amount: number
  change_percentage: string
  volume: number
}

interface USMarketMovers {
  top_gainers: USMarketMover[]
  top_losers: USMarketMover[]
  most_actively_traded: USMarketMover[]
  last_updated: string
}

interface JPMarketMover {
  symbol: string
  name: string
  price: number
  change_percent: number
}

interface JPMarketMovers {
  gainers: JPMarketMover[]
  losers: JPMarketMover[]
}

const Dashboard: React.FC<DashboardProps> = ({ onStockSelect }) => {
  const { user } = useAuth()
  const [watchlist, setWatchlist] = useState<string[]>([
    '7203.T',  // Toyota Motor
    '6758.T',  // Sony Group
    '9984.T',  // SoftBank Group
    '7974.T',  // Nintendo
    '6861.T'   // Keyence
  ])
  const [quotes, setQuotes] = useState<Record<string, Quote>>({})
  const [profiles, setProfiles] = useState<Record<string, CompanyProfile>>({})
  const [news, setNews] = useState<Record<string, NewsArticle[]>>({})
  const [trends, setTrends] = useState<Record<string, TrendData>>({})
  const [jpMarketMovers, setJpMarketMovers] = useState<JPMarketMovers | null>(null)
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([
    { name: 'Nikkei 225', symbol: '^N225', price: 0, change: 0, changePercent: 0 },
    { name: 'TOPIX', symbol: '^TPX', price: 0, change: 0, changePercent: 0 },
    { name: 'JPX-Nikkei 400', symbol: '1592.T', price: 0, change: 0, changePercent: 0 },
    { name: 'USD/JPY', symbol: 'JPY=X', price: 0, change: 0, changePercent: 0 }
  ])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showSearchModal, setShowSearchModal] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [lastUpdated, setLastUpdated] = useState<Record<string, number>>({})
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number>()
  const searchTimeoutRef = useRef<number>()

  // Search for symbols with useCallback to avoid recreating on every render
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() || !user) {
      setIsSearching(false)
      return
    }
    
    const token = getToken()
    if (!token) {
      setIsSearching(false)
      return
    }
    
    setIsSearching(true)
    try {
      const response = await fetch(`${apiBase()}/dashboard/search?q=${encodeURIComponent(searchQuery)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data.results || [])
      } else {
        console.error(`Search failed: ${response.status}`)
        setSearchResults([])
      }
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }, [searchQuery, user])

  // Real-time search with debouncing
  useEffect(() => {
    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    // Don't search if query is empty or too short
    if (!searchQuery || searchQuery.trim().length < 2) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    // Set searching state immediately for UI feedback
    setIsSearching(true)

    // Debounce: wait 500ms after user stops typing
    searchTimeoutRef.current = window.setTimeout(() => {
      handleSearch()
    }, 500)

    // Cleanup
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery, handleSearch])

  // Test API connectivity on mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await fetch(`${apiBase()}/dashboard/test`)
        if (!response.ok) {
          setErrorMessage(`API test failed: ${response.status} ${response.statusText}`)
          console.error('API test response:', response)
        } else {
          const data = await response.json()
          console.log('Dashboard API test successful:', data)
          if (!data.finnhub_configured) {
            setErrorMessage('⚠️ Finnhub API key not configured. Add FINNHUB_API_KEY to .env file.')
          }
        }
      } catch (error) {
        setErrorMessage(`Cannot reach dashboard API: ${error}`)
        console.error('Connection test error:', error)
      }
    }
    testConnection()
  }, [])

  // Fetch company profiles for watchlist
  const fetchProfiles = useCallback(async () => {
    if (!user) return
    
    const token = getToken()
    if (!token) return
    
    // Skip profile fetching for Japanese stocks (they use yfinance which includes name in quote)
    // Finnhub profiles don't work well for .T symbols
    console.log('[Dashboard] Skipping Finnhub profile fetch for Japanese stocks')
  }, [user])

  // Fetch initial quotes for all symbols
  const fetchInitialQuotes = useCallback(async () => {
    if (!user) return
    
    const token = getToken()
    if (!token) return
    
    console.log('[Dashboard] Fetching initial JP stock data for:', watchlist)
    
    // Create an array to hold all news articles
    const allNews: Record<string, NewsArticle[]> = {}
    
    for (const symbol of watchlist) {
      try {
        // Fetch quote
        const quoteResponse = await fetch(`${apiBase()}/dashboard/jp/quote/${symbol}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (quoteResponse.ok) {
          const quote = await quoteResponse.json()
          setQuotes(prev => ({ ...prev, [symbol]: quote }))
          setLastUpdated(prev => ({ ...prev, [symbol]: Date.now() }))
          console.log(`[Dashboard] Loaded JP quote for ${symbol}:`, quote)
        }

        // Fetch news
        const newsResponse = await fetch(`${apiBase()}/dashboard/jp/news/${symbol}?limit=3`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (newsResponse.ok) {
          const newsData = await newsResponse.json()
          const articles = newsData.news || []
          console.log(`[Dashboard] Raw news response for ${symbol}:`, newsData)
          console.log(`[Dashboard] Parsed articles for ${symbol}:`, articles)
          if (articles.length > 0) {
            allNews[symbol] = articles
          }
          console.log(`[Dashboard] Loaded news for ${symbol}:`, articles.length, 'articles')
        } else {
          console.error(`[Dashboard] News fetch failed for ${symbol}:`, newsResponse.status, newsResponse.statusText)
        }

        // Fetch trend
        const trendResponse = await fetch(`${apiBase()}/dashboard/jp/trend/${symbol}?period=1mo`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (trendResponse.ok) {
          const trendData = await trendResponse.json()
          setTrends(prev => ({ ...prev, [symbol]: trendData }))
          console.log(`[Dashboard] Loaded trend for ${symbol}:`, trendData.trend)
        }

      } catch (error) {
        console.error(`Error fetching data for ${symbol}:`, error)
      }
      // Delay to avoid rate limits
      await new Promise(resolve => setTimeout(resolve, 500))
    }
    
    // Update all news at once
    setNews(allNews)
    console.log('[Dashboard] Total news loaded:', Object.keys(allNews).length, 'stocks with news')
  }, [watchlist, user])

  // Fetch market indices
  const fetchMarketIndices = useCallback(async () => {
    const indices = [
      { symbol: '^N225', name: 'Nikkei 225' },
      { symbol: '^TPX', name: 'TOPIX' },
      { symbol: '1592.T', name: 'JPX-Nikkei 400' },  // ETF tracking JPX-Nikkei 400
      { symbol: 'JPY=X', name: 'USD/JPY' }
    ]
    const updatedIndices: MarketIndex[] = []
    
    for (const { symbol, name } of indices) {
      try {
        const response = await fetch(`${apiBase()}/dashboard/jp/quote/${symbol}`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        })
        
        if (!response.ok) {
          console.warn(`[Dashboard] Failed to fetch ${name} (${symbol}): ${response.status}`)
          continue
        }
        
        const quote = await response.json()
        
        // Check if we got valid data
        if (quote.error || !quote.current_price) {
          console.warn(`[Dashboard] Invalid data for ${name} (${symbol}):`, quote)
          continue
        }
        
        updatedIndices.push({
          name,
          symbol,
          price: quote.current_price,
          change: quote.change || 0,
          changePercent: quote.percent_change || 0
        })
        
        console.log(`[Dashboard] ✓ Fetched ${name} (${symbol}): ¥${quote.current_price.toLocaleString()}`)
      } catch (error) {
        console.error(`[Dashboard] Error fetching ${name} (${symbol}):`, error)
      }
    }
    
    if (updatedIndices.length > 0) {
      setMarketIndices(updatedIndices)
    }
  }, [])

  // Fetch Japanese market movers
  const fetchJPMarketMovers = useCallback(async () => {
    if (!user) return
    
    const token = getToken()
    if (!token) return
    
    try {
      const response = await fetch(`${apiBase()}/dashboard/jp/market-movers?limit=5`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (!data.error) {
          setJpMarketMovers(data)
          console.log('[Dashboard] Loaded JP market movers:', data)
        } else {
          console.warn('[Dashboard] JP market movers error:', data.error)
        }
      }
    } catch (error) {
      console.error('[Dashboard] Error fetching JP market movers:', error)
    }
  }, [user])

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    if (!user) {
      console.log('Cannot connect WebSocket: user not logged in')
      return
    }

    // Don't reconnect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected, skipping reconnection')
      return
    }

    // Close existing connection if any (only if not already open)
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      console.log('Closing existing WebSocket connection')
      wsRef.current.close()
      wsRef.current = null
    }

    // Determine WebSocket URL - must use backend server, not frontend dev server
    const base = apiBase()
    console.log('[Dashboard] API base from apiBase():', base)
    console.log('[Dashboard] window.location.origin:', window.location.origin)
    console.log('[Dashboard] import.meta.env.DEV:', import.meta.env.DEV)
    
    // BUGFIX: If apiBase() returns the frontend dev server (localhost:5173),
    // force it to use the backend server instead
    let backendBase = base
    if (backendBase.includes('localhost:5173') || backendBase.includes('5173')) {
      console.warn('[Dashboard] apiBase() returned frontend URL, forcing backend URL')
      backendBase = 'http://127.0.0.1:8000'
    }
    
    const protocol = backendBase.startsWith('https') ? 'wss:' : 'ws:'
    const host = backendBase.replace(/^https?:\/\//, '')
    const wsUrl = `${protocol}//${host}/dashboard/ws`
    
    console.log('[Dashboard] Final WebSocket URL:', wsUrl)
    setWsStatus('connecting')
    
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected successfully')
        setWsStatus('connected')
        setErrorMessage('') // Clear any previous errors
        
        // Get current watchlist (don't rely on closure)
        const currentWatchlist = watchlist
        // Subscribe to watchlist symbols
        ws.send(JSON.stringify({
          action: 'subscribe',
          symbols: currentWatchlist
        }))
        console.log('Subscribed to symbols:', currentWatchlist)
      }

      ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'quote_update') {
          const quote = data.data as Quote
          setQuotes(prev => ({
            ...prev,
            [quote.symbol]: quote
          }))
          // Track last update time
          setLastUpdated(prev => ({
            ...prev,
            [quote.symbol]: Date.now()
          }))
        } else if (data.type === 'subscribed') {
          console.log('Subscribed to:', data.symbols)
          if (data.message) {
            // Show rate limit info
            console.info('Rate limit info:', data.message)
          }
        } else if (data.type === 'rate_limit_warning') {
          setErrorMessage(data.message || 'Rate limit reached. Updates paused.')
          console.warn('Rate limit warning:', data.message)
        } else if (data.type === 'error') {
          console.error('WebSocket error:', data.message)
          setErrorMessage(data.message)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setWsStatus('disconnected')
        setErrorMessage('Failed to connect to real-time updates')
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason)
        setWsStatus('disconnected')
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          console.log('Attempting to reconnect...')
          connectWebSocket()
        }, 3000)
      }
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
      setWsStatus('disconnected')
      setErrorMessage('Could not establish WebSocket connection')
    }
  }, [user]) // Only reconnect when user changes, not watchlist

  // Subscribe to new symbol
  const subscribeToSymbol = useCallback((symbol: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        symbols: [symbol]
      }))
    }
  }, [])

  // Unsubscribe from symbol
  const unsubscribeFromSymbol = useCallback((symbol: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'unsubscribe',
        symbols: [symbol]
      }))
    }
  }, [])

  // Add symbol to watchlist
  const addToWatchlist = (symbol: string) => {
    if (!watchlist.includes(symbol)) {
      setWatchlist(prev => [...prev, symbol])
      subscribeToSymbol(symbol)
      setSearchQuery('')
      setSearchResults([])
    }
  }

  // Remove symbol from watchlist
  const removeFromWatchlist = (symbol: string) => {
    setWatchlist(prev => prev.filter(s => s !== symbol))
    unsubscribeFromSymbol(symbol)
    setQuotes(prev => {
      const { [symbol]: _, ...rest } = prev
      return rest
    })
  }

  // Initialize dashboard and set up polling
  useEffect(() => {
    if (!user) return
    
    console.log('[Dashboard] Initializing JP dashboard for user:', user.username)
    
    // Ensure any existing WebSocket is closed
    if (wsRef.current) {
      console.log('[Dashboard] Closing any existing WebSocket connection')
      wsRef.current.close()
      wsRef.current = null
    }
    
    fetchInitialQuotes() // Load initial data immediately
    fetchMarketIndices() // Load market indices
    fetchJPMarketMovers() // Load Japanese market movers
    fetchProfiles()

    // Set up polling for updates (every 30 seconds to avoid rate limits)
    const pollInterval = setInterval(() => {
      console.log('[Dashboard] Polling for updates...')
      fetchInitialQuotes()
      fetchMarketIndices()
      fetchJPMarketMovers()
    }, 30000) // 30 seconds

    return () => {
      console.log('[Dashboard] Cleaning up dashboard')
      clearInterval(pollInterval)
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]) // Only run when user changes, not on every function recreation

  // Update subscriptions when watchlist changes
  // DISABLED: Japanese dashboard uses polling instead of WebSocket
  useEffect(() => {
    // No WebSocket updates needed for Japanese stocks
    console.log('[Dashboard] Watchlist updated:', watchlist)
  }, [watchlist])

  // Format price based on symbol (Japanese stocks get ¥, others get $)
  const formatPrice = (price?: number, symbol?: string) => {
    if (price == null) return 'N/A'
    
    // Check if it's a Japanese stock (.T suffix) or Japanese index
    const isJapanese = symbol?.endsWith('.T') || 
                       symbol?.startsWith('^N') || 
                       symbol?.startsWith('^TPX') || 
                       symbol === '1592.T' ||
                       symbol === 'JPY=X'
    
    if (isJapanese && symbol !== 'JPY=X') {
      // Japanese stocks: format with yen symbol
      return `¥${price.toLocaleString('ja-JP', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    } else if (symbol === 'JPY=X') {
      // USD/JPY exchange rate
      return `¥${price.toFixed(2)}`
    } else {
      // US stocks: format with dollar symbol
      return `$${price.toFixed(2)}`
    }
  }

  const formatPercent = (percent?: number) => {
    if (percent == null) return 'N/A'
    const sign = percent >= 0 ? '+' : ''
    return `${sign}${percent.toFixed(2)}%`
  }

  const getChangeColor = (change?: number) => {
    if (change == null) return 'text-gray-400'
    return change >= 0 ? 'text-green-400' : 'text-red-400'
  }

  const getTimeSinceUpdate = (symbol: string): string => {
    const lastUpdate = lastUpdated[symbol]
    if (!lastUpdate) return 'Never'
    
    const seconds = Math.floor((Date.now() - lastUpdate) / 1000)
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    return `${minutes}m ago`
  }

  // Get company favicon using Google's favicon service
  const getCompanyFavicon = (symbol: string): string => {
    // Map of known Japanese company domains
    const companyDomains: Record<string, string> = {
      '7203.T': 'toyota.com',        // Toyota
      '6758.T': 'sony.com',           // Sony
      '9984.T': 'softbank.jp',        // SoftBank
      '7974.T': 'nintendo.com',       // Nintendo
      '6861.T': 'keyence.com',        // Keyence
      '4063.T': 'shinetsu.co.jp',     // Shin-Etsu
      '8306.T': 'mufg.jp',            // MUFG
      '9432.T': 'ntt.co.jp',          // NTT
      '6902.T': 'denso.com',          // Denso
      '6501.T': 'hitachi.com',        // Hitachi
    }
    
    const domain = companyDomains[symbol]
    if (domain) {
      // Use Google's favicon service
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
    }
    
    // Fallback: return empty to show placeholder
    return ''
  }

  // Generate a colored avatar based on company name
  const getAvatarColor = (name: string): string => {
    const colors: string[] = [
      'from-blue-500 to-blue-600',
      'from-green-500 to-green-600',
      'from-purple-500 to-purple-600',
      'from-pink-500 to-pink-600',
      'from-indigo-500 to-indigo-600',
      'from-red-500 to-red-600',
      'from-yellow-500 to-yellow-600',
      'from-teal-500 to-teal-600',
    ]
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    const colorIndex = hash % colors.length
    return colors[colorIndex] || 'from-blue-500 to-blue-600'
  }

  // Generate mini chart path based on change percentage
  const generateMiniChartPath = (changePercent: number) => {
    // Create a more dynamic path with some variation
    const isPositive = changePercent >= 0
    const volatility = Math.abs(changePercent) * 2 // Add some volatility based on change
    
    if (isPositive) {
      // Uptrend with variation
      return `M 0 35 L 15 ${35 - volatility} L 30 ${32 - volatility} L 45 ${28 - volatility * 1.5} L 60 ${25 - volatility * 2} L 80 ${20 - volatility * 2.5}`
    } else {
      // Downtrend with variation
      return `M 0 20 L 15 ${20 + volatility} L 30 ${23 + volatility} L 45 ${27 + volatility * 1.5} L 60 ${30 + volatility * 2} L 80 ${35 + volatility * 2.5}`
    }
  }

  const generateMiniChartFill = (changePercent: number) => {
    const path = generateMiniChartPath(changePercent)
    return `${path} L 80 40 L 0 40 Z`
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white overflow-x-hidden">
      {/* Top Navigation Bar with Market Indices */}
      <div className="bg-gray-950 border-b border-gray-800 sticky top-0 z-10">
        <div className="max-w-[1920px] mx-auto px-6 py-3">
          <div className="grid grid-cols-4 gap-8">
            {marketIndices.map((index) => (
              <div key={index.symbol} className="flex items-center gap-4">
                {/* Mini Chart Indicator */}
                <div className="flex-shrink-0 w-20 h-12 bg-gray-900 rounded-lg p-2">
                  <svg className="w-full h-full" viewBox="0 0 80 40" preserveAspectRatio="none">
                    {/* Chart line */}
                    <path
                      d={generateMiniChartPath(index.changePercent)}
                      fill="none"
                      stroke={index.changePercent >= 0 ? "#10b981" : "#ef4444"}
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    {/* Fill area */}
                    <path
                      d={generateMiniChartFill(index.changePercent)}
                      fill={index.changePercent >= 0 ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)"}
                    />
                  </svg>
                </div>
                
                {/* Index Info */}
                <div className="flex flex-col">
                  <div className="text-xs text-gray-500 mb-1">{index.name}</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-lg font-semibold">{index.price.toLocaleString('ja-JP', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    <span className={`text-sm ${index.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {index.changePercent >= 0 ? '▲' : '▼'} {Math.abs(index.changePercent).toFixed(2)}%
                    </span>
                  </div>
                  <div className={`text-xs ${index.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {index.change >= 0 ? '+' : ''}{index.change.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-gray-900 border-b border-gray-800">
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <div className="relative max-w-2xl">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              {isSearching ? (
                <svg className="animate-spin h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              )}
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch()
              }}
              placeholder="Search stocks by symbol or name (e.g., 7203.T for Toyota, AAPL for Apple)..."
              className="w-full pl-12 pr-12 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            {searchQuery && (
              <div className="absolute inset-y-0 right-0 pr-4 flex items-center gap-2">
                {searchQuery.trim().length >= 2 && (
                  <span className="text-xs text-gray-500">
                    {isSearching ? 'Searching...' : `${searchResults.length} result${searchResults.length !== 1 ? 's' : ''}`}
                  </span>
                )}
                <button
                  onClick={() => {
                    setSearchQuery('')
                    setSearchResults([])
                  }}
                  className="text-gray-400 hover:text-white transition-colors"
                  title="Clear search"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
          </div>
          
          {/* Search Results Dropdown */}
          {searchResults.length > 0 && (
            <div className="mt-2 max-w-2xl bg-gray-800 border border-gray-700 rounded-lg shadow-lg overflow-hidden animate-fadeIn">
              <div className="px-4 py-2 bg-gray-750 border-b border-gray-700">
                <span className="text-xs text-gray-400">
                  Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} - Click to add to watchlist
                </span>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {searchResults.map((result, index) => (
                  <button
                    key={result.symbol}
                    onClick={() => {
                      addToWatchlist(result.symbol)
                      setSearchQuery('')
                      setSearchResults([])
                    }}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-700 transition-colors border-b border-gray-700 last:border-b-0 group"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className="flex flex-col items-start">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white group-hover:text-blue-400 transition-colors">
                          {result.displaySymbol || result.symbol}
                        </span>
                        {result.region && (
                          <span className="text-xs px-2 py-0.5 bg-gray-700 rounded text-gray-400">
                            {result.region}
                          </span>
                        )}
                      </div>
                      <span className="text-sm text-gray-400">{result.description}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{result.type}</span>
                      <svg className="h-5 w-5 text-green-400 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* No Results Message */}
          {searchQuery.trim().length >= 2 && !isSearching && searchResults.length === 0 && (
            <div className="mt-2 max-w-2xl bg-gray-800 border border-gray-700 rounded-lg shadow-lg p-4 text-center">
              <svg className="h-12 w-12 text-gray-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-gray-400 text-sm">No results found for "{searchQuery}"</p>
              <p className="text-gray-500 text-xs mt-1">Try a different stock symbol or company name</p>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[1920px] mx-auto px-6 py-6 h-[calc(100vh-240px)] overflow-y-auto">
        <div className="grid grid-cols-12 gap-6">
          {/* Left: Main Content (Col-span 9) */}
          <div className="col-span-9 space-y-6">
            {/* Market Summary Section */}
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Market Summary</h2>
                <span className="text-sm text-gray-400">Updated {new Date().toLocaleTimeString('ja-JP')}</span>
              </div>
              
              {/* Market News/Headlines from watchlist stocks */}
              <div className="space-y-4 max-h-[calc(100vh-280px)] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-800">
                {watchlist.map((symbol) => {
                  const stockNews = news[symbol] || []
                  const quote = quotes[symbol]
                  
                  return stockNews.length > 0 ? (
                    <div key={symbol} className="space-y-3 mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-sm font-semibold text-blue-400">{quote?.name || symbol}</span>
                        <span className="text-xs text-gray-500">•</span>
                        <span className="text-xs text-gray-500">{symbol}</span>
                      </div>
                      {stockNews.slice(0, 2).map((article, idx) => (
                        <a
                          key={idx}
                          href={article.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block pb-4 border-b border-gray-700 last:border-b-0 hover:bg-gray-700/30 rounded p-3 transition-colors"
                        >
                          <div className="flex gap-4">
                            {article.thumbnail && (
                              <img
                                src={article.thumbnail}
                                alt={article.title}
                                className="w-24 h-24 object-cover rounded flex-shrink-0"
                                onError={(e) => {
                                  (e.target as HTMLImageElement).style.display = 'none'
                                }}
                              />
                            )}
                            <div className="flex-1">
                              <h3 className="font-semibold text-base mb-2 text-white hover:text-blue-400 transition-colors line-clamp-2">
                                {article.title}
                              </h3>
                              <div className="flex items-center gap-2 text-xs text-gray-400">
                                <span>{article.publisher}</span>
                                <span>•</span>
                                <span>{new Date(article.published).toLocaleDateString('ja-JP', { 
                                  year: 'numeric',
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}</span>
                              </div>
                            </div>
                          </div>
                        </a>
                      ))}
                    </div>
                  ) : null
                })}
                
                {/* Show placeholder if no news loaded */}
                {watchlist.every(symbol => (news[symbol] || []).length === 0) && (
                  <div className="text-center py-12 text-gray-400">
                    <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                    </svg>
                    <p className="text-lg">Loading market news...</p>
                    <p className="text-sm text-gray-500 mt-2">News articles will appear here once loaded</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Sidebar: Watchlist & Gainers/Losers */}
          <div className="col-span-3 space-y-4 h-[calc(100vh-120px)] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-800">
            {/* Create Watchlist Header */}
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-bold">Create Watchlist</h3>
                <button 
                  onClick={() => {
                    setShowSearchModal(true)
                    setSearchQuery('')
                    setSearchResults([])
                  }}
                  className="text-gray-400 hover:text-white transition-colors"
                  title="Add stock"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>
              
              {/* Compact Watchlist */}
              <div className="space-y-1">
                {watchlist.map((symbol, idx) => {
                  const quote = quotes[symbol]
                  const faviconUrl = getCompanyFavicon(symbol)
                  const companyName = quote?.name || symbol
                  
                  return (
                    <div
                      key={symbol}
                      className="flex items-center gap-3 py-2.5 px-2 hover:bg-gray-700/50 rounded transition-colors group cursor-pointer"
                      onClick={() => onStockSelect?.(symbol)}
                    >
                      {/* Company Logo/Favicon */}
                      <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center overflow-hidden bg-white">
                        {faviconUrl ? (
                          <img
                            src={faviconUrl}
                            alt={companyName}
                            className="w-full h-full object-contain p-1"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement
                              target.style.display = 'none'
                              if (target.parentElement) {
                                target.parentElement.className = `flex-shrink-0 w-9 h-9 bg-gradient-to-br ${getAvatarColor(companyName)} rounded-lg flex items-center justify-center`
                                target.parentElement.innerHTML = `<span class="text-sm font-bold text-white">${companyName.charAt(0).toUpperCase()}</span>`
                              }
                            }}
                          />
                        ) : (
                          <div className={`w-full h-full bg-gradient-to-br ${getAvatarColor(companyName)} flex items-center justify-center`}>
                            <span className="text-sm font-bold text-white">{companyName.charAt(0).toUpperCase()}</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Company Info */}
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm truncate text-white">{quote?.name || symbol}</div>
                        <div className="text-xs text-gray-400">{symbol.replace('.T', '')} · TSE</div>
                      </div>
                      
                      {/* Price Info */}
                      <div className="text-right flex-shrink-0">
                        <div className="text-sm font-semibold text-white">
                          ¥{quote?.current_price?.toLocaleString('ja-JP', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '-'}
                        </div>
                        <div className={`text-xs font-medium ${quote?.change && quote.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {quote?.percent_change != null ? `${quote.percent_change >= 0 ? '+' : ''}${quote.percent_change.toFixed(2)}%` : '-'}
                        </div>
                      </div>
                      
                      {/* Arrow indicator (shows on hover) */}
                      <div className="flex-shrink-0 w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Gainers - Japanese stocks */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-sm font-bold mb-3 text-green-400">Top Gainers (JP)</h3>
              <div className="space-y-2 text-xs">
                {jpMarketMovers && jpMarketMovers.gainers?.length > 0 ? (
                  jpMarketMovers.gainers.map((stock, idx) => (
                    <div 
                      key={idx} 
                      className="flex justify-between py-1 hover:bg-gray-700/50 rounded px-2 cursor-pointer transition-colors"
                      onClick={() => onStockSelect?.(stock.symbol)}
                    >
                      <div>
                        <div className="font-medium">{stock.name}</div>
                        <div className="text-gray-500 text-[10px]">{stock.symbol}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-green-400">{stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%</div>
                        <div className="font-medium text-gray-300">¥{stock.price.toLocaleString('ja-JP')}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  // Loading or no data
                  <div className="text-center py-4 text-gray-500">
                    Loading...
                  </div>
                )}
              </div>
            </div>

            {/* Losers - Japanese stocks */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-sm font-bold mb-3 text-red-400">Top Losers (JP)</h3>
              <div className="space-y-2 text-xs">
                {jpMarketMovers && jpMarketMovers.losers?.length > 0 ? (
                  jpMarketMovers.losers.map((stock, idx) => (
                    <div 
                      key={idx} 
                      className="flex justify-between py-1 hover:bg-gray-700/50 rounded px-2 cursor-pointer transition-colors"
                      onClick={() => onStockSelect?.(stock.symbol)}
                    >
                      <div>
                        <div className="font-medium">{stock.name}</div>
                        <div className="text-gray-500 text-[10px]">{stock.symbol}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-red-400">{stock.change_percent.toFixed(2)}%</div>
                        <div className="font-medium text-gray-300">¥{stock.price.toLocaleString('ja-JP')}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  // Loading or no data
                  <div className="text-center py-4 text-gray-500">
                    Loading...
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search Modal */}
      {showSearchModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl border border-gray-700">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-white">Finance</h2>
              <p className="text-sm text-gray-400 mt-1">Set your watchlist for daily updates and summaries</p>
            </div>

            {/* Search Input */}
            <div className="px-6 py-4 border-b border-gray-700">
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSearch()
                    if (e.key === 'Escape') setShowSearchModal(false)
                  }}
                  placeholder="Search..."
                  className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                  autoFocus
                />
              </div>
            </div>

            {/* Search Results */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {isSearching ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-gray-400">Searching...</div>
                </div>
              ) : searchResults.length > 0 ? (
                <div className="space-y-2">
                  {searchResults.map((result) => (
                    <div
                      key={result.symbol}
                      className="flex items-center gap-3 p-3 hover:bg-gray-800 rounded-lg cursor-pointer transition-colors group"
                      onClick={() => {
                        addToWatchlist(result.symbol)
                      }}
                    >
                      {/* Drag Handle */}
                      <div className="text-gray-600">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
                        </svg>
                      </div>

                      {/* Company Logo/Favicon */}
                      <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center overflow-hidden bg-white">
                        {getCompanyFavicon(result.symbol) ? (
                          <img
                            src={getCompanyFavicon(result.symbol)}
                            alt={result.displaySymbol}
                            className="w-full h-full object-contain p-1"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement
                              target.style.display = 'none'
                              if (target.parentElement) {
                                target.parentElement.className = `flex-shrink-0 w-10 h-10 bg-gradient-to-br ${getAvatarColor(result.description)} rounded-lg flex items-center justify-center`
                                target.parentElement.innerHTML = `<span class="text-sm font-bold text-white">${result.displaySymbol.charAt(0).toUpperCase()}</span>`
                              }
                            }}
                          />
                        ) : (
                          <div className={`w-full h-full bg-gradient-to-br ${getAvatarColor(result.description)} flex items-center justify-center`}>
                            <span className="text-sm font-bold text-white">{result.displaySymbol.charAt(0).toUpperCase()}</span>
                          </div>
                        )}
                      </div>

                      {/* Company Info */}
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-white">{result.displaySymbol}</div>
                        <div className="text-sm text-gray-400 truncate">{result.description}</div>
                      </div>

                      {/* Remove Button */}
                      {watchlist.includes(result.symbol) ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            removeFromWatchlist(result.symbol)
                          }}
                          className="flex-shrink-0 text-gray-400 hover:text-red-400 transition-colors"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      ) : (
                        <div className="w-5 h-5"></div>
                      )}
                    </div>
                  ))}
                </div>
              ) : searchQuery ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <svg className="w-12 h-12 text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p className="text-gray-400">No results found</p>
                  <p className="text-sm text-gray-500 mt-1">Try searching for a different stock symbol</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <svg className="w-12 h-12 text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p className="text-gray-400">Search for stocks to add</p>
                  <p className="text-sm text-gray-500 mt-1">Enter a company name or symbol (e.g., 7203.T for Toyota)</p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-700 flex justify-end">
              <button
                onClick={() => {
                  setShowSearchModal(false)
                  setSearchQuery('')
                  setSearchResults([])
                }}
                className="px-6 py-2.5 bg-white text-gray-900 font-semibold rounded-lg hover:bg-gray-100 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
