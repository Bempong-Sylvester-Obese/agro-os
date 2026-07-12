import { useEffect, useCallback, useId, useRef } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/**
 * Scroll lock, Escape-to-close, and optional backdrop dismiss for dashboard modals.
 */
export function useModal(onClose, { closeOnBackdrop = true, label = 'Dialog' } = {}) {
  const dialogRef = useRef(null)
  const previousFocusRef = useRef(null)
  const generatedTitleId = useId()
  const titleId = `modal-title-${generatedTitleId.replace(/:/g, '')}`

  useEffect(() => {
    const prevOverflow = document.body.style.overflow
    previousFocusRef.current = document.activeElement
    document.body.style.overflow = 'hidden'

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab' || !dialogRef.current) return

      const focusable = Array.from(dialogRef.current.querySelectorAll(FOCUSABLE_SELECTOR))
      if (focusable.length === 0) {
        e.preventDefault()
        dialogRef.current.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)

    const focusFrame = requestAnimationFrame(() => {
      const firstFocusable = dialogRef.current?.querySelector(FOCUSABLE_SELECTOR)
      ;(firstFocusable || dialogRef.current)?.focus()
    })

    return () => {
      cancelAnimationFrame(focusFrame)
      document.body.style.overflow = prevOverflow
      document.removeEventListener('keydown', onKeyDown)
      if (previousFocusRef.current?.isConnected) previousFocusRef.current.focus()
    }
  }, [onClose])

  const onBackdropClick = useCallback((e) => {
    if (closeOnBackdrop && e.target === e.currentTarget) onClose()
  }, [onClose, closeOnBackdrop])

  return {
    onBackdropClick,
    titleId,
    closeButtonProps: { type: 'button', 'aria-label': `Close ${label}` },
    dialogProps: {
      ref: dialogRef,
      role: 'dialog',
      tabIndex: -1,
      'aria-modal': 'true',
      'aria-labelledby': titleId,
    },
  }
}
