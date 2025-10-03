/**
 * Authentication form component
 */

import React, { useState } from 'react'
import { TrendingUp } from 'lucide-react'
import { Button, Input } from '../ui'
import { translate, type Locale } from '../../i18n'
import type { AuthMode, AuthFormData } from '../../types'
import clsx from 'clsx'

export interface AuthFormProps {
  mode: AuthMode
  onModeChange: (mode: AuthMode) => void
  onSubmit: (data: AuthFormData) => Promise<void>
  error: string | null
  isLoading: boolean
  locale: Locale
}

const AuthForm: React.FC<AuthFormProps> = ({
  mode,
  onModeChange,
  onSubmit,
  error,
  isLoading,
  locale
}) => {
  const [formData, setFormData] = useState<AuthFormData>({
    username: '',
    password: '',
    email: ''
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit(formData)
  }

  const handleInputChange = (field: keyof AuthFormData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }))
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-gray-800 rounded-xl shadow-lg p-8 border border-gray-700">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
            <TrendingUp className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-white">
            {translate('appTitle', locale)}
          </h1>
          <p className="text-gray-400 mt-2">
            {translate('appSubtitle', locale)}
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex mb-6 bg-gray-700 rounded-lg p-1">
          <button
            type="button"
            onClick={() => onModeChange('login')}
            className={clsx(
              'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
              mode === 'login'
                ? 'bg-gray-600 text-white shadow-sm'
                : 'text-gray-300 hover:text-white'
            )}
          >
            {translate('authLogin', locale)}
          </button>
          <button
            type="button"
            onClick={() => onModeChange('register')}
            className={clsx(
              'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
              mode === 'register'
                ? 'bg-gray-600 text-white shadow-sm'
                : 'text-gray-300 hover:text-white'
            )}
          >
            {translate('authRegister', locale)}
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Username"
            type="text"
            value={formData.username}
            onChange={handleInputChange('username')}
            required
            disabled={isLoading}
          />

          {mode === 'register' && (
            <Input
              label="Email (optional)"
              type="email"
              value={formData.email}
              onChange={handleInputChange('email')}
              disabled={isLoading}
            />
          )}

          <Input
            label="Password"
            type="password"
            value={formData.password}
            onChange={handleInputChange('password')}
            required
            disabled={isLoading}
          />

          {error && (
            <div className="bg-red-900/50 border border-red-600 rounded-md p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <Button
            type="submit"
            className="w-full"
            loading={isLoading}
            disabled={!formData.username || !formData.password}
          >
            {mode === 'login' 
              ? translate('authLogin', locale) 
              : translate('authRegister', locale)
            }
          </Button>
        </form>
      </div>
    </div>
  )
}

export { AuthForm }