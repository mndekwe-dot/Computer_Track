import {
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  ClipboardCheck,
  Eye,
  ScanLine,
  ShieldCheck,
  Siren,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { PORTAL_LIST } from '../portals'

const PORTAL_BLURB = {
  guard: 'Check computers at a gate, and see the movement log.',
  registry: 'Approve registrations, and manage students and equipment.',
  admin: 'Oversight of every gate, staff accounts and the read audit log.',
}

const STEPS = [
  {
    icon: ClipboardCheck,
    title: 'Register your computer',
    body: 'Give your registration number, the serial on the computer and a photo of it. About a minute, and no account needed.',
  },
  {
    icon: BadgeCheck,
    title: 'Get it approved',
    body: 'Bring the computer to the registration office. A registrar checks it against your record and fits its QR sticker.',
  },
  {
    icon: ScanLine,
    title: 'Walk through any gate',
    body: 'The guard scans the sticker or types your registration number, sees the computer is yours, and you carry on.',
  },
]

const ASSURANCES = [
  {
    icon: Eye,
    title: 'What a guard can see',
    body: 'Your name, your photo and the computers registered to you. Not your results, your fees or anything else on your record.',
  },
  {
    icon: ShieldCheck,
    title: 'Every lookup is recorded',
    body: 'Each time a member of staff opens a student record the system logs who did it and when, and administrators review it.',
  },
  {
    icon: Siren,
    title: 'If yours is lost or stolen',
    body: 'Report it to the registration office. Every gate on campus refuses that computer from the moment the report is filed.',
  },
]

/**
 * An illustration of the result screen, not a component of it. Built from
 * static markup on purpose: importing the real gate console would drag the
 * authenticated bundle onto a public page, and this only ever needs to show
 * the shape of the answer.
 *
 * Hidden from assistive technology because everything it depicts is already
 * written in the prose beside it, and read aloud it is a jumble of invented
 * names and serial numbers.
 */
function GateCheckPreview() {
  return (
    <figure className="hero-preview">
      <div className="preview-card" aria-hidden="true">
        <div className="preview-head">
          <span className="preview-avatar" />
          <span className="preview-identity">
            <strong>Aline Uwase</strong>
            <span className="mono">218001234</span>
          </span>
          <span className="preview-verdict">
            <CheckCircle2 size={15} />
            Clear
          </span>
        </div>
        <div className="preview-row">
          <span className="preview-thumb" />
          <span className="preview-device">
            <strong>HP EliteBook 840</strong>
            <span className="mono">HP12345678</span>
          </span>
        </div>
        <div className="preview-row">
          <span className="preview-thumb" />
          <span className="preview-device">
            <strong>Dell Latitude 5420</strong>
            <span className="mono">DL98765432</span>
          </span>
        </div>
      </div>
      <figcaption>What a guard sees after typing a registration number.</figcaption>
    </figure>
  )
}

/**
 * The front door, serving two audiences with opposite needs. A student
 * arrives once, has never heard of any of this and needs telling what to do.
 * A guard arrives every shift and needs to be gone in one click.
 *
 * So it is ordered by importance rather than by explanation: both actions sit
 * in the first screenful, and everything that teaches sits below them, where
 * it costs a returning user nothing.
 */
export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-bar">
        <Brand title="Computer Track" subtitle="Campus gate computer register" />
        <a className="landing-bar-link" href="#staff-sign-in">
          Staff sign in
          <ArrowRight size={15} aria-hidden="true" />
        </a>
      </header>

      <main id="main-content">
        <section className="hero">
          <div className="hero-inner">
            <p className="hero-eyebrow">
              <ShieldCheck size={14} aria-hidden="true" />
              University computer register
            </p>
            <h1>Every computer that leaves campus, matched to the student carrying it.</h1>
            <p className="hero-lede">
              Register your laptop once. After that, any guard at any gate can confirm in seconds
              that it is yours, and you are on your way.
            </p>
            <div className="hero-actions">
              <Link to="/register" className="btn btn-primary btn-lg">
                Register my computer
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <a href="#staff-sign-in" className="btn btn-outline btn-lg">
                Staff sign in
              </a>
            </div>
            <p className="hero-note">
              No account needed. You can also check whether a computer you submitted has been
              approved yet.
            </p>
          </div>

          <GateCheckPreview />
        </section>

        <section className="band" aria-labelledby="how-it-works">
          <div className="band-inner">
            <h2 id="how-it-works">How it works</h2>
            <ol className="step-list">
              {STEPS.map((step, index) => (
                <li key={step.title} className="step">
                  {/* The digit is decorative: the ordered list already tells
                      assistive technology this is step 2 of 3. */}
                  <span className="step-number" aria-hidden="true">
                    {index + 1}
                  </span>
                  <span className="step-icon" aria-hidden="true">
                    <step.icon size={20} />
                  </span>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="band band-plain" aria-labelledby="what-to-expect">
          <div className="band-inner">
            <h2 id="what-to-expect">What to expect</h2>
            <div className="assurance-grid">
              {ASSURANCES.map((item) => (
                <article key={item.title} className="assurance">
                  <span className="assurance-icon" aria-hidden="true">
                    <item.icon size={18} />
                  </span>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="band" id="staff-sign-in" aria-labelledby="staff-heading">
          <div className="band-inner">
            <h2 id="staff-heading">Staff sign in</h2>
            <p className="band-lede">
              Each portal is a separate door with its own login. Accounts are issued by the
              registration office.
            </p>
            <div className="landing-portals">
              {PORTAL_LIST.map((portal) => (
                <Link
                  key={portal.key}
                  to={`${portal.base}/login`}
                  className="landing-portal"
                  style={{ '--portal-accent': portal.accent }}
                >
                  <span className="landing-portal-dot" aria-hidden="true" />
                  <strong>{portal.name}</strong>
                  <span className="muted">{PORTAL_BLURB[portal.key]}</span>
                  <ArrowRight className="landing-portal-arrow" size={16} aria-hidden="true" />
                </Link>
              ))}
            </div>
            <p className="landing-hint">
              <ScanLine size={14} aria-hidden="true" />
              <span>
                Working a gate? Bookmark <code>/guard/login</code> on the terminal to skip this
                page.
              </span>
            </p>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="band-inner">
          <p>Computer Track, campus gate computer register.</p>
          <p className="muted">
            Lost your sticker, or registered a computer you no longer own? Speak to the
            registration office.
          </p>
        </div>
      </footer>
    </div>
  )
}
