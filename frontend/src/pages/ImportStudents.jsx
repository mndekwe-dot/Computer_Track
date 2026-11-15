import { useState } from 'react'
import { CircleCheck, FileUp, TriangleAlert, Upload } from 'lucide-react'
import { students } from '../api/endpoints'
import { PageHeader } from '../components/PortalShell'
import { ErrorNote } from '../components/ui'
import { useToast } from '../components/Toasts'

const SAMPLE = `reg_number,first_name,last_name,email,phone,department,programme,year_of_study
218001234,Aline,Uwase,aline@student.university.edu,+250788000001,CS,BSc Computer Science,2
218009999,Bosco,Mugisha,bosco@student.university.edu,+250788000002,IS,BSc Information Systems,3`

export default function ImportStudents() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [updateExisting, setUpdateExisting] = useState(true)
  const toast = useToast()

  const choose = (event) => {
    setFile(event.target.files?.[0] || null)
    setPreview(null)
    setResult(null)
    setError(null)
  }

  const check = async () => {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      setPreview(await students.importPreview(file))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const commit = async () => {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const outcome = await students.importCommit(file, updateExisting)
      setResult(outcome)
      setPreview(null)
      toast.show({ tone: 'success', message: outcome.detail })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const downloadTemplate = () => {
    const blob = new Blob([SAMPLE], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'student-import-template.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <PageHeader title="Import students" subtitle="Load the register from a CSV export">
        <button type="button" className="btn btn-outline btn-sm" onClick={downloadTemplate}>
          <FileUp size={15} aria-hidden="true" />
          Download template
        </button>
      </PageHeader>

      <div className="content">
        <div className="card">
          <div className="note note-info">
            <span>
              Nothing is written until you press Import. Check the file first - the preview
              shows exactly what would be created, updated or skipped.
            </span>
          </div>

          <div className="import-drop">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={choose}
              id="csv-file"
              className="visually-hidden"
            />
            <label htmlFor="csv-file" className="btn btn-outline">
              <Upload size={16} aria-hidden="true" />
              {file ? 'Choose a different file' : 'Choose a CSV file'}
            </label>
            {file && (
              <span className="muted">
                {file.name} · {(file.size / 1024).toFixed(0)} kB
              </span>
            )}
          </div>

          <p className="muted" style={{ fontSize: 13 }}>
            Required columns: <code>reg_number</code>, <code>first_name</code>,{' '}
            <code>last_name</code>. Optional: <code>email</code>, <code>phone</code>,{' '}
            <code>national_id</code>, <code>department</code> (its code, e.g. CS),{' '}
            <code>programme</code>, <code>year_of_study</code>, <code>status</code>. Common
            alternative headings such as &ldquo;Surname&rdquo; or &ldquo;Registration
            Number&rdquo; are understood.
          </p>

          <label className="check-inline" style={{ marginBottom: 14 }}>
            <input
              type="checkbox"
              checked={updateExisting}
              onChange={(e) => setUpdateExisting(e.target.checked)}
            />
            Update students who are already on the register
          </label>

          <ErrorNote error={error} />

          <div className="row-actions">
            <button
              type="button"
              className="btn btn-outline"
              onClick={check}
              disabled={!file || busy}
            >
              {busy && !preview ? 'Checking…' : 'Check the file'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={commit}
              disabled={!file || busy || !preview}
            >
              {busy && preview ? 'Importing…' : 'Import'}
            </button>
          </div>
        </div>

        {preview && (
          <div className="card">
            <div className="card-header">
              <h3>Preview</h3>
            </div>
            <div className="stat-grid" style={{ marginBottom: 16 }}>
              <Tile label="Will be created" value={preview.summary.to_create} tone="pass" />
              <Tile
                label={updateExisting ? 'Will be updated' : 'Already exist (skipped)'}
                value={preview.summary.to_update}
              />
              <Tile label="Rows with problems" value={preview.summary.errors} tone="hold" />
            </div>

            {preview.errors.length > 0 && (
              <>
                <h4 style={{ fontSize: 13.5, marginBottom: 8 }}>
                  <TriangleAlert
                    size={15}
                    aria-hidden="true"
                    style={{ verticalAlign: '-2px', color: 'var(--hold)' }}
                  />{' '}
                  These rows will be skipped
                </h4>
                <div className="table-wrap" style={{ marginBottom: 16 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Line</th>
                        <th>Reg number</th>
                        <th>Problem</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.errors.map((row) => (
                        <tr key={row.line}>
                          <td>{row.line}</td>
                          <td className="mono">{row.reg_number || ' - '}</td>
                          <td className="muted">{row.problems.join(' ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {preview.creates.length > 0 && (
              <>
                <h4 style={{ fontSize: 13.5, marginBottom: 8 }}>
                  First {preview.creates.length} to be created
                </h4>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Reg number</th>
                        <th>Name</th>
                        <th className="hide-sm">Programme</th>
                        <th className="hide-sm">Year</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.creates.map((row) => (
                        <tr key={row.line}>
                          <td className="mono">{row.reg_number}</td>
                          <td>
                            {row.first_name} {row.last_name}
                          </td>
                          <td className="hide-sm">{row.programme || ' - '}</td>
                          <td className="hide-sm">{row.year_of_study || ' - '}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}

        {result && (
          <div className="card">
            <div className="public-success" style={{ padding: '10px 4px' }}>
              <CircleCheck size={34} aria-hidden="true" />
              <h2>Import finished</h2>
              <p>{result.detail}</p>
            </div>
          </div>
        )}
      </div>

    </>
  )
}

function Tile({ label, value, tone }) {
  return (
    <div className="stat" data-tone={tone}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  )
}
