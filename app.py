"""
app.py - Job Application Tracker (Flask)

Routes:
  /                          Dashboard
  /companies ...             Companies CRUD
  /jobs ...                  Jobs CRUD
  /applications ...          Applications CRUD
  /contacts ...              Contacts CRUD
  /match                     Job Match feature

Deletes use a GET confirmation page followed by a POST, so a record is
never removed by simply following a link.
"""

import os
import re
from datetime import date, datetime

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database as db
from matching import parse_skill_list, rank_jobs

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")


# =================================================================
# Validation helpers
# =================================================================
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
PHONE_RE = re.compile(r"^[0-9+()\-.\s]{7,20}$")


def clean(form, field):
    """Trimmed form value, or None if blank (stored as NULL)."""
    value = (form.get(field) or "").strip()
    return value or None


def check_length(errors, label, value, max_len):
    if value and len(value) > max_len:
        errors.append(f"{label} must be {max_len} characters or fewer.")


def check_url(errors, label, value, max_len):
    if value:
        check_length(errors, label, value, max_len)
        if not URL_RE.match(value):
            errors.append(f"{label} must start with http:// or https://.")


def parse_date(errors, label, value, required=False):
    if not value:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{label} must be a valid date (YYYY-MM-DD).")
        return None


def parse_int(errors, label, value, minimum=0):
    if value in (None, ""):
        return None
    try:
        number = int(str(value).replace(",", ""))
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if number < minimum:
        errors.append(f"{label} cannot be less than {minimum}.")
    return number


def parse_fk(errors, label, value, exists_fn):
    """Validate a foreign-key dropdown value against the parent table."""
    try:
        fk = int(value)
    except (TypeError, ValueError):
        errors.append(f"Please select a {label}.")
        return None
    if not exists_fn(fk):
        errors.append(f"The selected {label} does not exist.")
        return None
    return fk


def validate_company(form):
    errors = []
    data = {f: clean(form, f) for f in
            ("company_name", "industry", "website", "city", "state", "notes")}
    if not data["company_name"]:
        errors.append("Company name is required.")
    check_length(errors, "Company name", data["company_name"], 100)
    check_length(errors, "Industry", data["industry"], 50)
    check_url(errors, "Website", data["website"], 200)
    check_length(errors, "City", data["city"], 50)
    check_length(errors, "State", data["state"], 50)
    return data, errors


def validate_job(form):
    errors = []
    data = {
        "job_title": clean(form, "job_title"),
        "job_type": clean(form, "job_type"),
        "job_url": clean(form, "job_url"),
    }
    data["company_id"] = parse_fk(errors, "company", form.get("company_id"), db.get_company)
    if not data["job_title"]:
        errors.append("Job title is required.")
    check_length(errors, "Job title", data["job_title"], 100)
    if data["job_type"] and data["job_type"] not in db.JOB_TYPES:
        errors.append("Job type is not valid.")
    data["salary_min"] = parse_int(errors, "Minimum salary", clean(form, "salary_min"))
    data["salary_max"] = parse_int(errors, "Maximum salary", clean(form, "salary_max"))
    if (data["salary_min"] is not None and data["salary_max"] is not None
            and data["salary_min"] > data["salary_max"]):
        errors.append("Minimum salary cannot be greater than maximum salary.")
    check_url(errors, "Job URL", data["job_url"], 300)
    data["date_posted"] = parse_date(errors, "Date posted", clean(form, "date_posted"))
    if data["date_posted"] and data["date_posted"] > date.today():
        errors.append("Date posted cannot be in the future.")
    skills, skill_errors = parse_skill_list(form.get("requirements", ""))
    errors += skill_errors
    data["requirements"] = skills
    return data, errors


