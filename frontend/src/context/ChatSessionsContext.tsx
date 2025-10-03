import React, { createContext, useContext, useMemo } from 'react'
import { useChatSessions } from '../hooks'
import { useSettings } from './SettingsContext'

export type ChatSessionsContextValue = ReturnType<typeof useChatSessions>

const ChatSessionsContext = (
  import.meta.hot?.data.ChatSessionsContext as React.Context<ChatSessionsContextValue | undefined> | undefined
) ?? createContext<ChatSessionsContextValue | undefined>(undefined)

if (import.meta.hot) {
  import.meta.hot.data.ChatSessionsContext = ChatSessionsContext
}

// Hook must be in the same file to access the context
export function useChatSessionsContext(): ChatSessionsContextValue {
  const context = useContext(ChatSessionsContext)
  if (!context) {
    throw new Error('useChatSessionsContext must be used within a ChatSessionsProvider')
  }
  return context
}

interface ChatSessionsProviderProps {
  children: React.ReactNode
}

export const ChatSessionsProvider = ({ children }: ChatSessionsProviderProps) => {
  const { settings } = useSettings()
  const chatSessions = useChatSessions(settings.locale)
  const value = useMemo(() => chatSessions, [chatSessions])
  return <ChatSessionsContext.Provider value={value}>{children}</ChatSessionsContext.Provider>
}
