"""Main Autonomous Orchestrator Pipeline for Mumbai MMR Tech Fresher Jobs.

Coordinates:
1. Search & Discovery across Mumbai, Navi Mumbai, and Thane hubs.
2. Strict Parsing & Filtering (strictly 0-1 years / freshers, tech stack tagging).
3. SQLite Persistence with UNIQUE deduplication.
4. Live Notion Database Synchronization.
5. Polite Rate Limiting & Verification Reporting.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Dict, List, Optional

from config import (
    CANONICAL_LOCATIONS,
    REQUEST_DELAY_SECONDS,
    SQLITE_DB_PATH,
    TARGET_TECH_ROLES,
)
from database import (
    get_all_jobs,
    get_stats,
    get_unsynced_jobs,
    init_db,
    is_job_duplicate,
    mark_notion_synced,
    save_job,
)
from notion_sync import NotionSyncClient, get_notion_client
from parser import ParsedJob, parse_and_validate_job
from search_engine import discover_jobs

from pathlib import Path

# Setup clean, structured logging (both console and persistent execution log)
_log_file = Path(__file__).resolve().parent / "agent_execution.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(_log_file), encoding="utf-8"),
    ],
)
logger = logging.getLogger("tech_job_agent.pipeline")


class TechJobAgent:
    """Autonomous pipeline manager for tech fresher job opportunities."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        notion_client: Optional[NotionSyncClient] = None,
        request_delay: float = REQUEST_DELAY_SECONDS,
    ):
        self.db_path = db_path or SQLITE_DB_PATH
        self.notion_client = notion_client or get_notion_client()
        self.request_delay = request_delay

        # Pipeline runtime statistics
        self.stats = {
            "queries_executed": 0,
            "raw_postings_found": 0,
            "passed_fresher_filter": 0,
            "rejected_by_filter": 0,
            "duplicate_skipped": 0,
            "saved_to_sqlite": 0,
            "synced_to_notion": 0,
            "notion_sync_failed_or_skipped": 0,
        }

    def initialize(self) -> None:
        """Sets up the database and checks integrations."""
        logger.info("Initializing Autonomous Tech Job Agent...")
        init_db(self.db_path)

        # Check Notion connectivity
        if self.notion_client.is_configured():
            logger.info("Checking Notion Database connectivity...")
            connected = self.notion_client.verify_connection()
            if connected:
                logger.info("[STATUS] Live Notion Database Sync is ACTIVE and verified.")
            else:
                logger.warning(
                    "[STATUS] Notion connection could not be verified. "
                    "Jobs will be stored in SQLite and sync retried on next run."
                )
        else:
            logger.info(
                "[STATUS] Notion API credentials not provided in .env. "
                "Pipeline will operate in LOCAL SQLite storage mode."
            )

    def process_job_posting(self, raw_posting) -> Optional[ParsedJob]:
        """Runs a single raw posting through parsing, deduplication, SQLite, and Notion."""
        self.stats["raw_postings_found"] += 1

        # 1. Deduplication Pre-check by URL
        if is_job_duplicate(raw_posting.url, self.db_path):
            self.stats["duplicate_skipped"] += 1
            logger.debug("Duplicate job skipped (pre-check): %s", raw_posting.url)
            return None

        # 2. Strict Parsing & Filtering
        parsed: Optional[ParsedJob] = parse_and_validate_job(raw_posting)
        if not parsed:
            self.stats["rejected_by_filter"] += 1
            logger.debug(
                "Posting rejected by strict filter: '%s' at '%s'",
                raw_posting.title,
                raw_posting.company,
            )
            return None

        self.stats["passed_fresher_filter"] += 1
        logger.info(
            "[QUALIFIED FRESHER JOB] '%s' at '%s' | Loc: %s | Exp: %s | Tech: %s",
            parsed.job_title,
            parsed.company_name,
            parsed.canonical_location,
            parsed.experience_required,
            ", ".join(parsed.tech_stack[:5]) or "General",
        )

        # 3. Save to SQLite Database
        is_new, job_id = save_job(parsed, self.db_path)
        if not is_new or not job_id:
            self.stats["duplicate_skipped"] += 1
            logger.debug("Duplicate job hit during insert: %s", parsed.website_url)
            return None

        self.stats["saved_to_sqlite"] += 1

        # 4. Live Notion Sync
        if self.notion_client.is_configured():
            notion_page_id = self.notion_client.sync_job(parsed)
            if notion_page_id:
                mark_notion_synced(job_id, notion_page_id, self.db_path)
                self.stats["synced_to_notion"] += 1
            else:
                self.stats["notion_sync_failed_or_skipped"] += 1
        else:
            self.stats["notion_sync_failed_or_skipped"] += 1

        return parsed

    def run_pipeline(
        self,
        roles: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        max_jobs_per_query: int = 5,
    ) -> Dict[str, Any]:
        """Executes full discovery and sync pipeline across roles and locations."""
        target_roles = roles or TARGET_TECH_ROLES
        target_locations = locations or CANONICAL_LOCATIONS

        self.initialize()

        logger.info(
            "Starting pipeline run across %d roles and %d locations.",
            len(target_roles),
            len(target_locations),
        )

        start_time = time.time()

        for location in target_locations:
            for role in target_roles:
                self.stats["queries_executed"] += 1
                logger.info(
                    "--> Discovering candidates for Role: '%s' in Location: '%s'...",
                    role,
                    location,
                )

                try:
                    candidates = discover_jobs(
                        role=role,
                        location=location,
                        max_results=max_jobs_per_query,
                    )
                except Exception as exc:
                    logger.warning(
                        "Discovery failed for '%s' in '%s': %s", role, location, exc
                    )
                    candidates = []

                for raw_posting in candidates:
                    self.process_job_posting(raw_posting)

                # Respect polite rate limiting between queries
                time.sleep(self.request_delay)

        elapsed = round(time.time() - start_time, 2)
        self.stats["elapsed_seconds"] = elapsed

        self.print_summary_report()
        return self.stats

    def sync_pending_to_notion(self) -> int:
        """Pushes any previously stored SQLite jobs that haven't been synced to Notion yet."""
        if not self.notion_client.is_configured():
            logger.warning(
                "Cannot sync pending jobs: Notion credentials are not configured in .env."
            )
            return 0

        unsynced = get_unsynced_jobs(self.db_path)
        logger.info("Found %d unsynced jobs in SQLite database.", len(unsynced))
        synced_count = 0

        for row in unsynced:
            # Reconstruct ParsedJob from row dict
            job = ParsedJob(
                company_name=row["company_name"],
                job_title=row["job_title"],
                location=row["location"],
                canonical_location=row["location"].split(" ")[0],
                website_url=row["website_url"],
                experience_required=row["experience_required"],
                tech_stack=row["tech_stack"],
                description_summary=row["description_summary"],
                matched_role_category=row.get("role_category", "Software Engineer"),
            )
            page_id = self.notion_client.sync_job(job)
            if page_id:
                mark_notion_synced(row["id"], page_id, self.db_path)
                synced_count += 1
                logger.info(
                    "Synced job #%d ('%s') to Notion page %s",
                    row["id"],
                    job.job_title,
                    page_id,
                )
            time.sleep(0.5)

        logger.info("Successfully pushed %d pending jobs to Notion.", synced_count)
        return synced_count

    def print_summary_report(self) -> None:
        """Prints a comprehensive terminal summary report and logs summary."""
        db_stats = get_stats(self.db_path)
        logger.info(
            "PIPELINE RUN SUMMARY: Queries=%d, Raw Postings=%d, Fresher Matches=%d, New Saved=%d, Notion Synced=%d, Total Jobs in DB=%d",
            self.stats.get("queries_executed", 0),
            self.stats.get("raw_postings_found", 0),
            self.stats.get("passed_fresher_filter", 0),
            self.stats.get("saved_to_sqlite", 0),
            self.stats.get("synced_to_notion", 0),
            db_stats.get("total_jobs", 0),
        )

        border = "=" * 70
        print(f"\n{border}")
        print("    AUTONOMOUS TECH FRESHER JOB PIPELINE - RUN REPORT")
        print("          (Mumbai - Navi Mumbai - Thane Region)")
        print(f"{border}")
        print(f" Execution Time:              {self.stats.get('elapsed_seconds', 0)} seconds")
        print(f" Search Queries Executed:     {self.stats['queries_executed']}")
        print(f" Total Raw Postings Found:    {self.stats['raw_postings_found']}")
        print(f" Rejected by Filter (2+ yrs): {self.stats['rejected_by_filter']}")
        print(f" Passed Fresher Filter (0-1): {self.stats['passed_fresher_filter']}")
        print(f" Duplicate Jobs Skipped:      {self.stats['duplicate_skipped']}")
        print(f" Newly Saved to SQLite DB:    {self.stats['saved_to_sqlite']}")
        print(f" Pushed to Live Notion DB:    {self.stats['synced_to_notion']}")
        print(f"{'-' * 70}")
        print(f" [DATABASE PERSISTENCE STATUS] -> {self.db_path}")
        print(f" Total Stored Jobs in DB:     {db_stats['total_jobs']}")
        print(f" Notion Synced Count:         {db_stats['notion_synced_jobs']}")
        print(f" Pending Sync Count:          {db_stats['pending_sync']}")
        print(f"{'-' * 70}")
        print(" Regional Distribution:")
        for loc, cnt in db_stats["location_breakdown"].items():
            print(f"   * {loc:<35} : {cnt} jobs")
        print("\n Top Tech Stacks Detected:")
        for tech, cnt in list(db_stats["top_tech_stack"].items())[:8]:
            print(f"   * {tech:<20} : {cnt} occurrences")
        print(f"{border}\n")


