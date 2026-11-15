import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  CircleCheck,
  CircleHelp,
  Clock,
  LaptopMinimal,
  Search,
  ShieldCheck,
  Siren,
  TriangleAlert,
} from 'lucide-react'
import { publicApi } from '../api/endpoints'
import { Brand } from '../components/Brand'
import { PhotoInput } from '../components/PhotoInput'
import { Field, StatusPill, formatDateTime } from '../components/ui'

/**
 * The student-facing page. No login, no account, no portal - a student opens
 * this on their phone, and everything they submit lands in the registration
 * office's approval queue rather than on the register directly.
 */
export default function PublicRegister() {
  // The tab lives in the URL rather than in state, so "check my computers"
  // can be linked to and bookmarked, and the back button steps between the
  // two rather than leaving the page entirely.
  const [params, setParams] = useSearchParams()
  const TABS = ['register', 'status', 'missing']
  const requested = params.get('tab')
  const tab = TABS.includes(requested) ? requested : 'register'
  const setTab = (next) =>
    setParams(next === 'register' ? {} : { tab: next }, { replace: true })

  return (
    <div className="public-page">
      <div className="public-shell">
        <header className="public-head">
          <Brand title="Computer Registration" subtitle="University gate register" size="md" as="h1" />
          <p>
            Register your laptop so security can confirm it is yours when you carry it through a
            gate. You do not need an account.
          </p>
        </header>

        <div className="public-tabs" role="tablist" aria-label="Student computer registration">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'register'}
            onClick={() => setTab('register')}
          >
            <LaptopMinimal size={16} aria-hidden="true" />
            Register a computer
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'status'}
            onClick={() => setTab('status')}
          >
            <Search size={16} aria-hidden="true" />
            Check my computers
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'missing'}
            onClick={() => setTab('missing')}
          >
            <Siren size={16} aria-hidden="true" />
            Report lost or stolen
          </button>
        </div>

        {tab === 'register' && <RegisterForm />}
        {tab === 'status' && <StatusCheck />}
        {tab === 'missing' && <MissingReport />}

        <footer className="public-foot">
          <ShieldCheck size={15} aria-hidden="true" />
          Your details are only checked against the record the university already holds. Staff
          sign in elsewhere.
        </footer>
      </div>
    </div>
  )
}

function IdentityFields({ form, setForm, errors }) {
  return (
    <>
      <Field
        label="Registration number"
        required
        error={errors.reg_number}
        hint="Exactly as printed on your student ID. Spaces and dashes are fine."
      >
        <input
          value={form.reg_number}
          onChange={(e) => setForm({ ...form, reg_number: e.target.value })}
          placeholder="218001234"
          autoComplete="off"
          required
        />
      </Field>

      <Field
        label="Email or national ID"
        required
        error={errors.verification}
        hint="Whichever the university holds for you. This proves the record is yours."
      >
        <input
          value={form.verification}
          onChange={(e) => setForm({ ...form, verification: e.target.value })}
          placeholder="you@student.university.edu"
          autoComplete="off"
          required
        />
      </Field>
    </>
  )
}

