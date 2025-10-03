import React, { useCallback, useMemo, useState } from 'react'
import { ToolCard } from './ToolCard'

// Type definitions
type ToolCall = {
  id: string
  name: string
  result: unknown
}

interface ToolCallsPanelProps {
  toolCalls: ToolCall[]
}

const WEB_SEARCH_TOOL_NAMES = new Set([
  'perplexity_search',
  'web_search',
  'web_search_news',
  'augmented_rag_search',
  'financial_context_search',
  'augmented_rag_web',
])

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

type AggregatedSource = {
  title: string
  url: string
  snippet: string
  citation_id: number
  source?: string
  domain?: string
  publishDate?: string
}

const extractCandidateSources = (payload: any): AggregatedSource[] => {
  if (!payload || typeof payload !== 'object') return []

  const candidates: AggregatedSource[] = []

  const pushCandidate = (source: any) => {
    if (!source || typeof source !== 'object') return
    const url = typeof source.url === 'string' ? source.url : typeof source.link === 'string' ? source.link : ''
    const title = typeof source.title === 'string' ? source.title : typeof source.name === 'string' ? source.name : ''
    if (!url && !title) return
    const snippet = typeof source.snippet === 'string'
      ? source.snippet
      : typeof source.description === 'string'
        ? source.description
        : typeof source.content === 'string'
          ? source.content
          : ''
    const citationIdRaw = source.citation_id ?? source.citationId
    const citation_id = Number.isFinite(Number(citationIdRaw)) ? Number(citationIdRaw) : 0
    const domain = typeof source.domain === 'string'
      ? source.domain
      : (() => {
          if (!url) return ''
          try {
            return new URL(url).hostname
          } catch {
            return ''
          }
        })()
    const publishDate = typeof source.timestamp === 'string' ? source.timestamp : source.publishDate
    candidates.push({
      title: title || url || 'Untitled source',
      url,
      snippet,
      citation_id,
      source: typeof source.source === 'string' ? source.source : undefined,
      domain,
      publishDate: typeof publishDate === 'string' ? publishDate : undefined,
    })
  }

  if (Array.isArray(payload.sources)) {
    payload.sources.forEach(pushCandidate)
  }

  if (payload.citations && typeof payload.citations === 'object') {
    Object.entries(payload.citations).forEach(([key, value]) => {
      if (value && typeof value === 'object') {
        const enriched = {
          ...(value as Record<string, unknown>),
          citation_id: Number(key),
        }
        pushCandidate(enriched)
      }
    })
  }

  if (Array.isArray(payload.results)) {
    payload.results.forEach(pushCandidate)
  }

  if (Array.isArray(payload.raw_sources)) {
    payload.raw_sources.forEach(pushCandidate)
  }

  if (Array.isArray(payload.data)) {
    payload.data.forEach(pushCandidate)
  }

  if (Array.isArray(payload.combined_chunks)) {
    payload.combined_chunks
      .filter((chunk: any) => chunk && chunk.source === 'web_search')
      .forEach(pushCandidate)
  }

  return candidates
}

const aggregateWebSearchCalls = (webCalls: ToolCall[]) => {
  const seenKeys = new Set<string>()
  const sources: AggregatedSource[] = []
  const citationMap: Record<string, any> = {}
  const toolNames = new Set<string>()

  let synthesizedQuery: string | undefined
  let originalQuery: string | undefined
  let aggregatedAnswer: string | undefined

  webCalls.forEach((call) => {
    toolNames.add(call.name)
    const payload = call.result as any
    if (!originalQuery && typeof payload?.query === 'string') {
      originalQuery = payload.query
    }
    if (!synthesizedQuery && typeof payload?.synthesized_query === 'string') {
      synthesizedQuery = payload.synthesized_query
    }
    if (!aggregatedAnswer && typeof payload?.answer === 'string') {
      aggregatedAnswer = payload.answer
    }

    const candidates = extractCandidateSources(payload)

    candidates.forEach((candidate) => {
      const key = normalizeUrl(candidate.url) || candidate.title.toLowerCase()
      if (!key || seenKeys.has(key)) return
      seenKeys.add(key)
      sources.push(candidate)
    })
  })

  // Reassign citation IDs sequentially to ensure stable ordering and build citation map
  sources.forEach((source, index) => {
    const citationId = index + 1
    source.citation_id = citationId
    const domain = source.domain || (() => {
      if (!source.url) return 'Unknown'
      try {
        return new URL(source.url).hostname
      } catch {
        return 'Unknown'
      }
    })()
    citationMap[String(citationId)] = {
      title: source.title,
      url: source.url,
      domain,
      snippet: source.snippet,
      source: source.source,
      publishDate: source.publishDate,
    }
  })

  const representativeToolName = toolNames.has('perplexity_search')
    ? 'perplexity_search'
    : toolNames.has('web_search')
      ? 'web_search'
      : webCalls[0]?.name ?? 'perplexity_search'

  return {
    representativeToolName,
    sample: {
      query: originalQuery,
      synthesized_query: synthesizedQuery || originalQuery,
      answer: aggregatedAnswer,
      sources,
      citations: citationMap,
      tool_names: Array.from(toolNames),
    },
  }
}

export const ToolCallsPanel = React.memo(function ToolCallsPanel({ toolCalls }: ToolCallsPanelProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  // Convert each tool call to individual groups (no accumulation)
  const individualTools = useMemo(() => {
    if (!toolCalls.length) return []

    const webSearchCalls = toolCalls.filter((tool) => WEB_SEARCH_TOOL_NAMES.has(tool.name))
    const nonWebCalls = toolCalls.filter((tool) => !WEB_SEARCH_TOOL_NAMES.has(tool.name))

    const groups: Array<{ name: string; count: number; sample?: unknown; id: string }> = []

    if (webSearchCalls.length) {
      const { representativeToolName, sample } = aggregateWebSearchCalls(webSearchCalls)
      groups.push({
        name: representativeToolName,
        count: webSearchCalls.length,
        sample,
        id: 'web-search-aggregate',
      })
    }

    nonWebCalls.forEach((tool, index) => {
      groups.push({
        name: tool.name || 'unknown',
        count: 1,
        sample: tool.result,
        id: tool.id || `${tool.name}-${index}`,
      })
    })

    return groups
  }, [toolCalls])

  const toggleExpanded = useCallback((toolId: string) => {
    setExpanded((e) => ({ ...e, [toolId]: !e[toolId] }))
  }, [])

  if (!individualTools.length) return null

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-300 mb-3">Data Sources</p>
      <div className="space-y-3">
        {individualTools.map((tool) => (
          <ToolCard
            key={tool.id}
            group={tool}
            isExpanded={!!expanded[tool.id]}
            onToggleExpanded={() => toggleExpanded(tool.id)}
          />
        ))}
      </div>
    </div>
  )
})

ToolCallsPanel.displayName = 'ToolCallsPanel'