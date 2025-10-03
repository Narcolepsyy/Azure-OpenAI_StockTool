/**
 * Welcome screen component for when no chat session is active
 */

import React, { useState } from 'react'
import { TrendingUp, Wrench } from 'lucide-react'
import { ChatInput, ErrorDisplay, NetworkStatusIndicator } from './chat'
import { Sidebar } from './layout'
import SearchModal from './SearchModal'
import ToolsRegistry from './ToolsRegistry'
import { SettingsModal, LogoutModal } from './modals'
import { Button, Modal } from './ui'
import { translate, type Locale } from '../i18n'
import type { 
  User, 
  ModelsResponse, 
  ChatSession, 
  UIState, 
  AppSettings,
  NetworkStatusProps 
} from '../types'
import clsx from 'clsx'

export interface WelcomeScreenProps {
  user: User
  locale: Locale
  models: ModelsResponse | null
  currentDeployment: string
  prompt: string
  onPromptChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  onModelChange: (modelId: string) => void
  isLoading: boolean
  isStreaming: boolean
  error: string | null
  onErrorDismiss: () => void
  onStopGeneration: () => void
  networkStatus: NetworkStatusProps
  chatSessions: ChatSession[]
  uiState: UIState
  onUIStateChange: (updater: (prev: UIState) => UIState) => void
  settings: AppSettings
  onSettingsChange: (updater: (prev: AppSettings) => AppSettings) => void
  onNewChat: () => void
  onSessionSelect: (sessionId: string) => void
  onSessionDelete: (sessionId: string) => void
  onLogout: () => void
}

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  user,
  locale,
  models,
  currentDeployment,
  prompt,
  onPromptChange,
  onSubmit,
  onModelChange,
  isLoading,
  isStreaming,
  error,
  onErrorDismiss,
  onStopGeneration,
  networkStatus,
  chatSessions,
  uiState,
  onUIStateChange,
  settings,
  onSettingsChange,
  onNewChat,
  onSessionSelect,
  onSessionDelete,
  onLogout
}) => {
  const [showToolsRegistry, setShowToolsRegistry] = useState(false)
  return (
    <div className="relative h-screen min-h-0 bg-gray-900">
      {/* Sidebar */}
      <div className={clsx(
        'fixed left-0 top-0 h-full z-50 transition-all duration-300',
        uiState.isLeftSidebarExpanded ? 'w-80' : 'w-12'
      )}>
        <div className="h-full bg-gray-800/90 backdrop-blur-sm border-r border-gray-700 flex flex-col">
          <Sidebar
            isExpanded={uiState.isLeftSidebarExpanded}
            onToggleExpanded={() => 
              onUIStateChange(prev => ({ 
                ...prev, 
                isLeftSidebarExpanded: !prev.isLeftSidebarExpanded 
              }))
            }
            sessions={chatSessions}
            currentSessionId={null}
            user={user}
            locale={locale}
            onNewChat={onNewChat}
            onSearchClick={() => 
              onUIStateChange(prev => ({ ...prev, showSearchModal: true }))
            }
            onSessionClick={onSessionSelect}
            onSessionDelete={onSessionDelete}
            onSettingsClick={() => 
              onUIStateChange(prev => ({ 
                ...prev, 
                showSettings: true, 
                showUserMenu: false 
              }))
            }
            onLogoutClick={() => 
              onUIStateChange(prev => ({ 
                ...prev, 
                showLogoutConfirm: true, 
                showUserMenu: false 
              }))
            }
            showUserMenu={uiState.showUserMenu}
            onUserMenuToggle={() =>
              onUIStateChange(prev => ({ ...prev, showUserMenu: !prev.showUserMenu }))
            }
          />
        </div>
      </div>

      {/* Centered Welcome Content */}
      <div className="absolute inset-0 flex flex-col bg-gray-900">
        <div className="flex-1 flex flex-col items-center justify-center min-h-0 p-4 md:p-6">
          <div className="w-full max-w-2xl flex flex-col items-center justify-center text-center welcome-entrance">
            {/* App Icon and Title */}
            <div className="mb-6 md:mb-8">
              <div className="welcome-icon mb-4">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full">
                  <TrendingUp className="w-8 h-8 text-blue-600" />
                </div>
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
                {translate('appTitle', locale)}
              </h1>
              <p className="text-sm md:text-base text-gray-400 mb-8 max-w-xl mx-auto leading-relaxed">
                {translate('appSubtitle', locale)}
              </p>
            </div>

            {/* Main Input */}
            <div className="w-full max-w-2xl mb-6">
              <ChatInput
                value={prompt}
                onChange={onPromptChange}
                onSubmit={onSubmit}
                onStop={onStopGeneration}
                isLoading={isLoading}
                isStreaming={isStreaming}
                placeholder={translate('placeholder', locale)}
                models={models || undefined}
                currentDeployment={currentDeployment}
                onModelChange={onModelChange}
              />
            </div>

            {/* Network Status Indicator */}
            <div className="mb-4 w-full flex justify-center">
              <NetworkStatusIndicator 
                isOnline={networkStatus.isOnline} 
                connectionQuality={networkStatus.connectionQuality}
              />
            </div>

            {/* Error Display */}
            {error && (
              <div className="mb-4 w-full max-w-2xl">
                <ErrorDisplay 
                  error={error} 
                  onRetry={onSubmit}
                  onDismiss={onErrorDismiss}
                  canRetry={!!prompt.trim() && !isLoading && !isStreaming}
                />
              </div>
            )}

            {/* Quick actions or suggestions */}
            <div className="text-center">
              <p className="text-xs text-gray-400 mb-3">
                Ask about stocks, market analysis, or financial insights
              </p>
              
              {/* Action Buttons */}
              <div className="flex flex-wrap justify-center gap-2 mb-4">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowToolsRegistry(true)}
                  className="inline-flex items-center gap-2 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 border-gray-600"
                >
                  <Wrench className="w-3 h-3" />
                  View Available Tools
                </Button>
              </div>
              
              <div className="flex flex-wrap justify-center gap-1.5 text-xs">
                <span className="px-2.5 py-1 bg-blue-800/50 text-blue-300 rounded-full hover:bg-blue-700/50 transition-colors cursor-default">
                  Stock Analysis
                </span>
                <span className="px-2.5 py-1 bg-green-800/50 text-green-300 rounded-full hover:bg-green-700/50 transition-colors cursor-default">
                  Market Data
                </span>
                <span className="px-2.5 py-1 bg-purple-800/50 text-purple-300 rounded-full hover:bg-purple-700/50 transition-colors cursor-default">
                  Financial News
                </span>
                <span className="px-2.5 py-1 bg-amber-800/50 text-amber-300 rounded-full hover:bg-amber-700/50 transition-colors cursor-default">
                  Risk Assessment
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={uiState.showSettings}
        onClose={() => onUIStateChange(prev => ({ ...prev, showSettings: false }))}
        settings={settings}
        onSettingsChange={onSettingsChange}
        models={models}
        locale={locale}
      />

      {/* Tools Registry Modal */}
      <Modal
        isOpen={showToolsRegistry}
        onClose={() => setShowToolsRegistry(false)}
        title="Available Tools"
        maxWidth="6xl"
        className="!p-4"
      >
        <div className="max-h-[75vh] overflow-y-auto px-2">
          <ToolsRegistry />
        </div>
      </Modal>

      {/* Logout Confirmation Modal */}
      <LogoutModal
        isOpen={uiState.showLogoutConfirm}
        onClose={() => onUIStateChange(prev => ({ ...prev, showLogoutConfirm: false }))}
        onConfirm={onLogout}
        locale={locale}
      />

      {/* Search Modal */}
      <SearchModal
        isOpen={uiState.showSearchModal}
        onClose={() => 
          onUIStateChange(prev => ({ 
            ...prev, 
            showSearchModal: false, 
            searchModalQuery: '' 
          }))
        }
        query={uiState.searchModalQuery}
        onQueryChange={(query: string) => 
          onUIStateChange(prev => ({ 
            ...prev, 
            searchModalQuery: query 
          }))
        }
        sessions={chatSessions}
        onSessionSelect={(sessionId: string) => {
          onSessionSelect(sessionId)
          onUIStateChange(prev => ({ 
            ...prev, 
            showSearchModal: false, 
            searchModalQuery: '' 
          }))
        }}
        locale={locale}
      />
    </div>
  )
}

export default WelcomeScreen