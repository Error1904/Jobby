"""Live Notion Database synchronization client.

Uses the official `notion-client` library to push validated fresher job postings
as structured pages into a Notion Database. Includes robust fail-safe exception
handling and validation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from config import NOTION_API_KEY, NOTION_DATABASE_ID
from parser import ParsedJob

logger = logging.getLogger("tech_job_agent.notion_sync")


class NotionSyncClient:
    """Client for synchronizing job postings to a Notion database."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        database_id: Optional[str] = None,
    ):
        self.api_key = (api_key or NOTION_API_KEY).strip()
        self.database_id = (database_id or NOTION_DATABASE_ID).strip()
        self.client: Optional[Client] = None

        if self.is_configured():
            try:
                self.client = Client(auth=self.api_key)
                logger.info(
                    "Initialized Notion client with database ID: %s...",
                    self.database_id[:8] if len(self.database_id) >= 8 else self.database_id,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Notion client: %s. Local pipeline will continue.",
                    exc,
                )
                self.client = None
        else:
            logger.info(
                "Notion credentials not fully configured (NOTION_API_KEY or NOTION_DATABASE_ID missing). "
                "Local pipeline will persist to SQLite without live Notion sync."
            )

    def is_configured(self) -> bool:
        """Checks if both Notion API key and database ID are set."""
        return bool(self.api_key and self.database_id)

    def verify_connection(self) -> bool:
        """Tests connectivity and permissions to the specified Notion database.

        Returns:
            True if connection and read permissions succeed, False otherwise.
        """
        if not self.is_configured() or not self.client:
            logger.warning(
                "Cannot verify Notion: NOTION_API_KEY or NOTION_DATABASE_ID not set."
            )
            return False

        try:
            # Query or retrieve database metadata
            db_info = self.client.databases.retrieve(database_id=self.database_id)
            db_title = "Untitled"
            if "title" in db_info and db_info["title"]:
                db_title = db_info["title"][0].get("plain_text", "Untitled")
            logger.info(
                "Successfully connected to Notion Database: '%s' (ID: %s)",
                db_title,
                self.database_id,
            )
            return True
        except APIResponseError as err:
            logger.warning(
                "Notion API error during connection test: %s (Status: %s). "
                "Verify database ID and ensure the Integration is invited to the database.",
                err.message,
                err.status,
            )
            return False
        except Exception as exc:
            logger.warning("Unexpected error connecting to Notion: %s", exc)
            return False

    def sync_job(self, job: ParsedJob) -> Optional[str]:
        """Pushes a parsed job posting to the connected Notion database.

        Maps properties:
        - Job Title (Title)
        - Company (Rich Text)
        - Location (Select)
        - Apply Link (URL)
        - Tech Stack (Multi-select)
        - Experience (Rich Text)

        Fail-safe: Catches any Notion error, logs warning, returns None.

        Returns:
            Notion page ID if created successfully, None otherwise.
        """
        if not self.is_configured():
            logger.debug(
                "Notion sync skipped for '%s': Missing API key or database ID.",
                job.job_title,
            )
            return None

        if not self.client:
            logger.warning("Notion client is not initialized.")
            return None

        try:
            # Sanitize tech stack tags: Notion multi-select does not allow commas
            # and restricts tag length to 100 characters.
            multi_select_tags: List[Dict[str, str]] = []
            for tag in job.tech_stack[:15]:
                clean_tag = tag.replace(",", "").strip()[:100]
                if clean_tag:
                    multi_select_tags.append({"name": clean_tag})

            # Clean location for select property
            clean_location = job.canonical_location.replace(",", "").strip()[:100]

            properties: Dict[str, Any] = {
                # Title property
                "Job Title": {
                    "title": [
                        {
                            "text": {
                                "content": job.job_title[:2000]
                            }
                        }
                    ]
                },
                # Company (Rich Text)
                "Company": {
                    "rich_text": [
                        {
                            "text": {
                                "content": job.company_name[:2000]
                            }
                        }
                    ]
                },
                # Location (Select)
                "Location": {
                    "select": {
                        "name": clean_location
                    }
                },
                # Apply Link (URL)
                "Apply Link": {
                    "url": job.website_url[:2000]
                },
                # Tech Stack (Multi-select)
                "Tech Stack": {
                    "multi_select": multi_select_tags
                },
                # Experience (Rich Text)
                "Experience": {
                    "rich_text": [
                        {
                            "text": {
                                "content": job.experience_required[:2000]
                            }
                        }
                    ]
                },
            }

            # Optional children block for description summary
            children_blocks = [
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Role Summary"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": job.description_summary[:2000]}}
                        ]
                    },
                },
            ]

            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children_blocks,
            )

            page_id = response.get("id")
            logger.info(
                "[NOTION SYNC SUCCESS] Job '%s' at '%s' created (Page ID: %s)",
                job.job_title,
                job.company_name,
                page_id,
            )
            return page_id

        except APIResponseError as err:
            logger.warning(
                "[NOTION SYNC WARNING] Failed to create page for '%s': %s (Status: %s)",
                job.job_title,
                err.message,
                err.status,
            )
            return None
        except Exception as exc:
            logger.warning(
                "[NOTION SYNC WARNING] Unexpected error syncing '%s' to Notion: %s",
                job.job_title,
                exc,
            )
            return None


# Module-level singleton instance
_default_sync_client: Optional[NotionSyncClient] = None


def get_notion_client() -> NotionSyncClient:
    """Returns singleton instance of NotionSyncClient."""
    global _default_sync_client
    if _default_sync_client is None:
        _default_sync_client = NotionSyncClient()
    return _default_sync_client


def sync_job_to_notion(job: ParsedJob) -> Optional[str]:
    """Helper function to sync a job using the default NotionSyncClient."""
    client = get_notion_client()
    return client.sync_job(job)
