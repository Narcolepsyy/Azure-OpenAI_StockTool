/**
 * Custom hook for managing chat sessions
 */

import { useState, useEffect, useCallback } from 'react'
import type { ChatSession, Message } from '../types'
import { chatSessionUtils, stripMarkdown } from '../utils'
import { translate, type Locale } from '../i18n'

export const useChatSessions = (locale: Locale) => {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])

  // Load sessions and current session on mount
  useEffect(() => {
    const loadedSessions = chatSessionUtils.loadSessions()
    setSessions(loadedSessions)

    const sessionId = chatSessionUtils.loadCurrentSessionId()
    if (sessionId) {
      // Load messages immediately for the current session
      const sessionMessages = chatSessionUtils.loadSessionMessages(sessionId)
      setCurrentSessionId(sessionId)
      setMessages(sessionMessages)
      
      // Debug logging
      if (import.meta.env.DEV) {
        console.log('[useChatSessions] Loaded session on mount:', {
          sessionId,
          messageCount: sessionMessages.length,
        })
      }
    } else if (loadedSessions.length > 0) {
      // Auto-activate most recent session if no current session
      const mostRecent = loadedSessions[0]
      if (mostRecent) {
        const sessionMessages = chatSessionUtils.loadSessionMessages(mostRecent.id)
        setCurrentSessionId(mostRecent.id)
        setMessages(sessionMessages)
        chatSessionUtils.saveCurrentSessionId(mostRecent.id)
        
        // Debug logging
        if (import.meta.env.DEV) {
          console.log('[useChatSessions] Auto-activated most recent session:', {
            sessionId: mostRecent.id,
            messageCount: sessionMessages.length,
          })
        }
      }
    }
  }, [])

  // Sync messages from localStorage whenever currentSessionId changes
  // This is CRITICAL for handling the transition from WelcomeScreen to ChatLayout
  // when the first message is sent in a new session
  useEffect(() => {
    if (currentSessionId) {
      const sessionMessages = chatSessionUtils.loadSessionMessages(currentSessionId)
      setMessages(sessionMessages)
    }
  }, [currentSessionId])

  const createNewSession = useCallback(() => {
    setCurrentSessionId(null)
    setMessages([])
    chatSessionUtils.saveCurrentSessionId(null)
  }, [])

  const switchToSession = useCallback((sessionId: string) => {
    // Always load fresh messages from localStorage when switching sessions
    const sessionMessages = chatSessionUtils.loadSessionMessages(sessionId)
    setCurrentSessionId(sessionId)
    setMessages(sessionMessages)
    chatSessionUtils.saveCurrentSessionId(sessionId)
  }, [])

  const deleteSession = useCallback((sessionId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== sessionId)
    const savedSessions = chatSessionUtils.saveSessions(updatedSessions)
    setSessions(savedSessions)
    
    chatSessionUtils.deleteSession(sessionId)

    if (currentSessionId === sessionId) {
      if (savedSessions.length > 0 && savedSessions[0]) {
        switchToSession(savedSessions[0].id)
      } else {
        createNewSession()
      }
    }
  }, [sessions, currentSessionId, switchToSession, createNewSession])

  const ensureSession = useCallback((): string => {
    if (currentSessionId) {
      return currentSessionId
    }

    // Create new session
    const newSession = chatSessionUtils.createNewSession(translate('newChat', locale))
    const updatedSessions = [newSession, ...sessions]
    const savedSessions = chatSessionUtils.saveSessions(updatedSessions)
    setSessions(savedSessions)
    
    setCurrentSessionId(newSession.id)
    chatSessionUtils.saveCurrentSessionId(newSession.id)
    // Clear messages state for new session
    setMessages([])
    chatSessionUtils.saveSessionMessages(newSession.id, [])
    
    return newSession.id
  }, [currentSessionId, sessions, locale])

  const addMessage = useCallback((message: Message, targetSessionId?: string) => {
    const sessionId = targetSessionId ?? ensureSession()
    if (targetSessionId && currentSessionId !== targetSessionId) {
      setCurrentSessionId(targetSessionId)
      chatSessionUtils.saveCurrentSessionId(targetSessionId)
    }
    
    setMessages(prev => {
      // For new sessions, prev might have stale data from previous session
      // Always use localStorage as source of truth for the target session
      const currentMessages = chatSessionUtils.loadSessionMessages(sessionId)
      
      // Check if message already exists to prevent duplicates
      const messageExists = currentMessages.some(m => m.id === message.id)
      if (messageExists) {
        // Message already saved, just ensure state matches localStorage
        return currentMessages
      }
      
      const newMessages = [...currentMessages, message]
      chatSessionUtils.saveSessionMessages(sessionId, newMessages)
      return newMessages
    })

    // Update session metadata
    setSessions(prev => {
      const updatedSessions = prev.map(session => {
        if (session.id === sessionId) {
          return chatSessionUtils.updateSessionAfterMessage(session, message, stripMarkdown)
        }
        return session
      })
      return chatSessionUtils.saveSessions(updatedSessions)
    })
  }, [ensureSession, currentSessionId])

  const updateLastMessage = useCallback((updater: (prev: Message[]) => Message[]) => {
    const sessionId = currentSessionId
    if (!sessionId) return

    setMessages(prev => {
      const newMessages = updater(prev)
      chatSessionUtils.saveSessionMessages(sessionId, newMessages)
      return newMessages
    })
  }, [currentSessionId])

  // New: Update messages using an explicit sessionId to avoid race conditions
  // when a session is just created (first question) and currentSessionId
  // hasn't updated yet in this closure.
  const updateMessagesForSession = useCallback((sessionId: string, updater: (prev: Message[]) => Message[]) => {
    if (!sessionId) return
    
    // CRITICAL FIX: Load messages for the SPECIFIC sessionId from localStorage
    // This prevents corruption when:
    // 1. User sends message in session A
    // 2. Assistant starts responding to session A
    // 3. User switches to session B (state now has session B messages)
    // 4. Streaming update for session A arrives
    // 5. Without this fix: updater would receive session B messages and corrupt session A
    // 6. With this fix: updater receives session A messages from localStorage
    const sessionMessages = chatSessionUtils.loadSessionMessages(sessionId)
    const newMessages = updater(sessionMessages)
    chatSessionUtils.saveSessionMessages(sessionId, newMessages)
    
    // Update state - React will only re-render if this is the current session
    setMessages(newMessages)
  }, [])

  const clearCurrentSession = useCallback(() => {
    setMessages([])
    setCurrentSessionId(null)
    chatSessionUtils.saveCurrentSessionId(null)
  }, [])

  return {
    sessions,
    currentSessionId,
    messages,
    createNewSession,
    switchToSession,
    deleteSession,
    addMessage,
    updateLastMessage,
    updateMessagesForSession,
    clearCurrentSession,
    ensureSession,
  }
}