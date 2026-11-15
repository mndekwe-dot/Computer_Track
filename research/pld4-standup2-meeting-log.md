# PLD 4 Stand-Up 2 Meeting Log

**Date:** Sunday, 15 November 2026
**Time:** 6:00pm to 7:00pm (CAT)
**Platform:** Google Meet (online)
**Chaired by:** NDEKWE Dieu Merci
**Minutes by:** Ishimwe Axcel

## Attendance

| Member | Project | Attendance |
| --- | --- | --- |
| Ishimwe Axcel | Gaia | Present |
| INEZA Henry Jayz | Skill Gap Analyzer | Present |
| NDEKWE Dieu Merci | etracker (formerly Computer Track) | Present |
| Alvin Mutangana | PanaLink | Present |
| Bol Dau | Metlink | Present |

All five members attended.

## Agenda

1. Confirm attendance and the purpose of the stand-up
2. Each member reports progress against the goals set at stand-up 1
3. Identify shared resource needs, dependencies and roadblocks
4. Agree action items and the next meeting date

## Individual reports

**Gaia, Ishimwe Axcel.** All four phases are done and on GitHub. Phase 4 gives district admins a
report of referral numbers, declines and their reasons, and facilities that keep running out of
resources. Admins can manage staff accounts, the 29 real Gasabo district facilities are loaded,
and the interface was redesigned. Automated tests went from 84 to 183. Kinyarwanda translation was
taken out of this release because medical terms must not be mistranslated.

**Skill Gap Analyzer, INEZA Henry Jayz.** Moved from design to a working MVP on GitHub: Flask and
SQLite backend, profile form, a gap engine that ranks missing skills by market demand, a roadmap
with free and paid resource tags, and a readiness score. The seed data is still small.

**etracker, NDEKWE Dieu Merci.** The project formerly called Computer Track was renamed etracker, with a new logo. The interface was redesigned around the campus gate, all 16
staff pages were reviewed and fixed, one staff sign-in page replaced the three portal logins, and
the UML class and activity diagrams were updated. The security items planned at stand-up 1
(evidence at approval, one-time verification codes, masked serial numbers) were moved to the next
sprint so the interface could be finished first.

**PanaLink, Alvin Mutangana.** Sprint 1 is built: accounts with buyer, seller and admin roles,
listings with compressed photos, search by category and district, seller ID verification, and a
Kinyarwanda, English and French interface. Mobile money remains the main risk for Sprint 3.

**Metlink, Bol Dau.** The ERD brought forward from stand-up 1 became a 10-table PostgreSQL
database. The Flask admin API passes 15 of 15 checks, and the admin dashboard and public landing
page are complete. A WSL environment failure and seed login bugs were resolved. USSD and SMS
integration remain.

## Shared issues

- **Resource needs:** pilot users for every project, a Kinyarwanda reviewer for medical terms, and
  Africa's Talking sandbox access.
- **Dependencies:** MTN MoMo and Airtel Money (PanaLink), Africa's Talking (Metlink and
  etracker), Gasabo facility data (Gaia), partly estimated demand data (Skill Gap Analyzer).
- **Roadblocks:** no project has been tested by its real users, most are not deployed, and
  Kinyarwanda translation affects Gaia, Metlink and PanaLink.

## Action items

| Action | Owner | Deadline |
| --- | --- | --- |
| Run the end-to-end tests, push and merge the redesign, start the stand-up 1 security items, ask the learning coaches about pilot access | NDEKWE Dieu Merci | 22 Nov 2026 |
| Styled templates and landing page | INEZA Henry Jayz | 22 Nov 2026 |
| Sprint 2 listing detail and messaging, deploy for phone testing | Alvin Mutangana | 22 Nov 2026 |
| Find a Kinyarwanda reviewer, add the admin activity log page | Ishimwe Axcel | 22 Nov 2026 |
| Recommendation engine, connect the Africa's Talking sandbox | Bol Dau | 22 Nov 2026 |
| Proofread, share with ALU and submit the summary | NDEKWE Dieu Merci | 15 Nov 2026 |

## Next meeting

Sunday, 22 November 2026, 6:00pm (CAT), on Google Meet.
