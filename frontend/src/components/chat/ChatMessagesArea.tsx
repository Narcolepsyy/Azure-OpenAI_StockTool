/**
 * Chat Messages Area Component
 * Handles message display, scrolling, and active tools
 */

import React, { useRef, useCallback, useEffect, useState } from 'react'
import clsx from 'clsx'
import { QASection } from '../QASection'
import { translate } from '../../i18n'
import type { Message, TabType, LiveTool, ModelsResponse } from '../../types'

const BOTTOM_SCROLL_OFFSET = 96

interface ChatMessagesAreaProps {
  messages: Message[]
  isLoading: boolean
  isStreaming: boolean
  activeTools: LiveTool[]
  activeTab: Record<string, TabType>
  locale: 'en' | 'ja'
  models?: ModelsResponse | null
  deployment: string
  onTabChange: (messageId: string, tab: TabType) => void
  onRewriteMessage: (message: Message) => void
  onCopyAnswer: (message: Message) => void
}

export const ChatMessagesArea: React.FC<ChatMessagesAreaProps> = ({
  messages,
  isLoading,
  isStreaming,
  activeTools,
  activeTab,
  locale,
  models,
  deployment,
  onTabChange,
  onRewriteMessage,
  onCopyAnswer,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const messageRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const autoScrollLockRef = useRef(false)
  const [showScrollButton, setShowScrollButton] = useState(false)

  const isNearBottom = useCallback(() => {
    const el = scrollContainerRef.current
    if (!el) return true
    const threshold = 160
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
  }, [])

  const scrollToBottom = useCallback((opts: { smooth?: boolean; offset?: number } = {}) => {
    const el = scrollContainerRef.current
    if (!el) return
    const { smooth = true, offset } = opts
    const effectiveOffset = typeof offset === 'number' ? offset : BOTTOM_SCROLL_OFFSET
    const top = el.scrollHeight - el.clientHeight - effectiveOffset
    try {
      el.scrollTo({ top, behavior: smooth ? 'smooth' : 'auto' })
    } catch {
      el.scrollTop = top
    }
  }, [])

  const getCurrentTab = useCallback((messageId: string): TabType => {
    return activeTab[messageId] || 'answer'
  }, [activeTab])

  const handleTabChange = useCallback((messageId: string, tab: TabType) => {
    onTabChange(messageId, tab)

    requestAnimationFrame(() => {
      const el = messageRefs.current[messageId]
      if (el) {
        try {
          el.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' })
        } catch {
          const container = scrollContainerRef.current
          if (container) {
            container.scrollTop = el.offsetTop - 16
          }
        }
      }
    })
  }, [onTabChange])

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) return
    const handleScroll = () => {
      const near = isNearBottom()
      autoScrollLockRef.current = !near
      setShowScrollButton(!near)
    }

    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [isNearBottom])

  // Auto-scroll when streaming
  useEffect(() => {
    if (isStreaming && !autoScrollLockRef.current) {
      scrollToBottom({ smooth: true })
    }
  }, [messages, isStreaming, scrollToBottom])

  if (messages.length === 0) {
    return (
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
        <div className="p-4 flex items-center justify-center h-full">
          <div className="text-center max-w-md">
            <h3 className="text-xl font-semibold text-white mb-2">
              {translate('onboardingTitle', locale)}
            </h3>
            <p className="text-gray-400 mb-4">
              {translate('onboardingBody', locale)}
            </p>
            {models && deployment && (
              <div className="inline-flex items-center space-x-2 px-3 py-1 bg-blue-800/50 rounded-full text-sm text-blue-300">
                <span>
                  {translate('usingModel', locale)}{' '}
                  {models.available.find((m) => m.id === deployment)?.name || 'AI Model'}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto messages-scroll-container">
        <div className="p-4 space-y-5 min-h-full transition-[padding] duration-200 ease-out">
          {messages.reduce((acc: React.ReactNode[], message, index) => {
            if (message.role === 'user') {
              const assistantMessage =
                messages[index + 1]?.role === 'assistant'
                  ? messages[index + 1]
                  : undefined

              const isFirstQuestion = messages.length === 1 && index === 0
              const isLastUserMessage =
                index === messages.length - 1 ||
                (assistantMessage && index === messages.length - 2)

              const isCurrentlyStreaming =
                (isStreaming || isLoading) && (isFirstQuestion || isLastUserMessage)

              acc.push(
                <div
                  key={message.id}
                  ref={(el) => {
                    if (assistantMessage) {
                      messageRefs.current[assistantMessage.id] = el
                    }
                  }}
                  className="scroll-mt-20"
                >
                  <QASection
                    userMessage={message}
                    assistantMessage={assistantMessage}
                    isActive={false}
                    activeTools={isCurrentlyStreaming ? activeTools : []}
                    isStreaming={isCurrentlyStreaming}
                    isLoading={isLoading && (isFirstQuestion || isLastUserMessage)}
                    currentTab={assistantMessage ? getCurrentTab(assistantMessage.id) : 'answer'}
                    onTabChange={(tab) => {
                      if (assistantMessage) {
                        handleTabChange(assistantMessage.id, tab)
                      }
                    }}
                    onRewriteMessage={onRewriteMessage}
                    onCopyAnswer={onCopyAnswer}
                  />
                </div>
              )
            }
            return acc
          }, [])}

          {activeTools.length > 0 && (
            <div className="max-w-2xl mx-auto px-8 py-2">
              <div className="bg-gray-800 border border-blue-600 rounded-lg px-4 py-3 shadow-sm">
                <p className="text-xs font-medium text-blue-300 mb-2">
                  {translate('toolActivity', locale)}
                </p>
                <div className="space-y-1">
                  {activeTools.map((tool) => (
                    <div key={tool.name} className="flex items-center gap-2 text-xs">
                      <span className="text-gray-300">{tool.name}</span>
                      <span
                        className={clsx(
                          'px-2 py-0.5 rounded text-xs',
                          tool.status === 'running' && 'bg-blue-100 text-blue-800',
                          tool.status === 'completed' && 'bg-green-100 text-green-800',
                          tool.status === 'error' && 'bg-red-100 text-red-800'
                        )}
                      >
                        {tool.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <div aria-hidden="true" className="h-20 lg:h-24" />
        </div>
      </div>

      {/* Scroll to Bottom Button */}
      <div
        className={clsx(
          'absolute bottom-28 right-6 z-40 transition-all duration-300 ease-out',
          showScrollButton
            ? 'opacity-100 translate-y-0 pointer-events-auto'
            : 'opacity-0 translate-y-2 pointer-events-none'
        )}
        aria-hidden={!showScrollButton}
      >
        <button
          type="button"
          onClick={() => {
            scrollToBottom({ smooth: true })
            setShowScrollButton(false)
          }}
          className="group flex items-center gap-1 px-3 py-2 rounded-full bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shadow-lg shadow-black/40 border border-blue-400/40 transition-colors duration-300"
          aria-label="Scroll to bottom"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-4 h-4"
          >
            <path d="M19 9l-7 7-7-7" />
          </svg>
          <span className="hidden sm:inline">Scroll to bottom</span>
        </button>
      </div>
    </>
  )
}