function RegisterForm() {
  const [types, setTypes] = useState([])
  const [form, setForm] = useState({
    reg_number: '',
    verification: '',
    serial_number: '',
    device_type: 'LAPTOP',
    brand: '',
    model_name: '',
    colour: '',
    distinguishing_marks: '',
    photo: null,
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)

  useEffect(() => {
    publicApi
      .choices()
      .then((data) => setTypes(data.device_types || []))
      .catch(() => setTypes([{ value: 'LAPTOP', label: 'Laptop' }]))
  }, [])

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      setDone(await publicApi.registerComputer(form))
    } catch (error) {
      setErrors(
        error.status === 429
          ? { detail: 'Too many attempts from this device. Try again later, or visit the registration office.' }
          : error.fieldErrors || { detail: error.readable },
      )
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="card public-card">
        <div className="public-success">
          <CircleCheck size={40} aria-hidden="true" />
          <h2>Registration received</h2>
          <p>{done.detail}</p>
          <dl className="reference-box">
            <div>
              <dt>Reference</dt>
              <dd className="mono">{done.reference}</dd>
            </div>
            <div>
              <dt>Serial</dt>
              <dd className="mono">{done.serial_number}</dd>
            </div>
          </dl>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => {
              setDone(null)
              setForm({
                ...form,
                serial_number: '',
                brand: '',
                model_name: '',
                colour: '',
                distinguishing_marks: '',
                photo: null,
              })
            }}
          >
            Register another computer
          </button>
        </div>
      </div>
    )
  }

  return (
    <form className="card public-card" onSubmit={submit}>
      {errors.detail && (
        <div className="note note-error" role="alert">
          <span>{errors.detail}</span>
        </div>
      )}

      <div className="note note-info">
        <span>
          <TriangleAlert size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} /> A
          registration is not approved automatically. Bring the computer to the registration
          office - until it is approved, the gate will hold it.
        </span>
      </div>

      <h3 className="form-section">Who you are</h3>
      <IdentityFields form={form} setForm={setForm} errors={errors} />

      <h3 className="form-section">The computer</h3>
      <div className="form-grid">
        <Field
          label="Serial number"
          required
          error={errors.serial_number}
          hint="Usually on a sticker underneath, or under the battery."
        >
          <input
            value={form.serial_number}
            onChange={(e) => setForm({ ...form, serial_number: e.target.value })}
            placeholder="5CD1234ABC"
            autoComplete="off"
            required
          />
        </Field>
        <Field label="Type" error={errors.device_type}>
          <select
            value={form.device_type}
            onChange={(e) => setForm({ ...form, device_type: e.target.value })}
          >
            {types.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Brand" required error={errors.brand}>
          <input
            value={form.brand}
            onChange={(e) => setForm({ ...form, brand: e.target.value })}
            placeholder="HP"
            required
          />
        </Field>
        <Field label="Model" error={errors.model_name}>
          <input
            value={form.model_name}
            onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            placeholder="EliteBook 840"
          />
        </Field>
        <Field label="Colour" error={errors.colour}>
          <input
            value={form.colour}
            onChange={(e) => setForm({ ...form, colour: e.target.value })}
            placeholder="Silver"
          />
        </Field>
      </div>

      <Field
        label="Anything that makes it recognisable"
        error={errors.distinguishing_marks}
        hint="Stickers, a cracked corner, an engraving - this is what the guard checks at a glance."
      >
        <input
          value={form.distinguishing_marks}
          onChange={(e) => setForm({ ...form, distinguishing_marks: e.target.value })}
          placeholder="Blue sticker on the lid"
        />
      </Field>

      <PhotoInput
        label="Photo of the computer"
        hint="Strongly recommended. A guard comparing a picture is far quicker and surer than reading a worn serial sticker."
        value={form.photo}
        onChange={(photo) => setForm({ ...form, photo })}
        error={errors.photo}
      />

      <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy}>
        {busy ? 'Submitting…' : 'Submit registration'}
      </button>
    </form>
  )
}

/**
 * Report your own computer lost or stolen, without an account.
 *
 * This is the only public form that changes something rather than requesting
 * something, so the copy is deliberately blunt about the consequence before
 * the button is pressed, and blunt about what to do if it was a mistake.
 */