def validate_application(form):
    errors = []
    data = {
        "status": clean(form, "status") or "Applied",
        "resume_version": clean(form, "resume_version"),
        "cover_letter_sent": form.get("cover_letter_sent") == "on",
    }
    data["job_id"] = parse_fk(errors, "job", form.get("job_id"), db.get_job)
    data["application_date"] = parse_date(
        errors, "Application date", clean(form, "application_date"), required=True)
    if data["status"] not in db.STATUSES:
        errors.append("Status is not valid.")
    check_length(errors, "Resume version", data["resume_version"], 50)

    # Interview rounds arrive as parallel lists from repeated form rows
    rounds = []
    rows = zip(form.getlist("iv_date"), form.getlist("iv_round"),
               form.getlist("iv_interviewer"), form.getlist("iv_notes"))
    for i, (iv_date, iv_round, iv_who, iv_notes) in enumerate(rows, start=1):
        iv_date, iv_round = iv_date.strip(), iv_round.strip()
        iv_who, iv_notes = iv_who.strip(), iv_notes.strip()
        if not any((iv_date, iv_round, iv_who, iv_notes)):
            continue  # blank row
        parsed = parse_date(errors, f"Interview #{i} date", iv_date, required=True)
        if not iv_round:
            errors.append(f"Interview #{i} needs a round name (e.g. Phone Screen).")
        rounds.append({
            "date": parsed.isoformat() if parsed else iv_date,
            "round": iv_round[:50],
            "interviewer": iv_who[:100],
            "notes": iv_notes[:500],
        })
    rounds.sort(key=lambda r: r["date"])
    data["interview_data"] = rounds
    return data, errors


def validate_contact(form):
    errors = []
    data = {f: clean(form, f) for f in
            ("contact_name", "title", "email", "phone", "linkedin_url", "notes")}
    data["company_id"] = parse_fk(errors, "company", form.get("company_id"), db.get_company)
    if not data["contact_name"]:
        errors.append("Contact name is required.")
    check_length(errors, "Contact name", data["contact_name"], 100)
    check_length(errors, "Title", data["title"], 100)
    if data["email"]:
        check_length(errors, "Email", data["email"], 100)
        if not EMAIL_RE.match(data["email"]):
            errors.append("Email address is not valid.")
    if data["phone"] and not PHONE_RE.match(data["phone"]):
        errors.append("Phone may only contain digits, spaces, + - ( ) . and be 7-20 characters.")
    check_url(errors, "LinkedIn URL", data["linkedin_url"], 200)
    return data, errors


def show_errors(errors):
    for message in errors:
        flash(message, "error")


# =================================================================
# Error handling
# =================================================================
@app.errorhandler(404)
def not_found(_err):
    return render_template("error.html", title="Not found",
                           message="That record or page does not exist."), 404


@app.errorhandler(mysql.connector.Error)
def database_error(err):
    app.logger.exception("Database error")
    return render_template(
        "error.html", title="Database error",
        message="The app could not talk to MySQL. Check that the server is running "
                "and that the settings in your .env file are correct.",
        detail=str(err)), 500


def get_or_404(fetch, record_id):
    record = fetch(record_id)
    if record is None:
        abort(404)
    return record


# =================================================================
# Dashboard
# =================================================================
@app.route("/")
def dashboard():
    stats, by_status, recent = db.get_dashboard_stats()
    upcoming = db.get_upcoming_interviews(date.today().isoformat())
    return render_template("dashboard.html", stats=stats, by_status=by_status,
                           recent=recent, upcoming=upcoming)


# =================================================================
# Companies
# =================================================================
@app.route("/companies")
def companies():
    search = request.args.get("q", "").strip()
    return render_template("companies.html", companies=db.get_companies(search), search=search)


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404(db.get_company, company_id)
    return render_template("company_detail.html", company=company,
                           jobs=db.get_jobs(company_id=company_id),
                           contacts=db.get_contacts(company_id=company_id))


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    form = request.form
    if request.method == "POST":
        data, errors = validate_company(form)
        if not errors:
            try:
                new_id = db.create_company(data)
                flash(f'Company "{data["company_name"]}" added.', "success")
                return redirect(url_for("company_detail", company_id=new_id))
            except mysql.connector.Error as err:
                if not db.is_duplicate_error(err):
                    raise
                errors.append("A company with that name already exists.")
        show_errors(errors)
    return render_template("company_form.html", form=form, company=None)


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_or_404(db.get_company, company_id)
    form = company
    if request.method == "POST":
        form = request.form
        data, errors = validate_company(form)
        if not errors:
            try:
                db.update_company(company_id, data)
                flash("Company updated.", "success")
                return redirect(url_for("company_detail", company_id=company_id))
            except mysql.connector.Error as err:
                if not db.is_duplicate_error(err):
                    raise
                errors.append("A company with that name already exists.")
        show_errors(errors)
    return render_template("company_form.html", form=form, company=company)


