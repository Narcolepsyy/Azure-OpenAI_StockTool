/**
 * Settings modal component - reusable across the app
 */

import React from 'react'
import { Modal, Textarea } from '../ui'
import { translate, type Locale } from '../../i18n'
import type { ModelsResponse, AppSettings } from '../../types'

export interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  settings: AppSettings
  onSettingsChange: (updater: (prev: AppSettings) => AppSettings) => void
  models: ModelsResponse | null
  locale: Locale
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onSettingsChange,
  models,
  locale
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={translate('settings', locale)}
    >
      <div className="space-y-6">
        <Textarea
          label={translate('systemPrompt', locale)}
          value={settings.systemPrompt}
          onChange={(e) => onSettingsChange(prev => ({ 
            ...prev, 
            systemPrompt: e.target.value 
          }))}
          rows={6}
          placeholder="Enter system prompt..."
        />

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {translate('language', locale)}
          </label>
          <select
            value={settings.locale}
            onChange={(e) => onSettingsChange(prev => ({ 
              ...prev, 
              locale: e.target.value as Locale 
            }))}
            className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="en">{translate('english', locale)}</option>
            <option value="ja">{translate('japanese', locale)}</option>
          </select>
        </div>

        {models && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {translate('modelSelection', locale)}
            </label>
            <select
              value={settings.deployment}
              onChange={(e) => onSettingsChange(prev => ({ 
                ...prev, 
                deployment: e.target.value 
              }))}
              className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">{translate('selectModelPlaceholder', locale)}</option>
              {models.available.map((model) => (
                <option key={model.id} value={model.id} disabled={!model.available}>
                  {model.name} {model.default ? '(Default)' : ''} - {model.provider.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </Modal>
  )
}

export default SettingsModal