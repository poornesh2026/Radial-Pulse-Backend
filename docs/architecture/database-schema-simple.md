# Radial Pulse — Database Schema (Simple Version)

Milestone 1 · Person 1 (Backend) · updated 27 Sep 2026 (review fixes: people locked, doctors at several branches, metric numbers, safe search, status check, S3 archive)

The database is where the platform keeps all its information: people, clinics,
reports, tasks. Information is kept in **tables** (like Excel sheets). Each table has
**columns** (the headings) and **rows** (one row = one thing, e.g. one clinic).

---

## 1. The picture

```
                      ┌─────────────┐
                      │   users     │  everyone who can log in
                      └──────┬──────┘
             ┌───────────────┴───────────────┐
             ▼                               ▼
   ┌───────────────────┐           ┌───────────────────┐
   │ clinic_assignments│           │ clinic_memberships│
   │ which DSM looks   │           │ which doctor/owner│
   │ after which clinic│           │ belongs to which  │
   │ (our staff)       │           │ clinic (clients)  │
   └─────────┬─────────┘           └─────────┬─────────┘
             └───────────────┬───────────────┘
                             ▼
   ┌───────────────┐   ┌─────────────┐
   │ organizations │──►│  clinics    │  THE CENTRE of everything
   │ the business  │   │             │
   └───────────────┘   └──────┬──────┘
                              │ every table below belongs to one clinic
      ┌──────────────┬────────┼─────────────┬───────────────┐
      ▼              ▼        ▼             ▼               ▼
  doctors       stage       online       reports        tasks to fix
               diary       links        (score +       problems +
                                        problems)      DSM review
```

---

## 2. People

### `users` — everyone who can log in

| Column | What it means | Example |
|---|---|---|
| id | unique number for this person | (auto) |
| email | their login email | priya@radialpulse.com |
| full_name | their name | Priya Shah |
| phone | their phone | +91 98765 43210 |
| role | what kind of user they are | `platform_administrator` / `digital_success_manager` / `clinic_user` |
| is_active | can they log in? | yes / no |
| last_invited_at | when we last sent them the invite email | 26 Sep, 10:30 |
| last_login_at | when they last logged in | 26 Sep, 11:00 |

**4 kinds of people:**
- **Platform Admin**: our boss user (Rohan). Sees everything.
- **DSM (Digital Success Manager)**: our staff (Priya). Sees only her clinics.
- **Clinic Administrator**: the doctor or owner (Dr. Rahul). Sees only his own clinic.
- **Clinic Team Member**: the clinic's staff (front desk, manager). Sees only their own clinic,
  **view-only**, but can upload photos and files.

The last two are both `clinic_user` in this table; their exact role inside the clinic is in
`clinic_memberships`.

---

## 3. Clinics

### `organizations` — the business that owns clinics

One business can have many branches. Example: "Smile Group" owns 3 clinics.

| Column | What it means | Example |
|---|---|---|
| id | unique number | (auto) |
| name | business name | Smile Group |

### `clinics` — one clinic (the most important table)

| Column | What it means | Example |
|---|---|---|
| id | unique number | (auto) |
| organization_id | which business owns it | Smile Group |
| name | clinic name | Smile Dental Care |
| specialty | what they do | General Dentistry, Implants |
| description | short intro | "Modern dental care…" |
| email, phone | contact | info@smiledental.in |
| website_url | their website | smiledentalcare.in |
| address, city, state, pin code | where it is | Kakinada, Andhra Pradesh |
| latitude, longitude | the map pin | 16.98, 82.24 |
| cover_photo | the clinic photo | (a file) |
| **stage** | how far we have got with this clinic | see below |
| stage_changed_at | when the stage last changed | 25 Sep |
| is_active | yes = normal, no = **archived** (clinic said no) | yes |
| archived_reason | why it was archived | "Already has an agency" |

**The 5 stages:**

```
1. New lead → 2. Found online → 3. Report ready → 4. In talks → 5. Customer
```

