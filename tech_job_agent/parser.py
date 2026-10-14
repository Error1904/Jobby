"""Parsing and filtering engine for tech job postings.

Enforces strict experience constraints (strictly 0-1 years / freshers),
validates target locations (Mumbai, Navi Mumbai, Thane and tech hubs),
verifies technical roles, and extracts tech stack keywords.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from config import (
    ALL_LOCATION_KEYWORDS,
    CANONICAL_LOCATIONS,
    DISQUALIFIED_EXPERIENCE_PATTERNS,
    DISQUALIFIED_ROLES,
    FRESHER_TERMS,
    LOCATION_HUBS,
    ROLE_KEYWORDS,
    TARGET_TECH_ROLES,
    TECH_TAXONOMY,
)


# ==============================================================================
# Pydantic Schemas
# ==============================================================================
class RawJobPosting(BaseModel):
    """Raw unprocessed job listing discovered from web or API."""

    title: str
    company: str
    location_raw: str
    url: str
    description_raw: str
    snippet: Optional[str] = ""
    source: Optional[str] = "web_search"


class ExperienceEvaluation(BaseModel):
    """Result of parsing and evaluating experience requirements."""

    is_eligible: bool
    detected_experience_text: str
    min_years: Optional[float] = None
    max_years: Optional[float] = None
    rejection_reason: Optional[str] = None


class ParsedJob(BaseModel):
    """Structured and validated tech fresher job posting ready for DB and Notion."""

    company_name: str = Field(..., description="Name of the hiring company")
    job_title: str = Field(..., description="Role title")
    location: str = Field(..., description="Original detected location string")
    canonical_location: str = Field(
        ..., description="Standardized: Mumbai, Navi Mumbai, or Thane"
    )
    website_url: str = Field(..., description="Direct link or apply URL (UNIQUE)")
    experience_required: str = Field(..., description="Formatted experience string")
    tech_stack: List[str] = Field(
        default_factory=list, description="Extracted tech stack keywords"
    )
    description_summary: str = Field(
        ..., description="Cleaned, concise summary of the job description"
    )
    is_fresher_eligible: bool = Field(
        True, description="Strictly meets 0-1 years criteria"
    )
    matched_role_category: str = Field(
        ..., description="Categorized role (e.g. Software Engineer)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 UTC timestamp",
    )


# ==============================================================================
# Experience Parsing & Filtering (Strict 0-1 Years)
# ==============================================================================
# Regex to match numeric ranges like "0-1 years", "0 - 1 yrs", "0 to 1 year", "1 yr", "6 months"
_RANGE_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:-|to|\+)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
_SINGLE_EXP_REGEX = re.compile(
    r"\b(?:min(?:imum)?|at least)?\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)
_MONTHS_REGEX = re.compile(
    r"\b(\d{1,2})\s*(?:-|to)?\s*(\d{1,2})?\s*months?\b", re.IGNORECASE
)


def evaluate_experience(text: str, title: str = "") -> ExperienceEvaluation:
    """Strictly evaluates whether the text indicates 0-1 years of experience.

    Rejection criteria:
    - Title contains senior, lead, staff, principal, architect.
    - Explicit requirement for 2+ years (e.g. "2+ years", "min 2 years", "3-5 years").
    - Minimum required experience > 1.0 year.
    - If a range like "0-2 years" or "1-2 years" is mentioned, checks if role explicitly
      accepts freshers or disqualifies based on 2+ yrs requirement.

    Acceptance criteria:
    - Mentions "fresher", "entry level", "trainee", "intern", "college graduate", "0 years",
      "0-1 years", "0 to 1 year", "6 months".
    - Minimum experience is <= 1.0 year and no senior/2+ yr disqualification is present.
    """
    combined_text = f"{title} {text}".lower()

    # 1. Quick Title Disqualification Check
    senior_title_pattern = re.compile(
        r"\b(sr\.?|senior|lead|principal|architect|staff|tech lead|director|vp|manager)\b",
        re.IGNORECASE,
    )
    if senior_title_pattern.search(title):
        return ExperienceEvaluation(
            is_eligible=False,
            detected_experience_text="Senior/Lead Title",
            rejection_reason="Job title indicates senior or lead position.",
        )

    # 2. Check for explicit 2+ year disqualifiers in text
    for pattern in DISQUALIFIED_EXPERIENCE_PATTERNS:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            # Check if this matched "0-2" or something similar vs pure "2+" or "3+"
            matched_str = match.group(0)
            return ExperienceEvaluation(
                is_eligible=False,
                detected_experience_text=matched_str,
                rejection_reason=f"Requires 2+ years of experience ({matched_str}).",
            )

    # 3. Check for positive fresher indicators
    found_fresher_terms: List[str] = []
    for term in FRESHER_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", combined_text, re.IGNORECASE):
            found_fresher_terms.append(term)

    # 4. Check for numeric ranges in text
    range_match = _RANGE_REGEX.search(combined_text)
    if range_match:
        try:
            val1 = float(range_match.group(1))
            val2 = float(range_match.group(2))
            min_yrs = min(val1, val2)
            max_yrs = max(val1, val2)

            if min_yrs > 1.0:
                return ExperienceEvaluation(
                    is_eligible=False,
                    detected_experience_text=range_match.group(0),
                    min_years=min_yrs,
                    max_years=max_yrs,
                    rejection_reason=f"Minimum required experience is {min_yrs} years (> 1 year limit).",
                )

            if min_yrs <= 1.0 and max_yrs <= 1.0:
                return ExperienceEvaluation(
                    is_eligible=True,
                    detected_experience_text=range_match.group(0),
                    min_years=min_yrs,
                    max_years=max_yrs,
                )

            # Range spans beyond 1 yr, e.g., 0-2 yrs. If freshers/0 yrs is the floor, check:
            if min_yrs == 0.0 and max_yrs <= 2.0 and found_fresher_terms:
                return ExperienceEvaluation(
                    is_eligible=True,
                    detected_experience_text=f"{range_match.group(0)} (Freshers eligible)",
                    min_years=0.0,
                    max_years=max_yrs,
                )
            elif min_yrs > 0:
                return ExperienceEvaluation(
                    is_eligible=False,
                    detected_experience_text=range_match.group(0),
                    min_years=min_yrs,
                    max_years=max_yrs,
                    rejection_reason=f"Experience range {range_match.group(0)} exceeds strict 0-1 fresher cutoff.",
                )
        except (ValueError, TypeError):
            pass

    # 5. Check for single experience numbers (e.g. "1 year experience")
    single_match = _SINGLE_EXP_REGEX.search(combined_text)
    if single_match:
        try:
            years = float(single_match.group(1))
            if years > 1.0:
                return ExperienceEvaluation(
                    is_eligible=False,
                    detected_experience_text=single_match.group(0),
                    min_years=years,
                    rejection_reason=f"Requires {years} years of experience (exceeds 1 year maximum).",
                )
            if years <= 1.0:
                return ExperienceEvaluation(
                    is_eligible=True,
                    detected_experience_text=single_match.group(0),
                    min_years=years,
                    max_years=years,
                )
        except (ValueError, TypeError):
            pass

    # 6. Check months (e.g., 6 months experience)
    months_match = _MONTHS_REGEX.search(combined_text)
    if months_match:
        m1 = float(months_match.group(1))
        if m1 <= 12.0:
            return ExperienceEvaluation(
                is_eligible=True,
                detected_experience_text=months_match.group(0),
                min_years=0.0,
                max_years=round(m1 / 12.0, 2),
            )

    # 7. Fallback to matched fresher terms
    if found_fresher_terms:
        term_str = ", ".join(set(found_fresher_terms[:3]))
        return ExperienceEvaluation(
            is_eligible=True,
            detected_experience_text=f"Fresher / Entry Level ({term_str})",
            min_years=0.0,
            max_years=1.0,
        )

    # If no explicit experience or fresher term found, reject as unverified/not fresher
    return ExperienceEvaluation(
        is_eligible=False,
        detected_experience_text="Not Specified / Ambiguous",
        rejection_reason="No explicit 0-1 years or fresher indicator detected in posting.",
    )


# ==============================================================================
# Location Matching (Mumbai, Navi Mumbai, Thane & Commercial Hubs)
# ==============================================================================
def match_location(location_str: str, text: str = "") -> Tuple[bool, str, str]:
    """Matches and categorizes location into Mumbai, Navi Mumbai, or Thane.

    Returns:
        (is_matched, canonical_location, matched_hub_or_name)
    """
    combined = f"{location_str} {text}".lower()

    # Prioritize Navi Mumbai and Thane first to avoid greedy "Mumbai" match
    for hub in LOCATION_HUBS["Navi Mumbai"]:
        if re.search(rf"\b{re.escape(hub)}\b", combined):
            return True, "Navi Mumbai", hub.title()

    for hub in LOCATION_HUBS["Thane"]:
        if re.search(rf"\b{re.escape(hub)}\b", combined):
            return True, "Thane", hub.title()

    for hub in LOCATION_HUBS["Mumbai"]:
        if re.search(rf"\b{re.escape(hub)}\b", combined):
            return True, "Mumbai", hub.title()

    return False, "Unknown", "Unknown"


# ==============================================================================
# Role Verification & Categorization
# ==============================================================================
def verify_tech_role(title: str, text: str = "") -> Tuple[bool, str]:
    """Checks if the posting is a bona fide technical role.

    Returns:
        (is_tech_role, matched_role_category)
    """
    clean_title = title.lower()

    # Check for disqualified non-tech roles
    for disq in DISQUALIFIED_ROLES:
        if re.search(rf"\b{re.escape(disq)}\b", clean_title):
            return False, f"Disqualified Role ({disq.title()})"

    # Match against target tech roles
    for role_name, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", clean_title):
                return True, role_name

    # Check combined text if title has generic "Engineer" or "Developer"
    if re.search(r"\b(software|developer|programmer|engineer|coder)\b", clean_title):
        return True, "Software Engineer"

    return False, "Non-Target Role"


# ==============================================================================
# Tech Stack Extraction
# ==============================================================================
def extract_tech_stack(text: str, title: str = "") -> List[str]:
    """Extracts known programming languages, frameworks, and tools.

    Uses exact word-boundary regexes to prevent false positives (e.g., 'go' vs 'Go').
    """
    combined = f"{title} {text}"
    detected: Set[str] = set()

    for keyword, canonical_name in TECH_TAXONOMY.items():
        # Special case handling for short keywords or punctuation
        if keyword in {"c++", "c#"}:
            pattern = rf"(?:^|\s|\W){re.escape(keyword)}(?:$|\s|\W)"
        elif keyword == "go" or keyword == "golang":
            pattern = r"\b(golang|go\s+language)\b"
        elif keyword == ".net":
            pattern = r"(?:\b|\s)\.net(?:\s|\b)"
        elif keyword == "r":
            pattern = r"\br\s+programming\b"
        elif keyword == "c":
            pattern = r"\bc\s+language\b"
        else:
            pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(pattern, combined, re.IGNORECASE):
            detected.add(canonical_name)

    # Return sorted list for deterministic results
    return sorted(list(detected))


# ==============================================================================
# Description Cleaning & Summarization
# ==============================================================================
def clean_and_summarize(html_or_text: str, max_length: int = 320) -> str:
    """Strips HTML tags, collapses whitespace, and creates a concise summary."""
    if not html_or_text:
        return "No description provided."

    # Parse HTML if tags present
    if "<" in html_or_text and ">" in html_or_text:
        soup = BeautifulSoup(html_or_text, "html.parser")
        text = soup.get_text(separator=" ")
    else:
        text = html_or_text

    # Collapse excess whitespaces and newlines
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= max_length:
        return text

    # Truncate at last complete word before max_length
    truncated = text[:max_length].rsplit(" ", 1)[0]
    return f"{truncated}..."


# ==============================================================================
# Full Pipeline Parsing Function
# ==============================================================================
def parse_and_validate_job(raw: RawJobPosting) -> Optional[ParsedJob]:
    """Applies the full parsing and filtering pipeline to a raw job posting.

    Returns:
        ParsedJob if eligible, None if filtered out.
    """
    combined_content = f"{raw.description_raw} {raw.snippet or ''}"

    # 1. Tech Role Check
    is_tech, role_category = verify_tech_role(raw.title, combined_content)
    if not is_tech:
        return None

    # 2. Location Check (Mumbai, Navi Mumbai, Thane MMR)
    loc_matched, canonical_loc, matched_hub = match_location(
        raw.location_raw, combined_content
    )
    if not loc_matched:
        return None

    # 3. Strict Experience Check (0-1 years only)
    exp_eval = evaluate_experience(combined_content, title=raw.title)
    if not exp_eval.is_eligible:
        return None

    # 4. Tech Stack Extraction
    tech_stack = extract_tech_stack(combined_content, title=raw.title)

    # 5. Summary Generation
    summary = clean_and_summarize(combined_content)

    return ParsedJob(
        company_name=raw.company.strip() or "Confidential",
        job_title=raw.title.strip(),
        location=f"{canonical_loc} ({matched_hub})",
        canonical_location=canonical_loc,
        website_url=raw.url.strip(),
        experience_required=exp_eval.detected_experience_text,
        tech_stack=tech_stack,
        description_summary=summary,
        is_fresher_eligible=True,
        matched_role_category=role_category,
    )
