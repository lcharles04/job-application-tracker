"""Unit tests for the Job Match algorithm (no database needed).

Run with:  python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matching import calculate_match, parse_skill_list, rank_jobs  # noqa: E402


class TestMatching(unittest.TestCase):
    def test_spec_example(self):
        user = ["Python", "SQL", "Flask"]
        jobs = [
            {"job_title": "Data Analyst", "requirements": ["Python", "SQL", "Tableau"]},
            {"job_title": "Software Developer", "requirements": ["Python", "SQL", "Flask"]},
        ]
        ranked = rank_jobs(user, jobs)
        self.assertEqual(ranked[0]["job_title"], "Software Developer")
        self.assertEqual(ranked[0]["percent"], 100)
        self.assertEqual(ranked[1]["percent"], 67)
        self.assertEqual(ranked[1]["missing"], ["Tableau"])

    def test_case_and_space_insensitive(self):
        result = calculate_match(["  python ", "sql"], ["Python", "SQL"])
        self.assertEqual(result["percent"], 100)

    def test_aliases(self):
        self.assertEqual(calculate_match(["JS"], ["JavaScript"])["percent"], 100)

    def test_no_requirements(self):
        self.assertEqual(calculate_match(["Python"], [])["percent"], 0)

    def test_zero_matches_filtered_unless_requested(self):
        jobs = [{"job_title": "Chef", "requirements": ["Cooking"]}]
        self.assertEqual(rank_jobs(["Python"], jobs), [])
        self.assertEqual(len(rank_jobs(["Python"], jobs, min_percent=0)), 1)

    def test_parse_skill_list_dedupes(self):
        skills, errors = parse_skill_list("Python, python ,SQL;; \nFlask")
        self.assertEqual(skills, ["Python", "SQL", "Flask"])
        self.assertEqual(errors, [])

    def test_parse_skill_list_too_long(self):
        _, errors = parse_skill_list("x" * 60)
        self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
