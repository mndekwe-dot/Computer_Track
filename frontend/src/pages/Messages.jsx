import { useCallback, useEffect, useState } from 'react'
import { Eye, RotateCcw, Save } from 'lucide-react'
import { notifications } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, StatusPill, formatDateTime } from '../components/ui'
import { useToast } from '../components/Toasts'

/**
 * The wording of every message the system sends.
 *
 * Each of these was an f-string in the code, so a university could not change
 * a greeting, add their own telephone number or translate anything without a
 * developer and a release.
 *
 * The editor has to show a preview. Editing text full of placeholders with no
 * way to see the result is how `{studnet_name}` reaches four thousand people,
 * and the preview is rendered from what is in the box rather than from what
 * was last saved, so it reflects the edit being made.
 */

export default function Messages() {
  const [rows, setRows] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    notifications
      .templates()
      .then(setRows)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  return (
    <>
      <PageHeader
        title="Messages"
        subtitle="What students are told, and in whose words"
      />

      <div className="content">
        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={rows ?? null}
          emptyTitle="No messages"
          emptyBody="Nothing is configured to be sent."
        >
          <div className="note note-info">
            <span>
              Email and SMS are edited separately on purpose. An email can carry a greeting and a
              paragraph of explanation; an SMS is charged by the segment and read on a lock
              screen. One text serving both makes the email curt and the SMS expensive.
            </span>
          </div>

          {rows?.map((template) => (
            <TemplateCard key={template.id} template={template} onSaved={load} toast={toast} />
          ))}
        </DataState>
      </div>
    </>
  )
}

function TemplateCard({ template, onSaved, toast }) {
  const [subject, setSubject] = useState(template.subject)
  const [body, setBody] = useState(template.body)
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})

  const dirty = subject !== template.subject || body !== template.body
  const isEmail = template.channel === 'EMAIL'

  const save = async () => {
    setBusy(true)
    setErrors({})
    try {
      await notifications.updateTemplate(template.id, { subject, body })
      toast.success(`${template.kind_display} (${template.channel_display}) saved.`)
      onSaved()
    } catch (error) {
      setErrors(error.fieldErrors || { detail: error.readable })
      toast.error(error.readable)
    } finally {
      setBusy(false)
    }
  }

  const showPreview = async () => {
    try {
      setPreview(await notifications.previewTemplate(template.id, { subject, body }))
    } catch (error) {
      toast.error(error.readable)
    }
  }

  const reset = async () => {
    try {
      const restored = await notifications.resetTemplate(template.id)
      setSubject(restored.subject)
      setBody(restored.body)
      setPreview(null)
      toast.success('Back to the wording it shipped with.')
      onSaved()
    } catch (error) {
      toast.error(error.readable)
    }
  }

  return (
    <section className="card message-card" aria-labelledby={`t-${template.id}`}>
      <header className="message-head">
        <div>
          {/* The channel belongs in the heading, not below it. Each kind of
              message appears twice on this page, once per channel, and with
              the channel in small print underneath the two cards read as the
              same heading repeated. */}
          <h2 id={`t-${template.id}`}>
            {template.kind_display} · {template.channel_display}
          </h2>
          <p className="muted">Last changed {formatDateTime(template.updated_at)}</p>
        </div>
        <StatusPill status={template.is_active ? 'ACTIVE' : 'RETIRED'}>
          {template.is_active ? 'IN USE' : 'BUILT-IN'}
        </StatusPill>
      </header>

      {errors.detail && <div className="note note-error">{errors.detail}</div>}

      {isEmail && (
        <Field label="Subject" error={errors.subject}>
          <input value={subject} onChange={(event) => setSubject(event.target.value)} />
        </Field>
      )}

      <Field
        label="Message"
        error={errors.body}
        hint={
          isEmail
            ? 'Plain text. Blank lines separate paragraphs.'
            : 'Kept short: every 160 characters is another segment, and every segment is charged.'
        }
      >
        <textarea
          value={body}
          rows={isEmail ? 8 : 3}
          onChange={(event) => setBody(event.target.value)}
        />
      </Field>

      {template.placeholders?.length > 0 && (
        <p className="placeholder-list">
          <span className="muted">Available: </span>
          {template.placeholders.map((name) => (
            <button
              key={name}
              type="button"
              className="placeholder-chip"
              // Inserting rather than only listing: a registrar should not
              // have to retype `{student_first_name}` correctly from memory.
              onClick={() => setBody(`${body}{${name}}`)}
              title={`Add {${name}} to the message`}
            >
              {`{${name}}`}
            </button>
          ))}
        </p>
      )}

      {preview && (
        <div className="message-preview">
          <h3>Preview</h3>
          {preview.subject && (
            <p>
              <strong>{preview.subject}</strong>
            </p>
          )}
          <pre>{preview.body}</pre>
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={reset}>
          <RotateCcw size={14} aria-hidden="true" />
          Reset
        </button>
        <button type="button" className="btn btn-ghost" onClick={showPreview}>
          <Eye size={14} aria-hidden="true" />
          Preview
        </button>
        <button type="button" className="btn btn-primary" onClick={save} disabled={busy || !dirty}>
          <Save size={14} aria-hidden="true" />
          {busy ? 'Saving…' : 'Save'}
        </button>
      </div>
    </section>
  )
}