| Stage | Meaning |
|---|---|
| New lead | clinic is on our list, nothing done yet |
| Found online | we found its website, Google listing, Instagram… |
| Report ready | its digital presence report (score) is done |
| In talks | DSM is meeting the doctor about the report and the deal |
| Customer | doctor said yes and has an app login |

If the clinic says **no** at any step → it is **archived** with a reason (not deleted).

### `clinic_stage_history` — diary of stage changes

Every time a clinic moves stage, one line is added here. Lines can never be edited or deleted.

| Column | What it means | Example |
|---|---|---|
| clinic_id | which clinic | Smile Dental Care |
| from_stage → to_stage | the move | Report ready → In talks |
| note | optional note | "Met Dr. Rahul at clinic" |
| changed_by | who moved it | Priya |
| changed_at | when | 25 Sep, 4 pm |

### `practitioners` — the doctor (one row per doctor)

A doctor is **just a record**, not a login (unless we give them one).
A doctor belongs to the **business**, so one doctor who works at 3 branches is still **one row**.

| Column | What it means | Example |
|---|---|---|
| organization_id | which business | Smile Group |
| full_name | doctor's name | Dr. Rahul Mehta |
| specialty | what they treat | Dentistry |
| qualifications | degrees | BDS, MDS |
| registration_number | medical council number | APDC/1234 |
| bio | short intro | "15 years experience…" |

### `clinic_practitioners` — which doctor works at which branch (NEW)

| Column | What it means | Example |
|---|---|---|
| clinic_id | the branch | Smile Dental – Banjara Hills |
| practitioner_id | the doctor | Dr. Rahul Mehta |
| is_main | the main doctor shown in lists (only one per branch) | yes |
| is_active | still working at this branch? | yes |

Example: Dr. Rahul works at Banjara Hills (main doctor) and Jubilee Hills (not main) =
1 row in `practitioners` + 2 rows here. A doctor can only be linked to branches of **his own business**.

---

## 4. Who looks after what

### `clinic_assignments` — which DSM looks after which clinic

| Column | What it means | Example |
|---|---|---|
| clinic_id | the clinic | Smile Dental Care |
| user_id | the DSM | Priya |
| is_active | yes = looks after it **now**, no = looked after it before | yes |
| assigned_by | who gave it | Rohan (Admin) |

**Rule:** a clinic has **only one DSM at a time**. When the Admin changes the DSM, the old
line is marked "no" and kept as history.

### `clinic_memberships` — which clinic people belong to which clinic

| Column | What it means | Example |
|---|---|---|
| clinic_id | the clinic | Smile Dental Care |
| user_id | the person | Dr. Rahul |
| role | their role in the clinic | Clinic Administrator (full) or Clinic Team Member (staff, view-only) |
| is_active | still has access? | yes |
| invited_by | who added them | Priya |

An owner with 3 branches has 3 lines, one per branch.

---

## 5. Online presence and reports

### `presence_profiles` — where the clinic is found online

| Column | What it means | Example |
|---|---|---|
| clinic_id | the clinic | Smile Dental Care |
| platform | which site | website / google / instagram / facebook / youtube / linkedin / practo / justdial |
| url | the link | instagram.com/smiledental |
| verification | is it really theirs? | not checked / confirmed / rejected |
| found_by | a person or the system | system |

### `metric_snapshots` — numbers from those sites

Followers, likes, reviews, views… saved with the date, so we can draw growth charts.
Example: `instagram.followers = 5,432` on 26 Sep.

| Column | What it means | Example |
|---|---|---|
| metric_key | which number | instagram.followers |
| value | the full data as it came in (JSON) | `{"value": 5432}` |
| value_number | **NEW** — just the number, so charts and sums are easy | 5432 |
| fetched_at | when we got it | 26 Sep |

Numbers older than **6 months** are moved to the S3 archive once a month (see the rules below).

### `assessments` — the Digital Presence Report

One row = one report for one clinic. Running it again ("Re-run") makes a new row.