function MissingReport() {
  const [form, setForm] = useState({
    reg_number: '',
    verification: '',
    serial_number: '',
    kind: 'STOLEN',
    details: '',
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)

  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      setDone(await publicApi.reportMissing(form))
    } catch (error) {
      setErrors(
        error.status === 429
          ? { detail: 'Too many attempts from this device. Try again later, or call security.' }
          : { ...error.fieldErrors, detail: error.fieldErrors?.detail || error.readable },
      )
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="card public-card">
        <div className="public-success public-success-hold">
          <Siren size={40} aria-hidden="true" />
          <h2>Every gate will now stop this computer</h2>
          <p>{done.detail}</p>
          <dl className="reference-box">
            <div>
              <dt>Serial</dt>
              <dd className="mono">{done.serial_number}</dd>
            </div>
            <div>
              <dt>Recorded as</dt>
              <dd>{done.status === 'STOLEN' ? 'Reported stolen' : 'Reported lost'}</dd>
            </div>
          </dl>
          <p className="muted">
            We have emailed the address on your record. If you find the computer, the registration
            office can lift the hold once they have seen your student ID.
          </p>
        </div>
      </div>
    )
  }

  return (
    <form className="card public-card" onSubmit={submit}>
      <div className="note note-warn">
        <TriangleAlert size={16} aria-hidden="true" />
        <span>
          This blocks the computer at every gate straight away. Only report a computer that is
          registered to you. If it was taken from you, tell security control as well.
        </span>
      </div>

      {errors.detail && <div className="note note-error">{errors.detail}</div>}

      <h2 className="form-section">Who you are</h2>
      <div className="form-grid">
        <Field label="Registration number" required error={errors.reg_number}>
          <input
            value={form.reg_number}
            onChange={set('reg_number')}
            autoComplete="off"
            placeholder="218001234"
          />
        </Field>
        <Field
          label="Email or national ID"
          required
          error={errors.verification}
          hint="Whichever the university holds for you. This proves the record is yours."
        >
          <input
            value={form.verification}
            onChange={set('verification')}
            placeholder="you@student.university.edu"
          />
        </Field>
      </div>

      <h2 className="form-section">Which computer</h2>
      <Field
        label="Serial number"
        required
        error={errors.serial_number}
        hint="The serial you registered. Check my computers will show it if you are not sure."
      >
        <input value={form.serial_number} onChange={set('serial_number')} placeholder="5CD1234ABC" />
      </Field>

      <Field label="What happened" required error={errors.kind}>
        <select value={form.kind} onChange={set('kind')}>
          <option value="STOLEN">It was stolen</option>
          <option value="LOST">I lost it</option>
        </select>
      </Field>

      <Field
        label="Anything that would help"
        error={errors.details}
        hint="Where and roughly when you last had it. Security reads this."
      >
        <textarea
          value={form.details}
          onChange={set('details')}
          placeholder="Last had it in the library reading room on Tuesday afternoon."
        />
      </Field>

      <button type="submit" className="btn btn-hold btn-lg btn-block" disabled={busy}>
        {busy ? 'Reporting…' : 'Report it and block it at every gate'}
      </button>
    </form>
  )
}

function StatusCheck() {
  const [form, setForm] = useState({ reg_number: '', verification: '' })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    setResult(null)
    try {
      setResult(await publicApi.myComputers(form))
    } catch (error) {
      setErrors(
        error.status === 429
          ? { detail: 'Too many attempts from this device. Try again later.' }
          : error.fieldErrors || { detail: error.readable },
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <form className="card public-card" onSubmit={submit}>
        {errors.detail && (
          <div className="note note-error" role="alert">
            <span>{errors.detail}</span>
          </div>
        )}
        <IdentityFields form={form} setForm={setForm} errors={errors} />
        <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy}>
          <Search size={17} aria-hidden="true" />
          {busy ? 'Checking…' : 'Check my computers'}
        </button>
      </form>

      {result && (
        <div className="card public-card">
          <div className="card-header">
            <h3>{result.student.full_name}</h3>
            <span className="mono muted">{result.student.reg_number}</span>
          </div>

          {result.computers.length === 0 ? (
            <div className="empty-state" style={{ padding: '26px 10px' }}>
              <CircleHelp size={30} aria-hidden="true" />
              <h3 style={{ marginTop: 10 }}>Nothing registered yet</h3>
              <p>Use the other tab to register your computer.</p>
            </div>
          ) : (
            <ul className="status-list">
              {result.computers.map((computer) => (
                <li key={computer.serial_number} className="status-item">
                  <div className="status-item-head">
                    <div>
                      <strong>{computer.label}</strong>
                      <div className="mono muted">{computer.serial_number}</div>
                    </div>
                    <StatusPill status={computer.status}>{computer.status_display}</StatusPill>
                  </div>
                  <p className="status-guidance">
                    {computer.status === 'PENDING' ? (
                      <Clock size={15} aria-hidden="true" />
                    ) : computer.status === 'ACTIVE' ? (
                      <CircleCheck size={15} aria-hidden="true" />
                    ) : (
                      <TriangleAlert size={15} aria-hidden="true" />
                    )}
                    {computer.guidance}
                  </p>
                  <div className="muted" style={{ fontSize: 12 }}>
                    Submitted {formatDateTime(computer.registered_at)}
                    {computer.asset_tag ? ` · asset tag ${computer.asset_tag}` : ''}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  )
}
