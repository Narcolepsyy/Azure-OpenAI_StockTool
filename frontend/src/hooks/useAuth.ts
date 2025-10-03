/**
 * Custom hook for managing authentication state
 */

import { useState, useEffect, useCallback } from 'react'
import { 
  login as loginApi, 
  register as registerApi, 
  logout as logoutApi, 
  me as meApi, 
  setToken, 
  getToken,
  type User,
  type RegisterRequest 
} from '../lib/api'
import type { AuthState, AuthMode, AuthFormData } from '../types'

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    error: null,
  })
  
  const [authMode, setAuthMode] = useState<AuthMode>('login')

  // Initialize auth state on mount
  useEffect(() => {
    const token = getToken()
    if (!token) {
      setAuthState(prev => ({ ...prev, isLoading: false }))
      return
    }

    meApi()
      .then((user: User) => {
        setAuthState({ user, isLoading: false, error: null })
      })
      .catch(() => {
        setToken(null)
        setAuthState({ user: null, isLoading: false, error: null })
      })
  }, [])

  const login = useCallback(async (credentials: AuthFormData) => {
    setAuthState(prev => ({ ...prev, error: null }))
    
    try {
      const response = await loginApi(credentials.username, credentials.password)
      setToken(response.access_token)
      setAuthState({ 
        user: response.user, 
        isLoading: false, 
        error: null 
      })
      return response.user
    } catch (error: any) {
      const errorMessage = error?.message || 'Login failed'
      setAuthState(prev => ({ 
        ...prev, 
        error: errorMessage 
      }))
      throw error
    }
  }, [])

  const register = useCallback(async (credentials: AuthFormData) => {
    setAuthState(prev => ({ ...prev, error: null }))
    
    try {
      await registerApi({
        username: credentials.username,
        password: credentials.password,
        email: credentials.email,
      } as RegisterRequest)
      
      // Auto-login after successful registration
      const response = await loginApi(credentials.username, credentials.password)
      setToken(response.access_token)
      setAuthState({ 
        user: response.user, 
        isLoading: false, 
        error: null 
      })
      return response.user
    } catch (error: any) {
      const errorMessage = error?.message || 'Registration failed'
      setAuthState(prev => ({ 
        ...prev, 
        error: errorMessage 
      }))
      throw error
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutApi()
    } catch {
      // Ignore logout API errors
    }
    
    setToken(null)
    setAuthState({ 
      user: null, 
      isLoading: false, 
      error: null 
    })
  }, [])

  const clearError = useCallback(() => {
    setAuthState(prev => ({ ...prev, error: null }))
  }, [])

  return {
    ...authState,
    authMode,
    setAuthMode,
    login,
    register,
    logout,
    clearError,
  }
}