# Architecture

How Computer Track is put together, and why. This is the document to read
before changing something structural; the README covers running it, and
[CHANGELOG.md](CHANGELOG.md) covers what changed when.

---

## The problem, stated precisely

A student walks towards a campus gate carrying a laptop. A guard has a few
seconds to answer one question: **does this computer belong to this person,
and may it leave?**

Everything below follows from three properties of that moment.

**It is time-critical.** A queue forms behind the person being checked. A
lookup that takes four seconds instead of one is a queue that does not clear,
and a guard who starts waving people through.

**It happens at the edge of the network.** Gates are at the perimeter, often
outdoors, on wifi that drops. The system has to keep working when the network
does not, and record what happened when it comes back.

**It is a decision about a person, made by a person.** The software's job is
to put the right facts in front of the guard and to record what they decided.
It does not decide anything itself, and the record of the decision matters as
much as the decision.

---

## Shape

```
                    ┌─────────────────────────┐
   students  ─────► │  public form  /register │ ─┐
   (no account)     └─────────────────────────┘  │
                                                 │
   guards    ─────► ┌─────────────────────────┐  │      ┌──────────────┐
   registrars ────► │  React SPA, 3 portals   │ ─┼────► │  Django API  │
   admins    ─────► └─────────────────────────┘  │      └──────┬───────┘
                              │                  │             │
                    service worker (shell)       │      ┌──────┴───────┐
                    localStorage (scan queue) ───┘      │  PostgreSQL  │
                                                        └──────┬───────┘
                                                               │
                          ┌────────────────────────────────────┤
                          │                                    │
                   ┌──────┴──────┐                      ┌──────┴──────┐
                   │  Redis      │◄─── Celery ────────► │  outbox     │
                   │  cache      │     worker + beat    │  table      │
                   │  broker     │                      └──────┬──────┘
                   └─────────────┘                             │
                                                    Resend (email) ─┐
                                                    Africa's Talking ┘ (SMS)
```

---

## The two kinds of configuration

This is the distinction that most of the design hangs off, and getting it
wrong is what makes a system like this need a developer for everything.

**Deployment configuration** lives in `config/settings.py`, read from the
environment through `python-decouple`. Database credentials, an API key, a
rate limit, where Redis is. It changes when the software moves between
machines, and only a developer or a sysadmin touches it.

**Policy** lives in the database and is edited in the Registration Office
portal. How many computers a student may register, whether a projector needs
a gate pass, the exact sentence a guard reads when a computer is held, what
kinds of equipment exist, the wording of every message sent to a student.

None of the second list is a technical question. None of it is the same at two
universities. None of it should need an engineer and a release.

The registry in `campus/rules.py` is code, deliberately: it declares *what* is
configurable, its type, its bounds, its help text and its default. The values
are data. A key not in the registry cannot be stored, which is what stops the
settings table becoming an unvalidated dump — and a stored value that fails
its own validation falls back to the default rather than raising at a gate.

---

## Backend

Django 5 and DRF, JWT auth. Seven apps, split by what they are about rather
than by layer:

| App | Holds |
| --- | --- |
| `accounts` | Staff users, roles, two-factor, the read audit log and its alerting |
| `campus` | Departments, gates, equipment types, and the policy rule store |
| `students` | Student records, CSV import, and the public unauthenticated form |
| `devices` | Computers, holds, gate passes, ownership transfers, registration attempts |
| `checkpoint` | Gate lookups and the append-only scan log |
| `search` | The inverted index that makes lookups fast |
| `notifications` | The outbox, the message templates and the delivery providers |

### Why the search index exists

The obvious implementation of "find a student by name" is `icontains`, which
cannot use an index and degrades to a full table scan. At the gate that is the
one query that must not get slower as the register grows.

`search/` maintains an inverted index of tokens. Reg numbers and serials are
served by direct range scans on their own normalised columns and never touch
the token table at all — the fastest path, and the one the gate uses all day.
Names fall through to the index. `search/indexer.py` explains why a prefix
range beats `LIKE 'x%'` even though they look equivalent.

### Query shapes, and the N+1 that keeps coming back

`devices/queries.py` holds the querysets a device list needs, in one place,
because the same shape was being rebuilt slightly differently at four call
sites and getting it slightly wrong at three of them.

The recurring mistake is worth naming: `self.flags.filter(is_active=True)`
reads correctly and looks harmless, but calling `.filter()` on a related
manager always goes back to the database. `prefetch_related` caches the result
of `.all()` and nothing else. So a device list rendering blocking reasons for
thirty rows issued thirty extra queries no matter how carefully the queryset
was prefetched.

`tests/test_performance.py` asserts that a page of thirty rows costs the same
number of queries as a page of three. That is the property that actually
breaks when this regresses; a fixed number would fail on unrelated changes and
get relaxed until it meant nothing.

### Caching, in two layers

`config/cache.py` defines two aliases:

- **`default`** — rate-limit counters. What it holds *is* the truth while it
  lives there; losing it resets somebody's throttle window.
- **`derived`** — copies of what the database already knows: rules, equipment
  types, message templates, dashboard totals. Losing all of it costs a few
  queries and nothing else.

In front of both, `config/requestcache.py` is a per-thread memo that expires
in seconds. The rules are read once per row rendered, so a page of thirty
computers asks thirty times what the wording of a hold is. With a shared cache
that is free. Without one — a fresh deployment, a flushed cache — it is thirty
queries, which is exactly the N+1 the caching was meant to remove.

Rules and equipment types are invalidated by a signal on write, on commit
rather than on save, so a concurrent read cannot repopulate the cache from the
row that is about to change.

### The notification outbox

Notifications are written to a database table inside the same transaction as
the thing they describe, and sent afterwards by a worker.

