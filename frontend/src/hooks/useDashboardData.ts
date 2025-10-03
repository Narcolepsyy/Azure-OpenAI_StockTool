/**
 * Custom hook for fetching dashboard data (quotes, news, trends, etc.)
 */

import { useState, useCallback } from 'react'
import { getToken, apiBase } from '../lib/api'
import type { Quote } from './useWebSocket'

export interface NewsArticle {
  title: string
  publisher: string
  link: string
  published: string
  thumbnail?: string
}

export interface TrendData {
  symbol: string
  period: string
  period_change_percent: number
  trend: 'strong_uptrend' | 'uptrend' | 'neutral' | 'downtrend' | 'strong_downtrend'
  sma_20: number
  sma_50?: number
  latest_price: number
}

export interface MarketIndex {
  name: string
  symbol: string
  price: number
  change: number
  changePercent: number
}

export interface JPMarketMover {
  symbol: string
  name: string
  price: number
  change_percent: number
}

export interface JPMarketMovers {
  gainers: JPMarketMover[]
  losers: JPMarketMover[]
}

interface UseDashboardDataReturn {
  quotes: Record<string, Quote>
  setQuotes: React.Dispatch<React.SetStateAction<Record<string, Quote>>>
  news: Record<string, NewsArticle[]>
  trends: Record<string, TrendData>
  marketIndices: MarketIndex[]
  jpMarketMovers: JPMarketMovers | null
  fetchInitialQuotes: (watchlist: string[]) => Promise<void>
  fetchMarketIndices: () => Promise<void>
  fetchJPMarketMovers: () => Promise<void>
}

export const useDashboardData = (user: any): UseDashboardDataReturn => {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({})
  const [news, setNews] = useState<Record<string, NewsArticle[]>>({})
  const [trends, setTrends] = useState<Record<string, TrendData>>({})
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([
    { name: 'Nikkei 225', symbol: '^N225', price: 0, change: 0, changePercent: 0 },
    { name: 'TOPIX', symbol: '^TPX', price: 0, change: 0, changePercent: 0 },
    { name: 'JPX-Nikkei 400', symbol: '1592.T', price: 0, change: 0, changePercent: 0 },
    { name: 'USD/JPY', symbol: 'JPY=X', price: 0, change: 0, changePercent: 0 }
  ])
  const [jpMarketMovers, setJpMarketMovers] = useState<JPMarketMovers | null>(null)

  const fetchInitialQuotes = useCallback(async (watchlist: string[]) => {
    if (!user) return
    
    const token = getToken()
    if (!token) return
    
    if (import.meta.env.DEV) {
      console.log('[Dashboard] Fetching initial JP stock data for:', watchlist)
    }
    
    const allNews: Record<string, NewsArticle[]> = {}
    
    for (const symbol of watchlist) {
      try {
        // Fetch quote
        const quoteResponse = await fetch(`${apiBase()}/dashboard/jp/quote/${symbol}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (quoteResponse.ok) {
          const quote = await quoteResponse.json()
          setQuotes(prev => ({ ...prev, [symbol]: quote }))
          if (import.meta.env.DEV) {
            console.log(`[Dashboard] Loaded JP quote for ${symbol}`)
          }
        }

        // Fetch news
        const newsResponse = await fetch(`${apiBase()}/dashboard/jp/news/${symbol}?limit=3`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (newsResponse.ok) {
          const newsData = await newsResponse.json()
          const articles = newsData.news || []
          if (articles.length > 0) {
            allNews[symbol] = articles
          }
        }

        // Fetch trend
        const trendResponse = await fetch(`${apiBase()}/dashboard/jp/trend/${symbol}?period=1mo`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (trendResponse.ok) {
          const trendData = await trendResponse.json()
          setTrends(prev => ({ ...prev, [symbol]: trendData }))
        }

      } catch (error) {
        if (import.meta.env.DEV) {
          console.error(`Error fetching data for ${symbol}:`, error)
        }
      }
      // Delay to avoid rate limits
      await new Promise(resolve => setTimeout(resolve, 500))
    }
    
    // Update all news at once
    setNews(allNews)
  }, [user])

  const fetchMarketIndices = useCallback(async () => {
    const indices = [
      { symbol: '^N225', name: 'Nikkei 225' },
      { symbol: '^TPX', name: 'TOPIX' },
      { symbol: '1592.T', name: 'JPX-Nikkei 400' },
      { symbol: 'JPY=X', name: 'USD/JPY' }
    ]
    const updatedIndices: MarketIndex[] = []
    
    for (const { symbol, name } of indices) {
      try {
        const response = await fetch(`${apiBase()}/dashboard/jp/quote/${symbol}`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        })
        
        if (!response.ok) {
          if (import.meta.env.DEV) {
            console.warn(`[Dashboard] Failed to fetch ${name} (${symbol}): ${response.status}`)
          }
          continue
        }
        
        const quote = await response.json()
        
        if (quote.error || !quote.current_price) {
          if (import.meta.env.DEV) {
            console.warn(`[Dashboard] Invalid data for ${name} (${symbol})`)
          }
          continue
        }
        
        updatedIndices.push({
          name,
          symbol,
          price: quote.current_price,
          change: quote.change || 0,
          changePercent: quote.percent_change || 0
        })
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error(`[Dashboard] Error fetching ${name} (${symbol}):`, error)
        }
      }
    }
    
    if (updatedIndices.length > 0) {
      setMarketIndices(updatedIndices)
    }
  }, [])

  const fetchJPMarketMovers = useCallback(async () => {
    if (!user) return
    
    const token = getToken()
    if (!token) return
    
    try {
      const response = await fetch(`${apiBase()}/dashboard/jp/market-movers?limit=5`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (!data.error) {
          setJpMarketMovers(data)
          if (import.meta.env.DEV) {
            console.log('[Dashboard] Loaded JP market movers')
          }
        } else if (import.meta.env.DEV) {
          console.warn('[Dashboard] JP market movers error:', data.error)
        }
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('[Dashboard] Error fetching JP market movers:', error)
      }
    }
  }, [user])

  return {
    quotes,
    setQuotes,
    news,
    trends,
    marketIndices,
    jpMarketMovers,
    fetchInitialQuotes,
    fetchMarketIndices,
    fetchJPMarketMovers,
  }
}
