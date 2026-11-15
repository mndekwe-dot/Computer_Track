# Appendix B: UML Software Design Models

**Submission File Name Convention:** `ndekwe_dieu_merci_[Assignment2]_[10262026]`

This appendix presents **four (4) distinct types of UML 2.5 diagrams** for the **Computer Track** campus equipment registration and gate verification system: two **Structural Diagrams** (**UML Class Diagram** and **UML Component Diagram**) and two **Behavioral Diagrams** (**UML Use Case Diagram** and **UML Activity Diagram**).

---

## B.1 UML Class Diagram (Structural Diagram 1)

> **[Insert exported image of `research/diagrams/class-diagram.drawio` here]**
> *Figure B.1: Computer Track — UML 2.5 Class Diagram (Domain Model & Core Operations)*

* **Description of the Diagram:**
  The UML Class Diagram models the static domain structure and relational database schema of Computer Track across fourteen (14) 3-compartment UML classes (`Department`, `EquipmentType`, `Rule`, `Student`, `RegistrationAttempt`, `Device`, `DeviceFlag`, `OwnershipTransfer`, `ScanEvent`, `TemporaryPermit`, `Notification`, `Gate`, `User`, and `ReadAuditLog`).

* **Major Elements & Actors:**
  * **Core Registry Classes (`Department`, `Student`, `Device`, `EquipmentType`):** Represent university departments, enrolled students (who act as unauthenticated self-service actors without login accounts), equipment categories, and registered devices (`uid`, `serial_number`, `serial_key`, `ownership`, `status`, and clearance methods `active_flags()`, `valid_permits()`, `blocking_reasons()`, `exit_restrictions()`, and `is_blocked()`).
  * **Lifecycle & Policy Classes (`DeviceFlag`, `TemporaryPermit`, `OwnershipTransfer`, `RegistrationAttempt`, `Rule`):** Govern active security holds (`LOST`, `STOLEN`, `DISPUTED`, `UNPAID_LOAN`, `EXPIRED_PERMIT`), time-bounded third-party borrower passes (`is_valid_now()`), ownership transfer history, public registration attempts (`is_throttled()`), and runtime JSON policy rules (`Rule.evaluate()`).
  * **Checkpoint, Staff Actor & Audit Classes (`ScanEvent`, `Gate`, `User`, `ReadAuditLog`, `Notification`):** Represent physical campus gates (`allows()`, `is_open_at()`), authenticated staff actors (`User` with roles `ADMIN`, `REGISTRAR`, `GUARD`), the append-only gate scan log (`snapshot_identity()`), staff read-audit records (`record_access()`), and the transactional notification outbox (`dispatch()`).

* **Relationships & Flow Represented:**
  * **Aggregation (`◇───▶` Hollow Diamond):** `Department (1)` aggregates `Student (0..*)` (`1 has 0..*`) and institutional `Device (0..*)` records (`0..1 owns 0..*`), which can exist independently if reassigned across departments.
  * **Composition (`◆───▶` Filled Diamond):** `Device (1)` strongly owns `DeviceFlag (0..*)` (`1 carries 0..*`), `TemporaryPermit (0..*)` (`1 authorised by 0..*`), and `OwnershipTransfer (0..*)` (`1 logs history 0..*`); these child records are bound to the lifecycle of their parent `Device`.
  * **Directed Associations (`───▶` Open Arrow):** `Student (0..1)` owns `Device (0..*)`, initiates `RegistrationAttempt (0..*)` (`0..1 attempted by 0..*`), and participates in `OwnershipTransfer (0..*)` (`1 from / to 0..*`). `Device (0..1)`, `TemporaryPermit (0..1)`, `Gate (1)`, and `User (1)` all reference `ScanEvent (0..*)`. `User (1)` triggers `ReadAuditLog (0..*)`.
  * **Dependencies (`- - -▷` Dashed Open Arrow):** `Device` depends on `EquipmentType` (`«classified by code»`) and `Rule` (`«evaluates policy»`). Both `ScanEvent` and `DeviceFlag` depend on `Notification` (`«enqueues alert»`) to trigger automated SMS and email alerts.

