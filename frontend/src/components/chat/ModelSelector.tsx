/**
 * Model selector dropdown component
 */

import React, { useState } from 'react'
import { Cpu, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import type { ModelDropdownProps } from '../../types'

const ModelSelector: React.FC<ModelDropdownProps> = ({
  models,
  currentDeployment,
  onModelChange,
  onClose
}) => {
  const [isOpen, setIsOpen] = useState(false)

  const currentModel = models.available.find(m => m.id === currentDeployment)

  const handleToggle = () => {
    setIsOpen(!isOpen)
  }

  const handleModelSelect = (modelId: string) => {
    onModelChange(modelId)
    setIsOpen(false)
    onClose?.()
  }

  const handleClickOutside = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setIsOpen(false)
    }
  }

  return (
    <div className="relative flex-shrink-0" data-model-dropdown>
      <button
        type="button"
        onClick={handleToggle}
        className="flex items-center justify-center w-8 h-8 hover:bg-gray-700 transition-colors rounded-lg"
        title={`Current model: ${currentModel?.name || 'Unknown'}`}
      >
        <Cpu className="w-4 h-4 text-gray-400" />
      </button>
      
      {isOpen && (
        <div 
          className="absolute bottom-full left-0 mb-3 w-72 bg-gray-800 border border-gray-600 rounded-xl shadow-2xl backdrop-blur-xl z-50 max-h-80 overflow-y-auto"
          onClick={handleClickOutside}
        >
          <div className="p-3">
            <div className="text-xs font-medium text-gray-400 mb-2 px-2">
              Select Model
            </div>
            {models.available.map((model) => (
              <button
                key={model.id}
                type="button"
                onClick={() => handleModelSelect(model.id)}
                disabled={!model.available}
                className={clsx(
                  'w-full flex items-center justify-between px-3 py-2.5 text-left rounded-lg hover:bg-gray-700 transition-all duration-150',
                  currentDeployment === model.id ? 'bg-gray-700 ring-1 ring-blue-500/30' : '',
                  !model.available ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                )}
              >
                <div className="flex items-center space-x-3">
                  <div 
                    className={clsx(
                      'w-2 h-2 rounded-full',
                      model.available ? 'bg-green-400' : 'bg-gray-500'
                    )}
                  />
                  <div>
                    <div className="text-white text-sm font-medium">
                      {model.name}
                    </div>
                    {model.default && (
                      <div className="text-xs text-gray-400">Default</div>
                    )}
                  </div>
                </div>
                {currentDeployment === model.id && (
                  <div className="w-2 h-2 bg-blue-400 rounded-full" />
                )}
                {!model.available && (
                  <span className="text-xs text-orange-400 bg-orange-400/20 px-2 py-1 rounded-md">
                    max
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ModelSelector