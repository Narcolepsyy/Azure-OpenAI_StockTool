/**
 * Sidebar component for chat navigation
 */

import React from 'react'
import { 
  Menu, 
  Plus, 
  Search as SearchIcon, 
  Settings, 
  LogOut, 
  User as UserIcon,
  MessageCircle,
  Trash2
} from 'lucide-react'
import { Button } from '../ui'
import type { ChatSession, User } from '../../types'
import { translate, type Locale } from '../../i18n'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import clsx from 'clsx'

export interface SidebarProps {
  isExpanded: boolean
  onToggleExpanded: () => void
  sessions: ChatSession[]
  currentSessionId: string | null
  user: User
  locale: Locale
  onNewChat: () => void
  onSearchClick: () => void
  onSessionClick: (sessionId: string) => void
  onSessionDelete: (sessionId: string) => void
  onSettingsClick: () => void
  onLogoutClick: () => void
  showUserMenu: boolean
  onUserMenuToggle: () => void
}

// Session item component
const SessionItem: React.FC<{
  session: ChatSession
  isActive: boolean
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
}> = ({ session, isActive, onClick, onDelete }) => (
  <div
    className={clsx(
      'group flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors',
      isActive
        ? 'bg-gray-700 text-white'
        : 'hover:bg-gray-700 text-gray-300'
    )}
    onClick={onClick}
  >
    <div className="flex items-center space-x-3 flex-1 min-w-0">
      <MessageCircle className="w-4 h-4 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ node, ...props }) => <span {...props} />,
              a: ({ node, ...props }) => <span {...props} />,
              h1: 'span', h2: 'span', h3: 'span', h4: 'span', h5: 'span', h6: 'span',
              ul: 'span', ol: 'span', li: 'span',
              blockquote: 'span', pre: 'span', table: 'span',
              thead: 'span', tbody: 'span', tr: 'span', td: 'span', th: 'span',
            }}
          >
            {session.title}
          </ReactMarkdown>
        </div>
      </div>
    </div>

    <button
      onClick={onDelete}
      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-600 transition-all flex-shrink-0"
    >
      <Trash2 className="w-4 h-4" />
    </button>
  </div>
)

const Sidebar: React.FC<SidebarProps> = ({
  isExpanded,
  onToggleExpanded,
  sessions,
  currentSessionId,
  user,
  locale,
  onNewChat,
  onSearchClick,
  onSessionClick,
  onSessionDelete,
  onSettingsClick,
  onLogoutClick,
  showUserMenu,
  onUserMenuToggle
}) => {
  if (!isExpanded) {
    // Collapsed sidebar
    return (
      <div 
        className="h-full flex flex-col cursor-pointer"
        onClick={onToggleExpanded}
      >
        {/* Top Section */}
        <div className="flex-1 p-2">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-center p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white">
              <Menu className="w-5 h-5" />
            </div>
            
            <div 
              className="flex items-center justify-center p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
              onClick={(e) => {
                e.stopPropagation()
                onNewChat()
              }}
            >
              <Plus className="w-5 h-5" />
            </div>
            
            <div 
              className="flex items-center justify-center p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                onSearchClick()
              }}
              title="Search chats"
            >
              <SearchIcon className="w-5 h-5" />
            </div>
          </div>
        </div>
        
        {/* Bottom Section - User Profile */}
        <div className="p-2 border-t border-gray-700">
          <div className="relative" data-user-menu>
            <div 
              className="flex items-center justify-center p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
              onClick={(e) => {
                e.stopPropagation()
                onUserMenuToggle()
              }}
            >
              <UserIcon className="w-5 h-5" />
            </div>
            
            {showUserMenu && (
              <div className="absolute bottom-full left-12 mb-2 w-48 bg-gray-800 border border-gray-600 rounded-lg shadow-lg">
                <div className="py-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onSettingsClick()
                    }}
                    className="w-full flex items-center px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                  >
                    <Settings className="w-4 h-4 mr-3" />
                    Settings
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onLogoutClick()
                    }}
                    className="w-full flex items-center px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                  >
                    <LogOut className="w-4 h-4 mr-3" />
                    Log out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Expanded sidebar
  return (
    <>
      {/* Top section with expanded icons */}
      <div className="p-2 space-y-1">
        <div 
          className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-300 hover:text-white cursor-pointer w-full"
          onClick={onToggleExpanded}
        >
          <Menu className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium truncate">Close sidebar</span>
        </div>
        
        <div 
          className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-300 hover:text-white cursor-pointer w-full"
          onClick={onNewChat}
        >
          <Plus className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium truncate">New chat</span>
        </div>
        
        <div 
          className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-300 hover:text-white cursor-pointer w-full"
          onClick={onSearchClick}
          title="Search chats (⌘K)"
        >
          <SearchIcon className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium truncate">Search chats</span>
        </div>
      </div>

      {/* Chat Sessions List */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-2 pb-2">
          <div className="text-xs font-medium text-gray-500 mb-2 px-2">Recent</div>
          <div className="space-y-1">
            {sessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <MessageCircle className="w-12 h-12 text-gray-600 mb-3" />
                <p className="text-gray-400 text-sm">{translate('noChatsYet', locale)}</p>
                <p className="text-gray-500 text-xs mt-1">
                  {translate('clickNewChat', locale)}
                </p>
              </div>
            ) : (
              sessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={currentSessionId === session.id}
                  onClick={() => onSessionClick(session.id)}
                  onDelete={(e) => {
                    e.stopPropagation()
                    onSessionDelete(session.id)
                  }}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Bottom section - User profile */}
      <div className="p-2 border-t border-gray-700">
        <div className="relative" data-user-menu>
          <div 
            className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-300 hover:text-white cursor-pointer w-full"
            onClick={onUserMenuToggle}
          >
            <UserIcon className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-medium truncate">{user.username}</span>
          </div>
          
          {showUserMenu && (
            <div className="absolute bottom-full left-0 mb-2 w-full bg-gray-800 border border-gray-600 rounded-lg shadow-lg">
              <div className="py-1">
                <button
                  onClick={onSettingsClick}
                  className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  <Settings className="w-4 h-4 flex-shrink-0" />
                  <span>Settings</span>
                </button>
                <button
                  onClick={onLogoutClick}
                  className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                >
                  <LogOut className="w-4 h-4 flex-shrink-0" />
                  <span>Log out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export { Sidebar }