@app.route("/companies/<int:company_id>/delete", methods=["GET", "POST"])
def company_delete(company_id):
    company = get_or_404(db.get_company, company_id)
    if request.method == "POST":
        db.delete_company(company_id)
        flash(f'Company "{company["company_name"]}" deleted.', "success")
        return redirect(url_for("companies"))
    impact = db.get_company_delete_impact(company_id)
    warnings = []
    if impact["jobs"]:
        warnings.append(f'{impact["jobs"]} job(s)')
    if impact["applications"]:
        warnings.append(f'{impact["applications"]} application(s)')
    if impact["contacts"]:
        warnings.append(f'{impact["contacts"]} contact(s)')
    return render_template("confirm_delete.html", kind="company",
                           name=company["company_name"], warnings=warnings,
                           cancel_url=url_for("company_detail", company_id=company_id))


# =================================================================
# Jobs
# =================================================================
@app.route("/jobs")
def jobs():
    search = request.args.get("q", "").strip()
    job_type = request.args.get("type", "")
    if job_type not in db.JOB_TYPES:
        job_type = ""
    return render_template("jobs.html", jobs=db.get_jobs(search, job_type),
                           search=search, job_type=job_type, job_types=db.JOB_TYPES)


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_or_404(db.get_job, job_id)
    return render_template("job_detail.html", job=job,
                           applications=db.get_applications_for_job(job_id))


