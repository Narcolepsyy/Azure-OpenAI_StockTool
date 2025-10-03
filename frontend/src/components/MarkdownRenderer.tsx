import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeRaw from 'rehype-raw'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import '../katex-dark.css'
import { CitationLink } from './CitationLink'
import { normalizeLatexDelimiters } from '../utils/latex'

// Type definitions for tool calls and citations
type ToolCall = {
  id: string
  name: string
  result: unknown
}

interface MarkdownRendererProps {
  content: string
  toolCalls?: ToolCall[]
  className?: string
}

export const MarkdownRenderer = React.memo(function MarkdownRenderer({
  content,
  toolCalls,
  className = "prose prose-lg max-w-none"
}: MarkdownRendererProps) {
  const paragraphCounterRef = React.useRef(0)
  const preparedContent = React.useMemo(() => normalizeLatexDelimiters(content), [content])
  const containerClassName = React.useMemo(() => {
    const base = 'markdown-body prose prose-base sm:prose-sm md:prose-base prose-invert max-w-none text-slate-100'
    return className ? `${base} ${className}` : base
  }, [className])

  const citationLookup = React.useMemo(() => {
    const map: Record<string, { title?: string; url?: string; domain?: string }> = {}
    if (!toolCalls) return map

    const normalizeId = (value: unknown): string | undefined => {
      if (value === null || value === undefined) return undefined
      if (typeof value === 'number' && Number.isFinite(value)) {
        return String(value)
      }
      const text = String(value).trim()
      return text ? text : undefined
    }

    const computeDomain = (url?: string): string | undefined => {
      if (!url || typeof url !== 'string') return undefined
      const trimmed = url.trim()
      if (!trimmed) return undefined
      try {
        const parsed = new URL(trimmed.startsWith('http') ? trimmed : `https://${trimmed}`)
        return parsed.hostname.replace(/^www\./, '')
      } catch {
        return undefined
      }
    }

    const extractTitle = (value: any): string | undefined => {
      if (!value) return undefined
      if (typeof value === 'string') return value
      return (
        value.title ??
        value.name ??
        value.label ??
        value.text ??
        value.description ??
        value.content ??
        undefined
      )
    }

    const extractUrl = (value: any): string | undefined => {
      if (!value || typeof value !== 'object') return undefined
      const candidates = [value.url, value.link, value.source, value.href]
      for (const candidate of candidates) {
        if (typeof candidate === 'string' && candidate.trim()) {
          return candidate.trim()
        }
      }
      return undefined
    }

    const extractDomain = (value: any, fallbackUrl?: string): string | undefined => {
      if (value && typeof value === 'object') {
        const domainCandidates = [value.domain, value.source_domain, value.host, value.hostname]
        for (const candidate of domainCandidates) {
          if (typeof candidate === 'string' && candidate.trim()) {
            return candidate.trim().replace(/^www\./, '')
          }
        }
      }
      return computeDomain(fallbackUrl)
    }

    const upsertCitation = (idRaw: unknown, value: any) => {
      const id = normalizeId(idRaw)
      if (!id) return

      const existing = map[id] ?? {}
      const title = extractTitle(value)
      const url = extractUrl(value)
      const domain = extractDomain(value, url ?? existing.url)

      if (title && !existing.title) existing.title = title
      if (url && !existing.url) existing.url = url
      if (domain && !existing.domain) existing.domain = domain

      map[id] = existing
    }

    const collectArray = (candidate: any): any[] => {
      if (!candidate) return []
      if (Array.isArray(candidate)) return candidate
      if (typeof candidate === 'object') {
        try {
          return Object.values(candidate)
        } catch {
          return []
        }
      }
      return []
    }

    for (const call of toolCalls) {
      const result = call.result as any
      if (!result) continue

      if (result.citations && typeof result.citations === 'object') {
        for (const [id, value] of Object.entries(result.citations)) {
          upsertCitation(id, value)
        }
      }

      const sourceBuckets = [
        collectArray(result.sources),
        collectArray(result.raw_sources),
        collectArray(result.source_documents),
        collectArray(result.citation_sources)
      ]

      for (const bucket of sourceBuckets) {
        for (const item of bucket) {
          if (!item || typeof item !== 'object') continue
          const idCandidate =
            (item as any).citation_id ??
            (item as any).citationId ??
            (item as any).id
          upsertCitation(idCandidate, item)
        }
      }
    }

    return map
  }, [toolCalls])

  React.useEffect(() => {
    paragraphCounterRef.current = 0
  }, [content])
  // Helper function to find source information from tool calls
  const findSourceInfo = React.useCallback(
    (citationNum: string) => citationLookup[citationNum] ?? {},
    [citationLookup]
  )

  const normalizeCitationText = React.useCallback(
    (input: string): string => {
      if (!input || !Object.keys(citationLookup).length) return input
      let normalized = input

      normalized = normalized.replace(/\*(\d{1,3})/g, (match, id: string) =>
        citationLookup[id] ? `[${id}]` : match
      )

      normalized = normalized.replace(/[（(](\d{1,3})[）)]/g, (match, id: string) =>
        citationLookup[id] ? `[${id}]` : match
      )

      normalized = normalized.replace(/([\s\u3000])(\d{1,3})(?=[。．、，・:：])/g, (match, space, id: string) =>
        citationLookup[id] ? `${space}[${id}]` : match
      )

      return normalized
    },
    [citationLookup]
  )

  // Process text content to replace citations with CitationLink components
  const processCitations = (text: any): any => {
    if (typeof text === 'string') {
      const normalized = normalizeCitationText(text)
      // Replace citation patterns like [1] with CitationLink components
      return normalized.split(/(\[\d+\])/g).map((part, index) => {
        if (/^\[\d+\]$/.test(part)) {
          const citationNum = part.slice(1, -1)
          const sourceInfo = findSourceInfo(citationNum)
          return (
            <CitationLink
              key={index}
              citationNum={citationNum}
              sourceInfo={Object.keys(sourceInfo).length ? sourceInfo : undefined}
            />
          )
        }
        return part
      })
    }
    return text
  }

  const renderChildrenWithCitations = React.useCallback(
    (children: React.ReactNode): React.ReactNode => {
      return React.Children.map(children, child => {
        if (typeof child === 'string') {
          return processCitations(child)
        }
        if (React.isValidElement(child) && child.props && child.props.children) {
          return React.cloneElement(child, {
            ...child.props,
            children: renderChildrenWithCitations(child.props.children)
          })
        }
        return child
      })
    },
    [processCitations]
  )

  return (
    <div className={containerClassName}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeKatex]}
        className="markdown-body-content text-[15px] leading-7 text-slate-100"
        components={{
          p: ({ children, node, ...rest }) => {
            // Determine paragraph index for stagger (count only previous p siblings)
            let index = 0
            if (node && node.position) {
              // Fallback simple increment based on existing rendered count
              // (We could lift state but keep lightweight)
              index = (paragraphCounterRef.current += 1) - 1
            }

            const processedChildren = renderChildrenWithCitations(children)

            return (
              <p
                {...rest}
                className="answer-paragraph mb-4 last:mb-0 text-[15px] leading-7 text-slate-100"
                style={{ animationDelay: `${Math.min(index * 90, 600)}ms` }}
              >
                {processedChildren}
              </p>
            )
          },
          ul: ({ children, ...rest }) => (
            <ul
              {...rest}
              className="my-4 ml-5 space-y-3 list-disc marker:text-blue-300"
            >
              {renderChildrenWithCitations(children)}
            </ul>
          ),
          ol: ({ children, ...rest }) => (
            <ol
              {...rest}
              className="my-4 ml-5 space-y-3 list-decimal marker:text-blue-300 marker:font-semibold"
            >
              {renderChildrenWithCitations(children)}
            </ol>
          ),
          li: ({ children, ...rest }) => (
            <li
              {...rest}
              className="leading-relaxed text-slate-100"
            >
              {renderChildrenWithCitations(children)}
            </li>
          ),
          h1: ({ children, ...rest }) => (
            <h1
              {...rest}
              className="mt-6 text-[1.45rem] font-semibold text-slate-50"
            >
              {renderChildrenWithCitations(children)}
            </h1>
          ),
          h2: ({ children, ...rest }) => (
            <h2
              {...rest}
              className="mt-6 text-[1.25rem] font-semibold text-slate-50"
            >
              {renderChildrenWithCitations(children)}
            </h2>
          ),
          h3: ({ children, ...rest }) => (
            <h3
              {...rest}
              className="mt-5 text-[1.1rem] font-semibold text-slate-100"
            >
              {renderChildrenWithCitations(children)}
            </h3>
          ),
          h4: ({ children, ...rest }) => (
            <h4
              {...rest}
              className="mt-4 text-[1rem] font-semibold text-slate-100"
            >
              {renderChildrenWithCitations(children)}
            </h4>
          ),
          blockquote: ({ children, ...rest }) => (
            <blockquote
              {...rest}
              className="relative my-5 rounded-xl border border-blue-500/30 bg-blue-500/10 px-5 py-4 text-[15px] leading-7 text-slate-100 shadow-inner"
            >
              <span aria-hidden className="absolute left-0 top-0 h-full w-1 rounded-l-xl bg-blue-400/80" />
              <div className="space-y-2 text-sm text-slate-100/90">
                {renderChildrenWithCitations(children)}
              </div>
            </blockquote>
          ),
          code: (props: any) => {
            const { inline, children, ...rest } = props
            if (inline) {
              return (
                <code
                  {...rest}
                  className="rounded-md bg-slate-800/70 px-1.5 py-0.5 text-xs font-medium text-blue-200"
                >
                  {children}
                </code>
              )
            }
            return (
              <code {...rest} className="text-[13px]">
                {children}
              </code>
            )
          },
          pre: ({ children, ...rest }) => (
            <pre
              {...rest}
              className="my-5 overflow-x-auto rounded-xl border border-slate-700/70 bg-slate-900/80 p-4 text-[13px] text-slate-100 shadow-inner"
            >
              {children}
            </pre>
          ),
          table: ({ children, ...rest }) => (
            <div className="my-5 overflow-x-auto rounded-xl border border-slate-700/70 bg-slate-900/60">
              <table
                {...rest}
                className="w-full text-left text-sm text-slate-100"
              >
                {children}
              </table>
            </div>
          ),
          thead: ({ children, ...rest }) => (
            <thead {...rest} className="bg-slate-800/80 text-xs uppercase tracking-wide text-slate-300">
              {children}
            </thead>
          ),
          tbody: ({ children, ...rest }) => (
            <tbody {...rest} className="divide-y divide-slate-800/80">
              {children}
            </tbody>
          ),
          tr: ({ children, ...rest }) => (
            <tr
              {...rest}
              className="transition-colors hover:bg-slate-800/60"
            >
              {children}
            </tr>
          ),
          th: ({ children, ...rest }) => (
            <th
              {...rest}
              className="px-4 py-3 font-medium text-slate-200"
            >
              {children}
            </th>
          ),
          td: ({ children, ...rest }) => (
            <td
              {...rest}
              className="px-4 py-3 align-top text-slate-100/90"
            >
              {renderChildrenWithCitations(children)}
            </td>
          ),
          hr: (props) => <hr {...props} className="my-6 border-slate-700/60" />,
          strong: ({ children, ...rest }) => (
            <strong
              {...rest}
              className="font-semibold text-slate-50"
            >
              {renderChildrenWithCitations(children)}
            </strong>
          ),
          em: ({ children, ...rest }) => (
            <em
              {...rest}
              className="text-slate-200"
            >
              {renderChildrenWithCitations(children)}
            </em>
          ),
          a: ({ children, ...rest }) => (
            <a
              {...rest}
              className="font-medium text-sky-300 underline decoration-sky-500/50 decoration-2 underline-offset-4 transition hover:text-sky-200"
              target="_blank"
              rel="noreferrer"
            >
              {renderChildrenWithCitations(children)}
            </a>
          )
        }}
      >
        {preparedContent}
      </ReactMarkdown>
    </div>
  )
})

MarkdownRenderer.displayName = 'MarkdownRenderer'