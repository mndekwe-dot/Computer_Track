# Changelog

Notable changes to etracker, newest first.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [semantic versioning](https://semver.org/spec/v2.0.0.html).

Entries say what changed and, where it is not obvious, why. A line that only
repeats the commit subject is not worth reading twice.

---

## [Unreleased]

### Added

**Messaging, with real providers.** Email through [Resend](https://resend.com)
and SMS through [Africa's Talking](https://africastalking.com). Email was
previously whatever SMTP server was configured, and SMS had no provider at
all — only a console backend that logged and returned success — so the one
message that matters most, *your computer has just left campus*, could not
reach a phone.

Two things about SMS are handled once, centrally, because both cost real money
when got wrong. Student records hold numbers as people write them
(`0788123456`) and the API accepts E.164 only. And every 160-character segment
is charged, so a long message is truncated rather than quietly costing four
times as much per student.

**Message wording is editable.** Every message was an f-string in the code, so
a university could not change a greeting, add their own telephone number or
translate anything without a developer and a release. The text is now a table
edited in the Registration Office portal, with a preview rendered from what is
in the editor rather than from what was last saved.

**Policy is editable.** How many computers a student may register, whether
university property needs a gate pass, the exact sentence a guard reads when a
computer is held. None of that is a technical question, none of it is the same
at two universities, and all of it needed an engineer. It is a rule store now,
with a registry in code declaring what may be set, its type and its bounds, so
the settings table cannot become an unvalidated dump.

**Equipment types are a table.** A university that checks lab equipment or
musical instruments at the gate had to file a bug and wait for a release. A
registrar adds them now, chooses which appear on the student form, and retires
one without stranding the computers already registered under it.

**Gates gained the details a guard needs** — which directions the gate serves,
when it is staffed, and a telephone number to call when something is held. A
gate that has ever recorded a scan is closed rather than deleted, since
deleting it would null the gate on a year of history.

**Registration attempts are recorded, refusals included.** A refused
submission previously returned an error and left no trace, which wasted the
single most informative event the public form can produce. A run of different
serials from one registration number is what working through a bag of stolen
laptops looks like.

**A serial matching a computer reported stolen alerts security immediately.**
It means that computer was on campus, in the hands of whoever filled in the
form. The submitter is told only that the serial is already registered —
telling them anything more would be telling them to run.

**Two further brakes on registering someone else's computer**, both rules
rather than constants: a ceiling on how many computers one student may hold,
counting submissions still awaiting approval so that queueing twenty and
waiting does not work; and a count of repeat submissions in a window, which
flags for review rather than blocking. A student with a broken keyboard
retypes a serial too, and a check that stops real students gets switched off.

**Optional proof of purchase and a required photograph.** Neither is proof.
Their value is that somebody registering a machine they picked up an hour ago
has to invent an answer, and the answer is on the record when the real owner
surfaces.

**The console works offline.** A service worker caches the application shell,
so a refresh at a gate is the console rather than a blank screen. Scans
already queued and synced; the application itself did not survive being
discarded.

Lookups the guard has already performed are kept briefly, in the tab's own
storage, cleared on sign-out — and labelled as copies, with the time they were
taken, because a computer reported stolen since then would still read as
clear. The register itself is deliberately *not* cached: a gate tablet is the
least physically secure device in the system.

**Background work runs on a schedule.** Celery with a Redis broker drains the
outbox, runs the audit-volume check and refreshes the dashboard. Each of those
was previously a crontab line somebody had to remember, documented in a README
that a new administrator would not read until something had already gone
wrong. With no broker configured, tasks run in process, so a fresh clone still
works.

**The whole system runs in containers.** `docker compose up` brings up the
database, cache, API, worker, scheduler and frontend. Previously the compose
file held one service and everything else was a page of setup instructions.

**Search engines see the public half and nothing else.** Per-page titles and
descriptions, generated `robots.txt` and `sitemap.xml`, a web manifest, and a
`noscript` fallback. Every portal route is `noindex` by default and has to ask
to be listed; they sit behind a login in front of a register of named students.

**A real 404 page.** A wrong address silently redirected to the landing page,
which reads as the application losing your place — and hides the mistake,
because nobody reports a broken link that quietly takes them somewhere
plausible.

**Screens for everything above**: rules and wording, equipment types,
messages, and the registration-attempt review queue.

### Changed

**Settings are read through `python-decouple`.** They were a mix of
`os.environ` lookups and hand-rolled casts, three of which were subtly wrong —
`MEDIA_ACCEL_REDIRECT` compared against the literal string `"True"`, so
`true` silently disabled it.

**One error shape for every API failure.** An unhandled exception arrived as
an HTML debug page or an empty 500; a mistyped URL got Django's HTML 404. Both
reach a `fetch()` as unparseable noise, and both surfaced at the gate as
"Request failed with 500", which names nothing the reader can do. Responses
now carry a sentence somebody can act on, a stable code, and a reference that
ties what the user was told to what the log recorded.

**Confirmations and failures come from one place.** Each page held its own
toast state, so a second message replaced the first mid-sentence and a
confirmation raised while navigating away was lost. Errors no longer
auto-dismiss, pointing at a message stops its clock, and failures and
confirmations use separate live regions because one region can only have one
politeness setting.

**The session idle timeout is a rule, not a build-time constant.** Changing it
on a terminal that faces an open queue no longer needs a redeploy.

**Two caches instead of one.** Rate-limit counters are the only copy of what
they hold; rules and dashboard totals are copies of what the database already
knows. Keeping them apart lets a test switch off the second without disabling
the rate limiting it is trying to test.

**Equipment type is validated against the register, not a fixed list.** The
column still stores a code rather than a foreign key, because a scan log
written this year has to still read correctly after somebody renames the type.

### Fixed

**Four N+1 queries**, all the same shape: `.filter()` on a related manager,
which reads correctly and cannot use `prefetch_related`. A guard looking up a
student with four laptops paid about twenty round trips to render four rows.
The tests now assert that thirty rows cost the same as three.

**A rate limit that made the application unusable.** The endpoint serving the
university's name and the equipment list shared the public form's
twelve-per-hour ceiling, and every page load reads it. Twelve visits from one
address — one lecture theatre behind a single NAT — and the application could
no longer render itself.

**Silent data loss in the offline queue.** A validation failure deleted every
queued scan, destroying a record of decisions a guard actually made, and
leaving nobody any way to find out. They are set aside for review now.

**A queue that never drained.** `navigator.onLine` reports only whether there
is a network interface; campus wifi that has dropped its uplink still reads as
online and fires no event. A periodic retry covers it.

**`--retry-failed` did nothing.** It reset a message's status but not its
backoff stamp, so the next pass skipped every message it had just reset.

**A shared loading component that crashed non-table screens.** It fell back to
a table skeleton requiring a `columns` prop, so any page that was not a table
went to the error boundary instead of showing a skeleton.

**The logo was left-aligned above a centred title** on every login screen: a
later bare `.brand` rule matched the same specificity as the stacked variant
and won.

**An unhandled exception was swallowed.** Returning a response from the DRF
exception handler meant Django's own handler never ran, so error reporting
never fired in production and, in tests, a real bug passed quietly as "a 500
was returned".

**The QR prefix had already drifted** — the printing half wrote `CTRACK:` and
the scanning half looked for `CTRACK`.

### Security

- A serial submitted to the public form that matches a computer reported
  stolen now alerts staff, without alerting the submitter.
- Every public submission is recorded with its address, so a pattern of
  attempts is visible.
- A rate-limit floor applies to every endpoint, including ones added later
  that nobody remembers to throttle, plus a separate ceiling on writes.
- Throttled responses say how long to wait, so a client waits instead of
  refreshing in a loop.
- Containers run as a non-root user, and `.dockerignore` keeps local `.env`
  files, the development database and uploaded photographs out of images.

---

## [1.0.0]

The first working system: three staff portals, a public student form, and a
gate console.

### Added

- **Gate console.** A guard types a registration number, a serial, an asset
  tag or scans a QR sticker, and sees the student, their photograph and every
  computer registered to them, each with a plain CLEAR or HOLD.
- **Student and computer register**, with holds, gate passes, ownership
  transfers and CSV import.
- **Public registration form** with no login. It can only ever create a
  pending record, and identity is checked against details already on file.
- **Public lost and stolen reporting**, which blocks a computer at every gate
  immediately — because a stolen laptop is walking away while anyone
  deliberates — and emails the owner, so a report they did not make cannot sit
  unnoticed.
- **University property** alongside student laptops, with a rule that depends
  on direction: a projector needs a gate pass to leave, and is never stopped
  for want of one on the way back in.
- **Inverted-index search.** The obvious `icontains` cannot use an index, and
  the gate lookup is the one query that must not get slower as the register
  grows.
- **Read audit log**, because any signed-in staff member can see every
  student's record, and without a log "a guard looked up their ex-partner
  forty times" is unanswerable. With alerting that compares each account
  against its own baseline, since one flat threshold cannot fit both a busy
  main gate and a quiet service gate.
- **Notification outbox.** Sending inline put an SMTP round trip on the
  critical path of the action that must never be slow, and lost the message
  when the mail server was down.
- **Offline scan queue** with idempotency keys, so a decision already made is
  never lost and a replayed sync does not double-record it.
- **Two-factor authentication** for administrator accounts.

### Fixed

- **Uploaded photographs were served straight off disk.** An `<img>` cannot
  send an auth header, and an unguessable filename is not a password — it is a
  URL that gets copied, logged and shared. They are signed, expiring links now.
- **CSV exports were vulnerable to formula injection.** A cell beginning `=`
  is a formula to a spreadsheet, and the delivery route is what made it
  serious: the public form sets brand and model with no login, and an
  administrator opens the export weeks later.
- **Scan snapshots were taken from the request body**, so a tampered client
  could write a history that never happened. They come from the register now.
- **The account screen crashed on unmount.** `useEffect(load, [])` returns the
  promise, and React takes an effect's return value to be its cleanup
  function. Found by making the end-to-end suite fail on console errors.
- **Measured colour contrast** across the interface, replacing values that had
  been chosen by eye, and made every hover path reachable by keyboard.
