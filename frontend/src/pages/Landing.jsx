import { ScanLine } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { PageMeta } from '../components/PageMeta'
import { useSiteSettings } from '../hooks/useSiteSettings'
import { PORTAL_LIST } from '../portals'

const PORTAL_BLURB = {
  guard: 'Check computers at a gate, and see the movement log.',
  registry: 'Approve registrations, and manage students and equipment.',
  admin: 'Oversight of every gate, staff accounts and the read audit log.',
}

// Built from the university's own names rather than fixed text: "the
// registration office" is called something different at every institution,
// and it appears in the one sentence telling a student where to go.
const steps = (office) => [
  {
    title: 'Register your computer',
    body: 'Give your registration number, the serial on the computer and a photo of it. About a minute, and no account needed.',
  },
  {
    title: 'Get it approved',
    body: `Bring the computer to ${office}. A registrar checks it against your record and fits its QR sticker.`,
  },
  {
    title: 'Walk through any gate',
    body: 'The guard scans the sticker or types your registration number, sees the computer is yours, and you carry on.',
  },
]

const assurances = (office) => [
  {
    title: 'What a guard can see',
    body: 'Your name, your photo and the computers registered to you. Not your results, your fees or anything else on your record.',
  },
  {
    title: 'Every lookup is recorded',
    body: 'Each time a member of staff opens a student record the system logs who did it and when, and administrators review it.',
  },
  {
    title: 'If yours is lost or stolen',
    body: `Report it to ${office}. Every gate on campus refuses that computer from the moment the report is filed.`,
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
      <div className="slip" aria-hidden="true">
        <div className="slip-query">
          <span className="slip-label">Registration number</span>
          <span className="slip-input">218001234</span>
        </div>
        <div className="slip-student">
          <span className="slip-photo">AU</span>
          <span>
            <strong>Aline Uwase</strong>
            <span>BSc Software Engineering, year 2</span>
          </span>
        </div>
        <div className="slip-device">
          <span>
            <strong>HP EliteBook 840</strong>
            <span className="mono">HP12345678</span>
          </span>
          <span className="slip-tag">Silver, sticker on lid</span>
        </div>
        <div className="slip-verdict">
          <span className="slip-word">CLEAR</span>
          <span>Details match the register</span>
        </div>
      </div>
      <figcaption>What the guard sees after typing your registration number.</figcaption>
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
  const { settings } = useSiteSettings()
  const systemName = settings['branding.system_name']
  const university = settings['branding.university_name']
  const office = settings['branding.office_name']
  const supportEmail = settings['branding.support_email']

  return (
    <div className="landing">
      <PageMeta
        index
        title={null}
        description={`Register your computer with ${university} and carry it through any campus gate. Security staff verify at the gate that a computer belongs to the person carrying it.`}
      />
      {/* Search engines read this to describe the site in a result. It is the
          same three facts the page states in prose, in the shape a crawler
          understands. */}
      <script
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            name: systemName,
            description: `The campus computer register for ${university}.`,
            potentialAction: {
              '@type': 'RegisterAction',
              name: 'Register a computer',
              target: `${window.location.origin}/register`,
            },
          }),
        }}
      />
      <header className="landing-bar">
        <Brand title={systemName} subtitle={university} />
        <a className="landing-bar-link" href="#staff-sign-in">
          Staff sign in
        </a>
      </header>

      <main id="main-content">
        <section className="hero">
          <div className="hero-inner">
            <h1>Every computer that leaves campus, matched to the student carrying it.</h1>
            <p className="hero-lede">
              Register your laptop once. After that, any guard at any gate can confirm in seconds
              that it is yours, and you are on your way.
            </p>
            <div className="hero-actions">
              <Link to="/register" className="btn btn-primary btn-lg">
                Register my computer
              </Link>
              <Link to="/register?tab=status" className="hero-secondary">
                Check a computer I already registered
              </Link>
            </div>
            <p className="hero-note">No account needed.</p>
          </div>

          <GateCheckPreview />
        </section>

        <div className="barrier" aria-hidden="true" />

        <section className="band" aria-labelledby="how-it-works">
          <div className="band-inner">
            <h2 id="how-it-works">How it works</h2>
            <ol className="route">
              {steps(office).map((step, index) => (
                <li key={step.title} className="route-stop">
                  {/* The digit is decorative: the ordered list already tells
                      assistive technology this is step 2 of 3. */}
                  <span className="route-number" aria-hidden="true">
                    {index + 1}
                  </span>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="band band-plain" aria-labelledby="what-to-expect">
          <div className="band-inner band-split">
            <h2 id="what-to-expect">What to expect</h2>
            <div className="assurance-list">
              {assurances(office).map((item) => (
                <div key={item.title} className="assurance">
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="band" id="staff-sign-in" aria-labelledby="staff-heading">
          <div className="band-inner band-split">
            <div>
              <h2 id="staff-heading">Staff sign in</h2>
              <p className="band-lede">
                Each portal is a separate door with its own login. Accounts are issued by{' '}
                {office}.
              </p>
            </div>
            <div>
              <ul className="landing-portals">
                {PORTAL_LIST.map((portal) => (
                  <li key={portal.key}>
                    <Link
                      to={`${portal.base}/login`}
                      className="landing-portal"
                      style={{ '--portal-accent': portal.accent }}
                    >
                      <strong>{portal.name}</strong>
                      <span>{PORTAL_BLURB[portal.key]}</span>
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="landing-hint">
                <ScanLine size={15} aria-hidden="true" />
                <span>
                  Working a gate? Bookmark <code>/guard/login</code> on the terminal to skip this
                  page.
                </span>
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="band-inner">
          <div className="footer-grid">
            <div className="footer-about">
              <Brand title={systemName} subtitle={university} />
              <p>
                Every computer carried through a campus gate is checked against the student it
                belongs to.
              </p>
            </div>

            {/* Each column is a nav with its own name, so a screen reader user
                gets three labelled groups rather than one undifferentiated
                pile of links at the end of the page. */}
            <nav className="footer-col" aria-labelledby="footer-students">
              <h2 id="footer-students">For students</h2>
              <ul>
                <li>
                  <Link to="/register">Register a computer</Link>
                </li>
                <li>
                  <Link to="/register?tab=status">Check my computers</Link>
                </li>
                <li>
                  <a href="#what-to-expect">What a guard can see</a>
                </li>
              </ul>
            </nav>

            <nav className="footer-col" aria-labelledby="footer-staff">
              <h2 id="footer-staff">For staff</h2>
              <ul>
                {PORTAL_LIST.map((portal) => (
                  <li key={portal.key}>
                    <Link to={`${portal.base}/login`}>{portal.name}</Link>
                  </li>
                ))}
              </ul>
            </nav>

            <nav className="footer-col" aria-labelledby="footer-help">
              <h2 id="footer-help">Help</h2>
              <ul>
                <li>
                  <a href="#how-it-works">How registration works</a>
                </li>
                {supportEmail && (
                  <li>
                    {/* Link text has to make sense read out of context, since
                        screen reader users navigate by a list of a page's
                        links. The address is the destination. */}
                    <a href={`mailto:${supportEmail}`}>Email {supportEmail}</a>
                  </li>
                )}
                <li>
                  <span className="footer-note">
                    For stickers, transfers and holds, go to {office}.
                  </span>
                </li>
              </ul>
            </nav>
          </div>

          <div className="footer-base">
            <p>Records opened by staff are logged and reviewed.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
