import { useCallback, useEffect, useState } from 'react'
import { Check, ShieldAlert } from 'lucide-react'
import { devices } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Field, Modal, Pagination, StatusPill, formatDateTime } from '../components/ui'
import { useToast } from '../components/Toasts'

/**
 * Who tried to register what, including the submissions that were refused.
 *
 * The refusals are the point of this screen. A student registering their own
 * laptop succeeds once and never appears here again. What shows up instead is
 * the shape of somebody working through a bag: a run of different serials
 * from one registration number, or one serial tried against several.
 *
 * It opens filtered to what actually needs a person. An accepted registration
 * and a mistyped serial are noise, and a review queue full of noise is a
 * review queue nobody opens.
 */

const COLUMNS = ['When', 'Registration number', 'Serial', 'Outcome', ' ']

const OUTCOME_TONE = {
  MATCHED_MISSING: 'STOLEN',
  TOO_MANY_ATTEMPTS: 'PENDING',
  LIMIT_REACHED: 'PENDING',
  DUPLICATE_SERIAL: 'RETIRED',
  VERIFY_FAILED: 'RETIRED',
  ACCEPTED: 'ACTIVE',
}

export default function Attempts() {
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [needsReview, setNeedsReview] = useState(true)
  const [page, setPage] = useState(1)
  const [reviewing, setReviewing] = useState(null)
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      devices.registrationAttempts({
        page,
        ...(needsReview ? { needs_review: '1' } : {}),
      }),
      devices.attemptsSummary(),
    ])
      .then(([list, counts]) => {
        setData(list)
        setSummary(counts)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [page, needsReview])

  useEffect(load, [load])

  return (
    <>
      <PageHeader
        title="Registration attempts"
        subtitle="Submissions to the public form, including the ones that were refused"
      />

      <div className="content">
        {summary?.awaiting_review > 0 && (
          <div className="note note-error" role="status">
            <ShieldAlert size={16} aria-hidden="true" />
            <span>
              <strong>{summary.awaiting_review}</strong>{' '}
              {summary.awaiting_review === 1 ? 'submission needs' : 'submissions need'} a second
              look. A serial matching a computer reported stolen means that computer was on campus
              when the form was filled in.
            </span>
          </div>
        )}

        <div className="filter-bar">
          <label className="check-inline">
            <input
              type="checkbox"
              checked={needsReview}
              onChange={(event) => {
                setNeedsReview(event.target.checked)
                setPage(1)
              }}
            />
            Only those needing review
          </label>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={COLUMNS}
          skeletonRows={6}
          emptyTitle={needsReview ? 'Nothing to review' : 'No submissions yet'}
          emptyBody={
            needsReview
              ? 'Nothing has come through the public form that needs a second look.'
              : 'Nobody has submitted the public registration form yet.'
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Registration number</th>
                  <th className="hide-sm">Serial</th>
                  <th>Outcome</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((attempt) => (
                  <tr key={attempt.id} data-attention={attempt.needs_review ? 'true' : 'false'}>
                    <td>{formatDateTime(attempt.created_at)}</td>
                    <td>
                      <strong className="mono">{attempt.reg_number || ' - '}</strong>
                      {attempt.student_name && <div className="muted">{attempt.student_name}</div>}
                    </td>
                    <td className="hide-sm mono">{attempt.serial_number || ' - '}</td>
                    <td>
                      <StatusPill status={OUTCOME_TONE[attempt.outcome] || 'RETIRED'}>
                        {attempt.outcome_display}
                      </StatusPill>
                      {attempt.detail && <div className="muted">{attempt.detail}</div>}
                    </td>
                    <td>
                      {attempt.reviewed_at ? (
                        <span className="muted">
                          Reviewed by {attempt.reviewed_by_name || 'staff'}
                        </span>
                      ) : (
                        attempt.needs_review && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setReviewing(attempt)}
                          >
                            <Check size={14} aria-hidden="true" />
                            Review
                          </button>
                        )
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataState>

        <Pagination count={data?.count || 0} page={page} onChange={setPage} />
      </div>

      {reviewing && (
        <ReviewDialog
          attempt={reviewing}
          onClose={() => setReviewing(null)}
          onDone={(message) => {
            setReviewing(null)
            toast.success(message)
            load()
          }}
        />
      )}
    </>
  )
}

function ReviewDialog({ attempt, onClose, onDone }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await devices.reviewAttempt(attempt.id, note)
      onDone('Marked as reviewed.')
    } catch (err) {
      setError(err.readable)
      setBusy(false)
    }
  }

  return (
    <Modal title="Mark this submission reviewed" onClose={onClose}>
      <form onSubmit={submit}>
        {error && <div className="note note-error">{error}</div>}

        <dl className="detail-list">
          <div>
            <dt>Submitted</dt>
            <dd>{formatDateTime(attempt.created_at)}</dd>
          </div>
          <div>
            <dt>Registration number</dt>
            <dd className="mono">{attempt.reg_number || ' - '}</dd>
          </div>
          <div>
            <dt>Serial submitted</dt>
            <dd className="mono">{attempt.serial_number || ' - '}</dd>
          </div>
          {attempt.existing_device_serial && (
            <div>
              <dt>Collided with</dt>
              <dd className="mono">
                {attempt.existing_device_serial} ({attempt.existing_device_status})
              </dd>
            </div>
          )}
          {attempt.ip_address && (
            <div>
              <dt>Submitted from</dt>
              <dd className="mono">{attempt.ip_address}</dd>
            </div>
          )}
          <div>
            <dt>Outcome</dt>
            <dd>{attempt.outcome_display}</dd>
          </div>
        </dl>

        <Field
          label="What was decided"
          hint="Kept on the record. Whoever reads this next will not have the context you have now."
        >
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            autoFocus
          />
        </Field>

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Mark reviewed'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
