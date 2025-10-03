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
      setCurrentSessionId(sessionId)
      const sessionMessages = chatSessionUtils.loadSessionMessages(sessionId)
      setMessages(sessionMessages)
    } else if (loadedSessions.length > 0) {
      // Auto-activate most recent session if no current session
      const mostRecent = loadedSessions[0]
      if (mostRecent) {
        setCurrentSessionId(mostRecent.id)
        chatSessionUtils.saveCurrentSessionId(mostRecent.id)
        const sessionMessages = chatSessionUtils.loadSessionMessages(mostRecent.id)
        setMessages(sessionMessages)
      }
    }
  }, [])

  const createNewSession = useCallback(() => {
    setCurrentSessionId(null)
    setMessages([])
    chatSessionUtils.saveCurrentSessionId(null)
  }, [])

  const switchToSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    const sessionMessages = chatSessionUtils.loadSessionMessages(sessionId)
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
    chatSessionUtils.saveSessionMessages(newSession.id, [])
    
    return newSession.id
  }, [currentSessionId, sessions, locale])

  const addMessage = useCallback((message: Message) => {
    const sessionId = ensureSession()
    
    setMessages(prev => {
      const newMessages = [...prev, message]
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
  }, [ensureSession])

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
    setMessages(prev => {
      const newMessages = updater(prev)
      chatSessionUtils.saveSessionMessages(sessionId, newMessages)
      return newMessages
    })
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