def job_form_context(form, job):
    return {"form": form, "job": job, "companies": db.get_company_choices(),
            "job_types": db.JOB_TYPES}


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    form = request.form if request.method == "POST" else {"company_id": request.args.get("company_id")}
    if request.method == "POST":
        data, errors = validate_job(form)
        if not errors:
            new_id = db.create_job(data)
            flash(f'Job "{data["job_title"]}" added.', "success")
            return redirect(url_for("job_detail", job_id=new_id))
        show_errors(errors)
    return render_template("job_form.html", **job_form_context(form, None))


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = get_or_404(db.get_job, job_id)
    form = dict(job, requirements=", ".join(job["requirements"]))
    if request.method == "POST":
        form = request.form
        data, errors = validate_job(form)
        if not errors:
            db.update_job(job_id, data)
            flash("Job updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        show_errors(errors)
    return render_template("job_form.html", **job_form_context(form, job))


@app.route("/jobs/<int:job_id>/delete", methods=["GET", "POST"])
def job_delete(job_id):
    job = get_or_404(db.get_job, job_id)
    if request.method == "POST":
        db.delete_job(job_id)
        flash(f'Job "{job["job_title"]}" deleted.', "success")
        return redirect(url_for("jobs"))
    impact = db.get_job_delete_impact(job_id)
    warnings = [f'{impact["applications"]} application(s)'] if impact["applications"] else []
    return render_template("confirm_delete.html", kind="job",
                           name=f'{job["job_title"]} at {job["company_name"]}',
                           warnings=warnings,
                           cancel_url=url_for("job_detail", job_id=job_id))


# =================================================================
# Applications
# =================================================================
@app.route("/applications")
def applications():
    status = request.args.get("status", "")
    if status not in db.STATUSES:
        status = ""
    search = request.args.get("q", "").strip()
    return render_template("applications.html",
                           applications=db.get_applications(status, search),
                           status=status, search=search, statuses=db.STATUSES)


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = get_or_404(db.get_application, application_id)
    return render_template("application_detail.html", app_row=application)


def application_form_context(form, application, rounds):
    # Always show two empty rows so the user can add interview rounds
    rows = list(rounds) + [{}, {}]
    return {"form": form, "application": application, "jobs": db.get_job_choices(),
            "statuses": db.STATUSES, "rounds": rows}


def rounds_from_form(form):
    return [{"date": d, "round": r, "interviewer": w, "notes": n}
            for d, r, w, n in zip(form.getlist("iv_date"), form.getlist("iv_round"),
                                  form.getlist("iv_interviewer"), form.getlist("iv_notes"))
            if any(x.strip() for x in (d, r, w, n))]


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    if request.method == "POST":
        form = request.form
        data, errors = validate_application(form)
        if not errors:
            new_id = db.create_application(data)
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
        show_errors(errors)
        rounds = rounds_from_form(form)
    else:
        form = {"job_id": request.args.get("job_id"),
                "application_date": date.today().isoformat(), "status": "Applied"}
        rounds = []
    return render_template("application_form.html",
                           **application_form_context(form, None, rounds))


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    application = get_or_404(db.get_application, application_id)
    form, rounds = application, application["interview_data"]
    if request.method == "POST":
        form = request.form
        data, errors = validate_application(form)
        if not errors:
            db.update_application(application_id, data)
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        show_errors(errors)
        rounds = rounds_from_form(form)
    return render_template("application_form.html",
                           **application_form_context(form, application, rounds))


@app.route("/applications/<int:application_id>/delete", methods=["GET", "POST"])
def application_delete(application_id):
    application = get_or_404(db.get_application, application_id)
    if request.method == "POST":
        db.delete_application(application_id)
        flash("Application deleted.", "success")
        return redirect(url_for("applications"))
    return render_template(
        "confirm_delete.html", kind="application",
        name=f'{application["job_title"]} at {application["company_name"]} '
             f'(applied {application["application_date"]})',
        warnings=[],
        cancel_url=url_for("application_detail", application_id=application_id))


# =================================================================
# Contacts
# =================================================================
@app.route("/contacts")
def contacts():
    search = request.args.get("q", "").strip()
    return render_template("contacts.html", contacts=db.get_contacts(search), search=search)


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    form = request.form if request.method == "POST" else {"company_id": request.args.get("company_id")}
    if request.method == "POST":
        data, errors = validate_contact(form)
        if not errors:
            db.create_contact(data)
            flash(f'Contact "{data["contact_name"]}" added.', "success")
            return redirect(url_for("contacts"))
        show_errors(errors)
    return render_template("contact_form.html", form=form, contact=None,
                           companies=db.get_company_choices())


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = get_or_404(db.get_contact, contact_id)
    form = contact
    if request.method == "POST":
        form = request.form
        data, errors = validate_contact(form)
        if not errors:
            db.update_contact(contact_id, data)
            flash("Contact updated.", "success")
            return redirect(url_for("contacts"))
        show_errors(errors)
    return render_template("contact_form.html", form=form, contact=contact,
                           companies=db.get_company_choices())


@app.route("/contacts/<int:contact_id>/delete", methods=["GET", "POST"])
def contact_delete(contact_id):
    contact = get_or_404(db.get_contact, contact_id)
    if request.method == "POST":
        db.delete_contact(contact_id)
        flash(f'Contact "{contact["contact_name"]}" deleted.', "success")
        return redirect(url_for("contacts"))
    return render_template("confirm_delete.html", kind="contact",
                           name=f'{contact["contact_name"]} ({contact["company_name"]})',
                           warnings=[], cancel_url=url_for("contacts"))


# =================================================================
# Job Match
# =================================================================
@app.route("/match", methods=["GET", "POST"])
def job_match():
    skills_text = request.values.get("skills", "")
    show_all = request.values.get("show_all") == "on"
    skills, results, searched = [], [], False
    if skills_text.strip():
        searched = True
        skills, errors = parse_skill_list(skills_text)
        show_errors(errors)
        if skills:
            results = rank_jobs(skills, db.get_jobs_for_matching(),
                                min_percent=0 if show_all else 1)
    elif request.method == "POST":
        flash("Enter at least one skill.", "error")
    return render_template("job_match.html", skills_text=skills_text, skills=skills,
                           results=results, searched=searched, show_all=show_all)


# =================================================================
# Template helpers
# =================================================================
@app.template_filter("money")
def money(value):
    return f"${value:,.0f}" if value is not None else ""


@app.template_filter("datefmt")
def datefmt(value):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value
    return value.strftime("%b %d, %Y")


@app.context_processor
def inject_globals():
    return {"current_year": date.today().year}


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1",
            port=int(os.getenv("PORT", "5000")))