This is not indirection for its own sake. Sending inline put an SMTP round
trip on the critical path of the one action that must never be slow, and a
mail server having a bad afternoon meant the message was simply lost. Writing
a row costs about as much as the scan itself, commits atomically with it, and
survives a restart.

Four dispatch modes, set by `NOTIFY_DISPATCH`: `celery` (production),
`inline` (development and tests), `thread` (single-process deployments), and
`worker` (cron). Every one of them writes the outbox row first, so the choice
affects latency and never durability. A broker that loses a message and a
committed row are different guarantees.

Failures are sorted into permanent and temporary. An unverified sending
domain, a number that is not a number, an empty SMS account: none of those
improve on the fifth attempt, and retrying them costs money on SMS and sender
reputation on email. Temporary failures back off linearly.

### Providers

`notifications/providers/` holds one thin adapter per service, each written so
the single function that touches a socket can be replaced in a test.
Everything above that line is logic — which address is used, what counts as
success, whether a failure is worth retrying — and it is the logic that
decides whether a student learns their laptop left campus.

Africa's Talking has one trap worth knowing about: it answers HTTP 200 and
reports the real outcome per recipient, so an invalid number or an empty
account looks like success at the transport layer. The recipient list is where
the truth is.

---

## Frontend

React 19, Vite, React Router, plain CSS with custom properties. No component
library and no CSS framework: the whole application is about twenty screens
with a consistent vocabulary, and a framework would have been more to learn
than to write.

### Three portals, not one app with role checks

`src/portals.js` declares three separate workspaces — Security Gate,
Registration Office, Administration — each with its own address, navigation
and accent colour. A guard and a registrar never see the same application.

They share one way in. `/login` names no portal, and `homePortalFor` routes
the person by role once the credentials are proved. Three labelled login
pages told an unauthenticated visitor which roles exist and which addresses to
try, and asked staff to know which door was theirs; the account already knows.
The old per-portal login paths redirect to `/login` so bookmarks survive.

Administrators may enter any portal, because being able to stand at a gate and
reproduce exactly what a guard is seeing is how a support call gets resolved.
There is no portal switcher in the sidebar: an administrator types the address,
which keeps the chrome identical for every role.

### Offline

Three separate mechanisms, because they fail differently:

**The shell** is cached by a service worker (`public/sw.js`), so the
application starts with no network. Without it, a refresh at a gate was a
blank page.

**Scans** queue in `localStorage` with an idempotency key and flush on
reconnect. The key is what makes retrying safe: the server answers a replayed
reference with the original scan rather than writing a second one.

**Lookups** the guard has already performed are kept in `sessionStorage` for
a few minutes, cleared on sign-out.

That last one is deliberately limited. The obvious way to make a gate console
work offline is to download the register to the device, and that is the one
thing it must not do: the register is every student's name, photograph,
telephone number and equipment, and a gate tablet is the least physically
secure device in the system. A cached answer is always labelled as one, with
the time it was taken, because a computer reported stolen since then would
still read as clear.

### What the server never trusts the client for

The offline queue is editable JSON in `localStorage`, so every rule is
enforced again on arrival. A tampered client cannot record ALLOWED against a
blocked computer, cannot take university property out without a pass, and
cannot write the history: `device_label` and `student_name` are snapshotted
from the register at decision time, not from the request body.

---

## Security

The threat model in full is in the README. The structural decisions:

**Photographs are never served off disk.** `config/media.py` hands out signed,
expiring links. An `<img>` tag cannot send an auth header, and an unguessable
filename is not a password — it is a URL that gets copied, logged and shared.

**Every read of the register is logged.** Any signed-in staff member can see
every student's name, photograph and equipment. That is necessary for the job
and uncomfortable for the same reason: without a record of reads, "a guard
looked up their ex-partner forty times" is an unanswerable question.
`accounts/alerting.py` compares each account against its own recent baseline,
because one flat threshold cannot fit both a busy main gate and a quiet
service gate.

**Exports are escaped.** A cell beginning `=` is a formula to a spreadsheet,
and much of what is exported was typed by a student on a form with no login.

**The public form can only ever create a pending record.** It cannot approve
anything, edit anything, or read the register. That, plus in-person approval,
is what makes an unauthenticated write endpoint safe to expose.

**Registration attempts are recorded, including refusals.** A student
registering their own laptop succeeds once. A run of different serials from
one registration number is what working through a bag of stolen laptops looks
like — and a serial matching a computer reported stolen means that computer
was on campus when the form was submitted, so the security office is told
while the submitter is told only that the serial is taken.

---

## Testing

| Suite | What it covers |
| --- | --- |
| `backend/tests/` | Gate rules, permissions, search, auditing, providers, policy, query counts |
| `frontend/src/test/` | The offline queue, live search, session expiry, accessibility contracts |
| `tests/` (root) | Playwright, driving the real application in a real browser |

Two conventions worth keeping:

Every test names the failure it prevents, in its own name or its docstring. A
test called `test_serializer_valid` tells the next reader nothing about
whether it still matters.

The suite runs against a dummy `derived` cache so one test cannot serve
another's stale rules, while the `default` cache stays real so that rate-limit
tests actually rate limit. The tests that are about caching turn it back on
explicitly.

---

## Things deliberately not done

**A student login.** Students are records, not users. Adding accounts for
several thousand people who each need the system twice a year would be a
password reset queue, not a feature. The public form checks identity against
what is already on file.

**Caching the register for offline lookup.** See above.

**Blocking a student who submits repeatedly.** It flags for review instead. A
student with a broken keyboard retypes a serial too, and a check that stops
real students is a check that gets switched off.

**Making the software decide.** It recommends CLEAR or HOLD and records what
the guard decided. Every hold can be overridden with a written reason, because
the alternative is a guard who cannot let an ambulance through.
