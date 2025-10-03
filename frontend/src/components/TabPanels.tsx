import React, { useState, useRef, useEffect, useMemo } from 'react'
import clsx from 'clsx'
import { Globe, Wrench, Search, FileText, Edit3, Copy, BookOpen } from 'lucide-react'
import { MessageContent } from './MessageContent'
import { MarkdownRenderer } from './MarkdownRenderer'
import { sanitizeHtml } from '../utils/sanitizeHtml'
import { decorateAnswerWithCitations } from '../utils/citations'
import { ToolCallsPanel } from './ToolCallsPanel'
import { normalizeLatexDelimiters } from '../utils/latex'

// Type definitions
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{ id: string; name: string; result: unknown }>
  timestamp: Date
}

type LiveTool = { 
  name: string
  status: 'running' | 'completed' | 'error'
  error?: string 
}

const TOOL_NAME_OVERRIDES: Record<string, string> = {
  perplexity_search: 'Perplexity search',
  web_search: 'Web search',
  augmented_rag_search: 'Augmented RAG search',
  citation_merger: 'Citation merge',
  citation_merge: 'Citation merge',
  citation_preserver: 'Citation preserver',
  answer_merger: 'Answer merger',
  answer_synthesizer: 'Answer synthesizer',
  reranker: 'Reranker'
}

