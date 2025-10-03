import React, { useState } from 'react'
import { ExternalLink, Globe, Copy, Share2 } from 'lucide-react'

interface WebSearchLink {
  title: string
  url: string
  snippet?: string
  domain?: string
  citationId?: number
  publishDate?: string
  wordCount?: number
  faviconUrl?: string
  source?: string // Add source field to identify search engine
  relevance_score?: number // Add relevance score for quality indication
}

interface WebSearchLinksProps {
  links: WebSearchLink[]
}

const mergeAdjacentCitations = (text?: string) => {
  if (!text) return text ?? ''

  return text.replace(/(?:\[\d+\]){2,}/g, (match) => {
    const numbers = match.match(/\d+/g)
    if (!numbers) return match
    return `[${numbers.join(',')}]`
  })
}

const extractCitationBadges = (text?: string) => {
  if (!text) {
    return { cleanedText: text ?? '', citations: [] as string[] }
  }

  const citations = new Set<string>()
  const cleanedText = text.replace(/\[(\d+(?:,\d+)*)\]/g, (_match, group: string) => {
    group
      .split(',')
      .map((value: string) => value.trim())
      .filter((value) => value.length > 0)
      .forEach((value) => citations.add(value))
    return ''
  })

  const sortedCitations = Array.from(citations).sort((a, b) => Number(a) - Number(b))

  return { cleanedText: cleanedText.trim(), citations: sortedCitations }
}

