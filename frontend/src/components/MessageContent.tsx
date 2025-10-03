import React, { useCallback } from 'react'
import { ExternalLink } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'

// Type definitions
type ToolCall = {
  id: string
  name: string
  result: unknown
}

interface MessageContentProps {
  content: string
  role: 'user' | 'assistant'
  toolCalls?: ToolCall[]
}

export const MessageContent = React.memo(function MessageContent({ 
  content, 
  role,
  toolCalls
}: MessageContentProps) {
  const renderWithLinks = useCallback((text?: string): React.ReactNode => {
    if (!text) return null
    const rgx = /(https:\/\/[^\s<>()]+[^\s<>().,!?;:])/g
    const out: React.ReactNode[] = []
    let lastIdx = 0
    let m: RegExpExecArray | null
    
    while ((m = rgx.exec(text)) !== null) {
      const start = m.index
      const end = start + m[0].length
      if (start > lastIdx) out.push(text.slice(lastIdx, start))
      const url = m[0]
      out.push(
        <a 
          key={`url-${start}-${end}`} 
          href={url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-blue-400 hover:text-blue-300 underline inline-flex items-center gap-1"
        >
          {url}
          <ExternalLink className="w-3 h-3" />
        </a>
      )
      lastIdx = end
    }
    if (lastIdx < text.length) out.push(text.slice(lastIdx))
    return out
  }, [])

  if (role === 'user') {
    return (
      <span className="text-inherit">
        {renderWithLinks(content)}
      </span>
    )
  }

  return (
    <MarkdownRenderer 
      content={content} 
      toolCalls={toolCalls}
      className="prose prose-xs max-w-none text-sm" 
    />
  )
})

MessageContent.displayName = 'MessageContent'