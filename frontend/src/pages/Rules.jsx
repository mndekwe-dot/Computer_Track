import { useCallback, useEffect, useMemo, useState } from 'react'
import { RotateCcw, Save } from 'lucide-react'
import { campus } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { useToast } from '../components/Toasts'

/**
 * The settings screen for everything that used to require a developer.
 *
 * How many computers a student may register, whether a projector needs a gate
 * pass, the exact sentence a guard reads when a computer is held: all of it is
 * policy, none of it is the same at two universities, and until now changing
 * any of it meant an engineer and a release.
 *
 * Three things this screen has to get right.
 *
 * It has to say what each setting *does*, in the same words the person
 * changing it would use. A settings page that lists keys and values is a page
 * only its author can use safely.
 *
 * It has to show which values this university has actually decided on, as
 * against which are simply sitting at whatever shipped. Without that, nobody
 * can tell a deliberate choice from an untouched default.
 *
 * It must not save on every keystroke. These change what happens at a gate
 * immediately, so the save is explicit and the screen says plainly that it
 * has taken effect.
 */
export default function Rules() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [edits, setEdits] = useState({})
  const [saving, setSaving] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const toast = useToast()

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    campus
      .rules()
      .then((payload) => {
        setData(payload)
        setEdits({})
        setFieldErrors({})
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const byGroup = useMemo(() => {
    if (!data) return []
    return data.groups
      .map((group) => ({
        ...group,
        rules: data.rules.filter((rule) => rule.group === group.key),
      }))
      .filter((group) => group.rules.length > 0)
  }, [data])

  const valueOf = (rule) => (rule.key in edits ? edits[rule.key] : rule.value)
  const dirtyCount = Object.keys(edits).length

  const setValue = (key, value) => {
    setEdits((current) => ({ ...current, [key]: value }))
    setFieldErrors((current) => {
      if (!current[key]) return current
      const next = { ...current }
      delete next[key]
      return next
    })
  }

  const save = async () => {
    if (!dirtyCount) return
    setSaving(true)
    setFieldErrors({})
    try {
      const result = await campus.saveRules(edits)
      toast.success(result.detail)
      load()
    } catch (err) {
      // Per-field where the server said which field, so the message lands
      // beside the input that caused it rather than at the top of a long page.
      const errors = err.fieldErrors || {}
      const perField = Object.fromEntries(
        Object.entries(errors).filter(([key]) => key in edits),
      )
      setFieldErrors(perField)
      toast.error(
        Object.keys(perField).length
          ? 'Some settings could not be saved. The details are beside each one.'
          : err.readable,
      )
    } finally {
      setSaving(false)
    }
  }

  const reset = async (rule) => {
    try {
      const result = await campus.resetRule(rule.key)
      toast.success(result.detail)
      load()
    } catch (err) {
      toast.error(err.readable)
    }
  }

  return (
    <>
      <PageHeader
        title="Rules and wording"
        subtitle="Policy the registration office sets, without a deployment"
      >
        <button
          type="button"
          className="btn btn-primary"
          onClick={save}
          disabled={saving || !dirtyCount}
        >
          <Save size={16} aria-hidden="true" />
          {saving ? 'Saving…' : dirtyCount ? `Save ${dirtyCount} change${dirtyCount === 1 ? '' : 's'}` : 'Save'}
        </button>
      </PageHeader>

      <div className="content">
        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data ? data.rules : null}
          emptyTitle="No settings"
          emptyBody="Nothing is configurable here yet."
        >
          {dirtyCount > 0 && (
            <div className="note note-warn" role="status">
              <span>
                {dirtyCount} unsaved change{dirtyCount === 1 ? '' : 's'}. These take effect at
                every gate the moment they are saved.
              </span>
            </div>
          )}

          {byGroup.map((group) => (
            <section className="card rule-group" key={group.key} aria-labelledby={`g-${group.key}`}>
              <h2 id={`g-${group.key}`}>{group.label}</h2>
              <p className="muted rule-group-blurb">{group.blurb}</p>

              <div className="rule-list">
                {group.rules.map((rule) => (
                  <RuleRow
                    key={rule.key}
                    rule={rule}
                    value={valueOf(rule)}
                    error={fieldErrors[rule.key]}
                    dirty={rule.key in edits}
                    onChange={(value) => setValue(rule.key, value)}
                    onReset={() => reset(rule)}
                  />
                ))}
              </div>
            </section>
          ))}
        </DataState>
      </div>
    </>
  )
}

function RuleRow({ rule, value, error, dirty, onChange, onReset }) {
  const id = `rule-${rule.key.replace(/\./g, '-')}`
  const describedBy = [rule.help ? `${id}-help` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="rule-row" data-dirty={dirty ? 'true' : 'false'}>
      <div className="rule-copy">
        <label htmlFor={id} className="rule-label">
          {rule.label}
        </label>
        {rule.help && (
          <p className="rule-help" id={`${id}-help`}>
            {rule.help}
          </p>
        )}
        {error && (
          <p className="field-error" id={`${id}-error`}>
            {error}
          </p>
        )}
      </div>

      <div className="rule-control">
        {rule.kind === 'BOOL' && (
          <label className="check-inline">
            <input
              id={id}
              type="checkbox"
              checked={Boolean(value)}
              aria-describedby={describedBy || undefined}
              onChange={(event) => onChange(event.target.checked)}
            />
            {/* Labelled for the on state, so the off state is inferable
                without a double negative. */}
            <span>{value ? 'On' : 'Off'}</span>
          </label>
        )}

        {rule.kind === 'INT' && (
          <input
            id={id}
            type="number"
            className="rule-number"
            value={value}
            min={rule.minimum ?? undefined}
            max={rule.maximum ?? undefined}
            aria-describedby={describedBy || undefined}
            aria-invalid={error ? 'true' : undefined}
            onChange={(event) => onChange(event.target.value)}
          />
        )}

        {rule.kind === 'TEXT' && (
          <textarea
            id={id}
            rows={rule.maximum && rule.maximum > 150 ? 3 : 2}
            value={value}
            maxLength={rule.maximum ?? undefined}
            aria-describedby={describedBy || undefined}
            aria-invalid={error ? 'true' : undefined}
            onChange={(event) => onChange(event.target.value)}
          />
        )}

        {/* Only offered where there is something to undo. On an untouched
            setting the button would do nothing and say nothing about why. */}
        {!rule.is_default && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onReset}>
            <RotateCcw size={13} aria-hidden="true" />
            Reset
          </button>
        )}
      </div>
    </div>
  )
}