* **Activities, Inputs, and Outputs:**
  * **Activities:** Normalizing registration and serial lookup keys, evaluating device hold flags and temporary permits, recording ownership transfers, logging gate scan verdicts, and auditing staff read operations.
  * **Inputs:** Student registration numbers, national IDs, E.164 phone numbers, device serial numbers, equipment types, hold reasons, and guard scan decisions (`direction`, `verdict`, `override_reason`, `client_reference` UUID).
  * **Outputs:** Evaluated clearance verdicts (`Student.is_clear_to_pass()`, `Device.blocking_reasons()`), immutable `ScanEvent` records with snapshotted `device_label` and `student_name`, `ReadAuditLog` entries, and queued `Notification` outbox rows.

---

## B.2 UML Component Diagram (Structural Diagram 2)

> **[Insert exported image of `research/diagrams/component-diagram.drawio` here]**
> *Figure B.2: Computer Track — UML 2.5 Component Diagram (Four-Tier Subsystem Architecture)*

* **Description of the Diagram:**
  The UML Component Diagram represents the modular software architecture of Computer Track across four (4) `«subsystem»` tiers: **Presentation Tier (React 19 PWA)**, **Application Tier (Django 5 REST API)**, **Persistence & Background Tasks**, and **Notification & Cloud Gateways**.

* **Major Components & Actors:**
  * **Presentation Tier (React 19 PWA):** Contains five client components (`Security Gate Console`, `Offline Queue & Worker`, `Registration Office Portal`, `Administration Dashboard`, and `Public Self-Service Form`) accessed by Security Guards, Registration Officers, Administrators, and Students via explicit boundary Ports (`□`).
  * **Application Tier (Django 5 REST API):** Contains the `API Gateway & Auth` entry module and five internal services (`Checkpoint & Search Service`, `Device Management Service`, `Student Registry Service`, `Policy & Rule Store`, and `Read-Audit & Security`).
  * **Persistence & Background Tasks Tier:** Contains `PostgreSQL Database` (`«database»`), `Redis Cache & Broker` (`«database»`), `Celery Worker & Beat`, and `Secure Media Storage`.
  * **Notification & Cloud Gateways Tier:** Contains the `Transactional Outbox`, `Africa's Talking SMS API`, and `Resend Email API`.

* **Relationships & Flow Represented:**
  * **Synchronous Invocations (`────▶` Solid Arrow):** Client portals invoke `API Gateway & Auth` through boundary ports (`p1`–`p4`) over `«HTTPS/JWT»`, `«HTTPS/2FA»`, and `«HTTPS Public»`. The gateway delegates validated requests (`«delegate»`) to `Checkpoint & Search Service` (`/checkpoint/*`), `Device Management Service` (`/devices/*`), and `Student Registry Service` (`/students/*`), which execute `«SQL»` queries against `PostgreSQL Database`. `PostgreSQL Database` commits atomic outbox rows (`«SQL»`) to `Transactional Outbox`, which dispatches alerts over `«HTTPS»` to `Africa's Talking SMS API` and `Resend Email API`.
  * **Dependencies & Asynchronous Flows (`- - -▷` Dashed Open Arrow):** `Security Gate Console` depends on `Offline Queue & Worker` (`«use» Cache & Queue`), which bulk-syncs offline scans (`«sync» POST /scans/bulk/`) to `Checkpoint & Search Service` on reconnect. Internal services call each other via `«use»` (`blocking_reasons()`, `is_clear_to_pass()`, `Gate Policy Rules`), log reads via `«log»` to `Read-Audit & Security`, cache rules in Redis (`«RESP»`), sign expiring photo URLs (`«HMAC»`), and drain outbox notifications asynchronously via `Celery Worker & Beat` (`«Broker»`, `«async» Drain Pending`).

* **Activities, Inputs, and Outputs:**
  * **Activities:** Authenticating JWT/2FA requests, looking up serials and QR codes in sub-second time, queueing and bulk-replaying offline gate scans, enforcing registrar approval workflows, and draining outbound SMS/email notifications.
  * **Inputs:** HTTPS JSON requests, JWT Bearer and TOTP 2FA tokens, QR/serial lookup queries, offline scan batches with UUID idempotency keys, CSV student rolls, and uploaded portrait/device photos.
  * **Outputs:** Sub-second JSON lookup verdicts (`CLEAR` or `HOLD`), HMAC-signed portrait URLs, ACID database commits, `ReadAuditLog` records, and outbound E.164 SMS and transactional email notifications.

---

