import React from 'react'
import { StickyHeader } from './StickyHeader'
import { AnswerTabPanel, SourcesTabPanel, StepsTabPanel } from './TabPanels'
import { useSticky } from '../hooks/useSticky'

// Define types locally (will eventually be moved to a shared types file)
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{ id: string; name: string; result: unknown }>
  timestamp: Date
}

type LiveTool = { name: string; status: 'running' | 'completed' | 'error'; error?: string }

interface QASectionProps {
  userMessage: Message
  assistantMessage?: Message
  isActive?: boolean
  activeTools?: LiveTool[]
  isStreaming?: boolean
  isLoading?: boolean
  currentTab: 'answer' | 'sources' | 'steps'
  onTabChange: (tab: 'answer' | 'sources' | 'steps') => void
  onStickyStateChange?: (isStuck: boolean, messageId: string) => void
  messagesContainerRef?: React.RefObject<HTMLDivElement>
  onRewriteMessage?: (userMessage: Message, assistantMessage?: Message) => void
  onCopyAnswer?: (assistantMessage: Message) => void
}

export const QASection = React.memo(function QASection({
  userMessage,
  assistantMessage,
  isActive = false,
  activeTools = [],
  isStreaming = false,
  isLoading = false,
  currentTab,
  onTabChange,
  onStickyStateChange,
  messagesContainerRef,
  onRewriteMessage,
  onCopyAnswer
}: QASectionProps) {
  // Use the sticky hook for intersection observer logic
  const headerRef = useSticky({
    onStickyStateChange,
    messageId: userMessage.id
  })

  // Count sources and steps for badges
  const sourcesCount = assistantMessage?.toolCalls?.length || 0
  const stepsCount = activeTools.length + sourcesCount

  return (
    <section 
      className="qa-section qa-section-enter" 
      aria-labelledby={`question-${userMessage.id}`}
      style={{ backgroundColor: '#111827' }}
    >
      {/* Sticky Header with Tab Navigation */}
      <StickyHeader
        userMessage={userMessage}
        assistantMessage={assistantMessage}
        currentTab={currentTab}
        onTabChange={onTabChange}
        sourcesCount={sourcesCount}
        stepsCount={stepsCount}
        messagesContainerRef={messagesContainerRef}
        headerRef={headerRef}
        isStreaming={isStreaming}
        isLoading={isLoading}
      />

      {/* Tab Content */}
      {(assistantMessage || isStreaming || isLoading) && (
        <div className="qa-body" style={{ backgroundColor: '#111827' }}>
          <div className="max-w-xl mx-auto px-4 py-4">
            {/* Answer Tab */}
            {currentTab === 'answer' && (
              <AnswerTabPanel
                assistantMessage={assistantMessage || {
                  id: `temp-${userMessage.id}`,
                  role: 'assistant' as const,
                  content: '',
                  timestamp: new Date()
                }}
                isStreaming={isStreaming || isLoading}
                onRewrite={assistantMessage && onRewriteMessage ? () => onRewriteMessage(userMessage, assistantMessage) : undefined}
                onCopy={assistantMessage && assistantMessage.content && onCopyAnswer ? () => onCopyAnswer(assistantMessage) : undefined}
                onSeeSources={assistantMessage ? () => onTabChange('sources') : undefined}
                hasSources={(assistantMessage?.toolCalls?.length ?? 0) > 0}
              />
            )}

            {/* Sources Tab */}
            {currentTab === 'sources' && assistantMessage && (
              <SourcesTabPanel assistantMessage={assistantMessage} />
            )}

            {/* Steps Tab */}
            {currentTab === 'steps' && (
              <StepsTabPanel
                assistantMessage={assistantMessage || {
                  id: `temp-${userMessage.id}`,
                  role: 'assistant' as const,
                  content: '',
                  timestamp: new Date()
                }}
                activeTools={activeTools}
                isStreaming={isStreaming || isLoading}
              />
            )}
          </div>
        </div>
      )}

      {/* Loading state for assistant response */}
      {!assistantMessage && isStreaming && (
        <div className="qa-body bg-gray-900">
          <div className="max-w-xl mx-auto px-4 py-4">
            <div className="flex items-center gap-2 text-gray-400 py-2">
              <span className="sr-only">Assistant is thinking</span>
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
          </div>
        </div>
      )}
    </section>
  )
})

QASection.displayName = 'QASection'