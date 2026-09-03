import { EmptyState, ErrorNote, Refreshing, SkeletonCard, SkeletonTable } from './ui'

/**
 * The one place that decides how a data screen behaves while it loads, fails
 * or comes back empty. Every list page renders through this, so the rules hold
 * everywhere instead of being re-decided page by page:
 *
 *   error          → a message with a retry, and nothing else
 *   first load     → a skeleton shaped like the table that is coming
 *   empty result   → an empty state that says what to do next, and where a
 *                    filter caused it, a control that undoes the filter
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
  emptyAction,
  children,
}) {
  if (error) return <ErrorNote error={error} onRetry={onRetry} />

  const hasLoaded = rows !== null && rows !== undefined
  if (loading && !hasLoaded) {
    // Not every screen that loads data is a table. `columns` was effectively
    // required - omitting it crashed the page into the error boundary rather
    // than showing a skeleton - which made this shared component a trap for
    // every screen that is a list of cards or a settings form.
    return columns?.length ? (
      <SkeletonTable columns={columns} rows={skeletonRows} />
    ) : (
      <SkeletonCard lines={skeletonRows} />
    )
  }
  if (hasLoaded && rows.length === 0) {
    return (
      <EmptyState title={emptyTitle} action={emptyAction}>
        {emptyBody}
      </EmptyState>
    )
  }
  if (!hasLoaded) return null

  return <Refreshing active={loading}>{children}</Refreshing>
}
