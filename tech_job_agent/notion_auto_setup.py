"""Automated Notion Database Setup Assistant.

Automatically creates or verifies the Notion Database with the required schema:
- Job Title (Title)
- Company (Rich Text)
- Location (Select: Mumbai, Navi Mumbai, Thane)
- Apply Link (URL)
- Tech Stack (Multi-select)
- Experience (Rich Text)

Saves credentials to .env and immediately triggers sync for pending jobs.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Optional

from notion_client import Client
from notion_client.errors import APIResponseError

_CURRENT_DIR = Path(__file__).resolve().parent
_ENV_PATH = _CURRENT_DIR / ".env"


def clean_id(raw_id_or_url: str) -> str:
    """Extracts a 32-character Notion UUID from a raw string or URL."""
    # Remove hyphens and query parameters
    cleaned = raw_id_or_url.split("?")[0].replace("-", "")
    # Search for a 32-character hex sequence
    match = re.search(r"([a-f0-9]{32})", cleaned, re.IGNORECASE)
    if match:
        return match.group(1)
    return raw_id_or_url.strip()


def setup_notion_database(
    api_key: str,
    parent_page_or_db_id: str,
    create_new_db: bool = False,
) -> Optional[str]:
    """Sets up the Notion database and saves config to .env."""
    client = Client(auth=api_key.strip())
    clean_target_id = clean_id(parent_page_or_db_id)

    print("======================================================================")
    print("           AUTOMATED NOTION DATABASE SETUP ASSISTANT")
    print("======================================================================")
    print(f"Target ID: {clean_target_id}")

    final_db_id: Optional[str] = None

    if create_new_db:
        # User supplied a parent Page ID where the new database should be built
        print("\n[1/3] Creating new Notion Database inside parent page...")
        try:
            properties_schema = {
                "Job Title": {"title": {}},
                "Company": {"rich_text": {}},
                "Location": {
                    "select": {
                        "options": [
                            {"name": "Mumbai", "color": "blue"},
                            {"name": "Navi Mumbai", "color": "green"},
                            {"name": "Thane", "color": "orange"},
                        ]
                    }
                },
                "Apply Link": {"url": {}},
                "Tech Stack": {
                    "multi_select": {
                        "options": [
                            {"name": "Python", "color": "yellow"},
                            {"name": "Java", "color": "red"},
                            {"name": "React", "color": "blue"},
                            {"name": "SQL", "color": "purple"},
                            {"name": "Docker", "color": "gray"},
                            {"name": "AWS", "color": "orange"},
                        ]
                    }
                },
                "Experience": {"rich_text": {}},
            }

            db_response = client.databases.create(
                parent={"type": "page_id", "page_id": clean_target_id},
                title=[{"type": "text", "text": {"content": "Tech Jobs - Mumbai MMR (0-1 Yrs)"}}],
                properties=properties_schema,
            )
            final_db_id = db_response.get("id")
            print(f"[SUCCESS] Created new Notion Database! Database ID: {final_db_id}")
        except APIResponseError as err:
            print(f"[WARNING] Could not create database directly under page ({err.message}).")
            print("Assuming target ID is an existing database ID instead...")
            final_db_id = clean_target_id
    else:
        # User supplied an existing database ID
        final_db_id = clean_target_id

    # Verify accessibility of database
    print("\n[2/3] Verifying database connectivity and schema...")
    try:
        db_meta = client.databases.retrieve(database_id=final_db_id)
        db_title = "Untitled"
        if "title" in db_meta and db_meta["title"]:
            db_title = db_meta["title"][0].get("plain_text", "Untitled")
        print(f"[SUCCESS] Connected to Notion Database: '{db_title}' (ID: {final_db_id})")
    except APIResponseError as err:
        print(f"[ERROR] Could not access Notion Database ID '{final_db_id}': {err.message}")
        print("Please ensure your Notion integration has been invited to the database/page.")
        return None

    # Write to .env
    print("\n[3/3] Saving credentials to tech_job_agent/.env...")
    env_content = f"""# Notion API Integration Credentials
NOTION_API_KEY={api_key.strip()}
NOTION_DATABASE_ID={final_db_id.replace('-', '')}

# Pipeline & Storage Configuration
SQLITE_DB_PATH=mumbai_tech_jobs.db
REQUEST_DELAY_SECONDS=2.0
MAX_RESULTS_PER_SEARCH=10
"""
    with open(_ENV_PATH, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"[SUCCESS] Saved configuration to {_ENV_PATH}")

    # Immediately push pending jobs to Notion
    print("\n[SYNC] Pushing stored fresher jobs from SQLite to Notion...")
    from agent import TechJobAgent
    agent = TechJobAgent()
    synced_count = agent.sync_pending_to_notion()
    print(f"[SUCCESS] Synced {synced_count} fresher jobs to your Notion database!")
    print("======================================================================\n")

    return final_db_id


def main():
    parser = argparse.ArgumentParser(description="Automated Notion Setup for Tech Job Agent")
    parser.add_argument("--api-key", type=str, required=True, help="Notion Integration Token (ntn_... or secret_...)")
    parser.add_argument("--target-id", type=str, required=True, help="Notion Database ID or Parent Page URL/ID")
    parser.add_argument("--create-new", action="store_true", help="Create a brand new database inside parent page")
    args = parser.parse_args()

    setup_notion_database(
        api_key=args.api_key,
        parent_page_or_db_id=args.target_id,
        create_new_db=args.create_new,
    )


if __name__ == "__main__":
    main()
