/**
 * The landing page is the one screen a student sees before they know anything
 * about the system, and the one a guard passes through every shift. These pin
 * the structure both of them depend on.
 */
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import Landing from '../pages/Landing'
import { PORTAL_LIST } from '../portals'

const renderLanding = () =>
  render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>,
  )

describe('Landing', () => {
  it('has exactly one h1 and no skipped heading levels', () => {
    renderLanding()
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)

    const levels = screen
      .getAllByRole('heading')
      .map((node) => Number(node.tagName.slice(1)))
    // A jump from h1 straight to h3 leaves a screen-reader user navigating by
    // heading with a gap they cannot explain.
    levels.forEach((level, index) => {
      if (index === 0) return
      expect(level - levels[index - 1]).toBeLessThanOrEqual(1)
    })
  })

  it('exposes a main landmark', () => {
    renderLanding()
    expect(screen.getByRole('main')).toBeTruthy()
  })

  it('puts both audiences one click from the top', () => {
    renderLanding()
    // The student action.
    const register = screen.getByRole('link', { name: /register my computer/i })
    expect(register.getAttribute('href')).toBe('/register')
    // And the staff route, which must be a real in-page link rather than a
    // control that has to be discovered. There are two, one in the top bar
    // and one beside the student action; both must land on the same section.
    const staffLinks = screen.getAllByRole('link', { name: /staff sign in/i })
    expect(staffLinks.length).toBeGreaterThan(0)
    staffLinks.forEach((link) => expect(link.getAttribute('href')).toBe('#staff-sign-in'))
  })

  it('links every portal to its own login', () => {
    renderLanding()
    const staff = document.getElementById('staff-sign-in')
    PORTAL_LIST.forEach((portal) => {
      const link = within(staff).getByRole('link', { name: new RegExp(portal.name, 'i') })
      expect(link.getAttribute('href')).toBe(`${portal.base}/login`)
    })
  })

  it('names each step rather than relying on the number alone', () => {
    renderLanding()
    // The digits are aria-hidden, so the titles carry the meaning.
    expect(screen.getByRole('heading', { name: /register your computer/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /get it approved/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /walk through any gate/i })).toBeTruthy()
  })
})