// Enhanced favicon component with better fallback handling
const FaviconWithFallback = React.memo(function FaviconWithFallback({ 
  url, 
  domain, 
  citationId 
}: { 
  url: string
  domain?: string
  citationId?: number 
}) {
  const [faviconError, setFaviconError] = useState(false)
  const [faviconLoaded, setFaviconLoaded] = useState(false)
  
  // Generate favicon URL from domain
  const getFaviconUrl = (url: string, domain?: string) => {
    try {
      const urlObj = new URL(url)
      const hostname = domain || urlObj.hostname
      
      // Try multiple favicon sources for better reliability
      const faviconSources = [
        `https://www.google.com/s2/favicons?domain=${hostname}&sz=32`,
        `https://favicons.githubusercontent.com/${hostname}`,
        `https://${hostname}/favicon.ico`,
        `https://api.faviconkit.com/${hostname}/32`
      ]
      
      return faviconSources[0] // Start with Google's favicon service
    } catch {
      return null
    }
  }
  
  const faviconUrl = getFaviconUrl(url, domain)
  
  if (!faviconUrl || faviconError) {
    return (
      <div
        className="relative flex-shrink-0 w-7 h-7"
        style={{ isolation: 'isolate', zIndex: 30 }}
      >
        {citationId ? (
          <div className="w-full h-full bg-gradient-to-br from-blue-500 to-blue-600 text-white text-xs font-semibold rounded-md flex items-center justify-center shadow-sm border border-blue-400/20">
            {citationId}
          </div>
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-gray-600 to-gray-700 rounded-md flex items-center justify-center">
            <Globe className="w-3.5 h-3.5 text-gray-300" />
          </div>
        )}
      </div>
    )
  }
  
  return (
    <div
      className="relative flex-shrink-0 w-7 h-7"
      style={{ isolation: 'isolate', zIndex: 30 }}
    >
      <div className="w-full h-full bg-white rounded-md shadow-sm border border-gray-200/10 overflow-hidden">
        <img 
          src={faviconUrl}
          alt={`${domain} favicon`}
          className={`w-full h-full object-contain transition-opacity duration-200 ${
            faviconLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          onLoad={() => setFaviconLoaded(true)}
          onError={() => setFaviconError(true)}
        />
        {!faviconLoaded && !faviconError && (
          <div className="absolute inset-0 bg-gray-600 animate-pulse rounded-md" />
        )}
      </div>
      
      {/* Citation badge overlay */}
      {citationId && (
        <div
          className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-br from-blue-500 to-blue-600 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md border border-white/20 pointer-events-none"
          style={{ zIndex: 40 }}
          aria-hidden="true"
        >
          {citationId}
        </div>
      )}
    </div>
  )
})

// Copy button component
const CopyButton = React.memo(function CopyButton({ 
  text, 
  label, 
  icon 
}: { 
  text: string
  label: string
  icon?: string 
}) {
  const [copied, setCopied] = useState(false)
  
  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }
  
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-2 w-full px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-700 transition-colors rounded-md"
      title={label}
    >
      <span className="text-sm">{icon || '📄'}</span>
      <span>{copied ? 'Copied!' : label}</span>
      {copied && <span className="text-green-400">✓</span>}
    </button>
  )
})

export const WebSearchLinks = React.memo(function WebSearchLinks({ links }: WebSearchLinksProps) {
  const [activeDropdown, setActiveDropdown] = useState<number | null>(null)

  if (links.length === 0) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-gray-300 font-medium">
          <Globe className="w-4 h-4" />
          <span>Sources</span>
        </div>
        {/* Skeleton placeholder (Perplexity style) */}
        <div className="grid gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl border border-gray-700/40 bg-gray-800/40 p-4 overflow-hidden relative"
            >
              <div className="absolute inset-0 opacity-30 skeleton-shimmer" />
              <div className="relative flex items-start gap-3">
                <div className="w-6 h-6 rounded-md bg-gray-600/40 skeleton-shimmer" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-2/3 bg-gray-600/40 rounded skeleton-shimmer" />
                  <div className="h-2.5 w-1/2 bg-gray-600/30 rounded skeleton-shimmer" />
                  <div className="h-2 w-full bg-gray-700/30 rounded skeleton-shimmer" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2 text-sm text-gray-300 font-medium">
        <Globe className="w-4 h-4" />
        <span>Sources</span>
        <span className="text-xs text-gray-500 bg-gray-700 px-2 py-0.5 rounded-full">
          {links.length}
        </span>
      </div>
      
      {/* Links grid - Perplexity style */}
      <div className="grid gap-2">
  {links.map((link, idx) => {
          const domain = link.domain || (link.url ? new URL(link.url).hostname : 'Unknown')
          const mergedSnippet = link.snippet ? mergeAdjacentCitations(link.snippet) : undefined
          const { cleanedText: snippetWithoutCitations, citations: extractedCitations } = extractCitationBadges(mergedSnippet)
          const formattedSnippet = snippetWithoutCitations || undefined
          const displayCitations = extractedCitations.length > 0
            ? extractedCitations
            : link.citationId
              ? [String(link.citationId)]
              : []
          
          // Determine if this is a high-quality Brave source
          const isBraveSource = link.source === 'brave_search'
          const isHighQuality = isBraveSource || (link.relevance_score && link.relevance_score > 0.8)
          
          return (
            <div
              key={idx}
              className={`group relative source-card-anim ${
                isBraveSource 
                  ? 'bg-gradient-to-r from-orange-900/20 to-gray-800/40 border-orange-500/30 hover:border-orange-400/50' 
                  : 'bg-gray-800/40 border-gray-700/40 hover:border-gray-600/60'
              } hover:bg-gray-800/60 rounded-xl p-4 transition-all duration-200 hover:shadow-lg hover:shadow-black/20`}
              style={{ animationDelay: `${Math.min(idx * 90, 600)}ms` }}
            >
              {/* High-quality source badge */}
              {isBraveSource && (
                <div className="absolute top-2 right-2 flex items-center gap-1 bg-orange-500/20 border border-orange-500/30 text-orange-300 text-xs px-2 py-1 rounded-full font-medium">
                  <span className="w-1.5 h-1.5 bg-orange-400 rounded-full"></span>
                  High Quality
                </div>
              )}
              
              {/* Main content */}
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block"
              >
                <div className="flex items-start gap-3">
                  {/* Favicon */}
                  <FaviconWithFallback 
                    url={link.url} 
                    domain={domain} 
                    citationId={link.citationId} 
                  />
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0 relative z-0">
                    {/* Title and domain */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h4 className={`text-sm font-medium leading-snug line-clamp-2 mb-1 ${
                          isBraveSource 
                            ? 'text-orange-300 group-hover:text-orange-200' 
                            : 'text-blue-400 group-hover:text-blue-300'
                        }`}>
                          {link.title}
                        </h4>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span className="font-medium">{domain}</span>
                          {isBraveSource && (
                            <>
                              <span>•</span>
                              <span className="text-orange-400 font-semibold">Brave Search</span>
                            </>
                          )}
                          {link.publishDate && (
                            <>
                              <span>•</span>
                              <span>{new Date(link.publishDate).toLocaleDateString()}</span>
                            </>
                          )}
                          {displayCitations.length > 0 && (
                            <>
                              <span>•</span>
                              <span className={`font-medium ${
                                isBraveSource ? 'text-orange-400' : 'text-blue-400'
                              }`}>[{displayCitations.join(',')}]</span>
                            </>
                          )}
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            setActiveDropdown(activeDropdown === idx ? null : idx)
                          }}
                          className="p-1.5 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-md transition-colors"
                          title="More options"
                        >
                          <Share2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            navigator.clipboard.writeText(link.url)
                          }}
                          className="p-1.5 text-gray-400 hover:text-gray-300 hover:bg-gray-700 rounded-md transition-colors"
                          title="Copy URL"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                        <div className="p-1.5 text-gray-400">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    </div>
                    
                    {/* Snippet */}
                    {displayCitations.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1 mb-2">
                        {displayCitations.map((id) => {
                          const handleBadgeActivate = (event: React.MouseEvent | React.KeyboardEvent) => {
                            if (!link.url) return
                            event.preventDefault()
                            event.stopPropagation()
                            window.open(link.url, '_blank', 'noopener,noreferrer')
                          }

                          return (
                            <span
                              key={id}
                              role="button"
                              tabIndex={0}
                              title={`Open source [${id}] in new tab`}
                              onClick={handleBadgeActivate}
                              onKeyDown={(event) => {
                                if (event.key === 'Enter' || event.key === ' ') {
                                  handleBadgeActivate(event)
                                }
                              }}
                              className={`inline-flex items-center px-2 py-0.5 text-[11px] font-semibold rounded-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-400/70 focus:ring-offset-gray-900 ${
                                isBraveSource
                                  ? 'text-orange-200 bg-orange-500/20 border border-orange-500/40'
                                  : 'text-blue-100 bg-blue-500/20 border border-blue-500/40'
                              }`}
                            >
                              [{id}]
                            </span>
                          )
                        })}
                      </div>
                    )}

                    {formattedSnippet && (
                      <p className={`text-xs leading-relaxed line-clamp-2 p-2 rounded-lg border-l-2 whitespace-pre-line ${
                        isBraveSource 
                          ? 'text-orange-100/90 bg-orange-900/20 border-orange-500/50' 
                          : 'text-gray-400 bg-gray-900/30 border-gray-600/50'
                      }`}>
                        {formattedSnippet}
                      </p>
                    )}
                    
                    {/* Metadata badges */}
                    <div className="flex items-center gap-2 mt-2">
                      {link.wordCount && link.wordCount > 0 && (
                        <span className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-700/50 px-2 py-1 rounded-md">
                          <span>📄</span>
                          <span>{link.wordCount.toLocaleString()} words</span>
                        </span>
                      )}
                      {isHighQuality && link.relevance_score && (
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md ${
                          isBraveSource 
                            ? 'text-orange-300 bg-orange-500/20 border border-orange-500/30' 
                            : 'text-green-300 bg-green-500/20 border border-green-500/30'
                        }`}>
                          <span>⭐</span>
                          <span>{Math.round(link.relevance_score * 100)}% relevance</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </a>
              
              {/* Dropdown menu */}
              {activeDropdown === idx && (
                <div className="absolute top-full right-4 mt-2 w-56 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 py-2">
                  <CopyButton 
                    text={link.url} 
                    label="Copy URL" 
                    icon="🔗" 
                  />
                  <CopyButton 
                    text={`[${link.title}](${link.url})`} 
                    label="Copy as Markdown" 
                    icon="📝" 
                  />
                  <CopyButton 
                    text={`${link.title}. ${domain}. ${link.publishDate || new Date().toLocaleDateString()}. ${link.url}`} 
                    label="Copy Citation (MLA)" 
                    icon="📚" 
                  />
                  <CopyButton 
                    text={`${link.title}. (${link.publishDate || new Date().toLocaleDateString()}). Retrieved from ${link.url}`} 
                    label="Copy Citation (APA)" 
                    icon="🎓" 
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
      
      {/* Click outside to close dropdown */}
      {activeDropdown !== null && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setActiveDropdown(null)}
        />
      )}
    </div>
  )
})

WebSearchLinks.displayName = 'WebSearchLinks'