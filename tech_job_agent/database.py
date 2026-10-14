"""SQLite database storage and deduplication layer for the Tech Fresher Job Pipeline.

Maintains table `tech_jobs` with UNIQUE constraint on `website_url` to guarantee
zero duplicates. Stores tech stacks as structured JSON arrays.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from config import SQLITE_DB_PATH
from parser import ParsedJob

logger = logging.getLogger("tech_job_agent.database")


@contextmanager
def get_db_connection(
    db_path: Optional[str] = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connection with row factory."""
    target_path = db_path or SQLITE_DB_PATH
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite database schema if not already present.

    Creates table `tech_jobs` with UNIQUE constraint on `website_url`.
    """
    with get_db_connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tech_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    location TEXT NOT NULL,
                    website_url TEXT UNIQUE NOT NULL,
                    experience_required TEXT NOT NULL,
                    tech_stack TEXT NOT NULL,          -- JSON serialized list
                    description_summary TEXT NOT NULL,
                    role_category TEXT,
                    notion_synced INTEGER DEFAULT 0,    -- 0=No, 1=Yes
                    notion_page_id TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            # Create indexing for fast lookup and deduplication
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_website_url ON tech_jobs(website_url);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_location ON tech_jobs(location);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notion_synced ON tech_jobs(notion_synced);"
            )
    logger.info("Initialized SQLite database at %s", db_path or SQLITE_DB_PATH)


def is_job_duplicate(url: str, db_path: Optional[str] = None) -> bool:
    """Checks whether a job listing with the specified website URL is already recorded.

    Returns:
        True if already exists in database, False otherwise.
    """
    normalized_url = url.strip()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM tech_jobs WHERE website_url = ? LIMIT 1;",
            (normalized_url,),
        )
        return cursor.fetchone() is not None


def save_job(
    job: ParsedJob, db_path: Optional[str] = None
) -> Tuple[bool, Optional[int]]:
    """Inserts a new parsed job into the database.

    Enforces deduplication via UNIQUE constraint.

    Returns:
        (is_inserted, job_id):
            is_inserted: True if newly added, False if duplicate skipped.
            job_id: ID of the record in SQLite, or existing job_id if duplicate.
    """
    init_db(db_path)

    tech_stack_json = json.dumps(job.tech_stack)
    created_at = job.timestamp or datetime.utcnow().isoformat()

    with get_db_connection(db_path) as conn:
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO tech_jobs (
                        company_name,
                        job_title,
                        location,
                        website_url,
                        experience_required,
                        tech_stack,
                        description_summary,
                        role_category,
                        notion_synced,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
                    """,
                    (
                        job.company_name,
                        job.job_title,
                        job.location,
                        job.website_url,
                        job.experience_required,
                        tech_stack_json,
                        job.description_summary,
                        job.matched_role_category,
                        created_at,
                    ),
                )
                job_id = cursor.lastrowid
                logger.info(
                    "Saved job #%d: '%s' at '%s'",
                    job_id,
                    job.job_title,
                    job.company_name,
                )
                return True, job_id
        except sqlite3.IntegrityError:
            # Duplicate URL hit
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM tech_jobs WHERE website_url = ?;",
                (job.website_url,),
            )
            row = cursor.fetchone()
            existing_id = row["id"] if row else None
            logger.debug(
                "Skipping duplicate job URL: %s (DB ID: %s)",
                job.website_url,
                existing_id,
            )
            return False, existing_id


def mark_notion_synced(
    job_id: int, notion_page_id: str, db_path: Optional[str] = None
) -> None:
    """Updates the record to indicate successful sync with Notion."""
    with get_db_connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                UPDATE tech_jobs
                SET notion_synced = 1, notion_page_id = ?
                WHERE id = ?;
                """,
                (notion_page_id, job_id),
            )
    logger.debug("Marked job #%d as synced to Notion (%s)", job_id, notion_page_id)


def get_all_jobs(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all jobs from the local database formatted as dictionaries."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tech_jobs ORDER BY id DESC;")
        rows = cursor.fetchall()
        jobs: List[Dict[str, Any]] = []
        for r in rows:
            job_dict = dict(r)
            job_dict["tech_stack"] = json.loads(job_dict["tech_stack"] or "[]")
            jobs.append(job_dict)
        return jobs


def get_unsynced_jobs(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all jobs that have not yet been synced to Notion."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tech_jobs WHERE notion_synced = 0 ORDER BY id ASC;"
        )
        rows = cursor.fetchall()
        jobs: List[Dict[str, Any]] = []
        for r in rows:
            job_dict = dict(r)
            job_dict["tech_stack"] = json.loads(job_dict["tech_stack"] or "[]")
            jobs.append(job_dict)
        return jobs


def get_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Generates analytical summary statistics of the stored jobs."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total FROM tech_jobs;")
        total_count = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS synced FROM tech_jobs WHERE notion_synced = 1;"
        )
        synced_count = cursor.fetchone()["synced"]

        cursor.execute(
            """
            SELECT location, COUNT(*) as cnt
            FROM tech_jobs
            GROUP BY location
            ORDER BY cnt DESC;
            """
        )
        location_counts = {row["location"]: row["cnt"] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT role_category, COUNT(*) as cnt
            FROM tech_jobs
            GROUP BY role_category
            ORDER BY cnt DESC;
            """
        )
        role_counts = {row["role_category"]: row["cnt"] for row in cursor.fetchall()}

        # Top tech stacks
        cursor.execute("SELECT tech_stack FROM tech_jobs;")
        tech_counts: Dict[str, int] = {}
        for row in cursor.fetchall():
            tags = json.loads(row["tech_stack"] or "[]")
            for tag in tags:
                tech_counts[tag] = tech_counts.get(tag, 0) + 1

        top_tech = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_jobs": total_count,
            "notion_synced_jobs": synced_count,
            "pending_sync": total_count - synced_count,
            "location_breakdown": location_counts,
            "role_breakdown": role_counts,
            "top_tech_stack": dict(top_tech),
        }
