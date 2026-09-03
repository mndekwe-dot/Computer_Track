import { useEffect, useState } from "react";
import {
  ArrowRight,
  Ban,
  CircleCheck,
  CircleHelp,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { checkpoint, devices, students } from "../api/endpoints";
import { usePortal } from "../auth/PortalContext";
import { PageHeader } from "../components/PortalShell";
import {
  ErrorNote,
  Refreshing,
  SkeletonCard,
  SkeletonStats,
  StatusPill,
  formatDateTime,
} from "../components/ui";

/*
 * Chart colours come from the validated palette, checked against this app's
 * white card surface:
 *
 *   Entries/exits - categorical slots 1 and 2 (blue, orange). Validated:
 *   CVD ΔE 24.7, normal-vision ΔE 33.6, both ≥ 3:1 on white. All checks pass.
 *
 *   Outcomes - the reserved status palette, which deliberately does NOT meet
 *   the categorical separation gates (warning and serious sit below 3:1 on a
 *   light surface by design). The documented mitigation applies: every row
 *   carries an icon and a written label plus its count, so colour never
 *   carries the meaning on its own.
 */
const SERIES_ENTRIES = "#2a78d6";
const SERIES_EXITS = "#eb6834";

const AXIS_INK = "#64748b";
const GRID_INK = "#e2e8f0";

const OUTCOMES = [
  { key: "allowed", label: "Allowed", colour: "#0ca30c", Icon: CircleCheck },
  { key: "denied", label: "Denied", colour: "#d03b3b", Icon: Ban },
  {
    key: "overrides",
    label: "Overrides",
    colour: "#fab219",
    Icon: TriangleAlert,
  },
  {
    key: "unregistered",
    label: "Unregistered",
    colour: "#ec835a",
    Icon: CircleHelp,
  },
];

export default function Dashboard() {
  const portal = usePortal();
  const [data, setData] = useState(null);
  const [deviceStats, setDeviceStats] = useState(null);
  const [studentStats, setStudentStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([checkpoint.dashboard(), devices.summary(), students.summary()])
      .then(([board, deviceSummary, studentSummary]) => {
        setData(board);
        setDeviceStats(deviceSummary);
        setStudentStats(studentSummary);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const outcomeRows = data
    ? OUTCOMES.map((outcome) => ({
        ...outcome,
        value: data.today[outcome.key] || 0,
      }))
    : [];
  const outcomePeak = Math.max(1, ...outcomeRows.map((row) => row.value));

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Movement across all gates today">
        <button type="button" className="btn btn-outline btn-sm" onClick={load}>
          <RefreshCw size={15} aria-hidden="true" />
          Refresh
        </button>
      </PageHeader>

      <div className="content">
        <ErrorNote error={error} onRetry={load} />

        {loading && !data && (
          <>
            <SkeletonStats count={4} />
            <div className="two-col">
              <SkeletonCard lines={5} />
              <SkeletonCard lines={5} />
            </div>
          </>
        )}

        {data && (
          <Refreshing active={loading}>
            <div className="stat-grid">
              <Stat label="Scans today" value={data.today.total} />
              <Stat
                label="Computers on campus"
                value={data.devices_on_campus}
                tone="pass"
              />
              <Stat
                label="Active holds"
                value={deviceStats?.active_flags ?? " - "}
                tone="hold"
              />
              <Stat
                label="Awaiting approval"
                value={deviceStats?.by_status?.PENDING ?? 0}
                tone="warn"
              />
            </div>

            <div className="two-col">
              <div className="card">
                <div className="card-header">
                  <h3>Movement over the last 7 days</h3>
                </div>
                {(data.trend || []).every(
                  (day) => !day.entries && !day.exits,
                ) ? (
                  <p className="muted" style={{ margin: 0 }}>
                    No movement recorded in the last 7 days. Bars appear here as
                    gates record entries and exits.
                  </p>
                ) : (
                  <div className="chart-frame">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={data.trend}
                        margin={{ top: 4, right: 4, bottom: 0, left: -18 }}
                        barGap={2}
                      >
                        <CartesianGrid stroke={GRID_INK} vertical={false} />
                        <XAxis
                          dataKey="label"
                          stroke={GRID_INK}
                          tick={{ fill: AXIS_INK, fontSize: 12 }}
                          tickLine={false}
                        />
                        <YAxis
                          stroke={GRID_INK}
                          tick={{ fill: AXIS_INK, fontSize: 12 }}
                          tickLine={false}
                          axisLine={false}
                          allowDecimals={false}
                          width={44}
                        />
                        <Tooltip
                          cursor={{ fill: "rgba(15,23,42,0.05)" }}
                          contentStyle={{
                            borderRadius: 8,
                            border: `1px solid ${GRID_INK}`,
                            fontSize: 13,
                            boxShadow: "0 6px 20px rgb(15 23 42 / 0.10)",
                          }}
                          labelFormatter={(label, payload) =>
                            payload?.[0]?.payload?.date
                              ? new Date(
                                  payload[0].payload.date,
                                ).toLocaleDateString(undefined, {
                                  weekday: "long",
                                  day: "numeric",
                                  month: "short",
                                })
                              : label
                          }
                        />
                        <Legend
                          iconType="circle"
                          iconSize={9}
                          wrapperStyle={{
                            fontSize: 12.5,
                            color: AXIS_INK,
                            paddingTop: 6,
                          }}
                        />
                        <Bar
                          dataKey="entries"
                          name="Entering"
                          fill={SERIES_ENTRIES}
                          radius={[4, 4, 0, 0]}
                          maxBarSize={18}
                        />
                        <Bar
                          dataKey="exits"
                          name="Leaving"
                          fill={SERIES_EXITS}
                          radius={[4, 4, 0, 0]}
                          maxBarSize={18}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              <div className="card">
                <div className="card-header">
                  <h3>Outcomes today</h3>
                </div>
                {data.today.total === 0 ? (
                  <p className="muted" style={{ margin: 0 }}>
                    Nothing has been recorded yet today.
                  </p>
                ) : (
                  <ul className="outcome-list">
                    {outcomeRows.map(({ key, label, colour, Icon, value }) => (
                      <li key={key} className="outcome-row">
                        <span className="outcome-label">
                          <Icon
                            size={15}
                            style={{ color: colour }}
                            aria-hidden="true"
                          />
                          {label}
                        </span>
                        <span className="outcome-track">
                          <span
                            className="outcome-fill"
                            style={{
                              width: `${(value / outcomePeak) * 100}%`,
                              background: colour,
                            }}
                          />
                        </span>
                        <span className="outcome-value">{value}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="register-mini">
                  <span>
                    <strong>{studentStats?.total ?? " - "}</strong> students
                  </span>
                  <span>
                    <strong>{deviceStats?.total ?? " - "}</strong> computers
                  </span>
                  <span>
                    <strong>{deviceStats?.valid_permits ?? " - "}</strong> live
                    permits
                  </span>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Activity by gate today</h3>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Gate</th>
                      <th className="hide-sm">Code</th>
                      <th>Scans today</th>
                      <th>Denials today</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.by_gate.map((gate) => (
                      <tr key={gate.id}>
                        <td>{gate.name}</td>
                        <td className="hide-sm mono">{gate.code}</td>
                        <td>{gate.scans_today}</td>
                        <td>
                          {gate.denials_today > 0 ? (
                            <strong>{gate.denials_today}</strong>
                          ) : (
                            0
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Recent problems</h3>
                <Link
                  to={`${portal.base}/log?problems=1`}
                  className="btn btn-ghost btn-sm"
                >
                  See the full log
                  <ArrowRight size={14} aria-hidden="true" />
                </Link>
              </div>
              {data.recent_problems.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>
                  No denials, overrides or unregistered devices recorded. Quiet
                  week.
                </p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>When</th>
                        <th className="hide-sm">Gate</th>
                        <th>Computer</th>
                        <th className="hide-md">Student</th>
                        <th>Outcome</th>
                        <th className="hide-md">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_problems.map((scan) => (
                        <tr key={scan.id}>
                          <td>{formatDateTime(scan.happened_at)}</td>
                          <td className="hide-sm">{scan.gate_name || " - "}</td>
                          <td className="mono">
                            {scan.device_label || scan.claimed_serial || " - "}
                          </td>
                          <td className="hide-md">
                            {scan.student_name || " - "}
                          </td>
                          <td>
                            <StatusPill status={scan.verdict} />
                          </td>
                          <td className="hide-md muted">
                            {scan.override_reason || scan.notes || " - "}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Refreshing>
        )}
      </div>
    </>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="stat" data-tone={tone}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
