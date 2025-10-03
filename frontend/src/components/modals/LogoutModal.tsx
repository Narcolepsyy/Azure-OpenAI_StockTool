/**
 * Logout confirmation modal component - reusable across the app
 */

import React from 'react'
import { Modal, Button } from '../ui'
import { translate, type Locale } from '../../i18n'

export interface LogoutModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  locale: Locale
}

const LogoutModal: React.FC<LogoutModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  locale
}) => {
  const handleConfirm = () => {
    onClose()
    onConfirm()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={translate('signOut', locale)}
      maxWidth="sm"
    >
      <p className="text-gray-300 mb-4">{translate('signOutConfirm', locale)}</p>
      <div className="flex space-x-3">
        <Button
          onClick={onClose}
          variant="ghost"
          className="flex-1"
        >
          {translate('cancel', locale)}
        </Button>
        <Button
          onClick={handleConfirm}
          variant="danger"
          className="flex-1"
        >
          {translate('signOut', locale)}
        </Button>
      </div>
    </Modal>
  )
}

export default LogoutModal