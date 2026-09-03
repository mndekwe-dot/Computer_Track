/**
 * These pin the accessibility contracts of the shared components, because
 * every one of them is invisible on screen and so survives a redesign only if
 * something checks it. Each test names the failure it prevents.
 */
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Field, Modal, Toast } from '../components/ui'

afterEach(() => {
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('Field', () => {
  it('keeps the hint out of the control name and links it as a description', () => {
    // The hint used to live inside the <label>, so a screen reader read the
    // label and the hint together as one long name on every focus.
    render(
      <Field label="Registration number" hint="Spaces and dashes are fine">
        <input />
      </Field>,
    )
    const input = screen.getByLabelText('Registration number')
    const describedBy = input.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(document.getElementById(describedBy).textContent).toBe('Spaces and dashes are fine')
  })

  it('marks a failing control invalid and points at the error', () => {
    render(
      <Field label="Serial number" error="Enter the serial printed on the computer">
        <input />
      </Field>,
    )
    const input = screen.getByLabelText('Serial number')
    expect(input.getAttribute('aria-invalid')).toBe('true')
    const describedBy = input.getAttribute('aria-describedby')
    expect(document.getElementById(describedBy).textContent).toBe(
      'Enter the serial printed on the computer',
    )
  })

  it('announces that a field is required, not only the asterisk', () => {
    render(
      <Field label="Reason" required>
        <input />
      </Field>,
    )
    // The visible * is aria-hidden, so without this text the requirement is
    // carried by a glyph assistive technology never sees. Asserted on the
    // label's own content rather than the computed name, because jsdom does
    // not exclude aria-hidden subtrees the way a real browser does.
    const input = screen.getByRole('textbox')
    expect(input.closest('label').textContent).toContain('(required)')
  })
})

describe('Toast', () => {
  it('keeps the live region mounted when there is nothing to say', () => {
    const { container } = render(<Toast toast={null} onDismiss={() => {}} />)
    // A region inserted at the same moment as its text is announced
    // inconsistently, which is why a repeat message often went unread.
    expect(container.querySelector('[role="status"]')).toBeTruthy()
  })

  it('dismisses a routine message on its own', () => {
    vi.useFakeTimers()
    const onDismiss = vi.fn()
    render(<Toast toast={{ tone: 'success', message: 'Saved' }} onDismiss={onDismiss} />)
    act(() => vi.advanceTimersByTime(5000))
    expect(onDismiss).toHaveBeenCalled()
  })

  it('leaves an error on screen until it is dismissed', () => {
    vi.useFakeTimers()
    const onDismiss = vi.fn()
    render(<Toast toast={{ tone: 'error', message: 'Unable to record the scan' }} onDismiss={onDismiss} />)
    act(() => vi.advanceTimersByTime(60000))
    // A message naming what went wrong is no use if it removes itself before
    // the guard looks up.
    expect(onDismiss).not.toHaveBeenCalled()
  })
})

describe('Modal', () => {
  it('returns focus to whatever opened it', () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()

    const { unmount } = render(
      <Modal title="Approve computer" onClose={() => {}}>
        <input />
      </Modal>,
    )
    unmount()
    expect(document.activeElement).toBe(opener)
  })

  it('keeps Tab inside the dialog', () => {
    render(
      <Modal title="Approve computer" onClose={() => {}}>
        <button type="button">Confirm</button>
      </Modal>,
    )
    const confirm = screen.getByText('Confirm')
    confirm.focus()
    // Tab from the last control must wrap to the first, not walk out into the
    // page behind, where the user could operate controls they cannot see.
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(document.activeElement).toBe(screen.getByLabelText('Close'))
  })

  it('closes on Escape', () => {
    const onClose = vi.fn()
    render(
      <Modal title="Approve computer" onClose={onClose}>
        <input />
      </Modal>,
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })
})

describe('ApiError copy', () => {
  it('always ends in something the reader can do', async () => {
    const { ApiError } = await import('../api/client')
    // The old fallback surfaced the raw Error message, so a 500 reached the
    // gate as "Request failed with 500".
    const cases = [
      [new ApiError('Request failed with 500', { status: 500 }), /try again/i],
      [new ApiError('Request failed with 404', { status: 404 }), /refresh the page/i],
      [new ApiError('Request failed with 429', { status: 429 }), /wait a minute/i],
      [new ApiError('boom', { isNetwork: true }), /check the network/i],
    ]
    for (const [error, expected] of cases) {
      expect(error.readable).toMatch(expected)
      expect(error.readable).not.toMatch(/Request failed/)
    }
  })

  it('prefers the field message the server sent over a generic one', async () => {
    const { ApiError } = await import('../api/client')
    const error = new ApiError('Request failed with 400', {
      status: 400,
      data: { serial_number: ['This serial is already registered.'] },
    })
    expect(error.readable).toBe('serial number: This serial is already registered.')
  })
})
