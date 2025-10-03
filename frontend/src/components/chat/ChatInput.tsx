/**
 * Chat input component with model selector
 */

import React, { useRef, useEffect } from 'react'
import { Send, Square, Cpu } from 'lucide-react'
import { Button } from '../ui'
import type { ChatInputProps } from '../../types'
import ModelSelector from './ModelSelector'

const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSubmit,
  onStop,
  isLoading,
  isStreaming,
  disabled = false,
  placeholder = 'Type your message...',
  models,
  currentDeployment,
  onModelChange
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim() && !isLoading && !isStreaming) {
        onSubmit(e)
      }
    }
  }

  const canSubmit = !disabled && value.trim() && !isLoading && !isStreaming

  return (
    <div className="bg-gray-900 p-4 ">
      <div className="max-w-xl mx-auto">
        <form onSubmit={onSubmit} className="relative">
          <div className="chat-input-container relative flex items-end gap-2 p-2 bg-gray-800/95 backdrop-blur-sm border border-gray-600 rounded-xl shadow-lg hover:shadow-xl focus-within:shadow-xl focus-within:border-gray-400 focus-within:bg-gray-800 transition-all duration-200">
            
            {/* Model Selector */}
            {models && onModelChange && (
              <ModelSelector
                models={models}
                currentDeployment={currentDeployment || ''}
                onModelChange={onModelChange}
                onClose={() => {}}
              />
            )}
            
            {/* Text Input */}
            <div className="flex-1 min-w-0">
              <textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                className="w-full resize-none bg-transparent text-white placeholder-gray-500 focus:placeholder-gray-400 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 leading-relaxed transition-colors duration-200 text-sm"
                rows={1}
                style={{ 
                  minHeight: '16px', 
                  maxHeight: '120px',
                  paddingTop: '1px',
                  paddingBottom: '1px'
                }}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-end gap-1 flex-shrink-0">
              {isStreaming ? (
                <Button
                  type="button"
                  onClick={onStop}
                  variant="secondary"
                  size="sm"
                  className="p-2 rounded-xl"
                  title="Stop generating"
                >
                  <Square className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={!canSubmit}
                  loading={isLoading}
                  size="sm"
                  className="p-2 rounded-xl"
                  title="Send message"
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

export { ChatInput }