const formatToolLabel = (name: string): string => {
  if (!name) return ''
  const override = TOOL_NAME_OVERRIDES[name]
  if (override) return override
  return name
    .replace(/[-_]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const formatList = (items: Array<string | undefined>): string => {
  const filtered = items.filter((item): item is string => Boolean(item && item.trim()))
  if (filtered.length === 0) return ''
  if (filtered.length === 1) return filtered[0]!
  if (filtered.length === 2) return `${filtered[0]!} and ${filtered[1]!}`
  return `${filtered.slice(0, -1).join(', ')}, and ${filtered[filtered.length - 1]!}`
}

const formatToolStatusLabel = (status: LiveTool['status']): string => {
  switch (status) {
    case 'running':
      return 'Running'
    case 'completed':
      return 'Completed'
    case 'error':
      return 'Error'
    default:
      return ''
  }
}

const normalizeCitationMarkers = (text: string, allowedIds?: Set<string>): string => {
  if (!text) return text
  const canUse = (id: string) => !allowedIds || allowedIds.has(id)

  let normalized = text

  normalized = normalized.replace(/\*(\d{1,3})/g, (match, id: string) =>
    canUse(id) ? `[${id}]` : match
  )

  normalized = normalized.replace(/[（(](\d{1,3})[）)]/g, (match, id: string) =>
    canUse(id) ? `[${id}]` : match
  )

  normalized = normalized.replace(/([\s\u3000])(\d{1,3})(?=[。．、，・:：])/g, (match, space: string, id: string) =>
    canUse(id) ? `${space}[${id}]` : match
  )

  return normalized
}

// Answer Tab Panel
interface AnswerTabPanelProps {
  assistantMessage: Message
  isStreaming: boolean
  onRewrite?: () => void
  onCopy?: () => void
  onSeeSources?: () => void
  hasSources?: boolean
}

export const AnswerTabPanel = React.memo(function AnswerTabPanel({
  assistantMessage,
  isStreaming,
  onRewrite,
  onCopy,
  onSeeSources,
  hasSources = false
}: AnswerTabPanelProps) {
  return (
    <div 
      role="tabpanel"
      id={`answer-${assistantMessage.id}`}
      className="qa-answer tab-panel-enter"
    >
      <div className="w-full">
        {/* Streaming placeholder */}
        {isStreaming && (!assistantMessage.content || assistantMessage.content.trim() === '') ? (
          <div className="py-2" aria-label="Loading answer">
            <div className="answer-skeleton-paragraph">
              <div className="answer-skeleton-line long" />
              <div className="answer-skeleton-line long" />
              <div className="answer-skeleton-line medium" />
            </div>
            <div className="answer-skeleton-paragraph">
              <div className="answer-skeleton-line long" />
              <div className="answer-skeleton-line short" />
            </div>
          </div>
        ) : (
          <div className="prose prose-xs max-w-none text-gray-100">
            <MessageContent 
              content={assistantMessage.content} 
              role="assistant" 
              toolCalls={assistantMessage.toolCalls}
            />
          </div>
        )}
        
        {/* End of answer indicator */}
        {!isStreaming && assistantMessage.content && (
          <div className="mt-3 pt-2 border-t border-gray-700/50"></div>
        )}

        {!isStreaming && (
          <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
            {onRewrite && (
              <button
                type="button"
                onClick={onRewrite}
                title="Rewrite answer"
                aria-label="Rewrite answer"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-700 bg-gray-800 text-gray-200 transition-colors hover:bg-gray-750"
              >
                <Edit3 className="h-4 w-4" />
                <span className="sr-only">Rewrite</span>
              </button>
            )}
            {onCopy && (
              <button
                type="button"
                onClick={onCopy}
                title="Copy answer"
                aria-label="Copy answer"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-700 bg-gray-800 text-gray-200 transition-colors hover:bg-gray-750"
              >
                <Copy className="h-4 w-4" />
                <span className="sr-only">Copy</span>
              </button>
            )}
            {onSeeSources && (
              <button
                type="button"
                onClick={onSeeSources}
                disabled={!hasSources}
                title={hasSources ? 'See sources' : 'Sources unavailable'}
                aria-label="See sources"
                className={clsx(
                  'inline-flex h-9 w-9 items-center justify-center rounded-md border transition-colors',
                  hasSources
                    ? 'border-blue-500/40 bg-blue-500/10 text-blue-200 hover:bg-blue-500/20'
                    : 'border-gray-700 bg-gray-800 text-gray-500 cursor-not-allowed'
                )}
              >
                <BookOpen className="h-4 w-4" />
                <span className="sr-only">See sources</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
})

// Sources Tab Panel
interface SourcesTabPanelProps {
  assistantMessage: Message
}

export const SourcesTabPanel = React.memo(function SourcesTabPanel({
  assistantMessage
}: SourcesTabPanelProps) {
  return (
    <div 
      role="tabpanel"
      id={`sources-${assistantMessage.id}`}
      className="qa-sources tab-panel-enter"
    >
      <div className="space-y-4">
        {assistantMessage.toolCalls && assistantMessage.toolCalls.length > 0 ? (
          <ToolCallsPanel toolCalls={assistantMessage.toolCalls} />
        ) : (
          <div className="text-center py-8 text-gray-400">
            <Globe className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No sources used for this response</p>
          </div>
        )}
      </div>
    </div>
  )
})

// Steps Tab Panel
interface StepsTabPanelProps {
  assistantMessage: Message
  activeTools?: LiveTool[]
  isStreaming: boolean
}

export const StepsTabPanel = React.memo(function StepsTabPanel({
  assistantMessage,
  activeTools = [],
  isStreaming
}: StepsTabPanelProps) {
  const hasActiveTools = isStreaming && activeTools.length > 0
  const hasCompletedTools = assistantMessage.toolCalls && assistantMessage.toolCalls.length > 0
  const hasAnySteps = hasActiveTools || hasCompletedTools

  // Check if we have perplexity search tools for enhanced step visualization
  const hasPerplexitySearch = activeTools.some(tool => 
    tool.name === 'perplexity_search' || 
    tool.name === 'web_search' || 
    tool.name === 'augmented_rag_search'
  ) || assistantMessage.toolCalls?.some(call => 
    call.name === 'perplexity_search' || 
    call.name === 'web_search' || 
    call.name === 'augmented_rag_search'
  )

  // Identify if we have a search tool call result to surface like Perplexity
  const searchToolNames = ['perplexity_search', 'web_search', 'augmented_rag_search']
  const searchToolCalls = (assistantMessage.toolCalls ?? []).filter(call => searchToolNames.includes(call.name)) as any[]
  const primarySearchCall = searchToolCalls.length > 0 ? searchToolCalls[searchToolCalls.length - 1] : undefined
  const activeSearchTools = activeTools.filter(tool => searchToolNames.includes(tool.name))
  const activeReviewTools = activeTools.filter(tool => !searchToolNames.includes(tool.name))
  const hasStreamingActivity = isStreaming && activeTools.length > 0

  const availableCitationIds = useMemo<Set<string> | undefined>(() => {
    if (searchToolCalls.length === 0) return undefined
    const ids = new Set<string>()
    for (const call of searchToolCalls) {
      const payload = call?.result as any
      if (!payload) continue

      const citations = payload?.citations
      if (citations && typeof citations === 'object' && !Array.isArray(citations)) {
        for (const key of Object.keys(citations)) {
          if (key !== undefined && key !== null && String(key).trim() !== '') {
            ids.add(String(key))
          }
        }
      }

      const rawSources = payload?.sources ?? payload?.raw_sources
      let sources: any[] = []
      if (Array.isArray(rawSources)) {
        sources = rawSources
      } else if (rawSources && typeof rawSources === 'object') {
        try {
          sources = Object.values(rawSources)
        } catch {
          sources = []
        }
      }

      for (const source of sources) {
        if (!source || typeof source !== 'object') continue
        const idRaw = (source as any).citation_id ?? (source as any).citationId
        if (idRaw === undefined || idRaw === null) continue
        const numeric = Number(idRaw)
        if (Number.isFinite(numeric)) {
          ids.add(String(numeric))
        } else {
          const text = String(idRaw).trim()
          if (text) ids.add(text)
        }
      }
    }
    return ids.size > 0 ? ids : undefined
  }, [searchToolCalls])

  const extractResultItems = (payload: any): any[] => {
    if (!payload) return []
    if (Array.isArray(payload)) return payload
    if (Array.isArray(payload?.results)) return payload.results
    if (Array.isArray(payload?.data)) return payload.data
    return []
  }

  const normalizeUrl = (value: unknown): string => {
    if (!value || typeof value !== 'string') return ''
    const trimmed = value.trim()
    if (!trimmed) return ''
    try {
      const hasProtocol = /^https?:\/\//i.test(trimmed)
      const url = new URL(hasProtocol ? trimmed : `https://${trimmed}`)
      let href = url.href
      if (href.endsWith('/')) {
        href = href.slice(0, -1)
      }
      return href.toLowerCase()
    } catch {
      return trimmed.toLowerCase()
    }
  }
  // Helper to safely coerce unknown value to a short string for display
  const toDisplayString = (val: any, fallback: string = ''): string => {
    if (val == null) return fallback
    if (typeof val === 'string') return val
    // Some APIs return objects like { title, url, ... } where we actually want a nested field
    if (typeof val === 'object') {
      const candidate = val.text || val.value || val.snippet || val.description || val.content || ''
      if (typeof candidate === 'string') return candidate
      try {
        const json = JSON.stringify(val)
        return json.length > 200 ? json.slice(0, 200) + ' …' : json
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
  // Additional guard to ensure we never return objects in JSX
  const safeText = (val: any, fallback: string = ''): string => {
    const str = toDisplayString(val, fallback)
    return typeof str === 'string' ? str : fallback
  }
  const aggregatedRawResults = searchToolCalls.flatMap(call => extractResultItems(call.result))
  const seenResultKeys = new Set<string>()
  const normalizedResults: Array<{ id: number; url: string; title: string; snippet: string }> = []
  for (const result of aggregatedRawResults) {
    if (!result || typeof result !== 'object') continue
    const urlRaw = (result as any).url ?? (result as any).link ?? (result as any).source ?? ''
    const key = normalizeUrl(urlRaw) || (String((result as any).title ?? (result as any).name ?? '').toLowerCase())
    if (key && seenResultKeys.has(key)) continue
    if (key) seenResultKeys.add(key)
    const titleRaw = (result as any).title ?? (result as any).name ?? `Result ${normalizedResults.length + 1}`
    const snippetRaw = (result as any).snippet ?? (result as any).description ?? (result as any).content ?? (result as any).display ?? ''
    const url = safeText(urlRaw)
    const title = safeText(titleRaw, `Result ${normalizedResults.length + 1}`)
    const snippet = safeText(snippetRaw)
    normalizedResults.push({ id: normalizedResults.length, url, title, snippet })
    if (normalizedResults.length >= 5) break
  }

  // Prefer explicit tool call synthesized answer if provided
  const toolSynthesisAnswer = (() => {
    for (let i = searchToolCalls.length - 1; i >= 0; i -= 1) {
      const candidate = (searchToolCalls[i]?.result as any)?.answer?.trim?.()
      if (candidate) {
  const normalizedLatex = normalizeLatexDelimiters(candidate)
  return normalizeCitationMarkers(normalizedLatex, availableCitationIds)
      }
    }
    return ''
  })()
  const baseAnswerRaw = (toolSynthesisAnswer || assistantMessage.content || '').trim()
  const latexNormalizedAnswer = normalizeLatexDelimiters(baseAnswerRaw)
  const rawFullAnswer = normalizeCitationMarkers(latexNormalizedAnswer, availableCitationIds)
  // Sanitize inline HTML to prevent script injection while allowing formatting tags
  const fullAnswer = sanitizeHtml(rawFullAnswer)
  const truncatedAnswer = fullAnswer.length > 600 ? fullAnswer.slice(0, 600) + ' …' : fullAnswer

  // Extract structured sources (enhanced) from perplexity tool result if present
  // Normalize sources from tool result; tolerate object or array forms
  const extractSources = (payload: any): any[] => {
    if (!payload) return []
    const sourcesData = payload?.sources ?? payload?.raw_sources
    if (Array.isArray(sourcesData)) return sourcesData
    if (sourcesData && typeof sourcesData === 'object') {
      try {
        return Object.values(sourcesData)
      } catch {
        return []
      }
    }
    return []
  }

  const extractCitations = (payload: any): Record<string, string> => {
    const rawCitations = payload?.citations
    if (rawCitations && typeof rawCitations === 'object' && !Array.isArray(rawCitations)) {
      return rawCitations as Record<string, string>
    }
    return {}
  }

  const aggregatedSources: any[] = []
  const aggregatedCitationLabels: Record<string, string> = {}
  const seenSourceKeys = new Set<string>()
  let maxCitationId = 0

  const pushSourcesFromCall = (call: any, preserveIds: boolean) => {
    if (!call?.result) return
    const sources = extractSources(call.result)
    const citations = extractCitations(call.result)
    for (const source of sources) {
      if (!source || typeof source !== 'object') continue
      const rawUrl = (source as any).url ?? (source as any).link ?? (source as any).source ?? ''
      const key = normalizeUrl(rawUrl) || (String((source as any).title ?? (source as any).name ?? '').toLowerCase())
      if (key && seenSourceKeys.has(key)) continue

      const originalCitationIdRaw = (source as any).citation_id ?? (source as any).citationId
      const numericOriginalCitationId = typeof originalCitationIdRaw === 'number'
        ? originalCitationIdRaw
        : Number(originalCitationIdRaw)
      const hasValidOriginalId = Number.isFinite(numericOriginalCitationId)
      let citationId: number
      if (preserveIds && hasValidOriginalId) {
        citationId = numericOriginalCitationId as number
      } else {
        maxCitationId += 1
        citationId = maxCitationId
      }
      maxCitationId = Math.max(maxCitationId, citationId)

      const originalIdKey = hasValidOriginalId ? String(numericOriginalCitationId) : undefined
      const assignedIdKey = String(citationId)
      const resolvedLabel = (originalIdKey && citations[originalIdKey]) || citations[assignedIdKey] || ''

      aggregatedSources.push({ ...source, citation_id: citationId })
      if (resolvedLabel) {
        aggregatedCitationLabels[citationId] = resolvedLabel
      }
      if (key) {
        seenSourceKeys.add(key)
      }
    }
  }

  if (primarySearchCall) {
    pushSourcesFromCall(primarySearchCall, true)
  }

  if (aggregatedSources.length > 0) {
    maxCitationId = aggregatedSources.reduce((acc, source) => {
      const id = (source as any).citation_id
      return typeof id === 'number' && Number.isFinite(id) ? Math.max(acc, id) : acc
    }, maxCitationId)
  }

  for (const call of searchToolCalls) {
    if (call === primarySearchCall) continue
    pushSourcesFromCall(call, false)
  }

  // Build synthesized per-source summaries using snippet/content
  const SOURCE_SUMMARY_COLLAPSED_COUNT = 6
  const allSourceSummaries = aggregatedSources.map((source, idx) => {
    const citationId = typeof (source as any).citation_id === 'number' && Number.isFinite((source as any).citation_id)
      ? (source as any).citation_id
      : idx + 1
    const title = safeText((source as any).title ?? (source as any).name, `Source ${citationId}`)
    const url = safeText((source as any).url ?? (source as any).link ?? (source as any).source ?? '')
    const rawText = safeText((source as any).snippet ?? (source as any).content ?? (source as any).description ?? (source as any).display ?? '')
    const text = rawText.length > 240 ? rawText.slice(0, 240) + ' …' : rawText
    const citationLabelRaw = aggregatedCitationLabels[citationId] ?? ''
    const citationLabel = safeText(citationLabelRaw)
    return {
      citationId,
      title: sanitizeHtml(title),
      url,
      text: sanitizeHtml(text),
      citationLabel: sanitizeHtml(citationLabel)
    }
  })

  const sanitizedSearchQueries = React.useMemo(() => {
    if (searchToolCalls.length === 0) return [] as string[]

    const queries: string[] = []
    const seen = new Set<string>()
    const containerKeys = new Set([
      'metadata',
      'search_metadata',
      'searchmetadata',
      'meta',
      'context',
      'details',
      'extras'
    ])
    const visited = new WeakSet<object>()

    const addQuery = (value: unknown) => {
      if (typeof value !== 'string') return
      const candidate = safeText(value).trim()
      if (!candidate) return
      const key = candidate.toLowerCase()
      if (seen.has(key)) return
      seen.add(key)
      queries.push(sanitizeHtml(candidate))
    }

    const traverse = (value: unknown) => {
      if (value == null) return
      if (typeof value === 'string') {
        addQuery(value)
        return
      }

      if (Array.isArray(value)) {
        for (const item of value) {
          traverse(item)
        }
        return
      }

      if (typeof value === 'object') {
        const obj = value as Record<string, unknown>
        if (visited.has(obj)) return
        visited.add(obj)

        for (const [key, nested] of Object.entries(obj)) {
          const keyLower = key.toLowerCase()
          if (keyLower.includes('query')) {
            traverse(nested)
          } else if (containerKeys.has(keyLower)) {
            traverse(nested)
          }
        }
      }
    }

    if (primarySearchCall?.result) {
      traverse(primarySearchCall.result)
    }

    for (const call of searchToolCalls) {
      traverse(call.result)
    }

    return queries
  }, [primarySearchCall, searchToolCalls])

  type StepStatus = LiveTool['status']

  const searchStepStatus: StepStatus = (() => {
    if (activeSearchTools.some(tool => tool.status === 'error')) return 'error'
    if (activeSearchTools.some(tool => tool.status === 'running')) return 'running'
    if (searchToolCalls.length > 0) return 'completed'
    if (hasCompletedTools) return 'completed'
    return hasStreamingActivity ? 'running' : 'completed'
  })()

  const reviewingStepStatus: StepStatus = (() => {
    if (activeReviewTools.some(tool => tool.status === 'error')) return 'error'
    if (allSourceSummaries.length > 0) return 'completed'
    if (isStreaming && (activeReviewTools.length > 0 || activeSearchTools.some(tool => tool.status === 'completed'))) return 'running'
    if (hasCompletedTools && searchToolCalls.length > 0) return 'completed'
    return hasStreamingActivity ? 'running' : 'completed'
  })()

  const shouldShowSearchingStep = hasStreamingActivity || searchToolCalls.length > 0 || activeSearchTools.length > 0
  const shouldShowReviewingStep = hasStreamingActivity || allSourceSummaries.length > 0 || activeReviewTools.length > 0

  const getStatusToneClass = (status: StepStatus) => {
    switch (status) {
      case 'running':
        return 'text-blue-300'
      case 'completed':
        return 'text-emerald-300'
      case 'error':
        return 'text-red-300'
      default:
        return 'text-gray-300'
    }
  }

  const completedSearchLabels = React.useMemo(() => {
    const seen = new Set<string>()
    const labels: string[] = []
    for (const call of searchToolCalls) {
      const label = formatToolLabel(call.name)
      const key = label.toLowerCase()
      if (!seen.has(key)) {
        seen.add(key)
        labels.push(label)
      }
    }
    return labels
  }, [searchToolCalls])

  const [showAllAnswer, setShowAllAnswer] = useState(false)
  const [showAllSources, setShowAllSources] = useState(false)
  const hasMoreSources = allSourceSummaries.length > SOURCE_SUMMARY_COLLAPSED_COUNT
  const visibleSourceSummaries = showAllSources ? allSourceSummaries : allSourceSummaries.slice(0, SOURCE_SUMMARY_COLLAPSED_COUNT)

  useEffect(() => {
    setShowAllSources(false)
  }, [assistantMessage.id])

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

  // We'll decorate citations after markdown is rendered to preserve markdown formatting.
  const synthesisRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!synthesisRef.current) return
    const currentHtml = synthesisRef.current.innerHTML
    // Decorate already-sanitized HTML; we trust MarkdownRenderer output combined with pre-sanitized input.
    const { html } = decorateAnswerWithCitations(currentHtml, allSourceSummaries)
    synthesisRef.current.innerHTML = html
  }, [showAllAnswer, fullAnswer, truncatedAnswer, allSourceSummaries])

  // Enhanced step rendering for perplexity-style search
  const renderPerplexitySteps = () => {
    type Step = {
      id: 'searching' | 'reviewing'
      label: string
      icon: typeof Search
      status: StepStatus
      description: string
    }

    const steps: Step[] = []
    const runningSearchLabels = activeSearchTools
      .filter(tool => tool.status === 'running')
      .map(tool => formatToolLabel(tool.name))
    const runningReviewLabels = activeReviewTools
      .filter(tool => tool.status === 'running')
      .map(tool => formatToolLabel(tool.name))
    const erroredSearchTool = activeSearchTools.find(tool => tool.status === 'error')
    const erroredReviewTool = activeReviewTools.find(tool => tool.status === 'error')

    if (shouldShowSearchingStep) {
      const searchDescription = (() => {
        if (searchStepStatus === 'error') {
          return erroredSearchTool?.error ? `Search error: ${erroredSearchTool.error}` : 'Search failed'
        }
        if (searchStepStatus === 'running') {
          const label = formatList(runningSearchLabels)
          return label ? `Searching via ${label}…` : 'Finding relevant information…'
        }
        const completedLabels = formatList(completedSearchLabels)
        return completedLabels ? `Search completed with ${completedLabels}` : 'Search completed'
      })()

      steps.push({
        id: 'searching',
        label: 'Searching the web',
        icon: Search,
        status: searchStepStatus,
        description: searchDescription
      })
    }

    if (shouldShowReviewingStep) {
      const reviewDescription = (() => {
        if (reviewingStepStatus === 'error') {
          return erroredReviewTool?.error ? `Review error: ${erroredReviewTool.error}` : 'Source review failed'
        }
        if (reviewingStepStatus === 'running') {
          const label = formatList(runningReviewLabels)
          return label ? `Reviewing with ${label}…` : 'Analyzing sources in real time…'
        }
        if (allSourceSummaries.length > 0) {
          return 'Sources reviewed'
        }
        return 'Review completed'
      })()

      steps.push({
        id: 'reviewing',
        label: 'Reviewing sources',
        icon: FileText,
        status: reviewingStepStatus,
        description: reviewDescription
      })
    }

    return steps
  }

  if (hasPerplexitySearch) {
    return (
      <div 
        role="tabpanel"
        id={`steps-${assistantMessage.id}`}
        className="qa-steps tab-panel-enter"
      >
        <div className="space-y-6">
          <section className="space-y-2">
            <div className="flex items-center gap-2 text-gray-200">
              <Search className="w-4 h-4 text-blue-300" />
              <h4 className="text-sm font-medium">Searching</h4>
            </div>
            {activeSearchTools.length > 0 && (
              <div className="space-y-2">
                {activeSearchTools.map((tool) => (
                  <div
                    key={`search-tool-${tool.name}`}
                    className="flex items-center justify-between rounded-md border border-gray-800/70 bg-gray-900/30 px-3 py-2 text-xs text-gray-200"
                  >
                    <span className="font-medium">{formatToolLabel(tool.name)}</span>
                    <span className={clsx('uppercase tracking-wide', getStatusToneClass(tool.status))}>
                      {formatToolStatusLabel(tool.status)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {completedSearchLabels.length > 0 && activeSearchTools.length === 0 && (
              <p className="text-[11px] text-gray-400">
                Completed via {formatList(completedSearchLabels)}.
              </p>
            )}
            {sanitizedSearchQueries.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {sanitizedSearchQueries.map((query, index) => (
                  <span
                    key={`search-query-${index}`}
                    className="inline-flex items-center gap-2 rounded-full bg-gray-900/40 border border-gray-700/60 px-3 py-1 text-[11px] text-gray-200"
                    dangerouslySetInnerHTML={{ __html: query }}
                  />
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400">
                {searchStepStatus === 'running' ? 'Capturing search queries…' : 'No search queries recorded.'}
              </p>
            )}
          </section>

          <section className="space-y-3">
            <div className="flex items-center gap-2 text-gray-200">
              <FileText className="w-4 h-4 text-emerald-300" />
              <h4 className="text-sm font-medium">Reviewing sources</h4>
            </div>
            {activeReviewTools.length > 0 && (
              <div className="space-y-2">
                {activeReviewTools.map(tool => (
                  <div
                    key={`review-tool-${tool.name}`}
                    className="flex items-center justify-between rounded-md border border-gray-800/70 bg-gray-900/30 px-3 py-2 text-xs text-gray-200"
                  >
                    <span className="font-medium">{formatToolLabel(tool.name)}</span>
                    <span className={clsx('uppercase tracking-wide', getStatusToneClass(tool.status))}>
                      {formatToolStatusLabel(tool.status)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {allSourceSummaries.length > 0 ? (
              <div className="rounded-lg border border-gray-800/70 bg-gray-900/30">
                <div className="max-h-72 overflow-y-auto divide-y divide-gray-800">
                  {allSourceSummaries.map((src) => {
                    const faviconUrl = getFaviconUrl(src.url)
                    const domain = getDisplayDomain(src.url)
                    const initial = domain ? domain.charAt(0).toUpperCase() : '•'
                    const href = typeof src.url === 'string' && src.url.startsWith('http') ? src.url : undefined

                    const content = (
                      <div className="flex items-center gap-3 px-3 py-2 hover:bg-gray-900/50 transition-colors">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-sm bg-blue-500/20 text-[10px] text-blue-300 font-medium border border-blue-500/40">
                            {src.citationId}
                          </span>
                          <div className="flex items-center gap-2 min-w-0">
                            {faviconUrl ? (
                              <img src={faviconUrl} alt="" className="w-5 h-5 rounded" loading="lazy" />
                            ) : (
                              <div className="w-5 h-5 rounded bg-gray-700/50 flex items-center justify-center text-[9px] text-gray-300">
                                {initial}
                              </div>
                            )}
                            <span
                              className="text-xs font-medium text-gray-100 line-clamp-1"
                              dangerouslySetInnerHTML={{ __html: src.title }}
                            />
                          </div>
                        </div>
                        {domain && (
                          <span className="text-[11px] text-gray-500 flex-shrink-0">
                            {domain.replace(/^www\./, '')}
                          </span>
                        )}
                      </div>
                    )

                    return (
                      <div key={src.citationId}>
                        {href ? (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block"
                          >
                            {content}
                          </a>
                        ) : (
                          content
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="rounded-md border border-gray-800/60 bg-gray-900/30 px-4 py-6 text-center text-xs text-gray-400">
                {reviewingStepStatus === 'running'
                  ? 'Reviewing sources in real time…'
                  : 'No sources available for this search.'}
              </div>
            )}
          </section>
        </div>
      </div>
    )
  }

  const perplexitySteps = renderPerplexitySteps()

  return (
    <div 
      role="tabpanel"
      id={`steps-${assistantMessage.id}`}
      className="qa-steps tab-panel-enter"
    >
      <div className="space-y-4">
        {hasAnySteps || perplexitySteps.length > 0 ? (
          <div>
            {/* Perplexity-style enhanced steps */}
            {perplexitySteps.length > 0 && (
              <div className="mb-6">
                <div className="space-y-3">
                  {perplexitySteps.map((step) => {
                    const IconComponent = step.icon
                    return (
                      <div key={step.id} className="flex items-start space-x-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                          step.status === 'running' ? 'bg-blue-500/20 border border-blue-500/50' :
                          step.status === 'completed' ? 'bg-green-500/20 border border-green-500/50' :
                          step.status === 'error' ? 'bg-red-500/20 border border-red-500/50' :
                          'bg-gray-500/20 border border-gray-500/50'
                        }`}>
                          <IconComponent className={`w-4 h-4 ${
                            step.status === 'running' ? 'text-blue-400 animate-pulse' :
                            step.status === 'completed' ? 'text-green-400' :
                            step.status === 'error' ? 'text-red-400' :
                            'text-gray-400'
                          }`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h4 className="text-sm font-medium text-gray-200">{step.label}</h4>
                            {step.status === 'running' && (
                              <div className="flex space-x-1">
                                <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" />
                                <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                              </div>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mt-1">{step.description}</p>
                          {step.id === 'searching' && step.status === 'completed' && normalizedResults.length > 0 && (
                            <div className="mt-3 space-y-2">
                              <p className="text-[11px] uppercase tracking-wide text-gray-400">Top results</p>
                              <ul className="space-y-2">
                                {normalizedResults.map(r => {
                                  const domain = (() => {
                                    if (!r.url || typeof r.url !== 'string') return ''
                                    try { return new URL(r.url).hostname.replace(/^www\./,'') } catch { return '' }
                                  })()
                                  return (
                                    <li key={r.id} className="group">
                                      <a
                                        href={typeof r.url === 'string' && r.url.startsWith('http') ? r.url : '#'}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block p-2 rounded-md bg-gray-900/40 hover:bg-gray-900/70 border border-gray-700/40 hover:border-gray-600 transition-colors"
                                      >
                                        <div className="flex items-center justify-between">
                                          <span className="text-xs font-medium text-blue-300 line-clamp-1 group-hover:underline">{r.title}</span>
                                          {domain && <span className="ml-2 text-[10px] text-gray-500 flex-shrink-0">{domain}</span>}
                                        </div>
                                        {r.snippet && typeof r.snippet === 'string' && <p className="mt-1 text-[11px] leading-tight text-gray-400 line-clamp-2">{r.snippet}</p>}
                                      </a>
                                    </li>
                                  )
                                })}
                              </ul>
                            </div>
                          )}
                          {step.id === 'reviewing' && fullAnswer && (
                            <div className="mt-3 space-y-2">
                              <p className="text-[11px] uppercase tracking-wide text-gray-400">Synthesis (OSS 120B)</p>
                              <div className="p-2 rounded-md bg-gray-900/40 border border-gray-700/40 text-xs leading-relaxed text-gray-300 relative citation-enabled">
                                {/* Use MarkdownRenderer for markdown + inline HTML, then post-process for citations */}
                                <div ref={synthesisRef} className="prose prose-xs max-w-none markdown-synthesis text-gray-100 [&_strong]:font-semibold [&_strong]:text-gray-100">
                                  <MarkdownRenderer 
                                    content={showAllAnswer ? fullAnswer : truncatedAnswer}
                                    toolCalls={assistantMessage.toolCalls}
                                  />
                                </div>
                              </div>
                              {fullAnswer.length > 600 && (
                                <button
                                  type="button"
                                  onClick={() => setShowAllAnswer(v => !v)}
                                  className="text-[11px] text-blue-400 hover:text-blue-300"
                                >
                                  {showAllAnswer ? 'Show less' : 'Show full answer'}
                                </button>
                              )}
                              {allSourceSummaries.length > 0 && (
                                <div className="pt-2 border-t border-gray-800/60 space-y-2">
                                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Source summaries</p>
                                  <ul className="space-y-2">
                                    {visibleSourceSummaries.map(src => (
                                      <li key={src.citationId} className="p-2 rounded-md bg-gray-900/30 border border-gray-800/60 hover:border-gray-700 transition-colors">
                                        <div className="flex items-start justify-between gap-2">
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-sm bg-blue-500/20 text-[10px] text-blue-300 font-medium border border-blue-500/40">{src.citationId}</span>
                                              <a
                                                href={typeof src.url === 'string' && src.url.startsWith('http') ? src.url : '#'}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-xs font-medium text-blue-300 hover:underline line-clamp-1"
                                              >
                                                <span dangerouslySetInnerHTML={{ __html: src.title }} />
                                              </a>
                                            </div>
                                            {src.text && typeof src.text === 'string' && (
                                              <p className="mt-1 text-[11px] leading-tight text-gray-400 line-clamp-3" dangerouslySetInnerHTML={{ __html: src.text }} />
                                            )}
                                            {src.citationLabel && typeof src.citationLabel === 'string' && (
                                              <p className="mt-1 text-[10px] text-gray-500 italic line-clamp-1" dangerouslySetInnerHTML={{ __html: src.citationLabel }} />
                                            )}
                                          </div>
                                        </div>
                                      </li>
                                    ))}
                                  </ul>
                                  {hasMoreSources && (
                                    <button
                                      type="button"
                                      onClick={() => setShowAllSources(v => !v)}
                                      className="text-[11px] text-blue-400 hover:text-blue-300"
                                    >
                                      {showAllSources ? 'Show fewer sources' : 'Load more sources'}
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Active/Live Tools */}
            {hasActiveTools && !hasPerplexitySearch && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Current Steps</h4>
                <div className="space-y-2">
                  {activeTools.map((tool) => (
                    <div key={tool.name} className="flex items-center space-x-3 text-sm">
                      <div className={`w-2 h-2 rounded-full ${
                        tool.status === 'running' ? 'bg-yellow-500 animate-pulse' :
                        tool.status === 'completed' ? 'bg-green-500' :
                        'bg-red-500'
                      }`} />
                      <span className="text-gray-200">{tool.name}</span>
                      <span className={`text-xs ${
                        tool.status === 'running' ? 'text-yellow-400' :
                        tool.status === 'completed' ? 'text-green-400' :
                        'text-red-400'
                      }`}>
                        {tool.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Completed Tool Calls */}
            {hasCompletedTools && !hasPerplexitySearch && (
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Completed Steps</h4>
                <div className="space-y-2">
                  {assistantMessage.toolCalls!.map((call, idx) => (
                    <div key={`${call.id}-${idx}`} className="flex items-center space-x-3 text-sm">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <span className="text-gray-200">{call.name}</span>
                      <span className="text-xs text-green-400">completed</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            <Wrench className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No steps recorded for this response</p>
          </div>
        )}
      </div>
    </div>
  )
})

AnswerTabPanel.displayName = 'AnswerTabPanel'
SourcesTabPanel.displayName = 'SourcesTabPanel'
StepsTabPanel.displayName = 'StepsTabPanel'