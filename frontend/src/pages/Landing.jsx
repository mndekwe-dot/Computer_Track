import { ArrowRight, LaptopMinimal, ScanLine, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { PORTAL_LIST } from '../portals'

const PORTAL_BLURB = {
  guard: 'Check computers at a gate, and see the movement log.',
  registry: 'Approve registrations, and manage students and equipment.',
  admin: 'Oversight of every gate, staff accounts and the read audit log.',
}

/**
 * The front door for the whole system.
 *
 * The three staff portals stay genuinely separate, each with its own login.
 * This page only points at them, so nobody has to be told a URL, while the
 * thing most visitors actually want, registering their own laptop, is the
 * most prominent item on the page rather than buried under staff options.
 */
export default function Landing() {
  return (
    <div className="landing">
      <div className="landing-inner">
        <header className="landing-head">
          <Brand title="Computer Track" subtitle="Campus gate computer register" size="lg" stacked />
          <p>
            Every computer carried through a gate is checked against the student it belongs to.
          </p>
        </header>

        <Link to="/register" className="landing-primary">
          <span className="landing-primary-icon" aria-hidden="true">
            <LaptopMinimal size={26} />
          </span>
          <span className="landing-primary-text">
            <strong>I am a student registering my computer</strong>
            <span>
              No account needed. Register a laptop, or check whether yours has been approved.
            </span>
          </span>
          <ArrowRight size={20} aria-hidden="true" />
        </Link>

        <div className="landing-divider">
          <span>Staff sign in</span>
        </div>

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

        <footer className="landing-foot">
          <ShieldCheck size={15} aria-hidden="true" />
          <span>
            Staff accounts are issued by the registration office. Every record opened is logged.
          </span>
        </footer>

        <p className="landing-hint">
          <ScanLine size={14} aria-hidden="true" />
          Guards: bookmark <code>/guard/login</code> on the gate terminal to skip this page.
        </p>
      </div>
    </div>
  )
}
