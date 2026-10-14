"""Configuration settings for the Autonomous Tech Fresher Job Pipeline.

Handles environment variables, target locations, role definitions,
and tech stack taxonomy for Mumbai, Navi Mumbai, and Thane.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Set
from dotenv import load_dotenv

# Automatically load .env file from the tech_job_agent folder or project root
_CURRENT_DIR = Path(__file__).resolve().parent
_ENV_PATH = _CURRENT_DIR / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()  # Fallback to root or system env

# ==============================================================================
# Notion & Google API Credentials
# ==============================================================================
NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "").strip()
NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "").strip()

GOOGLE_SEARCH_API_KEY: str = os.getenv("GOOGLE_SEARCH_API_KEY", "").strip()
GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "").strip()

# ==============================================================================
# Storage & Execution Settings
# ==============================================================================
DEFAULT_DB_FILENAME = "mumbai_tech_jobs.db"
_raw_db_path = os.getenv("SQLITE_DB_PATH", "").strip()
if _raw_db_path:
    _p = Path(_raw_db_path)
    SQLITE_DB_PATH: str = str((_p if _p.is_absolute() else _CURRENT_DIR / _p).resolve())
else:
    SQLITE_DB_PATH: str = str((_CURRENT_DIR / DEFAULT_DB_FILENAME).resolve())

REQUEST_DELAY_SECONDS: float = float(os.getenv("REQUEST_DELAY_SECONDS", "2.0"))
MAX_RESULTS_PER_SEARCH: int = int(os.getenv("MAX_RESULTS_PER_SEARCH", "10"))
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
)

# ==============================================================================
# Target Locations (Mumbai MMR Tech Hubs)
# ==============================================================================
CANONICAL_LOCATIONS: List[str] = [
    "Mumbai",
    "Navi Mumbai",
    "Thane",
]

# Detailed commercial hubs mapped to canonical regions
LOCATION_HUBS: Dict[str, List[str]] = {
    "Mumbai": [
        "mumbai",
        "bkc",
        "bandra kurla complex",
        "andheri",
        "andheri east",
        "andheri west",
        "powai",
        "lower parel",
        "goregaon",
        "malad",
        "worli",
        "kurla",
        "kanjurmarg",
        "dadar",
        "nariman point",
        "borivali",
        "chandivali",
        "vikhroli",
    ],
    "Navi Mumbai": [
        "navi mumbai",
        "mahape",
        "millennium business park",
        "mbp",
        "vashi",
        "airoli",
        "mindspace airoli",
        "ghansoli",
        "reliance corporate park",
        "rcp",
        "cbd belapur",
        "belapur",
        "nerul",
        "kopar khairane",
        "sanpada",
        "turbhe",
        "juinagar",
    ],
    "Thane": [
        "thane",
        "thane west",
        "wagle estate",
        "wagle industrial estate",
        "ghodbunder road",
        "ghodbunder",
        "majiwada",
        "kolshet",
        "kolshet road",
        "naupada",
    ],
}

# Flat set of all location tokens for quick verification
ALL_LOCATION_KEYWORDS: Set[str] = {
    keyword for hub_list in LOCATION_HUBS.values() for keyword in hub_list
}

# ==============================================================================
# Target Tech Roles (Strictly Technical)
# ==============================================================================
TARGET_TECH_ROLES: List[str] = [
    "Software Engineer",
    "Full Stack Developer",
    "Python Developer",
    "Java Developer",
    "Data Analyst",
    "Cloud/DevOps Engineer",
    "QA/Testing Engineer",
    "Backend Developer",
    "Frontend Developer",
]

# Role keywords for matching in job titles
ROLE_KEYWORDS: Dict[str, List[str]] = {
    "Software Engineer": [
        "software engineer",
        "software developer",
        "sde",
        "sde-1",
        "associate software engineer",
        "graduate software engineer",
        "trainee software engineer",
    ],
    "Full Stack Developer": [
        "full stack",
        "full-stack",
        "fullstack",
        "mean stack",
        "mern stack",
    ],
    "Python Developer": [
        "python developer",
        "python engineer",
        "backend python",
        "django developer",
        "fastapi developer",
    ],
    "Java Developer": [
        "java developer",
        "java engineer",
        "spring boot developer",
        "core java developer",
    ],
    "Data Analyst": [
        "data analyst",
        "junior data analyst",
        "business intelligence analyst",
        "bi analyst",
        "data engineer",
        "junior data engineer",
    ],
    "Cloud/DevOps Engineer": [
        "devops engineer",
        "cloud engineer",
        "aws engineer",
        "site reliability engineer",
        "sre",
        "cloud trainee",
    ],
    "QA/Testing Engineer": [
        "qa engineer",
        "quality assurance",
        "software tester",
        "automation tester",
        "test engineer",
        "qa analyst",
        "sdit",
    ],
    "Backend Developer": [
        "backend developer",
        "backend engineer",
        "node.js developer",
        "golang developer",
    ],
    "Frontend Developer": [
        "frontend developer",
        "front end developer",
        "react developer",
        "ui developer",
        "web developer",
    ],
}

# Roles/Keywords that are explicitly non-technical or disqualified
DISQUALIFIED_ROLES: List[str] = [
    "sales",
    "telecaller",
    "bpo",
    "kpo",
    "customer support",
    "recruiter",
    "hr executive",
    "marketing executive",
    "accountant",
    "business development",
    "bde",
    "data entry",
]

# ==============================================================================
# Strict Experience Constraints (0 - 1 Years Only)
# ==============================================================================
MAX_ALLOWED_EXPERIENCE_YEARS: float = 1.0

# Terms that strongly indicate fresher / entry level
FRESHER_TERMS: List[str] = [
    "fresher",
    "freshers",
    "entry level",
    "entry-level",
    "0 years",
    "0 year",
    "0-1 year",
    "0-1 years",
    "0 to 1 year",
    "0 to 1 years",
    "0 - 1 year",
    "0 - 1 years",
    "college graduate",
    "recent graduate",
    "new grad",
    "trainee",
    "intern",
    "internship",
    "junior",
    "jr.",
    "associate",
]

# Terms that strictly disqualify a role as requiring 2+ years of experience
DISQUALIFIED_EXPERIENCE_PATTERNS: List[str] = [
    r"\b([2-9]|\d{2,})\+?\s*(?:to|-)\s*\d*\+?\s*(?:years?|yrs?)\b",
    r"\b([2-9]|\d{2,})\s*\+\s*(?:years?|yrs?)\b",
    r"\b(?:at least|minimum|min)\s*([2-9]|\d{2,})\s*(?:years?|yrs?)\b",
    r"\b(?:senior|lead|principal|architect|staff|director|head of|vp)\b",
    r"\bmid[\s-]level\b",
]

# ==============================================================================
# Tech Stack Extraction Taxonomy
# ==============================================================================
TECH_TAXONOMY: Dict[str, str] = {
    # Languages
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c++": "C++",
    "c#": "C#",
    "golang": "Go",
    "go lang": "Go",
    "ruby": "Ruby",
    "php": "PHP",
    "kotlin": "Kotlin",
    "swift": "Swift",
    # Frontend
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "html": "HTML",
    "html5": "HTML5",
    "css": "CSS",
    "css3": "CSS3",
    "tailwind": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "redux": "Redux",
    # Backend & Frameworks
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "express.js": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    ".net": ".NET",
    "asp.net": "ASP.NET",
    # Databases
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "oracle": "Oracle",
    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "google cloud": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "linux": "Linux",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "ci/cd": "CI/CD",
    "jenkins": "Jenkins",
    "terraform": "Terraform",
    # Data & Analytics
    "pandas": "Pandas",
    "numpy": "NumPy",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "excel": "Excel",
    "scikit-learn": "Scikit-Learn",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    # QA & Testing
    "selenium": "Selenium",
    "pytest": "PyTest",
    "junit": "JUnit",
    "postman": "Postman",
    "cypress": "Cypress",
    "playwright": "Playwright",
    "manual testing": "Manual Testing",
    "automation testing": "Automation Testing",
    # APIs & Architectures
    "rest": "REST API",
    "rest api": "REST API",
    "restful": "REST API",
    "graphql": "GraphQL",
    "microservices": "Microservices",
}
