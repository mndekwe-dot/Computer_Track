# Computer Track - Campus Gate Computer Register

A system for university security guards to verify, at any gate, that the computer a student is
carrying actually belongs to them.

A student says their registration number, the guard types it in, and the screen shows the
student's photo, their details and every computer registered in their name - each with a clear
**CLEAR** or **HOLD** recommendation and the registered photo to compare against. The guard
matches the machine in front of them and records the decision.

**Stack:** Django 5.2 + DRF (JWT auth) · React 19 + Vite · SQLite by default, PostgreSQL via one
environment variable.

---

## Contents

- [Running it](#running-it) · [Demo accounts](#demo-accounts)
- [Who uses what](#who-uses-what) - three staff portals and one public student page
- [What it does](#what-it-does)
- [Search](#search) - the inverted index and why it is fast
- [Notifications](#notifications) - the outbox
- [Read audit log](#read-audit-log)
- [API](#api) · [Project layout](#project-layout) · [Commands](#management-commands)
- [Tests](#tests) · [Design decisions](#notes-on-some-design-decisions) · [Deployment](#deployment)

---

## Running it

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
copy .env.example .env          # cp on macOS / Linux - then edit it

python manage.py migrate
python manage.py seed_demo      # demo students, computers, gates and logs
python manage.py runserver
```

API on `http://127.0.0.1:8000`, Django admin on `/admin/`.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env          # cp on macOS / Linux
npm run dev
```

App on `http://localhost:5173`.

### Demo accounts

Created by `seed_demo`, all with password `passw0rd!`. Each signs in at **its own portal**:

| Username | Role | Sign in at |
|----------|------|-----------|
| `guard1` | Security guard, Main Gate | `/guard/login` |
| `guard2` | Security guard, West Gate | `/guard/login` |
| `registrar` | Registration officer | `/registry/login` |
| `admin` | Administrator (also a Django superuser) | `/admin/login` |

**Try this, in order - it exercises the whole system:**

1. Open `/register` signed out. Register a computer using a reg number from the Students page
   plus the email on that record. Note it comes back **pending**.
2. Sign in as `guard1` and look up that reg number. The console says **HOLD - pending approval**,
   and refuses to record a plain "allowed".
3. Sign in as `registrar`, go to **Pending Approvals**, approve it with an asset tag.
4. Back as `guard1`, look it up again - now **CLEAR**, and the exit records.
5. As `admin`, open **Read Audit Log** and see every one of those lookups attributed.

---

## Who uses what

### The landing page

`/` is a public landing page serving two audiences with opposite needs. A student arrives once,
has never heard of any of this and needs telling what to do. A guard arrives every shift and
needs to be past the page in one click.

So it is ordered by importance rather than by explanation. Both actions, "Register my computer"
and the staff portals, sit in the first screenful; everything that teaches (how it works, what a
guard can see, what happens if a computer is stolen) sits below them, where it costs a returning
user nothing. Anyone already signed in is sent straight to their own portal instead.

The portals stay genuinely separate behind it: the landing page only links to their logins.

### Three staff portals

Each user type has its **own front door** - a separate login URL, its own navigation and its own
accent colour. A guard and a registrar never see the same application.

| Portal | URL | Who signs in | What is in it |
|--------|-----|--------------|---------------|
| **Security Gate** | `/guard/login` | Security guards | Gate Console, Gate Log |
| **Registration Office** | `/registry/login` | Registration officers | Pending Approvals, Students, Import, Computers, Holds & Theft, Permits |
| **Administration** | `/admin/login` | Administrators | Everything above, plus Dashboard, Gates, Staff Accounts, Read Audit Log |

Sign in at the wrong door and the system says so plainly and links you to yours, rather than
just refusing. Administrators are admitted to every portal and get a **portal switcher** in the
sidebar, so they can stand at a gate and see exactly what the guard sees.

Guards deliberately **cannot** change ownership. That is the whole integrity of the system - if
the person checking computers could also reassign them, the register would be worthless.

### One public page for students - no account

Students **do not sign in and have no portal**. They open `/register` on a phone and either
**register a computer** (reg number, the email or national ID the university already holds, the
machine's details and a photo) or **check my computers** to see whether a submission was
approved.

What makes an open endpoint safe is what it *cannot* do. It can only ever create a **PENDING**
record - it cannot approve anything, edit an existing record, or read the register. On top of
that:

- Identity is checked against details already on the student's record, so a passer-by cannot
  register a laptop against somebody else's reg number.
- "No such student" and "details do not match" return the **same** message, so the form cannot
  be used to discover who is enrolled.
- A duplicate serial is refused **without naming the current owner**.
- Throttled to 12 requests an hour per IP - plenty for a student fixing a typo, useless for
  grinding reg numbers.
- PENDING is blocked at every gate, so nothing a student submits can leave campus until a human
  has approved it.

Submissions land in **Pending Approvals**, where a registrar approves (optionally applying an
asset tag) or rejects with a written reason. Either way the student is emailed the outcome.

---

## What it does

**At the gate**

- Look up a student by registration number - tolerant of spaces, dashes and case, because guards
  type in a hurry (`218 001 234`, `218-001-234` and `218001234` all match).
- **Live typeahead** as the guard types, with arrow-key selection.
- Reverse lookup: a laptop turns up without its owner - type the serial or asset tag and the
  system names the registered owner.
- QR stickers on each machine, scanned with the device camera.
- The registered **photo of the computer** sits beside the ALLOW/DENY buttons.
- Every decision recorded with gate, guard, direction, outcome and time.
- **Works offline.** If the network drops, decisions queue on the device and sync on reconnect,
  with no duplicates.

**Blocks and holds**

- A computer reported stolen or lost is refused at *every* gate immediately.
- Finance holds, disciplinary holds and ownership disputes block the same way.
- A guard cannot simply wave a blocked computer through - they must either deny it, or record an
  **override with a written reason**, which is flagged for the security office.
- Suspended and withdrawn students are called out before their equipment leaves.

**Register management**

- Students, computers, departments and gates.
- **Bulk student import from CSV** - validated and previewed before anything is written, then
  committed in one transaction. Alternative column headings are understood, blank cells never
  erase existing data, and a bad row is reported with its line number rather than failing the
  whole file.
- **Photo capture at registration**, downscaled in the browser before upload.
- **Email (and pluggable SMS) to the owner** the moment their computer leaves campus - the
  fastest theft detection there is - and again when a registration is approved or rejected.
- Temporary permits, for when a student lends their laptop to a classmate or a technician takes
  equipment out for repair. The gate shows the permitted carrier's name and ID.
- Ownership transfers, with full history retained.
- Printable QR stickers.

**Oversight**

- Dashboard: movement today, computers currently on campus, denials, overrides, per-gate
  activity, seven-day entries/exits chart.
- Searchable, filterable gate log with CSV export for investigations.
- The gate log is **append-only** - it cannot be edited or deleted, even by an administrator.

---

## Search

Search is the thing a guard touches most, so it gets its own data structure: an **inverted
index** (`search.SearchToken`), one row per searchable word per record.

The obvious `LIKE '%mug%'` cannot use a B-tree index - a leading wildcard gives the database
nowhere to start, so every search is a full table scan. Splitting records into words and
indexing those turns the common case into an ordered range scan.

Two details make the difference between it working and not:

- **Range, not `LIKE`.** SQLite's `LIKE` is case-insensitive by default and therefore *cannot*
  use a plain index either, so a prefix query is expressed as `token >= 'MUG' AND token < 'MUH'`.
  (Postgres has the same trap under a non-C collation without `text_pattern_ops`.)
- **Reg numbers skip the token table entirely.** `reg_number_key` and `serial_key` already carry
  unique indexes, so a digit-shaped query is served by a direct range scan on those columns.

Measured against the `icontains` scan it replaced, on the workload the API actually runs
(`COUNT(*)` plus one page), 20,000 students:

| query | scan | indexed | speed-up |
|---|---|---|---|
| common surname | 9.55 ms | 2.38 ms | 4.0x |
| common given name | 5.09 ms | 2.08 ms | 2.4x |
| reg number prefix | 7.33 ms | 0.62 ms | 11.8x |
| exact reg number | 16.49 ms | 0.51 ms | 32.5x |
| no match at all | 15.44 ms | 0.99 ms | 15.6x |

More important than the ratios: the reg-number path measured **0.62 ms at both 5,000 and 20,000
students** - flat, while the scan grew with the table.

The index is maintained by `post_save` signals and cascades on delete, so it cannot drift. After
a bulk load that bypasses signals, run `python manage.py rebuild_search_index`.

**Middle-of-word search.** A prefix index structurally cannot find `gish` inside `Mugisha`. On
PostgreSQL a `pg_trgm` GIN index handles that; elsewhere it falls back to a scan. Either way it
runs only when the fast prefix path already came back empty, and never for fragments under three
characters. The migration that creates it is a clean no-op on SQLite.

**Live search** is served by `/api/search/suggest/`. Three things keep it honest: a 180 ms
debounce so a burst of keystrokes is one request, an `AbortController` so a superseded request
cannot land late and overwrite a newer result, and a small in-memory cache so backspacing is
instant. Measured over HTTP: **26 ms average.**

---

## Notifications

Messages are never sent during a request. Each is written to an **outbox table**
(`notifications.Notification`) inside the same transaction as the thing it describes, and a
worker drains it afterwards:

```bash
python manage.py process_notifications            # one pass - run from cron
python manage.py process_notifications --loop     # stay running under systemd
python manage.py process_notifications --retry-failed
```

Three reasons for an outbox rather than sending inline:

- **The gate stays fast.** An SMTP round trip has no business on the critical path of recording
  a scan. Measured: approve 195 ms, scan 99 ms, with no mail sent in-request.
- **Nothing is lost.** A mail server having a bad afternoon used to mean the message vanished.
  Now it stays `PENDING` and is retried up to five times, then marked `FAILED` for a human.
- **A rollback sends nothing.** Dispatch hangs off `transaction.on_commit`, so a scan that fails
  to save cannot email anybody about it.

`NOTIFY_DISPATCH` picks how the outbox drains - `inline` (development and tests), `thread`
(single-process deployments) or `worker` (production). Swapping in Celery or django-q later means
changing one function, `_schedule_dispatch`; the outbox stays either way, because a broker that
loses a message and a database row that does not are different guarantees.

SMS ships as an interface with a console implementation - point `SMS_BACKEND` at a class with
`send(to, message)` to go live.

---

## Sessions

The gate console runs on a terminal several guards use in turn, often left facing an open
queue. An unattended signed-in session there is a bigger risk than anywhere else in the system,
so a session ends itself after `VITE_IDLE_MINUTES` (default 30) without activity.

- A warning appears 60 seconds before, with **Stay signed in**. Any real interaction cancels it,
  so in normal use it is never seen.
- Timing is **wall-clock, not a timer**: a laptop that sleeps for an hour comes back expired,
  where a `setTimeout` would simply have been suspended.
- Signing out in one tab signs out the others on the same machine.
- The login page then says *why* you were signed out, rather than just presenting a blank form.

**Redirection** goes with it. Ask for `/registry/devices/4` while signed out and you are sent to
that portal's login, told you will be returned there, and taken to that exact page afterwards.
The target is checked against the portal's own base path, so a stale or hostile `from` cannot
bounce you into a portal you have no access to. Signing in at the wrong door still explains
itself and links to the right one.

---

## Read audit log

Any signed-in staff member can read the whole register: names, photos, phone numbers, and what
equipment each student owns. That is what the job needs, and it is exactly why *"a guard looked
up their ex-partner forty times"* should be an answerable question.

Every gate lookup, typeahead search, searched list and CSV export is recorded with who, what they
typed, whose record it resolved to, how many results came back, and the client IP.
Administrators read it at **Administration → Read Audit Log**; guards and registrars cannot see
it at all, and **nobody can edit or delete an entry** - the API exposes no write path, because an
audit log the audited can tidy up is not an audit log.

Idle browsing is deliberately not recorded. Logging every page of the student list would bury the
reads that actually mean something.

Per-account rate limits back this up: `lookup-burst` (120/min) catches a script, `lookup-daily`
(4000/day) catches a slow scrape spread across a shift. Both are keyed on the **account**, so a
shared gate terminal does not pool its budget.

**Retention.** The log is pruned by `manage.py prune_audit_log`, keeping `AUDIT_RETENTION_DAYS`
(default 365). That default is a defensible starting point, not a recommendation: how long
reads should be kept is a policy decision for the university. The command refuses to delete
more than 90% of the log without `--force`, because a mistyped `--days` should not quietly
destroy the one record of who looked at whom.

**Alerting.** `manage.py check_audit_alerts`, run hourly, emails the security office when an
account reads far above **its own** recent baseline. A flat threshold would be useless here: the
Main Gate guard on a Monday legitimately does ten times the reads of the Service Gate guard on a
Sunday, and one number cannot fit both. A fixed floor sits underneath so a new account cannot
trip the ratio on three lookups, and each account is alerted about at most once per cooldown
window. The message says plainly that it is not evidence of anything on its own.

---

## Two-factor authentication

An administrator reaches every portal, can reset any password and can read the whole register.
One leaked admin password is the worst thing that can happen here, so TOTP is available on any
account and pressed on administrators.

- **TOTP only, no SMS.** The phone number lives in the same database as the account, so an
  attacker with database access would have both. An authenticator app keeps the factor separate.
- **Enforced where tokens are minted.** `django_otp`'s middleware assumes sessions; this API is
  JWT, so the check lives in the login serializer. A token is never issued without the factor.
- **Enrolment is two steps.** Creating a device does not arm it. You must prove you can generate
  a code first, so a mistyped setup cannot lock you out.
- **Rolls out account by account.** 2FA is required only once an account has a confirmed device,
  so turning it on does not lock out the whole office on deployment day.
- **Only you can turn off your own.** There is no path for one administrator to silently disable
  another's second factor, and doing it to your own requires your password.

A mistyped code briefly locks the device, which is `django_otp` working as intended. The UI says
so explicitly rather than reporting "wrong code", because otherwise a user resets an
authenticator app that was working perfectly well.

---

## API

All endpoints need `Authorization: Bearer <token>` except `/api/health/`, `/api/auth/login/` and
everything under `/api/public/`.

### Auth
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login/` | Access + refresh tokens **and** the user profile |
| POST | `/api/auth/refresh/` | New access token |
| GET/PATCH | `/api/auth/me/` | Own profile (a guard may change their gate, not their role) |
| POST | `/api/auth/change-password/` | Change own password |
| - | `/api/auth/users/` | Staff accounts (admin only); `POST {id}/reset_password/` |
| GET | `/api/auth/access-log/` | Read audit log (admin only, read-only) |
| GET | `/api/auth/access-log/summary/` | Busiest accounts, last 7 days |
| GET/POST/PUT/DELETE | `/api/auth/two-factor/` | Status, begin enrolment, confirm, turn off |

### Public - no authentication
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/public/choices/` | Equipment types for the form |
| POST | `/api/public/register-computer/` | Student self-registration → PENDING |
| POST | `/api/public/my-computers/` | "Has mine been approved yet?" |

### The gate
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/checkpoint/lookup/?q=` | **The core endpoint.** Reg number, serial, asset tag or QR payload |
| GET | `/api/search/suggest/?q=` | Live typeahead |
| POST | `/api/checkpoint/scans/` | Record a decision |
| POST | `/api/checkpoint/scans/bulk/` | Flush a queued offline batch |
| GET | `/api/checkpoint/scans/` | Filterable log |
| GET | `/api/checkpoint/scans/export/` | CSV export |
| GET | `/api/checkpoint/dashboard/` | Statistics |

### Register
| Method | Path | Purpose |
|--------|------|---------|
| - | `/api/students/` | Student CRUD |
| POST | `/api/students/import-preview/` | Validate a CSV, write nothing |
| POST | `/api/students/import-commit/` | Import in one transaction |
| GET | `/api/students/summary/` | Counts by status |
| - | `/api/devices/` | Computer CRUD (multipart for photos) |
| GET | `/api/devices/pending/` | The approval queue |
| POST | `/api/devices/{id}/approve/` | Approve, optionally applying an asset tag |
| POST | `/api/devices/{id}/reject/` | Reject with a written reason |
| GET | `/api/devices/{id}/qr/` | QR sticker PNG |
| POST | `/api/devices/{id}/transfer/` | Change owner |
| POST | `/api/devices/{id}/report_stolen/` | Block everywhere at once |
| GET | `/api/devices/{id}/history/` | Transfers, holds, permits |
| - | `/api/devices/flags/` | Holds; `POST {id}/resolve/` to lift |
| - | `/api/devices/permits/` | Permits; `POST {id}/revoke/` |
| - | `/api/campus/gates/`, `/api/campus/departments/` | Locations and faculties |

### Lookup response

```jsonc
{
  "query": "218001234",
  "resolved_as": "STUDENT",        // or DEVICE, NOT_FOUND
  "method": "REG_NUMBER",          // or SERIAL, ASSET_TAG, QR
  "student": { "reg_number": "…", "full_name": "…", "photo": "…", "status": "ACTIVE" },
  "devices": [{
    "serial_number": "HP12345678",
    "brand": "HP",
    "photo": "/media/devices/…",
    "distinguishing_marks": "Blue sticker on lid",
    "recommendation": { "action": "PASS", "reasons": [] },
    "valid_permits": [],
    "last_movement": { "direction": "IN", "gate": "Main Gate", "created_at": "…" }
  }],
  "matched_device_id": null,
  "warnings": []
}
```

---

## Project layout

```
backend/
  config/         settings, urls, pagination, signed media serving
  accounts/       staff users, roles, permissions, throttles, audit log
  campus/         departments and gates
  students/       student records, public form, CSV importer
  devices/        computers, holds, permits, ownership transfers
  checkpoint/     gate lookup, scan events, dashboard
  search/         inverted index, indexer, typeahead
  notifications/  outbox, delivery backends, worker command
  tests/          202 tests

frontend/src/
  api/            fetch client (token refresh, cancellation), endpoints
  auth/           AuthContext, PortalContext, route guards
  components/     PortalShell, DataState, PhotoInput, QrScanner, Brand, ui
  hooks/          useLiveSearch (debounce + cancel + cache), useOfflineQueue
  pages/          one per screen
  portals.js      the three portal definitions
```

### Your logo

The brand mark is a **slot**, not a fixed asset. Drop your file at `frontend/src/assets/logo.svg`
(or `.png`) and uncomment the two marked lines at the top of
[`frontend/src/components/Brand.jsx`](frontend/src/components/Brand.jsx). Nothing else changes - it feeds every sidebar, all three login screens and the public student page. Until then a neutral
`LOGO` placeholder holds the correct spacing.

---

## Management commands

| Command | What it is for |
|---------|----------------|
| `seed_demo` | Demo departments, gates, staff, students, computers and gate logs. Safe to re-run. |
| `rebuild_search_index` | Rebuild the inverted index after a bulk load that bypassed signals. |
| `process_notifications` | Drain the notification outbox. `--loop`, `--retry-failed`. |
| `prune_audit_log` | Delete audit entries past `AUDIT_RETENTION_DAYS`. `--dry-run`, `--days`, `--force`. |
| `check_audit_alerts` | Email the security office about unusual read volume. `--dry-run`. |

---

## Tests

```bash
cd backend
.venv\Scripts\python.exe manage.py test tests     # 202 tests

cd frontend
npm test                                          # 47 tests
```

The frontend suite is Vitest and jsdom, covering the two pieces of behaviour that are hard to
check by hand: the offline scan queue and live-search cancellation.

**202 backend tests.** Notable areas:

| Area | Covers |
|------|--------|
| `test_lookup` | Reg-number normalisation, QR/serial/asset-tag resolution, HOLD recommendations |
| `test_scans` | Block rules, override requirements, offline sync idempotency, dashboard maths |
| `test_devices` | Role permissions, duplicate serials, transfers, permit validity windows |
| `test_public_form` | What the open endpoint *cannot* do - enumeration, owner leakage, self-approval |
| `test_search` | Tokeniser, index maintenance on rename/delete, prefix semantics |
| `test_import_notify` | CSV validation and rollback, outbox behaviour, retry and recovery |
| `test_audit` | What is logged, who can read it, append-only enforcement |
| `test_retention_2fa` | Prune safety rails, baseline alerting, the whole 2FA flow |
| `test_auth` | Login, token use, self-service limits |

---

## Notes on some design decisions

**Reg numbers and serials are stored twice.** Once as typed, once normalised into a `_key` column
with punctuation stripped and uppercased. Lookups hit the indexed key column, so a guard's typing
style never causes a miss.

**Scan records snapshot their text.** `device_label`, `student_name` and `claimed_reg_number` are
copied onto the scan at decision time. If a device record is later deleted or transferred, the
historical log still reads correctly - which matters if it is ever evidence.

**Idempotency keys on every scan.** A queued offline scan carries a `client_reference` UUID.
Replaying it returns the original record rather than creating a duplicate, so a flaky connection
can retry safely.

**Overrides are a first-class outcome, not a loophole.** Real gates have real exceptions - a
lecturer vouches for a student, security control clears someone over the radio. Rather than
pretend that never happens, an override is its own verdict, requires a written reason, and
surfaces on the dashboard for review.

**Skeletons on first load, dimming on refetch.** A filter change dims the rows already on screen
instead of replacing them with placeholders - blanking out a table someone is halfway through
reading is worse than a moment of stale data.

**Chart colours were validated, not chosen by eye.** The entries/exits series use a blue/orange
categorical pair (colour-blind separation ΔE 24.7, both above 3:1 on white). The outcome bars use
the reserved status palette, which deliberately does *not* meet those separation gates - so every
outcome row carries an icon and a written label with its count, and colour never carries the
meaning alone.

**The app is deliberately light-only.** It runs on gate kiosks in daylight, and a guard should
never have to work out which colour scheme they are reading a HOLD banner in. The navigation,
the login and the landing page are light too: the earlier near-black sidebar and dark gradients
were the heaviest thing on screen and competed with the status colours, which are the one place
colour has to carry meaning.

**One accent, and everything tinted derives from it.** A portal declares a single colour and the
soft fills, hover states and active navigation are `color-mix`ed from it, so adding a fourth
portal means picking one hex value rather than six. The status palette is exempt and unchanged:
those values were checked for contrast and colour-blind separation, and a redesign is not a
reason to re-open that.

**Contrast is measured, not eyeballed.** Every foreground is checked against the background it
actually renders on. That caught a tier of grey introduced during the redesign at 2.63:1 where it
needed 4.5:1, and form-control borders at 1.42:1 where WCAG 1.4.11 wants 3:1. The palette now
carries two border roles for that reason: `--border` draws decorative structure between surfaces
and has no requirement, `--border-control` outlines a field and is measured at 3.41:1. There is
deliberately no third, lighter text tier, because on backgrounds this pale any text colour that
still passes lands within a hair of `--text-muted`, so the tier could only exist by failing.

**Keyboard paths are part of the layout.** The mobile drawer used to slide off-screen with
`translateX`, which left ten navigation links in the tab order pointing at an invisible menu; it
now goes `visibility: hidden` as well. Every page carries a skip link and a `<main>` landmark,
because otherwise reaching the table means tabbing the whole sidebar on every navigation. Dialogs
trap Tab and hand focus back to whatever opened them.

**Descriptions are not names.** A field's hint and error live outside its `<label>` and attach
with `aria-describedby`, so a screen reader announces the label rather than the label plus the
hint plus the error every time focus lands.

**Errors always end in an instruction.** The API error fallback used to surface the raw message,
so a 500 reached a gate terminal as "Request failed with 500". Every branch now names something
the reader can do, which matters most for the person who cannot open a console.

**Recharts is lazy-loaded.** It is only on the admin dashboard, so a guard on a phone downloads
110 kB gzipped instead of 224 kB.

---

## Deployment

```bash
docker compose up -d          # PostgreSQL
# backend/.env: DB_ENGINE=postgres, DJANGO_DEBUG=False, DJANGO_SSL_REDIRECT=True
python manage.py migrate
python manage.py rebuild_search_index
python manage.py check --deploy
```

`DJANGO_DEBUG=False` switches on HTTPS redirect, secure and HTTP-only cookies, HSTS (starting at
one day - raise it once every subdomain is HTTPS), `X-Frame-Options: DENY` and a same-origin
referrer policy. Behind nginx or a load balancer, leave `DJANGO_BEHIND_PROXY=True` so Django
trusts `X-Forwarded-Proto`; without it the SSL redirect becomes an infinite loop.

Run the notification worker from cron:

```
* * * * * cd /srv/computer_track/backend && .venv/bin/python manage.py process_notifications
```

SQLite is fine for the demo but allows a single writer at a time, which several gates recording at
once will hit. Switch to PostgreSQL before a pilot.

### Photos

Uploaded photos are **not** served off disk. Whitenoise handles `STATIC_ROOT` only, so a raw
`/media/` URL is dead with `DJANGO_DEBUG=False`, and serving that directory publicly would put
every student's face one guessed filename away from anybody. Instead the API returns short-lived
signed links, and `/api/media/<token>/` checks the signature before releasing a byte.

That works with no web server configuration at all. To let nginx send the file once Django has
approved it, set `MEDIA_ACCEL_REDIRECT=True` and add:

```nginx
location /protected-media/ {
    internal;                       # only reachable via X-Accel-Redirect
    alias /srv/computer_track/backend/media/;
}
```

`internal` is the load-bearing word. Without it that block is a public file listing and you have
reinvented the problem.

The tradeoff worth knowing: anyone who copies a photo URL out of the page can share it until it
expires. `MEDIA_LINK_TTL_SECONDS` (default 900) is how long you are willing for that to be true.
The alternative, fetching each image as an authenticated blob, would break "open the photo full
size in a new tab" at the gate, which guards actually use.

---

## Not built yet

- **Messaging system** - requested, spec pending from you. Nothing has been designed or stubbed
  for it, deliberately.

## If you take this further

1. **Decide the retention period.** 365 days is a placeholder I chose, not advice. Set
   `AUDIT_RETENTION_DAYS` to whatever the university's data policy actually says.
2. **Route the alert email somewhere staffed.** `AUDIT_ALERT_RECIPIENTS` is empty by default, so
   alerting stays inert until somebody fills it in.
3. **Recovery codes for two-factor**, and a password reset. Account recovery is the weakest
   operational surface here: `change-password` needs you to already be signed in, so a guard who
   forgets their password at 06:00 has to find an administrator, and an administrator who loses
   their phone needs another administrator.
4. **A backup and, more importantly, a restore drill.** The scan log is described above as
   something that may end up being evidence. There is no `pg_dump` schedule in this repository and
   nothing covering `media/`. A register nobody has ever restored from is a guess.
5. **Continuous integration.** 202 backend and 31 frontend tests, and nothing runs them on push.
   Cheapest useful addition in this list.
6. **A student lifecycle.** Nothing here handles graduation, withdrawal or suspension, so a
   registration is currently permanent and the gate will keep confirming ownership for somebody
   who left two years ago. Decide whether registrations expire each academic year.
7. **Make the gate console work fully offline.** The scan queue survives a dropped connection, but
   the app shell is not cached, so a guard who reloads the tab with no network gets a blank page.
   A service worker would close the gap between "tolerates flaky wifi" and "works at a gate".
8. **Widen the frontend suite.** Three files cover the trickiest hooks. The gate console's
   decision flow and the approval queue are the next most valuable to pin down.
