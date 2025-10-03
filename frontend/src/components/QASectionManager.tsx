import React, { useCallback, useMemo, useRef, useState } from 'react'
import { QASection } from './QASection'

// Import types from App.tsx temporarily (should be moved to shared types file)
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{ id: string; name: string; result: unknown }>
  timestamp: Date
}

type LiveTool = { name: string; status: 'running' | 'completed' | 'error'; error?: string }

interface QASectionManagerProps {
  messages: Message[]
  activeTools?: LiveTool[]
  isStreaming?: boolean
  onStickyStateChange?: (questionId: string, isStuck: boolean) => void
}

export const QASectionManager = React.memo(function QASectionManager({
  messages,
  activeTools = [],
  isStreaming = false,
  onStickyStateChange
}: QASectionManagerProps) {
  // Track active tabs for each message
  const [activeTab, setActiveTab] = useState<Record<string, 'answer' | 'sources' | 'steps'>>({})
  
  // Track currently stuck headers for better management
  const [stuckHeaders, setStuckHeaders] = useState<Set<string>>(new Set())

  // Group messages into Q/A pairs
  const qaPairs = useMemo(() => {
    const pairs: Array<{
      userMessage: Message
      assistantMessage?: Message
      id: string
    }> = []

    for (let i = 0; i < messages.length; i++) {
      const message = messages[i]
      
      // Ensure message exists and is a user message
      if (message && message.role === 'user') {
        const nextMessage = messages[i + 1]
        const assistantMessage = nextMessage && nextMessage.role === 'assistant' ? nextMessage : undefined
        
        pairs.push({
          userMessage: message,
          assistantMessage,
          id: message.id
        })
      }
    }

    return pairs
  }, [messages])

  // Handle tab changes for individual Q/A pairs
  const handleTabChange = useCallback((messageId: string, tab: 'answer' | 'sources' | 'steps') => {
    setActiveTab(prev => ({
      ...prev,
      [messageId]: tab
    }))
  }, [])

  // Handle sticky state changes
  const handleStickyStateChange = useCallback((messageId: string, isStuck: boolean) => {
    setStuckHeaders(prev => {
      const newSet = new Set(prev)
      if (isStuck) {
        newSet.add(messageId)
      } else {
        newSet.delete(messageId)
      }
      return newSet
    })
    
    // Notify parent component
    onStickyStateChange?.(messageId, isStuck)
  }, [onStickyStateChange])

  // Get current tab for a message (default to 'answer')
  const getCurrentTab = useCallback((messageId: string): 'answer' | 'sources' | 'steps' => {
    return activeTab[messageId] || 'answer'
  }, [activeTab])

  // Determine if this is the streaming message (last assistant message)
  const getStreamingStatus = useCallback((assistantMessage?: Message) => {
    if (!isStreaming || !assistantMessage) return false
    
    // Check if this is the last assistant message and if it's empty/streaming
    const lastMessage = messages[messages.length - 1]
    return lastMessage?.id === assistantMessage.id && 
           (!assistantMessage.content || assistantMessage.content.trim() === '')
  }, [isStreaming, messages])

  return (
    <div className="qa-section-manager">
      {qaPairs.map((pair, index) => {
        const isLastPair = index === qaPairs.length - 1
        const isStreamingThisPair = isLastPair && getStreamingStatus(pair.assistantMessage)
        const currentActiveTools = isStreamingThisPair ? activeTools : []

        return (
          <QASection
            key={pair.id}
            userMessage={pair.userMessage}
            assistantMessage={pair.assistantMessage}
            isActive={stuckHeaders.has(pair.userMessage.id)}
            activeTools={currentActiveTools}
            isStreaming={isStreamingThisPair}
            currentTab={pair.assistantMessage ? getCurrentTab(pair.assistantMessage.id) : 'answer'}
            onTabChange={(tab) => {
              if (pair.assistantMessage) {
                handleTabChange(pair.assistantMessage.id, tab)
              }
            }}
            onStickyStateChange={(isStuck) => {
              handleStickyStateChange(pair.userMessage.id, isStuck)
            }}
          />
        )
      })}

      {/* Show loading state for new user message without assistant response */}
      {isStreaming && qaPairs.length > 0 && !qaPairs[qaPairs.length - 1]?.assistantMessage && (
        <div className="qa-loading bg-gray-900">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-1">
                <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm">🤖</span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-gray-400 py-2">
                <span className="sr-only">Assistant is thinking</span>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
})

QASectionManager.displayName = 'QASectionManager'