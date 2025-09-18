import React, { useEffect, useRef, useState, useCallback } from 'react'
import { chat as chatApi, chatStream, cancelChatStream, login as loginApi, register as registerApi, me as meApi, setToken, getToken, type User, logout as logoutApi, listModels, type ModelsResponse } from './lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import {
  MessageCircle,
  Send,
  Plus,
  Settings,
  User as UserIcon,
  LogOut,
  Trash2,
  Bot,
  Menu,
  X,
  Loader2,
  ExternalLink,
  Calendar,
  TrendingUp,
  Cpu,
  Wrench,
  Check,
  XCircle
} from 'lucide-react'
import { Transition } from '@headlessui/react'
import clsx from 'clsx'

// Types
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: Array<{ id: string; name: string; result: unknown }>
  timestamp: Date
}

// Add type for live tool activity
type LiveTool = { name: string; status: 'running' | 'completed' | 'error'; error?: string }

type ChatSession = {
  id: string
  title: string
  lastMessage: string
  timestamp: Date
  messageCount: number
}

const STORAGE_KEY = 'chat_sessions'
const CURRENT_SESSION_KEY = 'current_session'

export default function App() {
  // Auth state
  const [user, setUser] = useState<User | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authError, setAuthError] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')

  // UI State
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)

  // Chat Sessions State
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])

  // Chat State
  const [prompt, setPrompt] = useState('')
  const [systemPrompt, setSystemPrompt] = useState(`You are a helpful virtual assistant specializing in financial topics.

When users ask about current or historical market data (such as stock prices, market indices, company profiles, news, or risk metrics), always retrieve information using the appropriate stock tools instead of guessing or relying only on prior knowledge.

Tool Usage Rules:
Use rag_search only for financial concepts, educational topics, and strategy explanations, including:
- Financial ratios, indicators, and technical analysis tools (e.g., P/E ratio, RSI, moving averages)
- Portfolio management theory, risk assessment methodologies, or trading strategies
- General investment education and market analysis techniques

Do NOT use rag_search when retrieving live or company-specific data. Instead:
- Use get_stock_quote → current stock price or snapshot
- Use get_historical_prices → historical stock/index data
- Use get_company_profile → company details, financials, and fundamentals
- Use get_stock_news / get_augmented_news → latest articles and headlines
- Use get_risk_assessment → real-time stock risk metrics

Provide clear, concise responses using the retrieved data. Format your answers naturally and conversationally.`)

  const [deployment, setDeployment] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [isTyping, setIsTyping] = useState(false)

  // Add streaming state variables
  const [isStreaming, setIsStreaming] = useState(false)

  // Live tool activity state
  const [activeTools, setActiveTools] = useState<LiveTool[]>([])
  const [isCachedStream, setIsCachedStream] = useState(false)

  // Models state
  const [models, setModels] = useState<ModelsResponse | null>(null)

  // Refs
  const endRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // Chat Session Management
  const loadChatSessions = useCallback(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const sessions = JSON.parse(stored).map((s: any) => ({
          ...s,
          timestamp: new Date(s.timestamp)
        }))
        setChatSessions(sessions.sort((a: ChatSession, b: ChatSession) => b.timestamp.getTime() - a.timestamp.getTime()))
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    }
  }, [])

  const saveChatSessions = useCallback((sessions: ChatSession[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
      setChatSessions(sessions.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()))
    } catch (error) {
      console.error('Failed to save chat sessions:', error)
    }
  }, [])

  const loadCurrentSession = useCallback(() => {
    try {
      const sessionId = localStorage.getItem(CURRENT_SESSION_KEY)
      if (sessionId) {
        setCurrentSessionId(sessionId)
        const sessionMessages = localStorage.getItem(`messages_${sessionId}`)
        if (sessionMessages) {
          const parsed = JSON.parse(sessionMessages).map((m: any) => ({
            ...m,
            timestamp: new Date(m.timestamp)
          }))
          setMessages(parsed)
        }
      }
    } catch (error) {
      console.error('Failed to load current session:', error)
    }
  }, [])

  const saveCurrentSession = useCallback((sessionId: string, sessionMessages: Message[]) => {
    try {
      localStorage.setItem(CURRENT_SESSION_KEY, sessionId)
      localStorage.setItem(`messages_${sessionId}`, JSON.stringify(sessionMessages))
    } catch (error) {
      console.error('Failed to save current session:', error)
    }
  }, [])

  // Initialize app
  useEffect(() => {
    const tok = getToken()
    if (!tok) return

    meApi().then(user => {
      setUser(user)
      loadChatSessions()
      loadCurrentSession()

      // Auto-create first session if none exist
      setTimeout(() => {
        const stored = localStorage.getItem(STORAGE_KEY)
        const currentSession = localStorage.getItem(CURRENT_SESSION_KEY)

        if (!stored || !currentSession) {
          const firstSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
          const firstSession: ChatSession = {
            id: firstSessionId,
            title: 'New Chat',
            lastMessage: '',
            timestamp: new Date(),
            messageCount: 0
          }

          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify([firstSession]))
            localStorage.setItem(CURRENT_SESSION_KEY, firstSessionId)
            localStorage.setItem(`messages_${firstSessionId}`, JSON.stringify([]))

            setChatSessions([firstSession])
            setCurrentSessionId(firstSessionId)
            setMessages([])
          } catch (error) {
            console.error('Failed to create first session:', error)
          }
        }
      }, 100)

    }).catch(() => setToken(null))
  }, [loadChatSessions, loadCurrentSession])

  // Load models with enhanced model selector
  useEffect(() => {
    listModels().then((m) => {
      setModels(m)
      console.log('Loaded models:', m)
      try {
        const saved = localStorage.getItem('selected_model')
        if (saved) {
          const found = m.available.find((x) => x.id === saved)
          setDeployment(found ? found.id : (m.default || ''))
        } else {
          // Use default model if no saved preference
          setDeployment(m.default || '')
        }
      } catch {
        setDeployment(m.default || '')
      }
    }).catch((err) => {
      console.error('Failed to load models:', err)
      try {
        const saved = localStorage.getItem('selected_model')
        if (saved) setDeployment(saved)
      } catch {}
    })
  }, [])

  // Save model choice
  useEffect(() => {
    try {
      if (deployment) localStorage.setItem('selected_model', deployment)
    } catch {}
  }, [deployment])

  // Auto-scroll to bottom
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, chatLoading, isTyping])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [prompt])

  const createNewSession = useCallback(() => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const newSession: ChatSession = {
      id: newSessionId,
      title: 'New Chat',
      lastMessage: '',
      timestamp: new Date(),
      messageCount: 0
    }

    const updatedSessions = [newSession, ...chatSessions]
    saveChatSessions(updatedSessions)

    setCurrentSessionId(newSessionId)
    setMessages([])
    setConversationId(null)
    setChatError(null)

    saveCurrentSession(newSessionId, [])
  }, [chatSessions, saveChatSessions, saveCurrentSession])

  const switchToSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    try {
      const sessionMessages = localStorage.getItem(`messages_${sessionId}`)
      if (sessionMessages) {
        const parsed = JSON.parse(sessionMessages).map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }))
        setMessages(parsed)
      } else {
        setMessages([])
      }
      localStorage.setItem(CURRENT_SESSION_KEY, sessionId)
    } catch (error) {
      console.error('Failed to switch session:', error)
      setMessages([])
    }
  }, [])

  const updateSessionAfterMessage = useCallback((sessionId: string, newMessage: Message) => {
    const updatedSessions = chatSessions.map(session => {
      if (session.id === sessionId) {
        const title = newMessage.role === 'user'
          ? newMessage.content.slice(0, 50) + (newMessage.content.length > 50 ? '...' : '')
          : session.title !== 'New Chat' ? session.title : newMessage.content.slice(0, 50) + (newMessage.content.length > 50 ? '...' : '')

        return {
          ...session,
          title,
          lastMessage: newMessage.content.slice(0, 100) + (newMessage.content.length > 100 ? '...' : ''),
          timestamp: new Date(),
          messageCount: session.messageCount + 1
        }
      }
      return session
    })

    saveChatSessions(updatedSessions)
  }, [chatSessions, saveChatSessions])

  const deleteSession = useCallback((sessionId: string) => {
    const updatedSessions = chatSessions.filter(s => s.id !== sessionId)
    saveChatSessions(updatedSessions)

    try {
      localStorage.removeItem(`messages_${sessionId}`)
    } catch (error) {
      console.error('Failed to delete session messages:', error)
    }

    if (currentSessionId === sessionId) {
      if (updatedSessions.length > 0 && updatedSessions[0]) {
        switchToSession(updatedSessions[0].id)
      } else {
        createNewSession()
      }
    }
  }, [chatSessions, currentSessionId, saveChatSessions, switchToSession, createNewSession])

  // Chat handlers
  const onSubmitChat = async (e: React.FormEvent) => {
    e.preventDefault()
    // Prevent duplicate sends while loading/streaming
    if (!prompt.trim() || chatLoading || isStreaming) return
    if (!user) { setChatError('Please sign in to chat.'); return }

    setChatError(null)
    setChatLoading(true)
    setActiveTools([]) // reset tool activity at start of a request

    // Ensure we have a current session
    let sessionId = currentSessionId
    if (!sessionId) {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const newSession: ChatSession = {
        id: newSessionId,
        title: 'New Chat',
        lastMessage: '',
        timestamp: new Date(),
        messageCount: 0
      }

      const updatedSessions = [newSession, ...chatSessions]
      saveChatSessions(updatedSessions)
      setCurrentSessionId(newSessionId)
      sessionId = newSessionId
      saveCurrentSession(newSessionId, [])
    }

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date()
    }

    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    updateSessionAfterMessage(sessionId, userMsg)
    saveCurrentSession(sessionId, newMessages)

    const currentPrompt = prompt
    setPrompt('')

    // Use streaming API with improved SSE handling
  setIsStreaming(true)
  setIsTyping(true)

    // Add placeholder message for streaming content
    const streamingMsg: Message = {
      id: `a-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date()
    }
    const messagesWithStreaming = [...newMessages, streamingMsg]
    setMessages(messagesWithStreaming)

    // Use a ref to track accumulated content to avoid closure issues
    let accumulatedContent = ''

    try {
      await chatStream(
        {
          prompt: currentPrompt,
          system_prompt: systemPrompt,
          deployment,
          conversation_id: conversationId || undefined,
        },
        // onChunk - handle real-time content
        (chunk) => {
          if (chunk.type === 'start') {
            if (chunk.conversation_id) setConversationId(chunk.conversation_id)
            if (chunk.cached === true) setIsCachedStream(true)
            console.log('SSE stream started:', chunk.model)
          } else if (chunk.type === 'content' && chunk.delta) {
            // Accumulate content
            accumulatedContent += chunk.delta

            // Update the streaming message in real-time (immutably)
            setMessages(prevMessages => {
              if (prevMessages.length === 0) return prevMessages
              const lastIndex = prevMessages.length - 1
              const lastMsg = prevMessages[lastIndex]
              if (!lastMsg || lastMsg.role !== 'assistant') return prevMessages
              const updatedLast: Message = { ...lastMsg, content: accumulatedContent }
              return [...prevMessages.slice(0, lastIndex), updatedLast]
            })
          } else if (chunk.type === 'tool_calls') {
            // Show tool execution indicator and add tool entries
            const names: string[] = Array.isArray(chunk.tools) ? chunk.tools : []
            setActiveTools(prev => {
              const existing = new Map(prev.map(t => [t.name, t]))
              names.forEach(n => {
                if (!existing.has(n)) existing.set(n, { name: n, status: 'running' })
              })
              return Array.from(existing.values())
            })
            setIsTyping(true) // Keep typing indicator during tool execution
          } else if (chunk.type === 'tool_call') {
            // Individual tool updated/completed; insert if missing
            const name = chunk.name as string | undefined
            const status = (chunk.status as 'completed' | 'error' | 'running' | undefined) || 'running'
            setActiveTools(prev => {
              const exists = prev.some(t => t.name === name)
              if (exists) return prev.map(t => t.name === name ? { ...t, status, error: chunk.error } : t)
              return [...prev, { name: name || 'unknown', status, error: chunk.error }]
            })
          }
        },
        // onComplete - finalize the response
        (data) => {
          const finalAssistantMsg: Message = {
            ...streamingMsg,
            content: accumulatedContent,
            toolCalls: data.tool_calls || [],
            timestamp: new Date()
          }

          const finalMessages = [...newMessages, finalAssistantMsg]
          setMessages(finalMessages)
          updateSessionAfterMessage(sessionId, finalAssistantMsg)
          saveCurrentSession(sessionId, finalMessages)

          // Update conversation ID if provided
          if (data.conversation_id) {
            setConversationId(data.conversation_id)
          }

          // Reset streaming state
          setIsStreaming(false)
          setIsTyping(false)
          setChatLoading(false)
          // Keep tool panel visible briefly after completion
          setTimeout(() => setActiveTools([]), 2000)
          setIsCachedStream(false)
        },
        // onError - handle errors
        (error) => {
          setChatError(error)
          setIsStreaming(false)
          setIsTyping(false)
          setChatLoading(false)
          // Keep any error states for a bit then clear
          setTimeout(() => setActiveTools([]), 3000)
          setIsCachedStream(false)
        }
      )
    } catch (err: any) {
      setChatError(err?.message || 'Streaming chat failed')
      setIsStreaming(false)
      setIsTyping(false)
      setChatLoading(false)
      setTimeout(() => setActiveTools([]), 3000)
      setIsCachedStream(false)
    }
  }

  const onLogout = async () => {
    try { await logoutApi() } catch {}
    setToken(null)
    setUser(null)
    setChatSessions([])
    setMessages([])
    setCurrentSessionId(null)
    try {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(CURRENT_SESSION_KEY)
    } catch {}
  }

  const onComposerKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const form = (e.currentTarget as HTMLTextAreaElement).closest('form') as HTMLFormElement | null
      form?.requestSubmit()
    }
  }

  const onStopGenerating = useCallback(() => {
    const didCancel = cancelChatStream()
    // Regardless of cancel result, bring UI back to idle
    setIsStreaming(false)
    setIsTyping(false)
    setChatLoading(false)
    // Keep the placeholder bubble as-is; it will remain with whatever content streamed so far
    // Hide any tool activity indicators shortly
    setTimeout(() => setActiveTools([]), 1000)
  }, [])

  // Auth handlers
  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setAuthError(null)
    try {
      const res = await loginApi(username, password)
      setToken(res.access_token)
      setUser(res.user)
      loadChatSessions()

    } catch (err: any) {
      setAuthError(err?.message || 'Login failed')
    }
  }

  const submitRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setAuthError(null)
    try {
      await registerApi({ username, password, email: email || undefined })
      const res = await loginApi(username, password)
      setToken(res.access_token)
      setUser(res.user)
      loadChatSessions()
    } catch (err: any) {
      setAuthError(err?.message || 'Register failed')
    }
  }

  const renderWithLinks = (text?: string): React.ReactNode => {
    if (!text) return null
    const rgx = /(https:\/\/[^\s<>()]+[^\s<>().,!?;:])/g
    const out: React.ReactNode[] = []
    let lastIdx = 0
    let m: RegExpExecArray | null
    while ((m = rgx.exec(text)) !== null) {
      const start = m.index
      const end = start + m[0].length
      if (start > lastIdx) out.push(text.slice(lastIdx, start))
      const url = m[0]
      out.push(
        <a key={`url-${start}-${end}`} href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-700 underline inline-flex items-center gap-1">
          {url}
          <ExternalLink className="w-3 h-3" />
        </a>
      )
      lastIdx = end
    }
    if (lastIdx < text.length) out.push(text.slice(lastIdx))
    return out
  }

  // If not authenticated, show auth form
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
              <TrendingUp className="w-8 h-8 text-blue-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">AI Stocks Assistant</h1>
            <p className="text-gray-600 mt-2">Your intelligent financial companion</p>
          </div>

          <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setAuthMode('login')}
              className={clsx(
                'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
                authMode === 'login'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              )}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setAuthMode('register')}
              className={clsx(
                'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
                authMode === 'register'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              )}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={authMode === 'login' ? submitLogin : submitRegister}>
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              {authMode === 'register' && (
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                    Email (optional)
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              )}

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              {authError && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
                  {authError}
                </div>
              )}

              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
              >
                {authMode === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  // Main chat interface
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Transition
        show={sidebarOpen}
        enter="transition-transform duration-300"
        enterFrom="-translate-x-full"
        enterTo="translate-x-0"
        leave="transition-transform duration-300"
        leaveFrom="translate-x-0"
        leaveTo="-translate-x-full"
        className="fixed inset-y-0 left-0 z-50 w-80 bg-gray-900 text-white lg:relative lg:translate-x-0"
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between p-4 border-b border-gray-700">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h1 className="text-base lg:text-lg font-semibold truncate">AI Stocks Assistant</h1>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-md hover:bg-gray-700 touch-manipulation"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-3 lg:p-4">
            <button
              onClick={createNewSession}
              className="w-full flex items-center space-x-3 p-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors touch-manipulation min-h-[44px]"
            >
              <Plus className="w-5 h-5" />
              <span>New Chat</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-4">
            <div className="space-y-2">
              {chatSessions.map((session) => (
                <div
                  key={session.id}
                  className={clsx(
                    'group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors',
                    currentSessionId === session.id
                      ? 'bg-gray-700 text-white'
                      : 'hover:bg-gray-800 text-gray-300'
                  )}
                  onClick={() => switchToSession(session.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <MessageCircle className="w-4 h-4 flex-shrink-0" />
                      <p className="text-sm font-medium truncate">{session.title}</p>
                    </div>
                    <p className="text-xs text-gray-400 truncate">{session.lastMessage}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Calendar className="w-3 h-3" />
                      <span className="text-xs text-gray-500">
                        {session.timestamp.toLocaleDateString()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {session.messageCount} messages
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteSession(session.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-600 transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 border-t border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                  <UserIcon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-medium">{user.username}</p>
                  <p className="text-xs text-gray-400">{user.email}</p>
                </div>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-2 rounded-md hover:bg-gray-700 transition-colors"
                >
                  <Settings className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowLogoutConfirm(true)}
                  className="p-2 rounded-md hover:bg-gray-700 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header with Enhanced Model Selector */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-md hover:bg-gray-100"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {chatSessions.find(s => s.id === currentSessionId)?.title || 'New Chat'}
              </h2>
              {currentSessionId && (
                <p className="text-sm text-gray-500">
                  {messages.length} messages
                </p>
              )}
            </div>
          </div>

          {/* Enhanced Model Selector */}
          <div className="hidden md:flex items-center space-x-3">
            {models && (
              <div className="flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-gray-500" />
                <div className="relative">
                  <select
                    value={deployment}
                    onChange={(e) => setDeployment(e.target.value)}
                    className="text-sm border border-gray-300 rounded-md px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white min-w-[160px] lg:min-w-[200px] appearance-none"
                  >
                    <option value="">Select AI Model...</option>
                    {models.available.map((model) => (
                      <option key={model.id} value={model.id} disabled={!model.available}>
                        {model.name} {model.default ? '(Default)' : ''} {!model.available ? '(Unavailable)' : ''}
                      </option>
                    ))}
                  </select>
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
                {deployment && (
                  <div className="hidden lg:flex items-center space-x-1 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    <span className={clsx(
                      "inline-block w-2 h-2 rounded-full",
                      models.available.find(m => m.id === deployment)?.available
                        ? "bg-green-500"
                        : "bg-red-500"
                    )} />
                    <span>{models.available.find(m => m.id === deployment)?.provider?.toUpperCase() || 'AI'}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Welcome to AI Stocks Assistant
                </h3>
                <p className="text-gray-600 mb-4">
                  Ask me anything about stocks, market data, financial analysis, or investment strategies.
                  I can help you with real-time quotes, historical data, company profiles, news, and risk assessments.
                </p>
                {models && deployment && (
                  <div className="inline-flex items-center space-x-2 px-3 py-1 bg-blue-50 rounded-full text-sm text-blue-700">
                    <Cpu className="w-4 h-4" />
                    <span>Using {models.available.find(m => m.id === deployment)?.name || 'AI Model'}</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={clsx(
                    'flex space-x-3',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                  )}

                  <div
                    className={clsx(
                      'max-w-3xl rounded-lg px-4 py-3',
                      message.role === 'user'
                        ? 'bg-blue-600 text-white ml-12'
                        : 'bg-white border border-gray-200 mr-12'
                    )}
                  >
                    {(() => {
                      const isAssistantPlaceholder = message.role === 'assistant' && (!message.content || message.content.trim() === '')
                      if (isAssistantPlaceholder) {
                        return (
                          <div className="flex items-center gap-2 text-gray-500" aria-live="polite" aria-busy="true">
                            <span className="sr-only">Assistant is typing</span>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                          </div>
                        )
                      }
                      return (
                        <div className="prose prose-sm max-w-none">
                          {message.role === 'user' ? (
                            <p className="text-white m-0">{renderWithLinks(message.content)}</p>
                          ) : (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeRaw]}
                              className="text-gray-900"
                            >
                              {message.content}
                            </ReactMarkdown>
                          )}
                        </div>
                      )
                    })()}

                    {message.toolCalls && message.toolCalls.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-2">Tool calls:</p>
                        <div className="space-y-1">
                          {message.toolCalls.map((tool, i) => (
                            <div key={i} className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded">
                              {tool.name}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {(!(message.role === 'assistant' && (!message.content || message.content.trim() === ''))) && (
                      <div className="mt-2 text-xs text-gray-400">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    )}
                  </div>

                  {message.role === 'user' && (
                    <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <UserIcon className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))}

              {isTyping && !(messages.length > 0 && messages[messages.length - 1]?.role === 'assistant' && (!messages[messages.length - 1]?.content || messages[messages.length - 1]?.content.trim() === '')) && (
                <div className="flex space-x-3 justify-start">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                    <div className="flex items-center space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                  </div>
                </div>
              )}

              {/* Live Tool Activity Panel */}
              {activeTools.length > 0 && (
                <div className="flex space-x-3 justify-start">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <Wrench className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white border border-blue-200 rounded-lg px-4 py-3 shadow-sm">
                    <p className="text-xs font-medium text-blue-700 mb-2">Tool activity</p>
                    <div className="space-y-1">
                      {activeTools.map((t) => (
                        <div key={t.name} className="flex items-center gap-2 text-xs">
                          <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full border border-blue-100">{t.name}</span>
                          {t.status === 'running' && (
                            <span className="inline-flex items-center text-gray-500"><Loader2 className="w-3 h-3 mr-1 animate-spin" /> running</span>
                          )}
                          {t.status === 'completed' && (
                            <span className="inline-flex items-center text-green-600"><Check className="w-3 h-3 mr-1" /> completed</span>
                          )}
                          {t.status === 'error' && (
                            <span className="inline-flex items-center text-red-600"><XCircle className="w-3 h-3 mr-1" /> error</span>
                          )}
                          {t.error && (
                            <span className="text-red-500">{String(t.error).slice(0, 120)}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Cached response indicator */}
              {isCachedStream && (
                <div className="flex space-x-3 justify-start">
                  <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/></svg>
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-xs text-gray-600">Served from cache — tools may not run for cached responses.</div>
                </div>
              )}
            </>
          )}

          <div ref={endRef} />
        </div>

        {chatError && (
          <div className="mx-4 mb-2 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            {chatError}
          </div>
        )}

        <div className="border-t border-gray-200 bg-white p-4">
          <form onSubmit={onSubmitChat} className="flex space-x-3 items-start">
            <div className="flex-1">
              <textarea
                ref={textareaRef}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={onComposerKeyDown}
                placeholder="Ask about stocks, market data, or financial analysis..."
                className="w-full resize-none border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={1}
                style={{ minHeight: '48px', maxHeight: '200px' }}
              />
            </div>
            {isStreaming ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onStopGenerating}
                  className="px-3 py-3 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors min-w-[44px]"
                  title="Stop generating"
                >
                  Stop
                </button>
                <div className="px-3 py-3 bg-blue-600 text-white rounded-lg flex items-center justify-center">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
              </div>
            ) : (
              <button
                type="submit"
                disabled={!prompt.trim() || chatLoading}
                className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center min-w-[44px]"
                title="Send"
              >
                {chatLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            )}
          </form>
        </div>
      </div>

      {/* Enhanced Settings Modal */}
      <Transition
        show={showSettings}
        enter="transition-opacity duration-300"
        enterFrom="opacity-0"
        enterTo="opacity-100"
        leave="transition-opacity duration-300"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      >
        <div className="bg-white rounded-xl p-6 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Settings</h3>
            <button
              onClick={() => setShowSettings(false)}
              className="p-1 rounded-md hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                System Prompt
              </label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="w-full h-32 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter system prompt..."
              />
            </div>

            {models && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AI Model Selection
                </label>
                <select
                  value={deployment}
                  onChange={(e) => setDeployment(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Model...</option>
                  {models.available.map((model) => (
                    <option key={model.id} value={model.id} disabled={!model.available}>
                      {model.name} {model.default ? '(Default)' : ''} - {model.provider.toUpperCase()}
                    </option>
                  ))}
                </select>

                {deployment && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm">
                    {(() => {
                      const selectedModel = models.available.find(m => m.id === deployment)
                      return selectedModel ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">Selected Model:</span>
                            <span>{selectedModel.name}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="font-medium">Provider:</span>
                            <span className="uppercase">{selectedModel.provider}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="font-medium">Status:</span>
                            <span className={clsx(
                              "inline-flex items-center space-x-1",
                              selectedModel.available ? 'text-green-600' : 'text-red-600'
                            )}>
                              <span className={clsx(
                                "inline-block w-2 h-2 rounded-full",
                                selectedModel.available ? "bg-green-500" : "bg-red-500"
                              )} />
                              <span>{selectedModel.available ? 'Available' : 'Unavailable'}</span>
                            </span>
                          </div>
                          <div className="pt-2 border-t border-gray-200">
                            <span className="font-medium">Description:</span>
                            <p className="text-gray-600 mt-1">{selectedModel.description}</p>
                          </div>
                        </div>
                      ) : <p className="text-red-600">Unknown model</p>
                    })()}
                  </div>
                )}

                <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm">
                  <h4 className="font-medium text-blue-900 mb-2">Available Models:</h4>
                  <div className="space-y-1">
                    {models.available.filter(m => m.available).map((model) => (
                      <div key={model.id} className="flex items-center justify-between">
                        <span className="text-blue-800">{model.name}</span>
                        <span className="text-xs text-blue-600 uppercase">{model.provider}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </Transition>

      <Transition
        show={showLogoutConfirm}
        enter="transition-opacity duration-300"
        enterFrom="opacity-0"
        enterTo="opacity-100"
        leave="transition-opacity duration-300"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      >
        <div className="bg-white rounded-xl p-6 max-w-sm w-full mx-4">
          <h3 className="text-lg font-semibold mb-2">Sign Out</h3>
          <p className="text-gray-600 mb-4">Are you sure you want to sign out?</p>
          <div className="flex space-x-3">
            <button
              onClick={() => setShowLogoutConfirm(false)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                setShowLogoutConfirm(false)
                onLogout()
              }}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </Transition>
    </div>
  )
}