## B.3 UML Use Case Diagram (Behavioral Diagram 1)

> **[Insert exported image of `research/diagrams/use-case.drawio` here]**
> *Figure B.3: Computer Track — UML 2.5 Use Case Diagram (System Scope & Actor Interactions)*

* **Description of the Diagram:**
  The UML Use Case Diagram defines the functional scope of the `«system» Computer Track — Campus Equipment Registry & Gate Verification Platform` boundary across twenty-four (24) use cases and six (6) actors, organized into five functional subsystems: *Public Self-Service Portal (No Login)*, *Gate Verification Console*, *Automated System Actions*, *Registration Office Portal*, and *System Configuration & Oversight*.

* **Actors:**
  * **Student (No Account):** Primary human actor who uses the public portal without login credentials to register a device, report a device lost or stolen, and check registered devices.
  * **Security Guard:** Primary human actor at campus gates who looks up devices, scans QR stickers, views owner photographs and device status, records gate decisions, overrides holds with a written reason, and queues decisions offline.
  * **Registration Officer:** Primary human actor who reviews pending registrations, approves/rejects registrations with physical evidence, places/resolves holds, issues temporary gate passes, manages students/CSV imports, reviews registration attempts, and configures rules/templates.
  * **Administrator:** Primary human actor who manages staff accounts, views the audit log and dashboard, and—via a formal UML **Actor Generalization (`───▷` hollow triangle)** labeled `inherits role`—inherits all **Registration Officer** (and Security Guard) use cases.
  * **Email Service (Resend) & SMS Gateway (Pindo):** Secondary `«external system»` actors that receive and deliver outbound email and SMS notifications.

* **Relationships & Flow Represented:**
  * **Actor Associations (`────────` Solid Line):** Connect each primary human actor on the left/right and secondary external system at the bottom to the use cases they initiate or receive output from.
  * **Actor Generalization (`───────▷` Hollow Triangle):** Connects `Administrator` to `Registration Officer` (`inherits role`), eliminating redundant association lines across shared registrar capabilities.
  * **Mandatory Inclusions (`- - «include» - -▷`):** `Register a device`, `Report a device lost or stolen`, and `Check my devices` all `«include»` `Verify identity against records on file`. `Report a device lost or stolen` also `«include»`s `Block the device at every gate`. `Look up a device` `«include»`s `View owner photograph and device status`. `Record the gate decision` `«include»`s `Write to the append-only scan log`. `Approve or reject a registration` `«include»`s both `Record approval evidence` and `Send a notification`.
  * **Conditional Extensions (`- - «extend» - -▷`):** `Scan a QR sticker` `«extend»`s `Look up a device`. `Override a hold with a written reason`, `Queue a decision offline and sync later`, and `Send a notification (on permitted OUT)` all conditionally `«extend»` `Record the gate decision` (arrow pointing from the extending use case to the base use case).

* **Activities, Inputs, and Outputs:**
  * **Activities:** Zero-login identity verification against student records on file, emergency lost/stolen reporting, QR/serial checkpoint verification, physical inspection and registration approval, and audit log monitoring.
  * **Inputs:** Student identity proofs (registration number + national ID/phone) and device details, QR/serial scans, guard verdicts and mandatory written override reasons, registrar approval evidence, and administrator rule/staff updates.
  * **Outputs:** Verified `PENDING` or `ACTIVE` device records, immediate campus-wide gate blocks on lost/stolen reports, immutable `ScanEvent` audit logs, and automated SMS/email notifications.

---

## B.4 UML Activity Diagram (Behavioral Diagram 2)

> **[Insert exported image of `research/diagrams/activity-diagram.drawio` here]**
> *Figure B.4: Computer Track — UML 2.5 Activity Diagram (Checkpoint Gate Verification Workflow)*

* **Description of the Diagram:**
  The UML Activity Diagram models the end-to-end dynamic operational workflow of a checkpoint gate inspection partitioned across four (4) vertical **Swimlanes**: **Security Guard**, **Gate Console (Client App)**, **Backend API & Registry**, and **Audit Log & Sync**. It uses all eleven (11) standard UML Activity Diagram notations: **Initial State**, **Swimlane**, **Activity State**, **Control Flow**, **Decision Node**, **Guard**, **Merge Node**, **Time Event**, **Fork Bar**, **Join Bar**, and **Final State**.

