import { useCallback, useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { auth } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Pagination, StatusPill, formatDateTime } from '../components/ui'
import { useDebouncedValue } from '../hooks/useLiveSearch'

const COLUMNS = ['When', 'Who', 'Action', 'Searched for', 'Whose record', 'Results', 'From']

const ACTIONS = [
  ['GATE_LOOKUP', 'Gate lookup'],
  ['SUGGEST', 'Typeahead search'],
  ['LIST_STUDENTS', 'Browsed students'],
  ['LIST_DEVICES', 'Browsed computers'],
  ['EXPORT', 'Exported the gate log'],
]

export default function AuditLog() {
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [filters, setFilters] = useState({ q: '', action: '', date_from: '', date_to: '' })
  const clearFilters = () => {
    setFilters({ q: '', action: '', date_from: '', date_to: '' })
    setPage(1)
  }
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const q = useDebouncedValue(filters.q)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    auth
      .accessLog({ ...filters, q, page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.action, filters.date_from, filters.date_to, q, page])

  useEffect(load, [load])
  useEffect(() => {
    auth.accessLogSummary().then(setSummary).catch(() => {})
  }, [])

  const update = (key, value) => {
    setPage(1)
    setFilters((current) => ({ ...current, [key]: value }))
  }

  return (
    <>
      <PageHeader
        title="Read Audit Log"
        subtitle="Who looked up whom, and when"
      />

      <div className="content">
        <div className="note note-info">
          <span>
            <ShieldCheck size={16} aria-hidden="true" style={{ verticalAlign: '-3px' }} /> Every
            staff member can read the whole register, which is what the job needs. This log is
            what makes that accountable. It is append-only - nobody, including you, can edit or
            delete an entry.
          </span>
        </div>

        {summary && (
          <div className="two-col" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="card-header">
                <h3>Busiest accounts, last 7 days</h3>
              </div>
              {summary.busiest_accounts.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>
                  Nothing recorded yet.
                </p>
              ) : (
                <ul className="outcome-list">
                  {summary.busiest_accounts.map((row) => (
                    <li key={row.username} className="outcome-row">
                      <span className="outcome-label">{row.username}</span>
                      <span className="outcome-track">
                        <span
                          className="outcome-fill"
                          style={{
                            width: `${
                              (row.reads / summary.busiest_accounts[0].reads) * 100
                            }%`,
                            background: 'var(--brand)',
                          }}
                        />
                      </span>
                      <span className="outcome-value">{row.reads}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Reads by type, last 7 days</h3>
              </div>
              <div className="stat-grid" style={{ marginBottom: 0 }}>
                <div className="stat">
                  <div className="stat-label">Total reads</div>
                  <div className="stat-value">{summary.total_reads}</div>
                </div>
                {ACTIONS.filter(([key]) => summary.by_action[key]).map(([key, label]) => (
                  <div className="stat" key={key}>
                    <div className="stat-label">{label}</div>
                    <div className="stat-value">{summary.by_action[key]}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="toolbar">
          <input
            className="grow"
            placeholder="Search by username, query or reg number…"
            value={filters.q}
            onChange={(e) => update('q', e.target.value)}
          />
          <select value={filters.action} onChange={(e) => update('action', e.target.value)}>
            <option value="">All actions</option>
            {ACTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => update('date_from', e.target.value)}
            aria-label="From date"
          />
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => update('date_to', e.target.value)}
            aria-label="To date"
          />
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={COLUMNS}
          skeletonRows={10}
          emptyTitle="Nothing recorded for those filters"
          emptyBody="Widen the date range or clear a filter."
          emptyAction={
            <button type="button" className="btn btn-outline" onClick={clearFilters}>
              Clear filters
            </button>
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>Action</th>
                  <th className="hide-sm">Searched for</th>
                  <th className="hide-md">Whose record</th>
                  <th className="hide-md">Results</th>
                  <th className="hide-md">From</th>
                </tr>
              </thead>
              <tbody>
                {data?.results.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatDateTime(entry.created_at)}</td>
                    <td>
                      <strong>{entry.full_name || entry.username}</strong>
                      <div className="muted">{entry.role_display || ' - '}</div>
                    </td>
                    <td>
                      <StatusPill status={entry.action === 'EXPORT' ? 'OVERRIDE' : 'IN'}>
                        {entry.action_display}
                      </StatusPill>
                    </td>
                    <td className="hide-sm mono">{entry.query || ' - '}</td>
                    <td className="hide-md mono">{entry.subject_reg_number || ' - '}</td>
                    <td className="hide-md">{entry.result_count}</td>
                    <td className="hide-md mono muted">{entry.ip_address || ' - '}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination count={data?.count ?? 0} page={page} onChange={setPage} />
        </DataState>
      </div>
    </>
  )
}
