import { useCallback, useEffect, useState } from 'react'
import { ArrowDownToLine, ArrowUpFromLine, Download } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { campus, checkpoint } from '../api/endpoints'
import { DataState } from '../components/DataState'
import { PageHeader } from '../components/PortalShell'
import { Pagination, StatusPill, formatDateTime } from '../components/ui'
import { useToast } from '../components/Toasts'
import { useDebouncedValue } from '../hooks/useLiveSearch'

const VERDICTS = ['ALLOWED', 'DENIED', 'OVERRIDE', 'UNREGISTERED']
const LOG_COLUMNS = [
  'When',
  'Gate',
  'Direction',
  'Computer',
  'Student',
  'Outcome',
  'Guard',
  'Reason / note',
]

export default function ScanLog() {
  const [params] = useSearchParams()
  const [data, setData] = useState(null)
  const [gates, setGates] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    gate: '',
    verdict: '',
    direction: '',
    date_from: '',
    date_to: '',
    problems: params.get('problems') || '',
  })
  const clearFilters = () => {
    setFilters({
      search: '',
      gate: '',
      verdict: '',
      direction: '',
      date_from: '',
      date_to: '',
      problems: '',
    })
    setPage(1)
  }
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const toast = useToast()

  const search = useDebouncedValue(filters.search)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    checkpoint
      .scans({ ...filters, search, page })
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    filters.gate,
    filters.verdict,
    filters.direction,
    filters.date_from,
    filters.date_to,
    filters.problems,
    search,
    page,
  ])

  useEffect(load, [load])
  useEffect(() => {
    campus.gates().then(setGates).catch(() => {})
  }, [])

  const updateFilter = (key, value) => {
    setPage(1)
    setFilters((current) => ({ ...current, [key]: value }))
  }

  const download = async () => {
    try {
      const blob = await checkpoint.exportCsv(filters)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `gate-log-${new Date().toISOString().slice(0, 10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.show({
        tone: 'error',
        message: 'Could not build the export. Try a narrower date range.',
      })
    }
  }

  return (
    <>
      <PageHeader title="Gate Log" subtitle="Every decision recorded at every gate">
        <button type="button" className="btn btn-outline btn-sm" onClick={download}>
          <Download size={15} aria-hidden="true" />
          Export CSV
        </button>
      </PageHeader>

      <div className="content">
        <div className="toolbar">
          <input
            className="grow"
            placeholder="Search serial, reg number or name…"
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
          />
          <select value={filters.gate} onChange={(e) => updateFilter('gate', e.target.value)}>
            <option value="">All gates</option>
            {gates.map((gate) => (
              <option key={gate.id} value={gate.id}>
                {gate.name}
              </option>
            ))}
          </select>
          <select
            value={filters.verdict}
            onChange={(e) => updateFilter('verdict', e.target.value)}
          >
            <option value="">All outcomes</option>
            {VERDICTS.map((verdict) => (
              <option key={verdict} value={verdict}>
                {verdict}
              </option>
            ))}
          </select>
          <select
            value={filters.direction}
            onChange={(e) => updateFilter('direction', e.target.value)}
          >
            <option value="">Both directions</option>
            <option value="IN">Entering</option>
            <option value="OUT">Leaving</option>
          </select>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => updateFilter('date_from', e.target.value)}
            aria-label="From date"
          />
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => updateFilter('date_to', e.target.value)}
            aria-label="To date"
          />
          <label className="check-inline">
            <input
              type="checkbox"
              checked={filters.problems === '1'}
              onChange={(e) => updateFilter('problems', e.target.checked ? '1' : '')}
            />
            Problems only
          </label>
        </div>

        <DataState
          loading={loading}
          error={error}
          onRetry={load}
          rows={data?.results ?? null}
          columns={LOG_COLUMNS}
          skeletonRows={10}
          emptyTitle="Nothing logged for those filters"
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
                    <th className="hide-md">Gate</th>
                    <th>Direction</th>
                    <th>Computer</th>
                    <th className="hide-sm">Student</th>
                    <th>Outcome</th>
                    <th className="hide-md">Guard</th>
                    <th className="hide-md">Reason / note</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((scan) => (
                    <tr key={scan.id}>
                      <td>{formatDateTime(scan.happened_at)}</td>
                      <td className="hide-md">{scan.gate_name || ' - '}</td>
                      <td>
                        <span className="direction-cell">
                          {scan.direction === 'IN' ? (
                            <ArrowDownToLine size={14} aria-hidden="true" />
                          ) : (
                            <ArrowUpFromLine size={14} aria-hidden="true" />
                          )}
                          {scan.direction === 'IN' ? 'In' : 'Out'}
                        </span>
                      </td>
                      <td className="mono">{scan.device_label || scan.claimed_serial || ' - '}</td>
                      <td className="hide-sm">
                        {scan.student_name || ' - '}
                        {scan.bearer_name && (
                          <div className="muted">carried by {scan.bearer_name}</div>
                        )}
                        <div className="muted mono">{scan.claimed_reg_number}</div>
                      </td>
                      <td>
                        <StatusPill status={scan.verdict} />
                      </td>
                      <td className="hide-md">{scan.guard_name || ' - '}</td>
                      <td className="hide-md muted">
                        {scan.override_reason || scan.notes || ' - '}
                      </td>
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
