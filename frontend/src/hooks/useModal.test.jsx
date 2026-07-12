import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import React, { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { useModal } from './useModal'

function TestDialog({ onClose }) {
  const { dialogProps, titleId, closeButtonProps } = useModal(onClose, { label: 'test dialog' })
  return (
    <div>
      <div {...dialogProps}>
        <h2 id={titleId}>Accessible dialog</h2>
        <button>First action</button>
        <button {...closeButtonProps} onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

function ModalHarness() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button onClick={() => setOpen(true)}>Open dialog</button>
      {open ? <TestDialog onClose={() => setOpen(false)} /> : null}
    </>
  )
}

describe('useModal', () => {
  it('labels the dialog, traps Tab, closes on Escape, and restores focus', async () => {
    render(<ModalHarness />)
    const trigger = screen.getByRole('button', { name: 'Open dialog' })
    trigger.focus()
    fireEvent.click(trigger)

    const dialog = screen.getByRole('dialog', { name: 'Accessible dialog' })
    const first = screen.getByRole('button', { name: 'First action' })
    const close = screen.getByRole('button', { name: 'Close test dialog' })
    expect(dialog.getAttribute('aria-modal')).toBe('true')

    await waitFor(() => expect(document.activeElement).toBe(first))
    close.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(first)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(trigger)
  })
})
