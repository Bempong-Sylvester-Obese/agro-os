import React, { useCallback } from 'react'
import { X } from 'lucide-react'
import { useModal } from '../../hooks/useModal'

/**
 * Shared dashboard dialog shell from the first unified modal language:
 * blurred overlay, clean header, readable subtitle, Cancel + primary actions.
 */
export default function DashboardModal({
  title,
  subtitle,
  onClose,
  children,
  label = 'dialog',
  wide = false,
  as: Body = 'div',
  bodyProps = {},
  closeOnBackdrop = true,
  closeDisabled = false,
}) {
  const handleClose = useCallback(() => {
    if (!closeDisabled) onClose()
  }, [closeDisabled, onClose])
  const { onBackdropClick, dialogProps, titleId, closeButtonProps } = useModal(handleClose, {
    label,
    closeOnBackdrop: closeOnBackdrop && !closeDisabled,
  })

  return (
    <div className="dashboard-modal-overlay" onClick={onBackdropClick}>
      <Body
        className={`dashboard-modal${wide ? ' dashboard-modal--wide' : ''}`}
        {...dialogProps}
        {...bodyProps}
      >
        <div className="dashboard-modal-head">
          <div>
            <div id={titleId} className="serif">{title}</div>
            {subtitle ? <p className="dashboard-modal-subtitle">{subtitle}</p> : null}
          </div>
          <button
            {...closeButtonProps}
            onClick={handleClose}
            className="dashboard-icon-close"
            type="button"
            disabled={closeDisabled}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </Body>
    </div>
  )
}

export function ModalField({ htmlFor, label, optional = false, hint, children, className = '' }) {
  return (
    <div className={`dashboard-modal-field${className ? ` ${className}` : ''}`}>
      {label ? (
        <label htmlFor={htmlFor} className="dashboard-modal-label">
          {label}
          {optional ? <span className="dashboard-modal-optional"> (optional)</span> : null}
        </label>
      ) : null}
      {children}
      {hint ? <span className="dashboard-modal-hint">{hint}</span> : null}
    </div>
  )
}