| Column | What it means | Example |
|---|---|---|
| clinic_id | the clinic | Smile Dental Care |
| number | 1st, 2nd, 3rd report | 2 |
| status | is it done? | waiting / running / done / partly done / failed |
| overall_score | the big score | 78 / 100 |
| approval | has the DSM checked it? | draft / sent for review / approved / rejected |
| published | can the clinic see it? | not published / **published** |
| published_at | when it was shown to the clinic | 26 Sep |

**Important rule:** the doctor sees a report **only after the DSM publishes it**.

### `assessment_components` — the 6 parts of every report

Website · Google Business Profile · Local Search · Search Readiness (SEO/AEO/GEO) ·
Social Media · Competitors. Each part has its own score, or "not available yet".
We never make up a score.

### `assessment_findings` — the problems found

| Column | What it means | Example |
|---|---|---|
| code | fixed name of the problem | gbp.description_weak |
| title | the problem | GBP description needs improvement |
| priority | how serious | critical / high / medium / low |
| recommendation | how to fix it | "Add services and keywords" |
| evidence | proof: link + short text + date | google.com/maps/… |

Serious problems (critical, high) **must** have proof.

---

## 6. Work and review

### `work_items` — tasks to fix problems ("Fix Now")

| Column | What it means | Example |
|---|---|---|
| clinic_id | the clinic | Smile Dental Care |
| title | the task | Update GBP description |
| area | which part it improves | website / google / local search / seo / social / competitors / profile / other |
| finding_code | which problem it fixes | gbp.description_weak |
| status | progress | to do / in progress / blocked / in review / **done** / cancelled |
| priority | how urgent | low / normal / high / urgent |
| owner | who is doing it | Priya |
| due_at | deadline | 30 Sep |
| completed_at | when it was finished | 29 Sep |

**Why the status is here and not on the problem:** when the report is run again, the
problems are made again, but the **task and its progress stay**. Only one open task per
problem.

### `approvals` — review records

Keeps track of who sent something for review, who approved it, and whether it was published.

The report also keeps a **copy** of this status (so lists load fast). The database now checks,
every time something is saved, that the copy and this table say **the same thing**. If some code
tries to publish a report without going through approvals, the save is refused.

### `notifications` — in-app messages

Example: "A new clinic was assigned to you."

---

## 7. Files and background work

| Table | What it stores |
|---|---|
| `assets` | info about uploaded files (photos, logos, PDFs). The file itself is in AWS S3 |
| `report_artifacts` | downloadable report files (e.g. the PDF of a report) |
| `background_jobs` | slow jobs running in the background (e.g. making a report) |
| `clinic_profiles` | clinic brand, services, timings |
| `consent_records` | what the clinic allowed us to do (e.g. check their website) |

---

## 8. The log

### `audit_events` — record of every action

| Column | What it means | Example |
|---|---|---|
| when | time | 26 Sep, 11:05 |
| who | person or system | Priya |
| action | what happened | clinic.stage_change |
| clinic | which clinic | Smile Dental Care |

Nobody can edit or delete this log. Only exception: once a month, entries older than
**1 year** are **copied to S3 first**, then removed from the database (so the database stays fast).
Nothing is lost — the archive can still be searched.

---

## 9. The rules (in plain words)

1. **Each clinic's data is locked.** A doctor or DSM can only see their own clinics. The
   database itself blocks the rest, even if our code has a mistake. This now covers
   **every table**, including people (`users`, team lists, DSM lists, notifications):
   a Clinic Administrator sees only the people of his own clinic, and only his own notifications.
2. **Nothing is deleted.** People and clinics are switched off, not removed.
3. **One DSM per clinic** at a time.
4. **One main doctor per clinic.** A doctor can work at several branches of the same business.
5. **Archiving needs a reason.**
6. **A clinic becomes "Customer" only after the doctor has a login.**
7. **Doctors see only published reports.**
8. **Every action is logged**, and the log cannot be changed.
9. **Old data goes to the archive (S3)** every month: numbers after 6 months, the log after 1 year.
10. **Search is fast and safe.** Typing `100%` finds "100% Smile", not every clinic starting with 100.

---

## 10. Count

**22 tables**: 20 were already built, 2 are new (`clinic_stage_history`, `clinic_practitioners`).
