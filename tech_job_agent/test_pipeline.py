"""Comprehensive test suite for the Autonomous Tech Fresher Job Pipeline.

Validates:
1. Strict experience filtering (0-1 years / freshers accepted; 2+ years rejected).
2. Location detection across Mumbai, Navi Mumbai, and Thane hubs.
3. Tech role verification and non-tech disqualification.
4. Tech stack keyword extraction.
5. SQLite schema persistence and deduplication via UNIQUE URL constraint.
6. Notion sync fail-safe behavior.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Add current directory to path
_CURRENT_DIR = Path(__file__).resolve().parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))

from database import (
    get_all_jobs,
    get_stats,
    init_db,
    is_job_duplicate,
    save_job,
)
from notion_sync import NotionSyncClient
from parser import (
    ParsedJob,
    RawJobPosting,
    evaluate_experience,
    extract_tech_stack,
    match_location,
    parse_and_validate_job,
    verify_tech_role,
)


class TestParserExperienceFiltering(unittest.TestCase):
    """Tests strict 0-1 years and fresher experience logic."""

    def test_freshers_accepted(self):
        cases = [
            ("Looking for freshers who graduated recently.", "Software Engineer"),
            ("0-1 years of experience in Python development.", "Python Developer"),
            ("0 to 1 year experience required.", "Associate Developer"),
            ("Entry level software developer role.", "Junior SDE"),
            ("Graduate Trainee Engineer opening.", "Graduate Trainee"),
            ("6 months experience or internship in React.", "Frontend Developer"),
            ("0 years experience, freshers can apply.", "SDE-1"),
        ]
        for text, title in cases:
            res = evaluate_experience(text, title=title)
            self.assertTrue(
                res.is_eligible,
                f"Failed for text: '{text}' (reason: {res.rejection_reason})",
            )

    def test_senior_and_2plus_years_rejected(self):
        disqualified_cases = [
            ("Requires 2+ years of experience in Java.", "Java Developer"),
            ("Looking for candidates with 2-4 years experience.", "Software Engineer"),
            ("Minimum 3 years of hands-on experience in AWS.", "DevOps Engineer"),
            ("At least 2 years in full stack web development.", "Full Stack Dev"),
            ("5+ years of experience required.", "Backend Engineer"),
            ("Mid-level engineer with 2 to 3 yrs exp.", "Engineer"),
            ("Lead Architect responsible for microservices.", "Lead Software Engineer"),
            ("Senior Python Developer needed.", "Senior Software Engineer"),
        ]
        for text, title in disqualified_cases:
            res = evaluate_experience(text, title=title)
            self.assertFalse(
                res.is_eligible,
                f"Expected rejection for '{text}' with title '{title}', but was accepted.",
            )

    def test_ambiguous_without_fresher_keywords_rejected(self):
        res = evaluate_experience(
            "Must have deep domain knowledge in banking algorithms.",
            title="Software Developer",
        )
        self.assertFalse(res.is_eligible)


class TestParserLocationAndRoles(unittest.TestCase):
    """Tests location hub matching and technical role verification."""

    def test_mumbai_hubs_matched(self):
        matched, canon, hub = match_location("BKC, Mumbai")
        self.assertTrue(matched)
        self.assertEqual(canon, "Mumbai")

        matched, canon, hub = match_location("Andheri East")
        self.assertTrue(matched)
        self.assertEqual(canon, "Mumbai")

    def test_navi_mumbai_hubs_matched(self):
        matched, canon, hub = match_location("Millennium Business Park, Mahape")
        self.assertTrue(matched)
        self.assertEqual(canon, "Navi Mumbai")

        matched, canon, hub = match_location("Airoli, Mindspace")
        self.assertTrue(matched)
        self.assertEqual(canon, "Navi Mumbai")

        matched, canon, hub = match_location("CBD Belapur")
        self.assertTrue(matched)
        self.assertEqual(canon, "Navi Mumbai")

    def test_thane_hubs_matched(self):
        matched, canon, hub = match_location("Wagle Estate, Thane")
        self.assertTrue(matched)
        self.assertEqual(canon, "Thane")

        matched, canon, hub = match_location("Ghodbunder Road")
        self.assertTrue(matched)
        self.assertEqual(canon, "Thane")

    def test_outside_locations_rejected(self):
        matched, canon, _ = match_location("Whitefield, Bangalore")
        self.assertFalse(matched)

        matched, canon, _ = match_location("Cyber City, Gurgaon")
        self.assertFalse(matched)

    def test_tech_roles_accepted(self):
        for role in [
            "Software Engineer",
            "Junior Python Developer",
            "Full Stack Developer (MERN)",
            "Data Analyst Trainee",
            "Associate DevOps Engineer",
            "QA Automation Tester",
        ]:
            is_tech, cat = verify_tech_role(role)
            self.assertTrue(is_tech, f"Role '{role}' should be accepted as tech role.")

    def test_non_tech_roles_rejected(self):
        for non_tech in [
            "Customer Support Telecaller",
            "BPO Voice Process Executive",
            "Sales Executive",
            "HR Recruiter",
            "Data Entry Operator",
        ]:
            is_tech, cat = verify_tech_role(non_tech)
            self.assertFalse(is_tech, f"Role '{non_tech}' should be rejected.")


class TestTechStackExtraction(unittest.TestCase):
    """Tests regex-based tech stack tagging."""

    def test_tech_stack_detected(self):
        description = """
            We are hiring engineers proficient in Python, FastAPI, React, PostgreSQL,
            and Docker. Good understanding of AWS and Git is required.
        """
        tags = extract_tech_stack(description)
        expected = {"Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS", "Git"}
        self.assertTrue(
            expected.issubset(set(tags)),
            f"Detected tags {tags} missing expected elements {expected - set(tags)}",
        )


class TestDatabaseDeduplication(unittest.TestCase):
    """Tests SQLite persistence and UNIQUE constraint deduplication."""

    TEST_DB = str(_CURRENT_DIR / "test_temp_jobs.db")

    def setUp(self):
        if os.path.exists(self.TEST_DB):
            os.remove(self.TEST_DB)
        init_db(self.TEST_DB)

    def tearDown(self):
        if os.path.exists(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_save_and_deduplicate(self):
        job = ParsedJob(
            company_name="Jio Platforms",
            job_title="Graduate Trainee Engineer",
            location="Navi Mumbai (Ghansoli)",
            canonical_location="Navi Mumbai",
            website_url="https://careers.jio.com/test-job-101",
            experience_required="0-1 years",
            tech_stack=["Python", "PostgreSQL", "Docker"],
            description_summary="Graduate Trainee Engineer in Ghansoli, Navi Mumbai.",
            matched_role_category="Software Engineer",
        )

        # 1. First insert must succeed
        is_new, job_id = save_job(job, self.TEST_DB)
        self.assertTrue(is_new)
        self.assertIsNotNone(job_id)

        # 2. Duplicate pre-check must detect existing URL
        self.assertTrue(is_job_duplicate(job.website_url, self.TEST_DB))

        # 3. Second insert attempt must be caught by deduplication logic
        is_new_again, existing_id = save_job(job, self.TEST_DB)
        self.assertFalse(is_new_again)
        self.assertEqual(job_id, existing_id)

        # 4. Verify only 1 record exists
        all_jobs = get_all_jobs(self.TEST_DB)
        self.assertEqual(len(all_jobs), 1)

        # 5. Verify stats
        stats = get_stats(self.TEST_DB)
        self.assertEqual(stats["total_jobs"], 1)


class TestNotionFailSafe(unittest.TestCase):
    """Tests fail-safe behavior of Notion client when credentials are absent or invalid."""

    def test_missing_credentials_does_not_crash(self):
        client = NotionSyncClient(api_key="", database_id="")
        self.assertFalse(client.is_configured())

        job = ParsedJob(
            company_name="Test Company",
            job_title="Associate SDE",
            location="Mumbai (BKC)",
            canonical_location="Mumbai",
            website_url="https://example.com/job-test",
            experience_required="Freshers",
            tech_stack=["Java", "Spring Boot"],
            description_summary="Test job description",
            matched_role_category="Software Engineer",
        )
        # Must return None safely without raising an exception
        page_id = client.sync_job(job)
        self.assertIsNone(page_id)


if __name__ == "__main__":
    unittest.main()