* **Actors & Swimlanes:**
  * **Security Guard (Swimlane 1):** Primary checkpoint actor who scans the equipment QR/serial, visually compares the bearer against the owner portrait, and decides whether to allow, deny, or override a hold.
  * **Gate Console — Client App (Swimlane 2):** React 19 PWA client that checks network connectivity, reads offline `sessionStorage` cache or calls the lookup API, prompts for mandatory override reasons, queues offline scans locally, and flushes queued scans when the `Reconnect Timer` fires.
  * **Backend API & Registry (Swimlane 3):** Django REST service that queries device and student registry status and returns either `CLEAR` or `HOLD` with the owner's photo.
  * **Audit Log & Sync (Swimlane 4):** Backend persistence and notification subsystem that forks post-scan processing into parallel append-only `ScanEvent` logging and conditional departure SMS alerting.

* **Activities, Relationships & Control Flow Represented:**
  1. **Lookup Initiation (`Initial State` -> `Decision Node` + `Guards`):** The workflow begins at the **Initial State** (`○`) in the `Security Guard` swimlane with the **Activity State** `Scan QR code or type serial / reg number`. A **Control Flow** (`───▶`) crosses into `Gate Console (Client App)` to a **Decision Node** (`◇`): under Guard `[Offline]`, it executes `Read sessionStorage cache or manual permit check`; under Guard `[Online]`, it executes `Call verification API (GET /checkpoint/lookup/)`.
  2. **Registry Evaluation & Lookup Merge (`Decision Node` -> `Merge Node`):** In `Backend API & Registry`, `Look up device & student in registry status` feeds a **Decision Node** (`◇`): Guard `[Clear]` executes `Return CLEAR + owner photo`, while Guard `[Hold / Unreg]` executes `Return HOLD + reason + owner photo`. Both online branches and the offline cache branch converge at a **Merge Node** (`◇`) before executing `Display owner photo + CLEAR / HOLD verdict`.
  3. **Visual Bearer Inspection & Verdict Merge (`Decision Nodes` -> `Merge Node`):** Control returns to `Security Guard` for `Visually check bearer against owner photo` and a **Decision Node** (`◇`): Guard `[Match & Clear]` leads to `Verdict: ALLOWED`. Guard `[Hold / Mismatch]` leads to a second **Decision Node** (`◇`): Guard `[Deny]` leads to `Verdict: DENIED`, whereas Guard `[Override]` transitions to `Prompt mandatory written override reason` and `Verdict: OVERRIDE`. All three verdicts converge at the Verdict **Merge Node** (`◇`).
  4. **Offline Queueing & Time Event (`Decision Node` -> `Time Event` Hourglass):** A **Decision Node** (`◇`) checks connectivity: Guard `[Online]` transitions directly to `Submit scan to API (POST /checkpoint/scans/)`. Guard `[Offline]` transitions to `Queue scan locally (UUID idempotency)`, which waits on the **Time Event** hourglass (`Reconnect Timer`) until `[Reconnected]` triggers `Submit scan to API (POST /checkpoint/scans/)`.
  5. **Concurrent Audit Logging & Notification (`Fork Bar` -> `Join Bar` -> `Final State`):** Submitting the scan enters a horizontal **Fork Bar** (`━━━`) in `Audit Log & Sync`, splitting control into two concurrent threads: Thread 1 executes `Commit to append-only ScanEvent log`, while Thread 2 evaluates a **Decision Node** (`◇`) where Guard `[Exit Allowed]` executes `Send departure SMS alert to owner phone` and Guard `[Skip]` bypasses it to a **Merge Node** (`◇`). Both parallel threads synchronize at the horizontal **Join Bar** (`━━━`) before terminating at the bullseye **Final State** (`◉`).

* **Inputs and Outputs:**
  * **Inputs:** Physical QR sticker or typed serial/registration number, bearer's physical appearance, network connectivity state (`[Online]` / `[Offline]`), `Reconnect Timer` event (`[Reconnected]`), guard's visual match decision, and mandatory written override reason.
  * **Outputs:** Visual `CLEAR` or `HOLD` verdict display with owner photo, recorded gate verdict (`ALLOWED`, `DENIED`, or `OVERRIDE`), immutable `ScanEvent` audit log entry, and an outbound departure SMS alert to the owner's phone on permitted exits.