def parse_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Tech Fresher Job Pipeline for Mumbai MMR"
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Comma-separated target roles (e.g., 'Software Engineer,Data Analyst')",
    )
    parser.add_argument(
        "--locations",
        type=str,
        default=None,
        help="Comma-separated target locations (e.g., 'Mumbai,Navi Mumbai,Thane')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max results per search query (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY_SECONDS,
        help=f"Delay between requests in seconds (default: {REQUEST_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display current SQLite database statistics and exit",
    )
    parser.add_argument(
        "--sync-unsynced",
        action="store_true",
        help="Push any pending unsynced SQLite records to Notion",
    )
    parser.add_argument(
        "--schedule",
        type=str,
        default=None,
        help="Run continuously and execute daily at HH:MM (e.g. '21:00' for 9:00 PM)",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="When using --schedule, execute immediately once before entering schedule",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.schedule:
        from scheduler import start_daemon_scheduler
        start_daemon_scheduler(target_time_str=args.schedule, run_immediately=args.now)
        return

    if args.stats:
        stats = get_stats()
        print("\n=== CURRENT DATABASE STATISTICS ===")
        print(f"Database File: {SQLITE_DB_PATH}")
        print(f"Total Jobs: {stats['total_jobs']}")
        print(f"Synced to Notion: {stats['notion_synced_jobs']}")
        print(f"Pending Sync: {stats['pending_sync']}")
        print("Locations:")
        for loc, count in stats["location_breakdown"].items():
            print(f"  {loc}: {count}")
        print("Top Tech Stacks:")
        for tech, count in stats["top_tech_stack"].items():
            print(f"  {tech}: {count}")
        return

    agent = TechJobAgent(request_delay=args.delay)

    if args.sync_unsynced:
        agent.sync_pending_to_notion()
        return

    roles = [r.strip() for r in args.roles.split(",")] if args.roles else None
    locations = (
        [l.strip() for l in args.locations.split(",")] if args.locations else None
    )

    agent.run_pipeline(
        roles=roles,
        locations=locations,
        max_jobs_per_query=args.limit,
    )


if __name__ == "__main__":
    main()
