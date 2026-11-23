"""
database.py - MySQL connection and data-access functions.

Every SQL statement in the app lives in this file. app.py calls these
functions and never builds SQL itself. All queries use parameterized
placeholders (%s) so user input is never pasted into SQL strings.
"""

import json
import os

import mysql.connector
from mysql.connector import errorcode

try:
    # Optional: load DB settings from a .env file if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "job_tracker"),
}

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]


# -----------------------------------------------------------------
# Connection helpers
# -----------------------------------------------------------------
def get_db():
    """Open a new connection to the job_tracker database."""
    return mysql.connector.connect(**DB_CONFIG)


def query_all(sql, params=()):
    """Run a SELECT and return every row as a dict."""
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql, params=()):
    """Run a SELECT and return the first row as a dict, or None."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE, commit, and return the new row id."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def parse_json(value, default=None):
    """
    JSON columns come back from the driver as str or bytes depending on
    the MySQL/MariaDB version. Normalize to a Python object.
    """
    if default is None:
        default = []
    if value is None or value == "":
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def is_duplicate_error(err):
    return getattr(err, "errno", None) == errorcode.ER_DUP_ENTRY


# -----------------------------------------------------------------
# Companies
# -----------------------------------------------------------------
def get_companies(search=""):
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id)     AS job_count,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.company_id) AS contact_count
        FROM companies c
    """
    params = ()
    if search:
        sql += " WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s"
        like = f"%{search}%"
        params = (like, like, like)
    sql += " ORDER BY c.company_name"
    return query_all(sql, params)


def get_company(company_id):
    return query_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))


def get_company_choices():
    """Lightweight list for <select> dropdowns."""
    return query_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


def create_company(data):
    return execute(
        """INSERT INTO companies (company_name, industry, website, city, state, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"]),
    )


def update_company(company_id, data):
    execute(
        """UPDATE companies
           SET company_name = %s, industry = %s, website = %s,
               city = %s, state = %s, notes = %s
           WHERE company_id = %s""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"], company_id),
    )


def delete_company(company_id):
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


def get_company_delete_impact(company_id):
    """Counts of child rows that ON DELETE CASCADE will remove."""
    return query_one(
        """SELECT
             (SELECT COUNT(*) FROM jobs WHERE company_id = %s) AS jobs,
             (SELECT COUNT(*) FROM contacts WHERE company_id = %s) AS contacts,
             (SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id = j.job_id
               WHERE j.company_id = %s) AS applications""",
        (company_id, company_id, company_id),
    )


# -----------------------------------------------------------------
# Jobs
# -----------------------------------------------------------------
def _decode_job(row):
    if row is not None:
        row["requirements"] = parse_json(row.get("requirements"))
    return row


def get_jobs(search="", job_type="", company_id=None):
    sql = """
        SELECT j.*, c.company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE 1 = 1
    """
    params = []
    if search:
        sql += " AND (j.job_title LIKE %s OR c.company_name LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    if job_type:
        sql += " AND j.job_type = %s"
        params.append(job_type)
    if company_id:
        sql += " AND j.company_id = %s"
        params.append(company_id)
    sql += " ORDER BY j.date_posted DESC, j.job_id DESC"
    return [_decode_job(r) for r in query_all(sql, tuple(params))]


def get_job(job_id):
    row = query_one(
        """SELECT j.*, c.company_name
           FROM jobs j JOIN companies c ON j.company_id = c.company_id
           WHERE j.job_id = %s""",
        (job_id,),
    )
    return _decode_job(row)


def get_job_choices():
    return query_all(
        """SELECT j.job_id, j.job_title, c.company_name
           FROM jobs j JOIN companies c ON j.company_id = c.company_id
           ORDER BY c.company_name, j.job_title"""
    )


def create_job(data):
    return execute(
        """INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                             job_url, date_posted, requirements)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
         data["salary_max"], data["job_url"], data["date_posted"],
         json.dumps(data["requirements"])),
    )


def update_job(job_id, data):
    execute(
        """UPDATE jobs
           SET company_id = %s, job_title = %s, job_type = %s, salary_min = %s,
               salary_max = %s, job_url = %s, date_posted = %s, requirements = %s
           WHERE job_id = %s""",
        (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
         data["salary_max"], data["job_url"], data["date_posted"],
         json.dumps(data["requirements"]), job_id),
    )


def delete_job(job_id):
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))


def get_job_delete_impact(job_id):
    return query_one(
        "SELECT COUNT(*) AS applications FROM applications WHERE job_id = %s", (job_id,)
    )


# -----------------------------------------------------------------
# Applications
# -----------------------------------------------------------------
def _decode_application(row):
    if row is not None:
        row["interview_data"] = parse_json(row.get("interview_data"))
        row["cover_letter_sent"] = bool(row.get("cover_letter_sent"))
    return row


def get_applications(status="", search=""):
    sql = """
        SELECT a.*, j.job_title, c.company_name, c.company_id
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        WHERE 1 = 1
    """
    params = []
    if status:
        sql += " AND a.status = %s"
        params.append(status)
    if search:
        sql += " AND (j.job_title LIKE %s OR c.company_name LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    return [_decode_application(r) for r in query_all(sql, tuple(params))]


def get_application(application_id):
    row = query_one(
        """SELECT a.*, j.job_title, c.company_name, c.company_id
           FROM applications a
           JOIN jobs j ON a.job_id = j.job_id
           JOIN companies c ON j.company_id = c.company_id
           WHERE a.application_id = %s""",
        (application_id,),
    )
    return _decode_application(row)


def get_applications_for_job(job_id):
    return [_decode_application(r) for r in query_all(
        "SELECT * FROM applications WHERE job_id = %s ORDER BY application_date DESC",
        (job_id,),
    )]


def create_application(data):
    return execute(
        """INSERT INTO applications (job_id, application_date, status, resume_version,
                                     cover_letter_sent, interview_data)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["job_id"], data["application_date"], data["status"],
         data["resume_version"], data["cover_letter_sent"],
         json.dumps(data["interview_data"])),
    )


