/**
 * The landing page is the one screen a student sees before they know anything
 * about the system, and the one a guard passes through every shift. These pin
 * the structure both of them depend on.
 */
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import Landing from '../pages/Landing'

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
    // control that has to be discovered. The ones at the top of the page jump
    // to the staff section; the section itself holds the link to the form.
    const jumpLinks = screen
      .getAllByRole('link', { name: /staff sign in/i })
      .filter((link) => link.getAttribute('href') === '#staff-sign-in')
    expect(jumpLinks.length).toBeGreaterThan(0)
  })

  it('sends staff to one sign-in page and names no portal', () => {
    renderLanding()
    const staff = document.getElementById('staff-sign-in')
    const link = within(staff).getByRole('link', { name: /staff sign in/i })
    expect(link.getAttribute('href')).toBe('/login')
    // Which portal somebody lands in is decided by their credentials, so the
    // public page must not hand out portal addresses. The office's name is
    // fair game: a student is told where to take the computer.
    const portalLinks = [...document.querySelectorAll('a[href]')].filter((link) =>
      /^\/(guard|registry|admin)(\/|$)/.test(link.getAttribute('href')),
    )
    expect(portalLinks).toEqual([])
  })

  it('names each step rather than relying on the number alone', () => {
    renderLanding()
    // The digits are aria-hidden, so the titles carry the meaning.
    expect(screen.getByRole('heading', { name: /register your computer/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /get it approved/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /walk through any gate/i })).toBeTruthy()
  })
})
