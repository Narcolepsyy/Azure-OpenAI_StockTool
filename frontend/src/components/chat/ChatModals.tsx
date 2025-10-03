/**
 * Chat Modals Container Component
 * Groups all modals used in chat layout
 */

import React from 'react'
import SearchModal from '../SearchModal'
import { SettingsModal, LogoutModal } from '../modals'
import type { ChatSession, AppSettings, ModelsResponse } from '../../types'

interface ChatModalsProps {
  // Settings Modal
  showSettings: boolean
  onSettingsClose: () => void
  settings: AppSettings
  onSettingsChange: (updater: (prev: AppSettings) => AppSettings) => void
  models: ModelsResponse | null
  
  // Logout Modal
  showLogoutConfirm: boolean
  onLogoutClose: () => void
  onLogoutConfirm: () => void
  
  // Search Modal
  showSearchModal: boolean
  onSearchClose: () => void
  searchModalQuery: string
  onSearchQueryChange: (query: string) => void
  sessions: ChatSession[]
  onSessionSelect: (sessionId: string) => void
  
  locale: 'en' | 'ja'
}

export const ChatModals: React.FC<ChatModalsProps> = ({
  showSettings,
  onSettingsClose,
  settings,
  onSettingsChange,
  models,
  showLogoutConfirm,
  onLogoutClose,
  onLogoutConfirm,
  showSearchModal,
  onSearchClose,
  searchModalQuery,
  onSearchQueryChange,
  sessions,
  onSessionSelect,
  locale,
}) => {
  return (
    <>
      <SettingsModal
        isOpen={showSettings}
        onClose={onSettingsClose}
        settings={settings}
        onSettingsChange={onSettingsChange}
        models={models}
        locale={locale}
      />

      <LogoutModal
        isOpen={showLogoutConfirm}
        onClose={onLogoutClose}
        onConfirm={onLogoutConfirm}
        locale={locale}
      />

      <SearchModal
        isOpen={showSearchModal}
        onClose={onSearchClose}
        query={searchModalQuery}
        onQueryChange={onSearchQueryChange}
        sessions={sessions}
        onSessionSelect={onSessionSelect}
        locale={locale}
      />
    </>
  )
}
