/**
 * Custom hook for stock symbol search functionality
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { getToken, apiBase } from '../lib/api'

export interface SearchResult {
  symbol: string
  description: string
  type: string
  displaySymbol: string
  region?: string
  currency?: string
  matchScore?: string
}

interface UseStockSearchReturn {
  searchQuery: string
  setSearchQuery: (query: string) => void
  searchResults: SearchResult[]
  isSearching: boolean
  clearSearch: () => void
}

export const useStockSearch = (user: any): UseStockSearchReturn => {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const searchTimeoutRef = useRef<number>()

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
      const response = await fetch(
        `${apiBase()}/dashboard/search?q=${encodeURIComponent(searchQuery)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data.results || [])
      } else {
        if (import.meta.env.DEV) {
          console.error(`Search failed: ${response.status}`)
        }
        setSearchResults([])
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Search error:', error)
      }
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

  const clearSearch = useCallback(() => {
    setSearchQuery('')
    setSearchResults([])
    setIsSearching(false)
  }, [])

  return {
    searchQuery,
    setSearchQuery,
    searchResults,
    isSearching,
    clearSearch,
  }
}
