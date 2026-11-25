# etracker - Campus Gate Computer Register

A system for university security guards to verify, at any gate, that the computer a student is
carrying actually belongs to them.

A student says their registration number, the guard types it in, and the screen shows the
student's photo, their details and every computer registered in their name - each with a clear
**CLEAR** or **HOLD** recommendation and the registered photo to compare against. The guard
matches the machine in front of them and records the decision.

**Stack:** Django 5.2 + DRF (JWT auth) · React 19 + Vite · PostgreSQL and Redis in production,
SQLite and in-process caching with no setup at all · Celery for background work · Resend and
Africa's Talking for email and SMS · Docker Compose for the lot.

Almost nothing here is fixed in code. The equipment types, the gate rules, the wording a guard
reads and the messages students receive are all edited by the registration office - see
[Rules and wording](#rules-and-wording).

## Project links

| | |
|---|---|
| **Live app** | **https://etracker-blush.vercel.app** |
| **Demo video** | [Final prototype demo (YouTube)](https://www.youtube.com/watch?v=8jatDaRBFm8) |
| **SRS and proposal** | [Project proposal and SRS (Google Doc)](https://docs.google.com/document/d/1RoiJfIf-zGDeVO3oBFSsr6Xa4U0G-lx18q0HA9okkSQ/edit) |
| **Student survey** | [Laptops at the Campus Gate (Google Form)](https://docs.google.com/forms/d/e/1FAIpQLSfc3yEK3QLCTlYxaLVL_0saSqivhtxQW4z7Cp8FzdxwVwRbTg/viewform), 22 responses, [results below](#what-students-told-us) |
| **System design (UML)** | [Appendix B: UML diagrams](research/APPENDIX_B_SRS.md) and the editable diagrams in [`research/diagrams`](research/diagrams) |

Sign in to the live app with the [demo accounts](#demo-accounts), then follow
[the guided tour](#a-guided-tour-for-anyone-marking-or-reviewing-this), which walks
through every part of the system in about ten minutes using real records from the
deployed site.
### Signing in to the live app

Open **https://etracker-blush.vercel.app/login** and use any of these. There is nothing
to create, and no portal to choose: the username decides which one opens.

| Username | Password | Opens |
|---|---|---|
| `admin` | `passw0rd!` | Administration: every screen in the system |
| `registrar` | `passw0rd!` | Registration Office: approvals and the register |
| `guard1` | `passw0rd!` | Security Gate: the gate console |

Students need no account at all: **`/register`** to register a computer, and
**`/register?tab=status`** to check one.

Then follow [the guided tour](#a-guided-tour-for-anyone-marking-or-reviewing-this),
which walks through everything the system does in about ten minutes, with real
serial numbers from the live site to paste in. The full account list is under
[demo accounts](#demo-accounts).

## The problem

Students carry their laptops through campus gates every day, but a guard has no quick way to
tell whether the computer belongs to the person carrying it, or whether it has been reported
lost or stolen. Checks are done from memory or paper, or not at all. Laptops are among the most
stolen items on university campuses, theft is the most commonly recorded crime in Rwanda, and for
a student a stolen laptop can mean a lost semester of coursework. Existing gate systems control
who walks in; none of them check what is carried out.

### What students told us

An anonymous survey, ["Laptops at the Campus Gate"](https://docs.google.com/forms/d/e/1FAIpQLSfc3yEK3QLCTlYxaLVL_0saSqivhtxQW4z7Cp8FzdxwVwRbTg/viewform),
had 22 student responses. All 22 bring a
laptop onto campus, and 18 carry it through a gate three or more days a week.

| Finding | Students |
| --- | --- |
| Know another student whose laptop or device was lost or stolen on campus in the last 12 months | 19 of 22 |
| Have been stopped or delayed because a guard could not confirm the laptop was theirs | 16 of 22 |
| Have been made late for a class, exam or appointment by a gate check | 16 of 22 |
| Think the current checks would not stop someone walking out with their laptop | 13 of 22 |
| Say the usual check is a serial number written by hand in a book | 14 of 22 |
| Agree the way laptops are checked at the gate needs to change | 20 of 22 |
| Would register their laptop once if the gate recognised it afterwards | 18 of 22 |

Ten respondents had lost a device on campus themselves; of the nine who said whether it came
back, one got it back. Their worries about registering shaped the design: how long it takes
(13 of 21) is why registration is one public form with no account; how the data is stored and
who sees it (12 and 10 of 21) is why student details are staff-only by role and every lookup is
written to the [read audit log](#read-audit-log); being wrongly stopped (8 of 21) is why the guard
sees the owner's photo and an override needs a written reason.

etracker is the register that closes that gap: students register their computers once, the
registration office approves them in person, and any guard at any gate can confirm ownership in
seconds, even with no network.

## How the SRS requirements map to the app

| SRS requirement | Where to see it |
|---|---|
| **FR 1** Student device registration (form, pending record, QR code) | `/register` (no account), then the QR sticker on a computer's detail page |
| **FR 2** Approval and management (approve, reject, approval evidence, transfer, holds) | Registration Office: *Pending approvals*, *Computers* (detail page: transfer owner, report stolen) |
| **FR 3** Gate verification (search by reg number, serial, asset tag or QR; owner photo; status) | Security Gate: *Gate console* |
| **FR 4** Lost and stolen devices (report, block at every gate, record who changed it) | *Holds and theft*; the public *Report lost or stolen* tab on `/register` |
| **FR 5** Gate decisions (gate, direction, rules, verdict, override with a written reason) | *Gate console* and *Gate log* |
| **FR 6** Temporary passes (issue, link to a device, validity, expiry) | *Permits* |
| **FR 7** Offline operation (cached app, queued decisions, sync without duplicates) | *Gate console* with the network turned off; see [Working offline](#working-offline) |
| **FR 8** Notifications (outbox, email, SMS, delivery status) | *Messages*; see [Notifications](#notifications) |
| **FR 9** Administration and audit (users, policies, audit log, suspicious access, reports) | Administration: *Staff accounts*, *Rules and wording*, *Read audit log*, *Dashboard*, CSV exports |

The three actors in the system design each have their own portal behind one sign-in page:
security guards, registration officers and administrators. Students use the public page and need
no account.

---

## Contents

- [Project links](#project-links) · [The problem](#the-problem) · [Requirements map](#how-the-srs-requirements-map-to-the-app)
- [Running it](#running-it) - [with Docker](#with-docker) or [from source](#from-source) · [Demo accounts](#demo-accounts)
- **[A guided tour](#a-guided-tour-for-anyone-marking-or-reviewing-this)** - the shortest path through everything the system does, with real values to paste in
- [Who uses what](#who-uses-what) - three staff portals and one public student page
- [What it does](#what-it-does)
- [Rules and wording](#rules-and-wording) - what a registrar can change without a developer
- [Search](#search) - the inverted index and why it is fast
- [Notifications](#notifications) - the outbox, Resend and Africa's Talking
- [Working offline](#working-offline)
- [Read audit log](#read-audit-log)
- [API](#api) · [Project layout](#project-layout) · [Commands](#management-commands)
- [Tests](#tests) · [Deployment](#deployment) - including [on Vercel](#on-vercel-the-live-demo)
- [ARCHITECTURE.md](ARCHITECTURE.md) - how it is put together, and why
- [CHANGELOG.md](CHANGELOG.md) - what changed when

---

## Running it

### Before you start

You need:

- **Git**
- **Python 3.12 or newer** (developed on 3.13)
- **Node.js 20 or newer**, with npm
- **Docker Desktop**, only if you use the Docker route

Get the code:

```bash
git clone https://github.com/mndekwe-dot/Computer_Track.git
cd Computer_Track
```

Then follow **one** of the two routes below. *From source* is the quickest on a laptop. Run the
backend and the frontend in two separate terminals.

### With Docker

The whole system - PostgreSQL, Redis, the API, the background worker, the scheduler and
the site - in one command. Nothing to install but Docker itself, and nothing to edit.

**1. Start Docker Desktop**, then, from the project folder:

```bash
cp .env.docker.example .env
docker compose up --build -d
```

The first build pulls images and compiles the frontend, so expect **three to five
minutes**. Later starts take seconds. `-d` leaves it running in the background and gives
you your terminal back.

**2. Create the tables and load the demo data**, once:

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_demo
docker compose exec api python manage.py rebuild_search_index
```

**3. Open http://localhost:8080** and sign in with `admin` / `passw0rd!`, or any of the
[demo accounts](#demo-accounts). The API is on http://localhost:8000.

The copied `.env` already contains a throwaway secret key and database password, so
there is nothing to fill in for a local run. Replace both before putting this anywhere
reachable from outside your machine.

**Useful afterwards:**

```bash
docker compose logs -f api     # follow the API log
docker compose ps              # what is running
docker compose down            # stop everything, keep the data
docker compose down -v         # stop and delete the database and uploads
```

If port 8080 or 8000 is already taken, change `WEB_PORT` or `API_PORT` in `.env` and
run `docker compose up -d` again.

**Why five services.** `db` is PostgreSQL, because SQLite allows one writer at a time
and several gates recording simultaneously will hit that. `redis` is the cache and the
Celery broker; without it four gunicorn workers keep four separate copies of the rules.
`api` is Django under gunicorn. `worker` drains the notification outbox, separately so a
slow provider cannot occupy a request thread. `beat` is the clock, without which nothing
sweeps up messages queued while the broker was down.

### From source

Neither PostgreSQL nor Redis is required. Without them it uses SQLite, caches in process memory
and runs background tasks inline, which is the right shape for a laptop.

#### Backend

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

#### Frontend

```bash
cd frontend
npm install
copy .env.example .env          # cp on macOS / Linux
npm run dev
```

App on `http://localhost:5173`.

### Demo accounts

Everyone signs in at the same page, **`/login`**. There is no account to create and no
portal to choose: the username decides which one opens.

**Password for every account below: `passw0rd!`**

| Username | Who they are | Where signing in takes you |
|----------|--------------|----------------------------|
| `admin` | Administrator | Dashboard, and every screen in the system |
| `registrar` | Registration officer | Pending Approvals |
| `guard1` | Security guard, Main Gate | Gate Console |
| `guard2` | Security guard, West Gate | Gate Console |
| `guard3` | Security guard, Hostel Gate | Gate Console |

Students need no account at all. The public pages are `/register` and `/register?tab=status`.

These accounts and their data come from `seed_demo`, which creates 40 students, 38
computers, 4 gates and 123 gate records. **It is invented data, not real people.**

---

## A guided tour, for anyone marking or reviewing this

This is the shortest path through everything the system does. It takes about ten
minutes, and every value below is real: these are the records on the live site right
now, so you can copy and paste them.

Start at the live app and sign in with the accounts above.

### 1. Register a computer, as a student (no login)

Open **`/register`**.

1. Pick any student from the register. If you want one ready to use:
   registration number **`218100002`**, email **`chantal.shema@student.university.edu`**.
2. Fill in a serial number you invent, a make and a colour, and submit.
3. It comes back **pending**. Nothing is approved online, because online nobody has
   seen the computer.

Then open **`/register?tab=status`**, enter the same registration number, and see the
computer you just submitted waiting for approval.

### 2. Approve it, as the registration office

Sign in as **`registrar`**.

1. **Pending Approvals** shows your submission.
2. Click approve. The dialog asks **what you actually checked**: student ID matched,
   computer unlocked in front of you, serial read from the running system, proof of
   purchase seen.
3. Approve it, then open the computer from **Computers** and scroll to **Approval
   evidence**. It is written once and cannot be edited afterwards.

This is the system's answer to a problem it cannot solve: no software can prove who
legally owns a laptop. It can record how carefully the claim was checked.

### 3. Check a computer at the gate, as a guard

Sign in as **`guard1`**, which opens the **Gate Console**.

Search each of these and watch the verdict change:

| Search for | What you should see | Why |
|---|---|---|
| `AC950366620` | **CLEAR**, with the owner's photo | Approved, owner in good standing |
| `LE720865338` | **HOLD** | Reported stolen: "taken from the library reading room on 3 August" |
| `LE651400959` | **HOLD** | Still waiting for approval |
| `218100002` | The student and their computers | Searching by registration number, not serial |

You can also search by asset tag, or scan a QR sticker with the camera or a USB
barcode scanner.

**Try it with no network.** Open your browser's developer tools, go to the Network
tab, set it to *Offline*, and record a decision. The console keeps working and queues
the decision. Go back online and it syncs. A campus gate is exactly where the wifi is
worst.

### 4. See that everything was recorded, as an administrator

Sign in as **`admin`**.

- **Gate Log** lists every lookup made, with the guard, the gate, the direction and
  the verdict. Including yours, just now.
- **Read Audit Log** records which staff member looked at which student's record. The
  register holds names, photographs and phone numbers, so someone quietly browsing it
  is itself worth seeing.
- **Dashboard** summarises scans, holds and gate activity.

### 5. The rest, in any order

| Screen | Sign in as | What it does |
|---|---|---|
| **Holds and theft** | `registrar` | Flag a computer as stolen or disputed, and watch the gate verdict change immediately |
| **Permits** | `registrar` | Issue a gate pass so someone can carry a computer that is not theirs |
| **Students** | `registrar` | The student register, with CSV import |
| **Registration attempts** | `registrar` | Every public form submission, including the refused ones |
| **Rules and wording** | `registrar` | Change policy without a developer: how many computers a student may register, the exact sentence a guard reads on a hold |
| **Messages** | `registrar` | The wording of every email and SMS, editable, with a live preview |
| **Equipment types** | `registrar` | Add projectors or lab equipment to the things a gate checks |
| **Gates** | `registrar` | Add a gate, set which directions it serves |
| **Staff accounts** | `admin` | Create staff, assign roles, require two-factor |
| **My account** | anyone | Change password, set up two-factor |

### Things worth knowing while you look

- **Guards cannot change ownership.** If the person checking computers could also
  reassign them, the register would be worthless. Sign in as `guard1` and you will
  find no way to do it.
- **Photos uploaded on the live site may disappear.** It runs as a serverless
  function, which can only write to temporary storage. This is a hosting limit, not a
  design one; a real deployment stores them in object storage.
- **The demo data is fictional**, and the password above is public, so please do not
  treat anything in it as a real student record.

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

The landing page links to one staff sign-in page, and names no portal.

### Three staff portals, one front door

A guard and a registrar never see the same application: separate addresses, separate
navigation, separate accent colour. What they share is the way in.

| Portal | Base | Who works there | What is in it |
|--------|------|-----------------|---------------|
| **Security Gate** | `/guard` | Security guards | Gate Console, Gate Log |
| **Registration Office** | `/registry` | Registration officers | Pending Approvals, Students, Import, Computers, Holds & Theft, Permits |
| **Administration** | `/admin` | Administrators | Everything above, plus Dashboard, Gates, Staff Accounts, Read Audit Log |

Everyone signs in at **`/login`**. The page names no portal and lists no roles, because an
unauthenticated visitor should not be able to read the shape of the organisation off a login
screen, and nobody should have to know which door is theirs. Credentials decide: sign in and
you arrive where you work. The old per-portal addresses still redirect there, so a bookmark on
a gate terminal keeps working.

Typing another portal's address while signed in simply returns you to your own. Administrators
are admitted everywhere, so they can stand at a gate and see exactly what the guard sees.

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

## Rules and wording

Most of what a university would want to change about this system is not in the code.

`config/settings.py` holds *deployment* configuration - database credentials, an API key, where
Redis lives. It changes when the software moves between machines.

Policy is different, and it lives in the database, edited under **Rules & Wording** in the
Registration Office portal:

| Group | What a registrar can set |
| --- | --- |
| Names and contact details | The university's name, the registration office's name, the support and security telephone numbers. These appear in every message a student receives. |
| Gate decisions | Whether a pending computer is held, whether a suspended student's equipment is held, whether university property needs a gate pass, whether an override needs a written reason and how long it must be, and **the exact sentence a guard reads** in each case. |
| Student registration | Whether the public form is open at all, the most computers one student may register, whether a photograph is required, whether to ask where the computer was bought, and how many repeat submissions trigger a review. |
| Gate passes | The longest pass that may be issued. |
| Sessions | How long a terminal may sit idle, and how much warning it gives first. |

Alongside them, **Equipment Types** is a table too. A campus that checks lab equipment or
musical instruments at the gate adds them itself; retiring a type leaves the computers already
registered under it alone.

Three things make handing this over safe:

- **A rule outside the registry cannot be stored.** `campus/rules.py` declares every key with
  its type, bounds, help text and default. The registry is code; only the values are data.
- **A bad stored value falls back to its default.** Nothing should be able to write one, but a
  hand edit in the Django admin can, and a gate lookup that raises is a queue that stops moving.
- **A wording rule with a mistyped placeholder leaves it visible** rather than blowing up the
  lookup, so the mistake gets reported rather than silently swallowing text.

Saving takes effect at every gate immediately. There is no deployment step and no cache to wait
for.

---

## Working offline

Gates are at the perimeter of campus, often outdoors, on wifi that drops. Three separate
mechanisms, because they fail differently.

**The application itself** is cached by a service worker, so a refresh with no network starts the
console rather than showing a blank page. Before this, a locked screen at a busy gate meant a
guard with nothing but a white screen and a queue.

**Scans** queue in the browser with an idempotency key and flush when the network returns. The
key is what makes retrying safe: the server answers a replayed reference with the original scan
rather than writing a second one, so a sync that half-succeeded can simply be repeated. Each
carries the time the guard actually decided, not the time the network came back.

If the server refuses a queued scan outright, it is set aside for review rather than deleted.
Discarding them destroyed a record of decisions a guard really made, and told nobody.

**Lookups** the guard has already performed are kept for a few minutes so the same person coming
back through the same gate can still be checked. They live in the tab's own session storage, are
cleared on sign-out, and are always shown with the time they were taken.

### What is deliberately not cached

The obvious way to make a gate console work offline is to download the register to the device.
That is the one thing this does not do. The register is every student's name, photograph,
telephone number and equipment, and a gate tablet - shared, left on a desk, occasionally stolen
- is the least physically secure device in the system.

So only what has actually been looked up is kept, and only briefly. The device never holds a
record of somebody who has not walked past it. And a cached answer is labelled as one, because a
computer reported stolen since the lookup would still read as clear, and that is exactly where
being confidently wrong matters most.

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
(`notifications.Notification`) inside the same transaction as the thing it describes, and drained
afterwards.

Three reasons for an outbox rather than sending inline:

- **The gate stays fast.** A provider round trip has no business on the critical path of
  recording a scan. Measured: approve 195 ms, scan 99 ms, with nothing sent in-request.
- **Nothing is lost.** A mail server having a bad afternoon used to mean the message vanished.
  It stays `PENDING`, backs off, and is retried until it succeeds or is marked `FAILED`.
- **A rollback sends nothing.** Dispatch hangs off `transaction.on_commit`, so a scan that fails
  to save cannot email anybody about it.

`NOTIFY_DISPATCH` picks how it drains: `celery` (production), `inline` (development and tests),
`thread` (a single-process deployment with no broker), or `worker` (cron). Every one of them
writes the outbox row first, so the choice affects latency and never durability - a broker that
loses a message and a committed row are different guarantees.

```bash
python manage.py process_notifications            # one pass - run from cron
python manage.py process_notifications --loop     # stay running under systemd
python manage.py process_notifications --retry-failed
```

### Email: Resend

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
DEFAULT_FROM_EMAIL=etracker <no-reply@your-university.edu>
```

The sending domain has to be verified in the Resend dashboard first, or every message is
refused. It is a Django email backend rather than something the outbox calls directly, so
anything else that sends mail goes through it without knowing.

`EMAIL_PROVIDER=console` prints to the terminal and is the default in development.

### SMS: Africa's Talking

```env
SMS_PROVIDER=africastalking
AFRICASTALKING_USERNAME=your_username     # "sandbox" selects the test environment
AFRICASTALKING_API_KEY=atsk_...
AFRICASTALKING_SENDER_ID=YOURUNI          # blank uses the shared sender pool
SMS_DEFAULT_COUNTRY_CODE=+250
```

`SMS_PROVIDER=console` logs instead of sending, and is the default, so nothing silently costs
money.

Two details that matter, both handled once in
`notifications/providers/africastalking.py`:

- **Numbers.** Student records hold them as people write them - `0788123456`, `788123456`,
  `+250788123456`, `250 788 123 456`. The API accepts E.164 only and does nothing useful with
  anything else. All four are normalised to the same number.
- **Length.** A segment is 160 characters and every segment is charged, so a long message is
  truncated on a word boundary rather than quietly costing four times as much per student.

There is a trap in this API worth knowing about: it answers HTTP 200 and reports the real
outcome *per recipient*, so an invalid number or an empty account looks like success at the
transport layer. The recipient status is what is actually checked.

### Failures that will never succeed

An unverified sending domain, a number that is not a number, an empty SMS account: none of those
improve on the fifth attempt, and retrying them costs money on SMS and sender reputation on
email. Providers mark those failures permanent and the outbox stops immediately, rather than
burning five attempts. Everything else backs off and retries.

### The wording

Every message is a template a registrar edits under **Messages**, with a preview. A missing
placeholder renders empty rather than raising, an unknown one is left visible so a typo gets
reported rather than vanishing, and a blank template falls back to what shipped - the system
cannot be left unable to warn somebody that their laptop has gone.

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
  tests/          230 tests

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
.venv\Scripts\python.exe manage.py test           # 300 tests

cd frontend
npm test                                          # 51 tests

npx playwright test                               # 42 end-to-end, needs both running
```

The frontend suite is Vitest and jsdom, covering the behaviour that is hard to check by hand:
the offline scan queue, live-search cancellation, session expiry and the accessibility contracts
of the shared components - each of which is invisible on screen and so survives a redesign only
if something checks it.

**300 backend tests.** Notable areas:

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
| `test_rules` | The policy registry, its bounds, and that a saved rule changes the gate's answer |
| `test_registration_defences` | Every check against registering another student's computer, and that being caught tells the submitter nothing |
| `test_providers` | Resend and Africa's Talking without a network: number formats, truncation, and which failures are worth retrying |
| `test_performance` | That a page of thirty rows costs the same number of queries as three |
| `test_university_property` | Direction-dependent gate passes |

The performance tests deserve a note. They assert that the query count does not change between a
small result set and a larger one, rather than asserting a fixed number. An N+1 is not a slow
query - it is a count that grows with the data, invisible in development where the table has
nine rows. A fixed number would fail on any unrelated change and be relaxed until it meant
nothing.

---

## University property

The register holds two kinds of equipment, and the question at the gate is
different for each. For a student laptop it is *does this belong to the person
carrying it*. For a departmental projector it is *is this authorised to leave
at all*.

A registrar sets **Belongs to** when registering equipment. University property
takes a department and a custodian instead of a student owner, and both appear
at the gate so a guard holding a projector at nine at night has somebody to
call.

**The rule is direction-dependent, and only university property has it.**
Equipment on its way *out* is held unless it carries a valid gate pass; the
same projector coming back *in* passes freely, because stopping returning
equipment for want of a pass would be absurd. Issue passes under **Permits**,
or record an override with a written reason like any other exception.

That rule is enforced in the API, not in the console. The gate console is a
client, its offline queue lives in `localStorage`, and anything only checked
there is not checked at all.

Registrars can also add and edit **gates**. A new entrance opens and the office
that keeps the register is the one that knows; the API always permitted this,
only the navigation was withholding it.

---

## How someone would get a computer out

Worth being blunt about this, because the software is the easy half. Most ways
past this system are physical or procedural, and no amount of Django fixes
them.

### What the software does stop

- **Recording a blocked computer as allowed.** The server re-checks the block
  on every scan, so it does not matter what the client sends. This is why the
  offline queue is safe: it lives in `localStorage` where anyone with the
  terminal can edit it, and a tampered entry claiming `ALLOWED` on a stolen
  laptop is refused on sync. There is a test for exactly this.
- **Falsifying the record.** `device_label` and `student_name` are taken from
  the register at decision time rather than from the request, so a tampered
  client cannot write a history that never happened. `claimed_serial` and
  `claimed_reg_number` stay as the guard typed them, because a mistyped claim
  is evidence too.
- **Registering a computer that is already somebody else's.** A duplicate
  serial is refused, without naming the current owner.
- **Walking out on a self-registration.** Anything submitted through the public
  form is PENDING, and PENDING is blocked at every gate until a registrar has
  seen the machine.
- **Grinding the register through the public form.** Twelve requests an hour
  per IP, and identical wording for "no such student" and "details do not
  match" so it cannot be used to discover who is enrolled.
- **Reading a student's photo from a leaked URL.** Links are signed and expire.
- **Formulas in the exported gate log.** A cell beginning with `=` is a formula
  to Excel, and the public registration form sets a computer's brand and model
  with no login at all, so a stranger could plant one that runs weeks later on
  an administrator's machine. Every exported cell is now escaped.

### What it does not stop

These are the ones to design procedure around.

**Swap the sticker.** Peel the QR sticker off a registered laptop, put it on a
stolen one, walk out. The scan says "registered" and the guard waves it
through. The only defence is the one already on screen: the registered photo
and serial sit beside the decision buttons, and the guard has to actually
compare them. Software cannot force that. It is worth making "check the serial
on the machine, not just the sticker" the trained habit, because this is the
cheapest attack in the list.

**Register the stolen machine first.** Steal a laptop whose owner never
registered it, then register it in your own name through the public form. It
comes out PENDING, so it will not pass a gate until a registrar approves it,
which means the whole defence rests on the registrar asking for proof of
purchase or a receipt for a machine nobody has seen before. That check is a
procedure, not a field in the database.

**Use a gate nobody is watching.** Every control here assumes the computer is
presented at a manned gate. An unmanned side gate defeats all of it.

**Borrow a guard's session.** A gate terminal left signed in is a guard
account. The idle timeout closes the session after thirty minutes, which
narrows the window rather than closing it. Two-factor is currently
administrator-only; guards sign in with a password alone.

**Override.** A guard can wave any blocked computer through by writing a
reason. That is deliberate, because real gates have real exceptions, and every
override is recorded and surfaced for review. But it is only a control if
somebody reads the overrides. `Recent problems` on the dashboard is where they
appear; nobody is currently obliged to look.

**Report someone else's computer stolen.** The public report blocks a machine
immediately, which is the entire point when a laptop is walking away. It takes
the same identity check as registration, so it needs the registration number
*and* the email or national ID already on file, it can only touch a device
belonging to that student, and the owner is emailed the moment it happens. A
malicious report is therefore possible for someone who holds both details, and
noisy: the hold is reversible by any registrar in one click, and the laptop is
not.

### Worth doing before a real deployment

1. **Two-factor for guards, not just administrators.** A guard account is the
   one that can wave things through.
2. **Somebody owns the override queue.** A control nobody reads is not a
   control. A weekly review, or an alert past a threshold.
3. **Rate-limit the public form by more than IP.** A phone hopping cell towers
   gets a fresh IP; the current limit is a speed bump, not a wall.
4. **Decide what a registrar must see** before approving a self-registration.
   That decision is the difference between the register meaning something and
   not.

---

## Looking at it

The project had no way to see its own output, and it showed: a landing page shipped with a
tiling background artefact, cards that rendered as empty placeholders, and a crash on the
settings page. All three were obvious within a minute of seeing them and invisible in the source.

```bash
# with the API on :8000 and the app on :5173
cd frontend
npm run shots -- screenshots
```

`scripts/shoot.mjs` signs in as a guard, a registrar and an administrator in turn, walks every
screen at 1440 and 390, and writes a PNG per screen per viewport. It also fails loudly on console
errors and reports any page that redirected somewhere unexpected, which is how the settings crash
surfaced.

The app must be served on `:5173`: that is the only origin in `CORS_ALLOWED_ORIGINS`, and on any
other port every request is blocked and every screenshot is an error state.

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

### On Vercel (the live demo)

The live app runs as **one** Vercel project: the React build and the Django API share one
domain. [`vercel.json`](vercel.json) builds the frontend and sends every `/api/...` request to
[`api/index.py`](api/index.py), a serverless function that loads the same Django project used
everywhere else.

1. **Import the repository.** In Vercel, choose *Add New → Project* and import
   `Computer_Track`. Leave the root directory as the repository root; the build settings come
   from `vercel.json`.
2. **Add a database.** In the project, open *Storage → Create Database*, pick **Neon
   (Postgres)** and connect it to the project. This adds a `DATABASE_URL` environment variable.
3. **Set two environment variables** under *Settings → Environment Variables*:

   | Name | Value |
   |---|---|
   | `DJANGO_SECRET_KEY` | a long random string, for example from `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DJANGO_DEBUG` | `False` |
   | `EMAIL_PROVIDER` | `resend`, or leave it out to print mail to the function log |
   | `RESEND_API_KEY` | your Resend key, if email is wanted |
   | `DEFAULT_FROM_EMAIL` | `etracker <onboarding@resend.dev>` until a domain is verified |
   | `SMS_PROVIDER` | `console` until an SMS account is connected |

   Resend will not send from a domain you have not verified with it, so the test sender
   above is the one that works immediately. It delivers only to the address that owns the
   Resend account; any other recipient needs a verified domain.

4. **Deploy**, or redeploy so the new variables take effect.
5. **Create the tables and the demo data once**, from your own computer, pointed at the Vercel
   database. Copy `DATABASE_URL` from *Settings → Environment Variables*, then:

   ```bash
   cd backend
   pip install -r requirements.txt "psycopg[binary]"

   # Windows PowerShell
   $env:DATABASE_URL = "paste-the-value-here"
   # macOS / Linux
   # export DATABASE_URL="paste-the-value-here"

   python manage.py migrate
   python manage.py seed_demo
   python manage.py rebuild_search_index
   ```

6. Open `https://<your-project>.vercel.app/login` and sign in with a
   [demo account](#demo-accounts).

Two things worth knowing before you repeat this:

- **The root `requirements.txt` lists its packages directly.** It cannot say
  `-r backend/requirements.txt`, because Vercel's Python builder does not follow an
  include and fails the whole deploy with `could not parse requirements.txt`. Keep the
  two files in step by hand.
- **Migrations should run over Neon's direct connection, not the pooled one.** Neon
  supplies both: `DATABASE_URL` is pooled and is what the application should use, while
  `DATABASE_URL_UNPOOLED` is the direct connection. Schema changes through a connection
  pooler are the kind of thing that works until they do not.

What is different on Vercel:

- **Uploaded photos are temporary.** A serverless function can only write to `/tmp`, which is
  not shared between requests, so a photo uploaded on the live site may disappear. A permanent
  deployment should store media in object storage.
- **There is no background worker.** Notifications are sent inside the request instead of by
  Celery.
- **The Django admin is not exposed.** `/admin` is the React administration portal.

### On your own server

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
* * * * * cd /srv/etracker/backend && .venv/bin/python manage.py process_notifications
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
    alias /srv/etracker/backend/media/;
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

- **Permanent photo storage on Vercel.** The live demo keeps uploads in `/tmp`; object
  storage (S3, Cloudflare R2 or Vercel Blob) would make them last.
- **Recovery codes for two-factor, and a password reset.** Account recovery is the weakest
  operational surface here.
- **A backup and restore drill.** There is no `pg_dump` schedule in this repository and nothing
  covering `media/`.
- **Student lifecycle.** Nothing archives a graduate's computers or reclaims their asset tags.
- **Two-factor for guards.** Currently administrator accounts only.
- **A pilot at a real gate.** In the [survey](#what-students-told-us) 18 of 22 students said they
  would register, but no student or guard has used etracker at a real gate yet.

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
5. **Continuous integration.** 300 backend, 51 frontend and 42 end-to-end tests. The
   Playwright workflow in `.github/workflows` still needs the API and seed data brought up
   before it will pass - the container images now make that straightforward.
6. **A real sending domain.** `EMAIL_PROVIDER` and `SMS_PROVIDER` default to `console`, so a
   fresh deployment sends nothing at all until somebody sets them. That is the safe direction to
   be wrong in, but it does mean the exit notification - the most useful thing this system does
   about a theft - is inert until it is configured.
   Cheapest useful addition in this list.
6. **A student lifecycle.** Nothing here handles graduation, withdrawal or suspension, so a
   registration is currently permanent and the gate will keep confirming ownership for somebody
   who left two years ago. Decide whether registrations expire each academic year.
7. **Make the gate console work fully offline.** The scan queue survives a dropped connection, but
   the app shell is not cached, so a guard who reloads the tab with no network gets a blank page.
   A service worker would close the gap between "tolerates flaky wifi" and "works at a gate".
8. **Widen the frontend suite.** Three files cover the trickiest hooks. The gate console's
   decision flow and the approval queue are the next most valuable to pin down.
