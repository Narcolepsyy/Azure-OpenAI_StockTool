/**
 * Search modal component for finding conversations
 */

import React from 'react'
import { X, Search as SearchIcon, MessageCircle } from 'lucide-react'
import { Modal } from './ui'
import { translate, type Locale } from '../i18n'
import { chatSessionUtils } from '../utils'
import type { ChatSession } from '../types'

export interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
  query: string
  onQueryChange: (query: string) => void
  sessions: ChatSession[]
  onSessionSelect: (sessionId: string) => void
  locale: Locale
}

const SearchModal: React.FC<SearchModalProps> = ({
  isOpen,
  onClose,
  query,
  onQueryChange,
  sessions,
  onSessionSelect,
  locale
}) => {
  const filteredSessions = chatSessionUtils.filterSessions(sessions, query)
  const displaySessions = query.trim() ? filteredSessions : sessions.slice(0, 10)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="2xl"
    >
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Search Conversations</h3>
          <p className="text-xs text-gray-400 mt-1">
            Press <kbd className="px-1.5 py-0.5 bg-gray-700 rounded text-xs">⌘K</kbd> to search anytime
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search your conversations..."
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          autoFocus
        />
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {displaySessions.length === 0 && query.trim() ? (
          <div className="text-center py-8 text-gray-400">
            <SearchIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No conversations found for "{query}"</p>
          </div>
        ) : displaySessions.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No conversations yet</p>
            <p className="text-xs mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          displaySessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSessionSelect(session.id)}
              className="w-full text-left p-3 rounded-lg hover:bg-gray-700 transition-colors border border-transparent hover:border-gray-600"
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-medium text-white truncate">
                    {session.title}
                  </h4>
                  <p className="text-xs text-gray-400 truncate mt-1">
                    {session.lastMessage || 'No messages yet'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {session.timestamp.toLocaleDateString()} • {session.messageCount} messages
                  </p>
                </div>
                <div className="ml-3 flex-shrink-0">
                  <MessageCircle className="w-4 h-4 text-gray-500" />
                </div>
              </div>
            </button>
          ))
        )}
      </div>

      {!query.trim() && (
        <div className="mt-4 text-xs text-gray-500 text-center">
          Showing recent conversations. Start typing to search.
        </div>
      )}
    </Modal>
  )
}

export default SearchModal