"""
matching.py - Job Match algorithm.

Match % for a job = (job requirements the user has) / (total job requirements).
This follows the spec example: a job needing Python, SQL, Tableau scores
67% (2/3) for a user with Python, SQL, Flask, and "Tableau" is listed as missing.

Comparison is case-insensitive and ignores extra spaces, so "python",
" Python " and "PYTHON" all count as the same skill. A few common
aliases are folded together (e.g. "JS" -> "javascript").
"""

import re

ALIASES = {
    "js": "javascript",
    "py": "python",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "html5": "html",
    "css3": "css",
    "mysql db": "mysql",
}


def normalize_skill(skill):
    key = re.sub(r"\s+", " ", str(skill)).strip().lower()
    return ALIASES.get(key, key)


def parse_skill_list(text, max_len=50):
    """
    Split comma/semicolon/newline separated text into a clean list.
    Keeps the user's original capitalization but removes blanks and
    case-insensitive duplicates. Returns (skills, errors).
    """
    skills, seen, errors = [], set(), []
    for raw in re.split(r"[,;\n]", text or ""):
        skill = re.sub(r"\s+", " ", raw).strip()
        if not skill:
            continue
        if len(skill) > max_len:
            errors.append(f'Skill "{skill[:20]}..." is longer than {max_len} characters.')
            continue
        key = normalize_skill(skill)
        if key not in seen:
            seen.add(key)
            skills.append(skill)
    return skills, errors


def calculate_match(user_skills, job_requirements):
    """
    Return a dict with matched skills, missing skills and percentage
    for a single job. Jobs with no listed requirements score 0%.
    """
    user_keys = {normalize_skill(s) for s in user_skills}
    matched = [r for r in job_requirements if normalize_skill(r) in user_keys]
    missing = [r for r in job_requirements if normalize_skill(r) not in user_keys]
    total = len(job_requirements)
    percent = round(len(matched) / total * 100) if total else 0
    return {
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "total": total,
        "percent": percent,
    }


def rank_jobs(user_skills, jobs, min_percent=1):
    """
    Score every job and return those at or above min_percent, best first.
    Ties are broken by number of matched skills, then by job title.
    """
    results = []
    for job in jobs:
        score = calculate_match(user_skills, job.get("requirements") or [])
        if score["percent"] >= min_percent:
            results.append({**job, **score})
    results.sort(key=lambda r: (-r["percent"], -r["matched_count"], r["job_title"].lower()))
    return results
