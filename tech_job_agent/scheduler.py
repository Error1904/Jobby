"""Daily Autonomous Scheduler for Mumbai MMR Tech Fresher Job Pipeline.

Runs the discovery, filtering, SQLite persistence, and Notion sync
automatically every day at a specified time (default: 21:00 / 9:00 PM).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
_CURRENT_DIR = Path(__file__).resolve().parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))

from agent import TechJobAgent
from config import SQLITE_DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tech_job_agent.scheduler")


def calculate_seconds_until(target_time_str: str) -> Tuple[int, datetime]:
    """Calculates the number of seconds until the next occurrence of HH:MM.

    Args:
        target_time_str: "21:00" (9:00 PM)

    Returns:
        (seconds_to_wait, next_run_datetime)
    """
    target_hour, target_minute = map(int, target_time_str.split(":"))
    now = datetime.now()

    # Determine next target run
    target_dt = now.replace(
        hour=target_hour, minute=target_minute, second=0, microsecond=0
    )

    # If 9 PM has already passed today, schedule for 9 PM tomorrow
    if target_dt <= now:
        target_dt += timedelta(days=1)

    seconds_to_wait = int((target_dt - now).total_seconds())
    return seconds_to_wait, target_dt


def run_scheduled_job() -> None:
    """Executes the full agent pipeline and syncs pending Notion items."""
    logger.info("=============================================================")
    logger.info("[TRIGGER] Running daily scheduled Tech Job Agent pipeline...")
    logger.info("=============================================================")

    try:
        agent = TechJobAgent()
        stats = agent.run_pipeline()
        logger.info(
            "[COMPLETED] Pipeline run finished. Stored %d new jobs in SQLite. Pushed %d to Notion.",
            stats.get("saved_to_sqlite", 0),
            stats.get("synced_to_notion", 0),
        )
    except Exception as exc:
        logger.error("[ERROR] Scheduled pipeline execution encountered an error: %s", exc)


def start_daemon_scheduler(target_time_str: str = "21:00", run_immediately: bool = False) -> None:
    """Continuous scheduler loop running every day at target_time_str."""
    print("=" * 65)
    print("  TECH JOB AGENT - AUTONOMOUS DAILY SCHEDULER")
    print(f"  Target Run Time: Everyday at {target_time_str} (9:00 PM)")
    print("=" * 65)

    if run_immediately:
        logger.info("Immediate execution requested (--now flag). Running initial pass...")
        run_scheduled_job()

    while True:
        seconds_to_wait, next_run = calculate_seconds_until(target_time_str)
        hours = seconds_to_wait // 3600
        minutes = (seconds_to_wait % 3600) // 60
        secs = seconds_to_wait % 60

        logger.info(
            "[STANDBY] Next execution scheduled for %s (in %dh %dm %ds).",
            next_run.strftime("%Y-%m-%d %I:%M:%S %p"),
            hours,
            minutes,
            secs,
        )

        try:
            # Sleep until target time
            time.sleep(seconds_to_wait)
            run_scheduled_job()
            # Brief pause to avoid re-triggering in the same minute
            time.sleep(65)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")
            break


def parse_args():
    parser = argparse.ArgumentParser(
        description="Daily Autonomous Scheduler for Mumbai MMR Tech Jobs"
    )
    parser.add_argument(
        "--time",
        type=str,
        default="21:00",
        help="Target daily time in 24-hr format (default: '21:00' for 9:00 PM)",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run once immediately before entering the 9:00 PM daily schedule",
    )
    return parser.parse_args()


if __name__ == "__main__":
    from typing import Tuple
    args = parse_args()
    start_daemon_scheduler(target_time_str=args.time, run_immediately=args.now)
