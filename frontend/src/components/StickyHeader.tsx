import React from 'react'
import clsx from 'clsx'
import { MessageSquare, Search, Activity } from 'lucide-react'
import { MessageContent } from '.'

// Type definitions
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{ id: string; name: string; result: unknown }>
  timestamp: Date
}

type TabType = 'answer' | 'sources' | 'steps'

interface StickyHeaderProps {
  userMessage: Message
  assistantMessage?: Message
  currentTab: TabType
  onTabChange: (tab: TabType) => void
  sourcesCount: number
  stepsCount: number
  messagesContainerRef?: React.RefObject<HTMLDivElement>
  headerRef: React.RefObject<HTMLDivElement>
  isStreaming?: boolean
  isLoading?: boolean
}

export const StickyHeader = React.memo(function StickyHeader({
  userMessage,
  assistantMessage,
  currentTab,
  onTabChange,
  sourcesCount,
  stepsCount,
  messagesContainerRef,
  headerRef,
  isStreaming = false,
  isLoading = false
}: StickyHeaderProps) {
  // Refs for tabs to calculate sliding indicator
  const answerRef = React.useRef<HTMLButtonElement | null>(null)
  const sourcesRef = React.useRef<HTMLButtonElement | null>(null)
  const stepsRef = React.useRef<HTMLButtonElement | null>(null)
  const indicatorRef = React.useRef<HTMLDivElement | null>(null)

  // Update indicator position whenever currentTab changes
  React.useEffect(() => {
    const map: Record<string, React.RefObject<HTMLButtonElement>> = {
      answer: answerRef,
      sources: sourcesRef,
      steps: stepsRef
    }
    const activeRef = map[currentTab]
    if (activeRef?.current && indicatorRef.current) {
      const el = activeRef.current
      const rect = el.getBoundingClientRect()
      const parentRect = el.parentElement?.getBoundingClientRect()
      if (!parentRect) return
      const width = rect.width
      const offset = rect.left - parentRect.left
      indicatorRef.current.style.width = width + 'px'
      indicatorRef.current.style.transform = `translateX(${offset}px)`
      indicatorRef.current.style.opacity = '1'
    }
  }, [currentTab])
  // Simple tab change handler without automatic scrolling
  const handleTabChange = React.useCallback((tab: TabType) => {
    onTabChange(tab)
    
    // Remove automatic scrolling behavior to prevent header selection
    // Users can manually scroll if needed
  }, [onTabChange])

  // Keyboard navigation with arrow keys
  const handleKeyDownTabs = React.useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    e.preventDefault()
    const order: TabType[] = ['answer', 'sources', 'steps']
    const idx = order.indexOf(currentTab)
    if (idx === -1) return
  const nextIdx = e.key === 'ArrowRight' ? (idx + 1) % order.length : (idx - 1 + order.length) % order.length
  const nextTab = order[nextIdx] as TabType
  handleTabChange(nextTab)
    const refMap: Record<TabType, React.RefObject<HTMLButtonElement>> = {
      answer: answerRef,
      sources: sourcesRef,
      steps: stepsRef
    }
    requestAnimationFrame(() => refMap[nextTab].current?.focus())
  }, [currentTab, handleTabChange])

  return (
    <header 
      ref={headerRef}
      className="qa-header sticky top-0 z-50"
      data-message-id={userMessage.id}
      style={{ 
        backgroundColor: '#111827',
        borderBottom: '1px solid #374151',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}
    >
      {(isStreaming || isLoading) && (
        <div className="header-scanning-bar" />
      )}
      {/* Question Content */}
      <div className="qa-header-content max-w-xl mx-auto px-4 py-2">
        <div className="flex items-start">
          {/* Question Text */}
          <div className="flex-1 min-w-0">
            <h2 
              id={`question-${userMessage.id}`}
              className="text-sm font-bold text-white leading-snug qa-question-text"
              style={{
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden'
              }}
            >
              <MessageContent content={userMessage.content} role="user" />
            </h2>
          </div>
        </div>
      </div>

      {/* Tab Navigation - Show if we have an assistant message or if we're streaming/loading */}
      {(assistantMessage || isStreaming || isLoading) && (
        <div className="qa-tabs border-t border-gray-700/30">
          <div className="max-w-xl mx-auto px-4">
            <nav className="flex items-center py-2" role="tablist" onKeyDown={handleKeyDownTabs}>
              <div className="flex items-center bg-gray-800/50 rounded-md p-0.5 gap-0.5">
                {/* Answer Tab */}
                <button
                  ref={answerRef}
                  role="tab"
                  aria-selected={currentTab === 'answer'}
                  aria-controls={`answer-${assistantMessage?.id || userMessage.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleTabChange('answer')
                  }}
                  onMouseDown={(e) => e.preventDefault()} // Prevent focus change
                  className={clsx(
                    "flex items-center space-x-1.5 px-2.5 py-1 text-xs font-medium rounded transition-all duration-200 min-w-0",
                    currentTab === 'answer'
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-400 hover:text-white hover:bg-gray-700/40"
                  )}
                >
                  <MessageSquare className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">Answer</span>
                </button>

                {/* Sources Tab */}
                <button
                  ref={sourcesRef}
                  role="tab"
                  data-tab="sources"
                  aria-selected={currentTab === 'sources'}
                  aria-controls={`sources-${assistantMessage?.id || userMessage.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleTabChange('sources')
                  }}
                  onMouseDown={(e) => e.preventDefault()} // Prevent focus change
                  className={clsx(
                    "flex items-center space-x-1.5 px-2.5 py-1 text-xs font-medium rounded transition-all duration-200 min-w-0",
                    currentTab === 'sources'
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-400 hover:text-white hover:bg-gray-700/40"
                  )}
                >
                  <Search className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">Sources</span>
                  {/* Count badge removed per design update */}
                </button>

                {/* Steps Tab */}
                <button
                  ref={stepsRef}
                  role="tab"
                  aria-selected={currentTab === 'steps'}
                  aria-controls={`steps-${assistantMessage?.id || userMessage.id}`}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleTabChange('steps')
                  }}
                  onMouseDown={(e) => e.preventDefault()} // Prevent focus change
                  className={clsx(
                    "flex items-center space-x-1.5 px-2.5 py-1 text-xs font-medium rounded transition-all duration-200 min-w-0",
                    currentTab === 'steps'
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-400 hover:text-white hover:bg-gray-700/40"
                  )}
                >
                  <Activity className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">Steps</span>
                  {/* Count badge removed per design update */}
                </button>
                {/* Sliding indicator */}
                <div ref={indicatorRef} className="tab-indicator-bar" style={{ opacity: 0 }} />
              </div>
            </nav>
          </div>
        </div>
      )}
    </header>
  )
})

StickyHeader.displayName = 'StickyHeader'