def update_application(application_id, data):
    execute(
        """UPDATE applications
           SET job_id = %s, application_date = %s, status = %s, resume_version = %s,
               cover_letter_sent = %s, interview_data = %s
           WHERE application_id = %s""",
        (data["job_id"], data["application_date"], data["status"],
         data["resume_version"], data["cover_letter_sent"],
         json.dumps(data["interview_data"]), application_id),
    )


def delete_application(application_id):
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))


# -----------------------------------------------------------------
# Contacts
# -----------------------------------------------------------------
def get_contacts(search="", company_id=None):
    sql = """
        SELECT k.*, c.company_name
        FROM contacts k JOIN companies c ON k.company_id = c.company_id
        WHERE 1 = 1
    """
    params = []
    if search:
        sql += " AND (k.contact_name LIKE %s OR k.title LIKE %s OR c.company_name LIKE %s)"
        params += [f"%{search}%"] * 3
    if company_id:
        sql += " AND k.company_id = %s"
        params.append(company_id)
    sql += " ORDER BY k.contact_name"
    return query_all(sql, tuple(params))


def get_contact(contact_id):
    return query_one(
        """SELECT k.*, c.company_name
           FROM contacts k JOIN companies c ON k.company_id = c.company_id
           WHERE k.contact_id = %s""",
        (contact_id,),
    )


def create_contact(data):
    return execute(
        """INSERT INTO contacts (company_id, contact_name, title, email, phone,
                                 linkedin_url, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (data["company_id"], data["contact_name"], data["title"], data["email"],
         data["phone"], data["linkedin_url"], data["notes"]),
    )


def update_contact(contact_id, data):
    execute(
        """UPDATE contacts
           SET company_id = %s, contact_name = %s, title = %s, email = %s,
               phone = %s, linkedin_url = %s, notes = %s
           WHERE contact_id = %s""",
        (data["company_id"], data["contact_name"], data["title"], data["email"],
         data["phone"], data["linkedin_url"], data["notes"], contact_id),
    )


def delete_contact(contact_id):
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))


# -----------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------
def get_dashboard_stats():
    counts = query_one(
        """SELECT
             (SELECT COUNT(*) FROM companies)    AS companies,
             (SELECT COUNT(*) FROM jobs)         AS jobs,
             (SELECT COUNT(*) FROM applications) AS applications,
             (SELECT COUNT(*) FROM contacts)     AS contacts,
             (SELECT COALESCE(SUM(JSON_LENGTH(interview_data)), 0)
                FROM applications)               AS interviews"""
    )
    by_status_rows = query_all(
        "SELECT status, COUNT(*) AS total FROM applications GROUP BY status"
    )
    by_status = {s: 0 for s in STATUSES}
    for row in by_status_rows:
        by_status[row["status"]] = row["total"]

    total = counts["applications"] or 0
    # "Response" = anything past the Applied stage
    responded = total - by_status["Applied"]
    counts["response_rate"] = round(responded / total * 100) if total else 0
    counts["active"] = by_status["Applied"] + by_status["Screening"] + by_status["Interview"]
    counts["interviews"] = int(counts["interviews"] or 0)

    recent = get_applications()[:5]
    return counts, by_status, recent


def get_upcoming_interviews(today_iso):
    """Pull interview rounds out of the JSON column whose date is today or later."""
    upcoming = []
    for app_row in get_applications():
        for rnd in app_row["interview_data"]:
            if rnd.get("date") and rnd["date"] >= today_iso:
                upcoming.append({
                    "date": rnd["date"],
                    "round": rnd.get("round", ""),
                    "interviewer": rnd.get("interviewer", ""),
                    "job_title": app_row["job_title"],
                    "company_name": app_row["company_name"],
                    "application_id": app_row["application_id"],
                })
    upcoming.sort(key=lambda r: r["date"])
    return upcoming[:5]


# -----------------------------------------------------------------
# Job Match
# -----------------------------------------------------------------
def get_jobs_for_matching():
    return [_decode_job(r) for r in query_all(
        """SELECT j.job_id, j.job_title, j.job_type, j.salary_min, j.salary_max,
                  j.requirements, c.company_name
           FROM jobs j JOIN companies c ON j.company_id = c.company_id"""
    )]
