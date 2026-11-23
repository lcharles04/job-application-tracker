# Job Application Tracker

A full-stack web app for tracking job applications. Built with **MySQL**, **Python/Flask**, and **HTML/CSS** for COP 4751.

## Features

- **Dashboard** with totals, response rate, applications by status, upcoming interviews and recent activity
- **Full CRUD** (create, list, view, edit, delete with confirmation) for all four tables: companies, jobs, applications, contacts
- **Server-side validation** on every form: required fields, max lengths, URL/email/phone formats, salary range, valid dates, enum values, and foreign keys that must exist
- **JSON columns**: `jobs.requirements` (skill list) and `applications.interview_data` (interview rounds), edited through normal form fields
- **Job Match**: enter your skills and see jobs ranked by match percentage, with matched and missing skills
- Search and filter on list pages, cascading deletes with a warning that shows what else will be removed

## Tech Stack

| Layer    | Technology                     |
|----------|--------------------------------|
| Database | MySQL 8.0+                     |
| Backend  | Python 3.10+, Flask 3          |
| Driver   | mysql-connector-python         |
| Frontend | Jinja2 templates, custom CSS   |

## Setup (fresh clone)

### 1. Prerequisites
- Python 3.10 or newer
- MySQL Server 8.0 or newer, running locally

### 2. Clone and install

```bash
git clone <your-repo-url>
cd job_tracker
python -m venv venv
# Windows:   venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the database

```bash
mysql -u root -p < schema.sql
```

This creates the `job_tracker` database, all four tables, and sample data. Running it again resets the database. (You can also open `schema.sql` in MySQL Workbench and execute it.)

### 4. Configure the connection

Copy the example settings file and put your MySQL password in it:

```bash
# Windows:   copy .env.example .env
# Mac/Linux: cp .env.example .env
```

Edit `.env`:

```
DB_USER=root
DB_PASSWORD=your_mysql_password
```

### 5. Run

```bash
python app.py
```

Open **http://127.0.0.1:5000** in a browser.

### 6. (Optional) Run the unit tests

```bash
python -m unittest discover tests
```

## Project Structure

```
job_tracker/
├── app.py              # Flask routes and form validation
├── database.py         # MySQL connection and all SQL queries
├── matching.py         # Job Match algorithm
├── schema.sql          # Database creation script + sample data
├── templates/          # Jinja2 HTML templates
│   ├── base.html           # Shared layout and navigation
│   ├── dashboard.html
│   ├── companies.html      # list
│   ├── company_form.html   # add / edit
│   ├── company_detail.html
│   ├── jobs.html, job_form.html, job_detail.html
│   ├── applications.html, application_form.html, application_detail.html
│   ├── contacts.html, contact_form.html
│   ├── job_match.html
│   ├── confirm_delete.html
│   └── error.html
├── static/
│   └── style.css
├── tests/
│   └── test_matching.py
├── AI_USAGE.md         # GenAI documentation
├── requirements.txt
├── .env.example
└── README.md
```

## Database Design

```
companies 1 ──< jobs 1 ──< applications
    1
    └──< contacts
```

| Table          | Key columns                                                         | Notes |
|----------------|---------------------------------------------------------------------|-------|
| `companies`    | `company_id` PK, `company_name` (unique)                            | |
| `jobs`         | `job_id` PK, `company_id` FK, `job_type` ENUM, `requirements` JSON  | CHECK: `salary_min <= salary_max` |
| `applications` | `application_id` PK, `job_id` FK, `status` ENUM, `interview_data` JSON | |
| `contacts`     | `contact_id` PK, `company_id` FK                                    | |

All foreign keys use `ON DELETE CASCADE`. Deleting a company removes its jobs, contacts, and the applications for those jobs. The confirmation page lists those counts before anything is deleted.

**JSON formats**

```json
// jobs.requirements
["Python", "SQL", "Flask"]

// applications.interview_data
[{"date": "2026-09-30", "round": "Phone Screen", "interviewer": "Maria Lopez", "notes": "Asked about Flask"}]
```

The dashboard uses MySQL's `JSON_LENGTH()` to count interview rounds across all applications.

## Job Match Algorithm

```
match % = (job requirements the user has) / (total job requirements) x 100
```

- Comparison is case-insensitive and ignores extra spaces
- Common aliases are treated as equal (`JS` = `JavaScript`, `Postgres` = `PostgreSQL`)
- Results are sorted by percentage, then by number of matched skills
- Jobs with 0% are hidden unless "Include 0% matches" is checked

Example with skills `Python, SQL, Flask`:

```
1. Software Developer at TechCorp - 100% (3/3 skills)
2. Data Analyst at DataCo - 67% (2/3 skills)   Missing: Tableau
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Database error" page / `Access denied` | Check `DB_USER` and `DB_PASSWORD` in `.env` |
| `Unknown database 'job_tracker'` | Run `mysql -u root -p < schema.sql` |
| `Can't connect to MySQL server` | Start the MySQL service |
| Port 5000 already in use (common on macOS) | Run with `PORT=5001 python app.py` |

## Demo Video

See `demo.mp4` in this repository for a walkthrough of the client, server, and database.
