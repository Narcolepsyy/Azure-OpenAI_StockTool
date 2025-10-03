import React, { createContext, useContext, useMemo } from 'react'
import { useChat } from '../hooks'

export type ChatContextValue = ReturnType<typeof useChat>

const ChatContext = createContext<ChatContextValue | undefined>(undefined)

// Hook must be in the same file to access the context
export function useChatContext(): ChatContextValue {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider')
  }
  return context
}

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const chat = useChat()
  const value = useMemo(() => chat, [chat])
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}
