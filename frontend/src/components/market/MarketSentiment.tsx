/**
 * Market Sentiment Indicator Component
 * Displays real-time market sentiment in the top-right corner
 * Similar to Perplexity's market status indicator
 */

import React, { useEffect, useState, useCallback } from 'react'
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react'
import { getToken, apiBase } from '../../lib/api'

interface MarketSentimentData {
  sentiment: 'bullish' | 'bearish' | 'neutral'
  sentiment_score: number
  confidence: 'high' | 'medium' | 'low'
  article_count?: number
  bullish_count?: number
  bearish_count?: number
  neutral_count?: number
  last_updated: string
  error?: string
}

interface MarketSentimentProps {
  className?: string
  autoRefresh?: boolean
  refreshInterval?: number
}

export const MarketSentiment: React.FC<MarketSentimentProps> = ({
  className = '',
  autoRefresh = true,
  refreshInterval = 300000, // 5 minutes default
}) => {
  const [sentiment, setSentiment] = useState<MarketSentimentData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSentiment = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setError('Not authenticated')
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch(`${apiBase()}/dashboard/market/sentiment`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data: MarketSentimentData = await response.json()
      setSentiment(data)
      setError(data.error || null)
      setIsLoading(false)
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('Error fetching market sentiment:', err)
      }
      setError('Failed to load')
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSentiment()

    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchSentiment, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [fetchSentiment, autoRefresh, refreshInterval])

  const getSentimentColor = (sentimentType: string) => {
    switch (sentimentType) {
      case 'bullish':
        return 'text-green-400'
      case 'bearish':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  const getSentimentBgColor = (sentimentType: string) => {
    switch (sentimentType) {
      case 'bullish':
        return 'bg-green-500/10 border-green-500/30'
      case 'bearish':
        return 'bg-red-500/10 border-red-500/30'
      default:
        return 'bg-gray-500/10 border-gray-500/30'
    }
  }

  const getSentimentIcon = (sentimentType: string) => {
    switch (sentimentType) {
      case 'bullish':
        return <TrendingUp className="w-3.5 h-3.5" />
      case 'bearish':
        return <TrendingDown className="w-3.5 h-3.5" />
      default:
        return <Minus className="w-3.5 h-3.5" />
    }
  }

  const getSentimentLabel = (sentimentType: string) => {
    switch (sentimentType) {
      case 'bullish':
        return 'Bullish'
      case 'bearish':
        return 'Bearish'
      default:
        return 'Neutral'
    }
  }

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 px-3 py-1.5 bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-full ${className}`}>
        <div className="w-3 h-3 border-2 border-gray-600 border-t-gray-400 rounded-full animate-spin" />
        <span className="text-xs text-gray-400 font-medium">Market</span>
      </div>
    )
  }

  if (error && !sentiment) {
    return (
      <div className={`flex items-center space-x-2 px-3 py-1.5 bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-full ${className}`}>
        <AlertCircle className="w-3.5 h-3.5 text-gray-500" />
        <span className="text-xs text-gray-500 font-medium">Market</span>
      </div>
    )
  }

  if (!sentiment) return null

  const colorClass = getSentimentColor(sentiment.sentiment)
  const bgClass = getSentimentBgColor(sentiment.sentiment)
  const icon = getSentimentIcon(sentiment.sentiment)
  const label = getSentimentLabel(sentiment.sentiment)

  return (
    <div
      className={`group relative flex items-center space-x-2 px-3 py-1.5 backdrop-blur-sm border rounded-full transition-all duration-200 hover:scale-105 cursor-pointer ${bgClass} ${className}`}
      title={`Market Sentiment: ${label} (${sentiment.article_count || 0} articles)`}
    >
      {/* Icon */}
      <div className={`${colorClass} transition-transform group-hover:scale-110`}>
        {icon}
      </div>

      {/* Status Text */}
      <div className="flex items-center space-x-1.5">
        <span className="text-xs text-gray-300 font-medium">Market</span>
        <span className={`text-xs font-semibold ${colorClass}`}>
          {label}
        </span>
      </div>

      {/* Confidence Indicator */}
      {sentiment.confidence && (
        <div className="flex space-x-0.5">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className={`w-0.5 h-2.5 rounded-full ${
                i <= (sentiment.confidence === 'high' ? 3 : sentiment.confidence === 'medium' ? 2 : 1)
                  ? colorClass.replace('text-', 'bg-')
                  : 'bg-gray-600'
              }`}
            />
          ))}
        </div>
      )}

      {/* Tooltip on Hover */}
      <div className="absolute top-full right-0 mt-2 w-64 p-3 bg-gray-800 border border-gray-700 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">Sentiment</span>
            <span className={`text-sm font-bold ${colorClass}`}>{label}</span>
          </div>
          
          {sentiment.sentiment_score !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Score</span>
              <span className="text-xs font-mono text-gray-300">
                {sentiment.sentiment_score > 0 ? '+' : ''}
                {sentiment.sentiment_score.toFixed(3)}
              </span>
            </div>
          )}

          {sentiment.article_count !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Articles</span>
              <span className="text-xs text-gray-300">{sentiment.article_count}</span>
            </div>
          )}

          {sentiment.confidence && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Confidence</span>
              <span className="text-xs text-gray-300 capitalize">{sentiment.confidence}</span>
            </div>
          )}

          {(sentiment.bullish_count !== undefined || sentiment.bearish_count !== undefined) && (
            <div className="pt-2 mt-2 border-t border-gray-700 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-green-400">● Bullish</span>
                <span className="text-gray-300">{sentiment.bullish_count || 0}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">● Neutral</span>
                <span className="text-gray-300">{sentiment.neutral_count || 0}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-red-400">● Bearish</span>
                <span className="text-gray-300">{sentiment.bearish_count || 0}</span>
              </div>
            </div>
          )}

          {error && (
            <div className="pt-2 mt-2 border-t border-gray-700">
              <p className="text-xs text-yellow-400">⚠ {error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
