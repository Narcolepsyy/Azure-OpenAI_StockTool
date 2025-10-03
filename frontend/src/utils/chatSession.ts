/**
 * Utility functions for chat session management
 */

import type { ChatSession, Message } from '../types'
import { STORAGE_KEYS } from '../constants'

export const chatSessionUtils = {
  /**
   * Load chat sessions from localStorage
   */
  loadSessions: (): ChatSession[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.CHAT_SESSIONS)
      if (!stored) return []
      
      const sessions = JSON.parse(stored).map((s: any) => ({
        ...s,
        timestamp: new Date(s.timestamp),
      }))
      
      return sessions.sort((a: ChatSession, b: ChatSession) => 
        b.timestamp.getTime() - a.timestamp.getTime()
      )
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
      return []
    }
  },

  /**
   * Save chat sessions to localStorage
   */
  saveSessions: (sessions: ChatSession[]): ChatSession[] => {
    try {
      const sortedSessions = [...sessions].sort((a, b) =>
        b.timestamp.getTime() - a.timestamp.getTime()
      )
      localStorage.setItem(STORAGE_KEYS.CHAT_SESSIONS, JSON.stringify(sortedSessions))
      return sortedSessions
    } catch (error) {
      console.error('Failed to save chat sessions:', error)
      return sessions
    }
  },

  /**
   * Load current session ID from localStorage
   */
  loadCurrentSessionId: (): string | null => {
    try {
      return localStorage.getItem(STORAGE_KEYS.CURRENT_SESSION)
    } catch (error) {
      console.error('Failed to load current session ID:', error)
      return null
    }
  },

  /**
   * Save current session ID to localStorage
   */
  saveCurrentSessionId: (sessionId: string | null): void => {
    try {
      if (sessionId) {
        localStorage.setItem(STORAGE_KEYS.CURRENT_SESSION, sessionId)
      } else {
        localStorage.removeItem(STORAGE_KEYS.CURRENT_SESSION)
      }
    } catch (error) {
      console.error('Failed to save current session ID:', error)
    }
  },

  /**
   * Load messages for a specific session
   */
  loadSessionMessages: (sessionId: string): Message[] => {
    try {
      const sessionMessages = localStorage.getItem(`messages_${sessionId}`)
      if (!sessionMessages) return []
      
      return JSON.parse(sessionMessages).map((m: any) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      }))
    } catch (error) {
      console.error('Failed to load session messages:', error)
      return []
    }
  },

  /**
   * Save messages for a specific session
   */
  saveSessionMessages: (sessionId: string, messages: Message[]): void => {
    try {
      localStorage.setItem(`messages_${sessionId}`, JSON.stringify(messages))
    } catch (error) {
      console.error('Failed to save session messages:', error)
    }
  },

  /**
   * Delete a session and its messages
   */
  deleteSession: (sessionId: string): void => {
    try {
      localStorage.removeItem(`messages_${sessionId}`)
    } catch (error) {
      console.error('Failed to delete session messages:', error)
    }
  },

  /**
   * Generate a unique session ID
   */
  generateSessionId: (): string => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  },

  /**
   * Create a new session object
   */
  createNewSession: (title: string = 'New Chat'): ChatSession => {
    return {
      id: chatSessionUtils.generateSessionId(),
      title,
      lastMessage: '',
      timestamp: new Date(),
      messageCount: 0,
    }
  },

  /**
   * Update session after a new message
   */
  updateSessionAfterMessage: (
    session: ChatSession, 
    message: Message, 
    stripMarkdown: (text: string) => string
  ): ChatSession => {
    const cleanContent = stripMarkdown(message.content)
    const title = message.role === 'user'
      ? cleanContent.slice(0, 30) + (cleanContent.length > 30 ? '...' : '')
      : session.title !== 'New Chat' 
        ? session.title 
        : cleanContent.slice(0, 30) + (cleanContent.length > 30 ? '...' : '')

    return {
      ...session,
      title,
      lastMessage: message.content.slice(0, 100) + (message.content.length > 100 ? '...' : ''),
      timestamp: new Date(),
      messageCount: session.messageCount + 1,
    }
  },

  /**
   * Filter sessions based on search query
   */
  filterSessions: (sessions: ChatSession[], query: string): ChatSession[] => {
    if (!query.trim()) return sessions
    
    const lowerQuery = query.toLowerCase().trim()
    return sessions.filter(session => 
      session.title.toLowerCase().includes(lowerQuery) || 
      session.lastMessage.toLowerCase().includes(lowerQuery)
    )
  },
}