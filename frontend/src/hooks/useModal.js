import { useEffect, useCallback } from 'react'

/**
 * Scroll lock, Escape-to-close, and optional backdrop dismiss for dashboard modals.
 */
export function useModal(onClose, { closeOnBackdrop = true } = {}) {
  useEffect(() => {
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.body.style.overflow = prevOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  const onBackdropClick = useCallback((e) => {
    if (closeOnBackdrop && e.target === e.currentTarget) onClose()
  }, [onClose, closeOnBackdrop])

  return {
    onBackdropClick,
    dialogProps: { role: 'dialog', 'aria-modal': 'true' },
  }
}
