# PLD 4 Stand-Up Meeting Log

**Date:** Sunday, 08 November 2026
**Time:** 6:00pm to 7:05pm (CAT)
**Platform:** Google Meet (online)
**Chaired by:** NDEKWE Dieu Merci
**Minutes by:** Ishimwe Axcel

## Attendance

| Member | Project | Attendance |
| --- | --- | --- |
| Ishimwe Axcel | Gaia | Present |
| INEZA Henry Jayz | Skill Gap Analyzer | Present |
| NDEKWE Dieu Merci | Computer Track | Present |
| Alvin Mutangana | PanaLink | Present |
| Bol Dau | Metlink | Present |

All five members attended. No absences and no apologies.

## Agenda

1. Confirm attendance and the purpose of the stand-up
2. Each member reports status, achievements, challenges and next steps
3. Identify blockers that are shared across projects
4. Allocate the remaining tasks for the summary document
5. Agree the next meeting date

## Discussion

### 1. Opening (6:00pm to 6:05pm)

The coordinator confirmed that all five members were present and restated the purpose of the
session: each member reports on their own project, and the group records the outcome in one
summary document with an accompanying participation tracker.

### 2. Individual reports (6:05pm to 6:45pm, roughly eight minutes each)

**Gaia, Ishimwe Axcel.** Reported three of four phases complete and on GitHub, with 84 automated
tests passing and a code review at each phase. Raised the difficulty of testing real-time features,
which need two users online at once, and reported a concurrency bug where two users acting on the
same referral could both succeed. The group noted that this is the kind of defect worth writing up,
because catching it before a pilot is a stronger result than never meeting it.

**Skill Gap Analyzer, INEZA Henry Jayz.** Reported the planning and design phase complete:
proposal, SRS v1.0 with FR 1 to FR 5 and NFR 1 to NFR 7, four UML diagrams, and a four-sprint plan.
Main blocker is the seed dataset mapping degrees to in-demand skills, which has to be compiled by
hand because no free API exists. The group suggested starting with a small number of degree
programmes rather than attempting full coverage.

**Computer Track, NDEKWE Dieu Merci.** Reported planning and design complete and the core system
built: three staff portals and a public registration form, a gate console that works offline and
syncs on reconnection, and 407 automated tests passing. Stated plainly that no system can prove
legal ownership of a laptop, and that identity on the public form rests on data that is semi-public
inside a university. The group accepted that layered evidence recorded at approval is a reasonable
response to a limitation that cannot be fully removed.

**PanaLink, Alvin Mutangana.** Reported design complete and build starting. Scope was narrowed from
cross-border East Africa to Rwanda only, which the group agreed was the right call for a
deliverable project. Dependencies on MTN MoMo and Airtel Money are outside his control, and the
hypothesis needs real rural sellers to test.

**Metlink, Bol Dau.** Reported the Scrum process, sprint plan, product backlog, Trello board and
GitHub repository all in place, with the ERD and database schema design underway. Reported no major
challenges so far. The group asked him to bring the ERD to the next meeting for review before
implementation begins.

### 3. Shared blockers (6:45pm to 6:55pm)

The group identified one blocker common to four of the five projects: the central hypothesis of
each project cannot be tested without real users. Gaia needs two facilities online simultaneously,
Skill Gap Analyzer needs graduates following a roadmap, Computer Track needs students registering
devices, and PanaLink needs rural sellers listing goods. The group agreed to treat pilot access as
a shared request for facilitator support rather than five separate problems.

A second shared theme was scope discipline. Three members had already cut scope deliberately:
PanaLink from regional to national, Skill Gap Analyzer by holding employer routing as a stretch
goal, and Computer Track by keeping policy values in configuration rather than building an admin
interface for them.

### 4. Task allocation (6:55pm to 7:00pm)

Tasks were allocated and recorded in the participation tracker. Each member writes their own
project entry; Alvin Mutangana performs the peer review pass against the template; Ishimwe Axcel
drafts the General Updates section from these minutes; Bol Dau proofreads, formats and submits.

### 5. Close (7:00pm to 7:05pm)

Next meeting date agreed. Meeting closed by the chair.

## Decisions taken

1. Each member writes their own entry in the shared summary document, due 08 November 2026.
2. One peer review pass is run over all five entries before submission, assigned to Alvin Mutangana.
3. The shared pilot-access problem is raised as a single group request for facilitator support, not
   as five individual blockers.
4. Bol Dau brings the Metlink ERD to the next meeting for group review before database
   implementation starts.
5. Bol Dau holds final responsibility for formatting and submitting the summary.

## Action items

| Action | Owner | Deadline |
| --- | --- | --- |
| Complete own project entry in the summary document | All members | 08 Nov 2026 |
| Peer review all five entries against the template | Alvin Mutangana | 08 Nov 2026 |
| Draft the General Updates section from these minutes | Ishimwe Axcel | 09 Nov 2026 |
| Proofread, format and submit the summary | Bol Dau | 09 Nov 2026 |
| Bring the Metlink ERD for group review | Bol Dau | Next meeting |

## Next meeting

Sunday, 22 November 2026, 6:00pm (CAT), on Google Meet.
