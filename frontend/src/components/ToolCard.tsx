import React from 'react'
import clsx from 'clsx'
import { Globe } from 'lucide-react'
import { sanitizeHtml } from '../utils/sanitizeHtml'
import PriceQuoteCard, { QuoteData } from './PriceQuoteCard'

// Type definitions
type ToolCall = {
  id: string
  name: string
  result: unknown
}

interface GroupedTool {
  name: string
  count: number
  sample?: unknown
  id?: string // Add optional id for unique identification
}

interface ToolCardProps {
  group: GroupedTool
  isExpanded: boolean
  onToggleExpanded: () => void // Simplified since we now pass the callback directly
}

type SanitizedSourceSummary = {
  citationId: number
  titleHtml: string
  url: string
  previewHtml: string
  fullHtml: string
  citationLabelHtml: string
}

// Helper: map tool names to friendly labels, icons, and color styles
const TOOL_META: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; color: string }> = {
  // Stock Data Tools
  get_company_profile: { label: 'Company Profile', icon: () => <span>🏢</span>, color: 'bg-purple-50 text-purple-700 border-purple-200' },
  get_stock_quote: { label: 'Live Quote', icon: () => <span>💲</span>, color: 'bg-green-50 text-green-700 border-green-200' },
  get_historical_prices: { label: 'Historical Prices', icon: () => <span>📈</span>, color: 'bg-amber-50 text-amber-800 border-amber-200' },
  
  // Financial Analysis Tools
  get_financials: { label: 'Financial Statements', icon: () => <span>�</span>, color: 'bg-blue-50 text-blue-700 border-blue-200' },
  get_earnings_data: { label: 'Earnings Data', icon: () => <span>📅</span>, color: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  get_analyst_recommendations: { label: 'Analyst Recommendations', icon: () => <span>🎯</span>, color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  get_institutional_holders: { label: 'Institutional Holders', icon: () => <span>�</span>, color: 'bg-violet-50 text-violet-700 border-violet-200' },
  get_market_cap_details: { label: 'Market Cap Details', icon: () => <span>🧮</span>, color: 'bg-teal-50 text-teal-700 border-teal-200' },
  get_dividends_splits: { label: 'Dividends & Splits', icon: () => <span>🪙</span>, color: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  
  // Market Intelligence Tools
  get_market_indices: { label: 'Market Indices', icon: () => <span>📊</span>, color: 'bg-purple-50 text-purple-700 border-purple-200' },
  get_market_summary: { label: 'Market Summary', icon: () => <span>📋</span>, color: 'bg-slate-50 text-slate-700 border-slate-200' },
  get_nikkei_news_with_sentiment: { label: 'Nikkei News & Sentiment', icon: () => <span>📰</span>, color: 'bg-orange-50 text-orange-700 border-orange-200' },
  get_augmented_news: { label: 'Augmented News', icon: () => <span>📰</span>, color: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  
  // Technical Analysis Tools
  get_technical_indicators: { label: 'Technical Indicators', icon: () => <span>📉</span>, color: 'bg-amber-50 text-amber-800 border-amber-200' },
  check_golden_cross: { label: 'Golden Cross Analysis', icon: () => <span>⚡</span>, color: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  calculate_correlation: { label: 'Correlation Analysis', icon: () => <span>🔗</span>, color: 'bg-pink-50 text-pink-700 border-pink-200' },
  
  // Risk Analysis Tools
  get_risk_assessment: { label: 'Risk Assessment', icon: () => <span>🛡️</span>, color: 'bg-rose-50 text-rose-700 border-rose-200' },
  
  // Search Tools  
  search_symbol: { label: 'Search Symbol', icon: () => <span>🔍</span>, color: 'bg-blue-50 text-blue-700 border-blue-200' },
  get_stock_news: { label: 'Stock News', icon: () => <span>📰</span>, color: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  rag_search: { label: 'Knowledge Search', icon: () => <span>📚</span>, color: 'bg-slate-50 text-slate-700 border-slate-200' },
  
  // Enhanced Web Search Tools
  web_search: { label: 'Web Search', icon: Globe, color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  perplexity_search: { label: 'AI Web Search', icon: Globe, color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  web_search_news: { label: 'News Search', icon: Globe, color: 'bg-orange-50 text-orange-700 border-orange-200' },
  augmented_rag_search: { label: 'Enhanced RAG Search', icon: Globe, color: 'bg-violet-50 text-violet-700 border-violet-200' },
  financial_context_search: { label: 'Financial Context Search', icon: Globe, color: 'bg-teal-50 text-teal-700 border-teal-200' },
}

const SOURCE_SUMMARY_COLLAPSED_COUNT = 6

const toDisplayString = (val: any, fallback: string = ''): string => {
  if (val == null) return fallback
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const candidate = val.text || val.value || val.snippet || val.description || val.content || val.display || ''
    if (typeof candidate === 'string') return candidate
    try {
      const json = JSON.stringify(val)
      return json.length > 200 ? `${json.slice(0, 200)} …` : json
    } catch {
      return fallback
    }
  }
  try {
    return String(val)
  } catch {
    return fallback
  }
}

const safeText = (val: any, fallback: string = ''): string => {
  const str = toDisplayString(val, fallback)
  return typeof str === 'string' ? str : fallback
}

const buildCitationLabel = (meta: any): string => {
  if (!meta) return ''
  if (typeof meta === 'string') return meta
  if (typeof meta !== 'object') {
    try {
      return String(meta)
    } catch {
      return ''
    }
  }

  const parts: string[] = []
  const source = safeText((meta as any).source)
  const domain = safeText((meta as any).domain)
  const publishDate = safeText((meta as any).publishDate ?? (meta as any).publish_date)

  if (source) parts.push(source)
  if (domain) parts.push(domain.replace(/^www\./, ''))
  if (publishDate) parts.push(publishDate)

  return parts.filter(Boolean).join(' • ')
}

const getFaviconUrl = (url: string): string => {
  if (!url || typeof url !== 'string') return ''
  try {
    const parsed = new URL(url.startsWith('http') ? url : `https://${url}`)
    const origin = `${parsed.protocol}//${parsed.hostname}`
    return `https://www.google.com/s2/favicons?sz=64&domain_url=${encodeURIComponent(origin)}`
  } catch {
    return ''
  }
}

const getDisplayDomain = (url: string): string => {
  if (!url || typeof url !== 'string') return ''
  try {
    const parsed = new URL(url.startsWith('http') ? url : `https://${url}`)
    return parsed.hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

// Check if a tool is a web search tool
const isWebSearchTool = (toolName: string): boolean => {
  const webSearchTools = ['web_search', 'perplexity_search', 'web_search_news', 'augmented_rag_search', 'financial_context_search']
  return webSearchTools.includes(toolName)
}

export const ToolCard = React.memo(function ToolCard({
  group,
  isExpanded,
  onToggleExpanded
}: ToolCardProps) {
  const contentRef = React.useRef<HTMLDivElement | null>(null)
  const [height, setHeight] = React.useState<number | null>(null)
  const [showAllSources, setShowAllSources] = React.useState(false)
  const [expandedSources, setExpandedSources] = React.useState<Record<number, boolean>>({})

  React.useEffect(() => {
    if (isExpanded && contentRef.current) {
      const el = contentRef.current
      // Set to auto first to get natural height
      requestAnimationFrame(() => {
        setHeight(el.scrollHeight)
      })
    } else if (!isExpanded) {
      setHeight(0)
    }
  }, [isExpanded, group.sample, showAllSources, expandedSources])

  // After transition ends when expanded, set height to auto to allow internal layout changes
  const handleTransitionEnd = React.useCallback((e: React.TransitionEvent) => {
    if (e.propertyName === 'height' && isExpanded && contentRef.current) {
      setHeight(contentRef.current.scrollHeight) // ensure final height
    }
  }, [isExpanded])
  const meta = TOOL_META[group.name]
  const Icon = meta?.icon || (() => <span>🔧</span>)
  const label = meta?.label || group.name
  const color = meta?.color || 'bg-gray-50 text-gray-700 border-gray-200'

  const isQuoteTool = group.name === 'get_stock_quote'
  const quoteSample: QuoteData | null = React.useMemo(() => {
    if (!isQuoteTool || !group.sample || typeof group.sample !== 'object') {
      return null
    }
    return group.sample as QuoteData
  }, [group.sample, isQuoteTool])

  if (isQuoteTool && quoteSample) {
    return (
      <div className="toolcard bg-transparent">
        <div className="flex items-center gap-3 mb-3">
          <span className={clsx('inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm', color)}>
            <Icon />
            <span className="font-medium">{label}</span>
          </span>
        </div>
        <PriceQuoteCard data={quoteSample} />
      </div>
    )
  }

  const webSample = isWebSearchTool(group.name) && group.sample && typeof group.sample === 'object'
    ? (group.sample as any)
    : undefined
  const sanitizedSourceSummaries = React.useMemo<SanitizedSourceSummary[]>(() => {
    if (!isWebSearchTool(group.name) || !webSample) return []

    const citations = (webSample.citations && typeof webSample.citations === 'object' && !Array.isArray(webSample.citations))
      ? (webSample.citations as Record<string, any>)
      : {}

    const rawSources = Array.isArray(webSample.sources) ? webSample.sources : []
    const typedSources = rawSources as Array<Record<string, any>>

    return typedSources
      .map((source, idx): SanitizedSourceSummary | null => {
        if (!source || typeof source !== 'object') return null

        const citationIdRaw = source.citation_id ?? source.citationId
        const citationId = Number.isFinite(Number(citationIdRaw)) ? Number(citationIdRaw) : idx + 1

        const titleRaw = safeText(source.title ?? source.name ?? `Source ${citationId}`, `Source ${citationId}`)
        const urlRaw = safeText(source.url ?? source.link ?? source.source ?? '')
        const snippetRaw = safeText(
          source.snippet ??
          source.description ??
          source.content ??
          source.display ??
          ''
        )
        const previewSnippet = snippetRaw.length > 240 ? `${snippetRaw.slice(0, 240).trimEnd()} …` : snippetRaw
        const citationMeta = citations[String(citationId)]
        const citationLabelRaw = buildCitationLabel(citationMeta)

        return {
          citationId,
          titleHtml: sanitizeHtml(titleRaw || `Source ${citationId}`),
          url: urlRaw,
          previewHtml: sanitizeHtml(previewSnippet),
          fullHtml: sanitizeHtml(snippetRaw),
          citationLabelHtml: citationLabelRaw ? sanitizeHtml(citationLabelRaw) : '',
        }
      })
    .filter((value: SanitizedSourceSummary | null): value is SanitizedSourceSummary => value !== null)
  }, [group.name, webSample])

  const hasMoreSources = sanitizedSourceSummaries.length > SOURCE_SUMMARY_COLLAPSED_COUNT
  const visibleSourceSummaries = showAllSources
    ? sanitizedSourceSummaries
    : sanitizedSourceSummaries.slice(0, SOURCE_SUMMARY_COLLAPSED_COUNT)
  const hiddenSourceCount = Math.max(0, sanitizedSourceSummaries.length - SOURCE_SUMMARY_COLLAPSED_COUNT)

  React.useEffect(() => {
    if (!isWebSearchTool(group.name)) return
    setShowAllSources(false)
    setExpandedSources({})
  }, [group.name, group.sample])

  const toggleSourceExpansion = React.useCallback((citationId: number) => {
    setExpandedSources((prev) => ({ ...prev, [citationId]: !prev[citationId] }))
  }, [])

  return (
    <div className="toolcard bg-gray-800 border border-gray-700 rounded-lg p-3">
      <div className="flex items-center gap-3 mb-2">
        <span className={clsx("inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm", color)}>
          <Icon />
          <span className="font-medium">{label}</span>
        </span>
        {/* Remove count display since each tool call is now individual */}
        {group.sample !== undefined && (
          <button
            type="button"
            className="ml-auto text-blue-400 hover:text-blue-300 text-sm"
            onClick={onToggleExpanded}
          >
            {isExpanded ? 'Hide details' : 'View details'}
          </button>
        )}
      </div>
      
      <div
        className="collapse-wrapper mt-2"
        data-state={isExpanded ? 'expanded' : 'collapsed'}
        style={{ height: isExpanded ? (height !== null ? height : 'auto') : 0 }}
        onTransitionEnd={handleTransitionEnd}
      >
        <div ref={contentRef} className="space-y-3 px-0.5 pb-1">
          {isExpanded && (
            <>
              {isWebSearchTool(group.name) && sanitizedSourceSummaries.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-300">Source summaries</h4>
                  <ul className="space-y-2">
                    {visibleSourceSummaries.map((src) => {
                      const faviconUrl = getFaviconUrl(src.url)
                      const domain = getDisplayDomain(src.url)
                      const href = typeof src.url === 'string' && src.url.startsWith('http') ? src.url : undefined
                      const isExpandedSource = !!expandedSources[src.citationId]
                      const summaryHtml = isExpandedSource ? src.fullHtml : src.previewHtml
                      const canToggle = src.fullHtml !== src.previewHtml && src.fullHtml !== ''

                      return (
                        <li
                          key={src.citationId}
                          className="p-3 rounded-md bg-gray-900/30 border border-gray-800/60 hover:border-gray-700 transition-colors"
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex-shrink-0">
                              {faviconUrl ? (
                                <img
                                  src={faviconUrl}
                                  alt=""
                                  className="w-6 h-6 rounded"
                                  loading="lazy"
                                />
                              ) : (
                                <div className="w-6 h-6 rounded bg-gray-700/50 flex items-center justify-center text-[10px] text-gray-300">
                                  {domain ? domain.charAt(0).toUpperCase() : '•'}
                                </div>
                              )}
                            </div>
                            <div className="flex-1 min-w-0 space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="inline-flex items-center justify-center w-5 h-5 rounded-sm bg-blue-500/20 text-[10px] text-blue-300 font-medium border border-blue-500/40">
                                  {src.citationId}
                                </span>
                                {href ? (
                                  <a
                                    href={href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs font-medium text-blue-300 hover:underline line-clamp-1"
                                    dangerouslySetInnerHTML={{ __html: src.titleHtml }}
                                  />
                                ) : (
                                  <span
                                    className="text-xs font-medium text-gray-200 line-clamp-1"
                                    dangerouslySetInnerHTML={{ __html: src.titleHtml }}
                                  />
                                )}
                              </div>
                              {domain && (
                                <p className="text-[10px] text-gray-500">{domain}</p>
                              )}
                              {summaryHtml && (
                                <p
                                  className="text-[11px] leading-tight text-gray-400"
                                  dangerouslySetInnerHTML={{ __html: summaryHtml }}
                                />
                              )}
                              {canToggle && (
                                <button
                                  type="button"
                                  onClick={() => toggleSourceExpansion(src.citationId)}
                                  className="text-[10px] text-blue-400 hover:text-blue-300"
                                >
                                  {isExpandedSource ? 'Show less' : 'View full summary'}
                                </button>
                              )}
                              {src.citationLabelHtml && (
                                <p
                                  className="text-[10px] text-gray-500 italic"
                                  dangerouslySetInnerHTML={{ __html: src.citationLabelHtml }}
                                />
                              )}
                            </div>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                  {hasMoreSources && (
                    <button
                      type="button"
                      onClick={() => setShowAllSources((v) => !v)}
                      className="text-[11px] text-blue-400 hover:text-blue-300"
                    >
                      {showAllSources ? 'Show fewer sources' : `Show more sources (${hiddenSourceCount})`}
                    </button>
                  )}
                </div>
              )}
              {isWebSearchTool(group.name) && sanitizedSourceSummaries.length === 0 && (
                <div className="rounded-md border border-gray-700/60 bg-gray-900/20 px-3 py-2 text-[11px] text-gray-400">
                  No sources were returned for this search.
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
})

ToolCard.displayName = 'ToolCard'