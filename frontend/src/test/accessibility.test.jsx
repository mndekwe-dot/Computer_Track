/**
 * These pin the accessibility contracts of the shared components, because
 * every one of them is invisible on screen and so survives a redesign only if
 * something checks it. Each test names the failure it prevents.
 */
import { act, fireEvent, render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Field, Modal } from '../components/ui'
import { ToastProvider, useToast } from '../components/Toasts'

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

describe('Toasts', () => {
  function Harness({ onReady }) {
    const toast = useToast()
    // Block body, not a concise one. `useEffect(() => onReady(toast), ...)`
    // returns whatever onReady returns, and React takes an effect's return
    // value to be its cleanup function - the same mistake that was crashing
    // the account screen on unmount.
    useEffect(() => {
      onReady(toast)
    }, [toast, onReady])
    return null
  }

  function mount() {
    let api = null
    const result = render(
      <ToastProvider>
        <Harness onReady={(value) => (api = value)} />
      </ToastProvider>,
    )
    return { ...result, api: () => api }
  }

  it('keeps both live regions mounted when there is nothing to say', () => {
    const { container } = mount()
    // A region inserted at the same moment as its text is announced
    // inconsistently, which is why a repeat message often went unread.
    expect(container.querySelector('[role="status"]')).toBeTruthy()
    // Failures need to interrupt; confirmations need to wait their turn. One
    // region can only have one politeness setting.
    expect(container.querySelector('[role="alert"]')).toBeTruthy()
  })

  it('announces a failure assertively and a confirmation politely', () => {
    const { container, api } = mount()
    act(() => {
      api().success('Saved')
      api().error('Unable to record the scan')
    })
    const polite = container.querySelector('[role="status"]')
    const assertive = container.querySelector('[role="alert"]')
    expect(polite.textContent).toContain('Saved')
    expect(assertive.textContent).toContain('Unable to record the scan')
  })

  it('dismisses a routine message on its own', () => {
    vi.useFakeTimers()
    const { container, api } = mount()
    act(() => api().success('Saved'))
    expect(container.textContent).toContain('Saved')
    act(() => vi.advanceTimersByTime(6000))
    expect(container.textContent).not.toContain('Saved')
  })

  it('leaves an error on screen until it is dismissed', () => {
    vi.useFakeTimers()
    const { container, api } = mount()
    act(() => api().error('Unable to record the scan'))
    act(() => vi.advanceTimersByTime(120000))
    // A message naming what went wrong is no use if it removes itself before
    // the guard looks up.
    expect(container.textContent).toContain('Unable to record the scan')
  })

  it('stops the clock while the pointer is over a message', () => {
    vi.useFakeTimers()
    const { container, api } = mount()
    act(() => api().success('Saved'))
    fireEvent.mouseEnter(container.querySelector('.toast'))
    act(() => vi.advanceTimersByTime(30000))
    // Reading is the one activity a disappearing message punishes.
    expect(container.textContent).toContain('Saved')
  })

  it('gives the dismiss button a label that says what it dismisses', () => {
    const { api } = mount()
    act(() => api().error('Unable to record the scan'))
    // "Dismiss" alone is ambiguous the moment two messages are on screen.
    expect(
      screen.getByRole('button', { name: /Dismiss: Unable to record the scan/ }),
    ).toBeTruthy()
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

describe('effect cleanup', () => {
  it('never returns a promise from an effect', async () => {
    // React treats an effect's return value as its cleanup function, so a
    // concise arrow body that returns a promise crashes the page on unmount
    // with "destroy is not a function". Settings did exactly that and took
    // the whole page into the error boundary. A source check rather than a
    // render test, because it is the shape that is dangerous and this catches
    // it across every page at once.
    const { readdir, readFile } = await import('node:fs/promises')
    const path = await import('node:path')
    // vitest does not give this file a file: URL, so resolve from the project
    // root, which is where the runner is invoked.
    const dir = path.resolve(process.cwd(), 'src/pages')
    const files = await readdir(dir)
    const offenders = []

    for (const file of files.filter((name) => name.endsWith('.jsx'))) {
      const raw = await readFile(path.join(dir, file), 'utf8')
      // Strip comments first, or a comment explaining the hazard trips
      // the check that guards against it.
      const source = raw.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')
      for (const match of source.matchAll(/useEffect\((\w+),/g)) {
        const name = match[1]
        // Passing a named function straight to useEffect is only safe when
        // that function has a block body, which returns undefined.
        const safe =
          source.includes(`const ${name} = useCallback(() => {`) ||
          source.includes(`const ${name} = () => {`)
        if (!safe) offenders.push(`${file}: useEffect(${name}, ...)`)
      }
    }

    expect(offenders).toEqual([])
  })
})
