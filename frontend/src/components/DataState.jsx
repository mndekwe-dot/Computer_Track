import { EmptyState, ErrorNote, Refreshing, SkeletonTable } from './ui'

/**
 * The one place that decides how a data screen behaves while it loads, fails
 * or comes back empty. Every list page renders through this, so the rules hold
 * everywhere instead of being re-decided page by page:
 *
 *   error          → a message with a retry, and nothing else
 *   first load     → a skeleton shaped like the table that is coming
 *   empty result   → an empty state that says what to do next
 *   refetch        → the existing rows stay put and dim
 *
 * `rows` is the already-loaded array (or null before the first response).
 */
export function DataState({
  loading,
  error,
  onRetry,
  rows,
  columns,
  skeletonRows = 8,
  emptyTitle = 'Nothing to show',
  emptyBody,
  children,
}) {
  if (error) return <ErrorNote error={error} onRetry={onRetry} />

  const hasLoaded = rows !== null && rows !== undefined
  if (loading && !hasLoaded) {
    return <SkeletonTable columns={columns} rows={skeletonRows} />
  }
  if (hasLoaded && rows.length === 0) {
    return <EmptyState title={emptyTitle}>{emptyBody}</EmptyState>
  }
  if (!hasLoaded) return null

  return <Refreshing active={loading}>{children}</Refreshing>
}
