import {
  ArrowRight,
  BadgeCheck,
  ClipboardCheck,
  Eye,
  LaptopMinimal,
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

/**
 * The front door for the whole system, serving two audiences with opposite
 * needs. A student arrives once, has never heard of any of this and needs
 * telling what to do. A guard arrives every shift and needs to be past this
 * page in one click.
 *
 * So the order is by importance rather than by explanation: both actions sit
 * in the first screenful, and everything that teaches sits below them, where
 * it costs a returning user nothing. The staff button jumps down the page
 * rather than opening a menu, so the three portals stay one visible click
 * away instead of hidden behind a control that has to be discovered.
 */

const STEPS = [
  {
    icon: ClipboardCheck,
    title: 'Register your computer',
    body: 'Give your registration number, the computer’s serial and a photo of it. It takes about a minute, and you do not need an account.',
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

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-bar">
        <Brand title="Computer Track" subtitle="Campus gate computer register" />
      </header>

      <main className="landing-main" id="main-content">
        <section className="landing-hero">
          <h1>Every computer that leaves campus, matched to the student carrying it.</h1>
          <p className="landing-lede">
            Register your laptop once. After that, any guard at any gate can confirm in seconds
            that it is yours, and you are on your way.
          </p>

          <Link to="/register" className="landing-primary">
            <span className="landing-primary-icon" aria-hidden="true">
              <LaptopMinimal size={26} />
            </span>
            <span className="landing-primary-text">
              <strong>Register my computer</strong>
              <span>
                No account needed. You can also check whether a computer you submitted has been
                approved yet.
              </span>
            </span>
            <ArrowRight className="landing-primary-arrow" size={20} aria-hidden="true" />
          </Link>

          <p className="landing-secondary">
            Work here? <a href="#staff-sign-in">Go to the staff portals</a>
          </p>
        </section>

        <section className="landing-section" aria-labelledby="how-it-works">
          <h2 id="how-it-works">How it works</h2>
          <ol className="step-list">
            {STEPS.map((step, index) => (
              <li key={step.title} className="step">
                <span className="step-icon" aria-hidden="true">
                  <step.icon size={20} />
                </span>
                <h3>
                  {/* The number is decorative: the list element already tells
                      assistive technology this is step 1 of 3. */}
                  <span className="step-number" aria-hidden="true">
                    {index + 1}
                  </span>
                  {step.title}
                </h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section" aria-labelledby="what-to-expect">
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
        </section>

        <section className="landing-section" id="staff-sign-in" aria-labelledby="staff-heading">
          <h2 id="staff-heading">Staff sign in</h2>
          <p className="landing-section-lede">
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
              </Link>
            ))}
          </div>
          <p className="landing-hint">
            <ScanLine size={14} aria-hidden="true" />
            Working a gate? Bookmark <code>/guard/login</code> on the terminal to skip this page.
          </p>
        </section>
      </main>

      <footer className="landing-footer">
        <p>Computer Track, campus gate computer register.</p>
        <p className="muted">
          Lost your sticker, or registered a computer you no longer own? Speak to the registration
          office.
        </p>
      </footer>
    </div>
  )
}
