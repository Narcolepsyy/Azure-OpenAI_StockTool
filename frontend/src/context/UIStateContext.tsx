import React, { createContext, useContext, useMemo, useState } from 'react'
import type { UIState } from '../types'

interface UIStateContextValue {
  uiState: UIState
  setUIState: React.Dispatch<React.SetStateAction<UIState>>
  updateUIState: (updater: (prev: UIState) => UIState) => void
}

const defaultUIState: UIState = {
  showSettings: false,
  showModelDropdown: false,
  showSearchModal: false,
  searchModalQuery: '',
  showUserMenu: false,
  isLeftSidebarExpanded: false,
  showLogoutConfirm: false,
  activeTab: {},
}

const UIStateContext = createContext<UIStateContextValue | undefined>(undefined)

export const UIStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [uiState, setUIState] = useState<UIState>(defaultUIState)

  const updateUIState = (updater: (prev: UIState) => UIState) => {
    setUIState((prev) => updater(prev))
  }

  const value = useMemo<UIStateContextValue>(() => ({
    uiState,
    setUIState,
    updateUIState,
  }), [uiState])

  return <UIStateContext.Provider value={value}>{children}</UIStateContext.Provider>
}

export const useUIState = (): UIStateContextValue => {
  const context = useContext(UIStateContext)
  if (!context) {
    throw new Error('useUIState must be used within a UIStateProvider')
  }
  return context
}
