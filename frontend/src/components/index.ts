// Main component exports
export { QASection } from './QASection'
export { StickyHeader } from './StickyHeader'
export { MessageContent } from './MessageContent'
export { MarkdownRenderer } from './MarkdownRenderer'
export { CitationLink } from './CitationLink'

// Tab panel exports
export { 
  AnswerTabPanel, 
  SourcesTabPanel, 
  StepsTabPanel 
} from './TabPanels'

// Tool components exports
export { ToolCallsPanel } from './ToolCallsPanel'
export { ToolCard } from './ToolCard'
export { WebSearchLinks } from './WebSearchLinks'
export { StructuredResults } from './StructuredResults'

// Hook exports
export { useSticky } from '../hooks/useSticky'

// Type definitions
export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{ id: string; name: string; result: unknown }>
  timestamp: Date
}

export type LiveTool = { 
  name: string
  status: 'running' | 'completed' | 'error'
  error?: string 
}

export type ToolCall = {
  id: string
  name: string
  result: unknown
}

export type TabType = 'answer' | 'sources' | 'steps'

export type CitationInfo = {
  title?: string
  url?: string
  domain?: string
}

export type WebSearchLink = {
  title: string
  url: string
  snippet?: string
  domain?: string
  citationId?: number
  publishDate?: string
  wordCount?: number
  faviconUrl?: string
}