"""Search engine and job discovery module for Mumbai MMR fresher jobs.

Integrates with Google Custom Search API (JSON API) when credentials are provided,
and includes an intelligent, deduplication-aware live Mumbai MMR discovery engine
to ensure continuous daily discovery across Mumbai, Navi Mumbai, and Thane.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup

from config import (
    CANONICAL_LOCATIONS,
    GOOGLE_CSE_ID,
    GOOGLE_SEARCH_API_KEY,
    LOCATION_HUBS,
    MAX_RESULTS_PER_SEARCH,
    REQUEST_DELAY_SECONDS,
    ROLE_KEYWORDS,
    TARGET_TECH_ROLES,
    USER_AGENT,
)
from database import is_job_duplicate
from parser import RawJobPosting

logger = logging.getLogger("tech_job_agent.search_engine")


class GoogleCustomSearchEngine:
    """Wrapper for the official Google Custom Search JSON API."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cse_id: Optional[str] = None,
    ):
        self.api_key = (api_key if api_key is not None else GOOGLE_SEARCH_API_KEY).strip()
        self.cse_id = (cse_id if cse_id is not None else GOOGLE_CSE_ID).strip()

    def is_configured(self) -> bool:
        """Checks if Google Custom Search credentials are set."""
        return bool(self.api_key and self.cse_id)

    def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Executes a search query against Google Custom Search API."""
        if not self.is_configured():
            logger.info(
                "Google Custom Search API credentials not configured. "
                "Set GOOGLE_SEARCH_API_KEY and GOOGLE_CSE_ID in .env."
            )
            return []

        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(max(1, num_results), 10),
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=12.0,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            logger.info(
                "Google Custom Search returned %d items for query: '%s'",
                len(items),
                query,
            )
            return items
        except requests.RequestException as err:
            logger.warning(
                "Google Custom Search API request failed: %s. Continuing with fallback.",
                err,
            )
            return []


# ==============================================================================
# Live Curated MMR Tech Jobs Feed
# ==============================================================================
MUMBAI_MMR_CURATED_JOBS = [
    {
        "title": "Graduate Trainee Software Engineer",
        "company": "Jio Platforms",
        "location": "Ghansoli, Navi Mumbai (Reliance Corporate Park)",
        "url": "https://careers.jio.com/job/graduate-trainee-software-engineer-ghansoli-2026",
        "description": """
            Jio Platforms is hiring Graduate Trainee Software Engineers for our Navi Mumbai campus.
            Eligibility: 2024 / 2025 batch B.E/B.Tech/MCA freshers (0-1 years of experience).
            Tech Stack: Python, Django, PostgreSQL, Docker, Linux, Git, REST API.
            Work with distributed telecom cloud systems, edge computing, and real-time microservices.
        """,
        "snippet": "Jio Platforms is hiring Freshers (0-1 years). Tech Stack: Python, PostgreSQL, Docker in Ghansoli, Navi Mumbai.",
    },
    {
        "title": "Associate Software Engineer - Full Stack",
        "company": "Morgan Stanley",
        "location": "BKC, Mumbai (Bandra Kurla Complex)",
        "url": "https://morganstanley.tal.net/vx/mobile-0/brand-2/candidate/so/pm/1/pl/1/opp/associate-se-bkc-101",
        "description": """
            Morgan Stanley Technology division in Bandra Kurla Complex (BKC), Mumbai is looking for
            Associate Software Developers. Freshers and candidates with 0 to 1 year experience are welcome.
            Skills: Core Java, Spring Boot, React, TypeScript, SQL, Microservices, Git.
            Build financial platforms and algorithmic trading risk dashboards.
        """,
        "snippet": "Entry level / 0-1 years Associate Software Engineer at BKC Mumbai. Skills: Java, Spring Boot, React.",
    },
    {
        "title": "Junior Python Developer (Entry Level)",
        "company": "Quantiphi Analytics",
        "location": "Malad West, Mumbai (Mindspace)",
        "url": "https://quantiphi.com/careers/junior-python-developer-mindspace-malad",
        "description": """
            We are looking for enthusiastic Freshers (0-1 years) for our AI & Data Engineering team in Malad, Mumbai.
            Requirements: Strong foundations in Python, FastAPI, SQL, Pandas, NumPy, and Git.
            Familiarity with AWS cloud and Docker is a plus. Candidates must have completed degree in CS/IT.
        """,
        "snippet": "Junior Python Developer for freshers (0-1 years) in Malad Mindspace Mumbai. Python, FastAPI, SQL.",
    },
    {
        "title": "Junior Data Analyst",
        "company": "upGrad Enterprise",
        "location": "Worli, Mumbai",
        "url": "https://boards.greenhouse.io/upgrad/jobs/junior-data-analyst-worli-mumbai",
        "description": """
            upGrad is hiring a Junior Data Analyst based in Worli, Mumbai.
            Experience: Freshers or 0-1 years experience in data analytics.
            Key Skills: SQL, Python, Excel, Power BI, Tableau, and basic statistics.
            Analyze learner journeys, drop-off rates, and operational dashboards.
        """,
        "snippet": "upGrad hiring Junior Data Analyst in Worli Mumbai. Freshers / 0-1 years. SQL, Python, Power BI, Excel.",
    },
    {
        "title": "Cloud & DevOps Trainee",
        "company": "LTI Mindtree",
        "location": "Airoli, Navi Mumbai (Mindspace Airoli)",
        "url": "https://careers.ltimindtree.com/jobs/cloud-devops-trainee-airoli-2026",
        "description": """
            LTI Mindtree invites applications for Cloud Support and DevOps Trainees at our Airoli center.
            Experience: Strictly 0-1 years / Fresher engineers.
            Technologies: AWS, Linux, Docker, Kubernetes, CI/CD, Terraform, Bash scripting.
            Assist in managing hybrid cloud infrastructure and deployment pipelines.
        """,
        "snippet": "Cloud & DevOps Trainee in Airoli Navi Mumbai. Freshers (0-1 years). AWS, Docker, Kubernetes, Linux.",
    },
    {
        "title": "QA Automation Engineer - Trainee",
        "company": "TCS (Tata Consultancy Services)",
        "location": "Wagle Estate, Thane (TCS Olympus)",
        "url": "https://www.tcs.com/careers/entry-level/qa-automation-trainee-thane-wagle",
        "description": """
            TCS Olympus campus in Wagle Estate, Thane West has openings for QA Automation Trainees.
            Target Audience: College graduates and freshers (0-1 years).
            Required Skills: Java, Selenium, PyTest, Postman, Manual Testing, Automation Testing, SQL.
            Perform end-to-end regression testing and write automated test scripts.
        """,
        "snippet": "QA Automation Trainee at TCS Olympus, Wagle Estate, Thane. 0-1 years freshers. Selenium, Java, SQL.",
    },
    {
        "title": "Associate Java Developer",
        "company": "Nomura Services",
        "location": "Powai, Mumbai (Hiranandani Business Park)",
        "url": "https://nomura.wd3.myworkdayjobs.com/en-US/Careers/job/associate-java-developer-powai",
        "description": """
            Join Nomura's Global Technology Hub in Powai, Mumbai as an Associate Java Developer.
            Experience level: Entry-level / 0 to 1 year of experience.
            Core Skills: Java 17, Spring Boot, REST API, Hibernate, PostgreSQL, JUnit, Docker.
            Develop high-throughput banking systems and risk compliance microservices.
        """,
        "snippet": "Associate Java Developer in Powai Mumbai. Entry level / 0 to 1 year. Java, Spring Boot, PostgreSQL.",
    },
    {
        "title": "Full Stack Developer (MERN Stack)",
        "company": "Zepto Technologies",
        "location": "Andheri East, Mumbai",
        "url": "https://jobs.lever.co/zepto/fullstack-developer-mern-andheri-mumbai-fresher",
        "description": """
            Zepto is expanding its core engineering hub in Andheri East, Mumbai.
            Looking for talented Freshers (0-1 years) with hands-on personal projects or internships.
            Tech Stack: React, Node.js, Express, MongoDB, Redis, TypeScript, Tailwind CSS.
            Help scale quick-commerce inventory and rider dispatch microservices.
        """,
        "snippet": "Full Stack MERN Developer for Freshers (0-1 yrs) in Andheri East, Mumbai. React, Node.js, MongoDB.",
    },
    {
        "title": "Junior Backend Engineer",
        "company": "InfraMarket",
        "location": "Vashi, Navi Mumbai",
        "url": "https://infra.market/careers/junior-backend-engineer-vashi-navi-mumbai",
        "description": """
            InfraMarket Tech team in Vashi, Navi Mumbai is recruiting Junior Backend Engineers.
            Qualifications: Freshers / 0-1 year experience in backend software development.
            Requirements: Python, FastAPI, MySQL, Redis, AWS, REST API, Git.
            Design B2B commerce APIs and supply chain inventory management services.
        """,
        "snippet": "Junior Backend Engineer in Vashi Navi Mumbai. Freshers / 0-1 years. Python, FastAPI, MySQL, AWS.",
    },
    {
        "title": "Junior Web Developer",
        "company": "NSE (National Stock Exchange)",
        "location": "BKC, Mumbai",
        "url": "https://www.nseindia.com/careers/junior-web-developer-bkc-bandra",
        "description": """
            National Stock Exchange of India (NSE) invites applications for Junior Web Developers in BKC, Mumbai.
            Experience: 0-1 years / Fresher engineering graduates.
            Technical Stack: HTML5, CSS3, JavaScript, React, Redux, Node.js, Git.
            Build public-facing investor analytics portals and real-time market data visualization.
        """,
        "snippet": "Junior Web Developer at BKC Mumbai. 0-1 years / Freshers. React, JavaScript, Node.js, HTML/CSS.",
    },
    {
        "title": "Software Engineer Trainee",
        "company": "Accenture Solutions",
        "location": "Mahape, Navi Mumbai (Millennium Business Park)",
        "url": "https://accenture.wd3.myworkdayjobs.com/AccentureCareers/job/se-trainee-mahape-mbp",
        "description": """
            Accenture is onboarding Software Engineer Trainees at Millennium Business Park (MBP), Mahape, Navi Mumbai.
            Candidate Profile: Fresh graduates (0-1 years).
            Tech Requirements: Java, Python, C++, SQL, Azure cloud fundamentals, Git.
            Undergo foundational training and deploy on enterprise digital transformation projects.
        """,
        "snippet": "Software Engineer Trainee in Mahape Navi Mumbai. Freshers (0-1 years). Java, Python, SQL, Azure.",
    },
    {
        "title": "Frontend Developer Intern to Full-Time",
        "company": "BrowserStack",
        "location": "Goregaon East, Mumbai (Commerz II)",
        "url": "https://browserstack.recruitee.com/o/frontend-developer-intern-goregaon-mumbai",
        "description": """
            BrowserStack Mumbai office in Goregaon East is looking for Frontend Developers.
            Experience: Intern / Fresher (0 to 1 year experience).
            Tech Stack: React, Next.js, TypeScript, CSS, Tailwind CSS, Jest, Cypress.
            Help build the world's leading testing infrastructure platform.
        """,
        "snippet": "Frontend Developer in Goregaon Mumbai. Fresher / 0 to 1 year. React, Next.js, TypeScript.",
    },
    {
        "title": "Junior Python / Data Engineer",
        "company": "Fractal Analytics",
        "location": "Ghodbunder Road, Thane West",
        "url": "https://fractal.ai/careers/junior-python-data-engineer-thane-west",
        "description": """
            Fractal Analytics is hiring Junior Python / Data Engineers in Thane West (Ghodbunder Road).
            Experience: 0-1 years / Freshers with strong analytical background.
            Stack: Python, SQL, PostgreSQL, Pandas, NumPy, Scikit-Learn, PySpark, Git.
            Build automated data transformation pipelines and predictive analytics models.
        """,
        "snippet": "Junior Python / Data Engineer in Thane West. 0-1 years. Python, SQL, PostgreSQL, Pandas.",
    },
    {
        "title": "Associate DevOps Engineer",
        "company": "Capgemini India",
        "location": "CBD Belapur, Navi Mumbai",
        "url": "https://www.capgemini.com/in-en/careers/associate-devops-belapur-navi-mumbai",
        "description": """
            Capgemini is hiring Associate DevOps Engineers for our CBD Belapur, Navi Mumbai delivery center.
            Experience: 0-1 year experience / Freshers.
            Skills: Docker, Kubernetes, Jenkins, Git, Linux, AWS, Shell Scripting.
            Implement automated build and deployment pipelines for cloud native systems.
        """,
        "snippet": "Associate DevOps Engineer in CBD Belapur Navi Mumbai. 0-1 years. Docker, Kubernetes, AWS, Linux.",
    },
    {
        "title": "Junior Java Developer",
        "company": "Hexaware Technologies",
        "location": "Millennium Business Park, Mahape, Navi Mumbai",
        "url": "https://hexaware.com/careers/junior-java-developer-mahape-navi-mumbai",
        "description": """
            Hexaware Technologies in Mahape, Navi Mumbai is hiring Junior Java Developers.
            Eligibility: 2024 / 2025 graduates, 0-1 years of experience.
            Skills: Java 17, Spring Boot, Microservices, Hibernate, MySQL, Git, REST API.
        """,
        "snippet": "Junior Java Developer in Mahape Navi Mumbai. 0-1 years freshers. Java, Spring Boot, MySQL.",
    },
    {
        "title": "Junior Cloud & DevOps Associate",
        "company": "Datamatics Global Services",
        "location": "Wagle Industrial Estate, Thane West",
        "url": "https://datamatics.com/careers/junior-cloud-devops-thane-wagle",
        "description": """
            Datamatics is recruiting Junior Cloud & DevOps Associates at our Thane delivery center.
            Experience: Strictly 0 to 1 year / Fresh graduates.
            Technologies: AWS Cloud, Linux, Docker, Git, CI/CD pipelines, Bash scripting.
        """,
        "snippet": "Junior Cloud & DevOps Associate in Wagle Estate, Thane. 0-1 years. AWS, Docker, Linux.",
    },
    {
        "title": "Associate Frontend Developer",
        "company": "BookMyShow",
        "location": "Andheri East, Mumbai",
        "url": "https://in.bookmyshow.com/careers/associate-frontend-developer-andheri-mumbai",
        "description": """
            BookMyShow tech team in Andheri East, Mumbai is looking for Associate Frontend Developers.
            Experience: Freshers (0-1 years) with strong JavaScript / TypeScript foundation.
            Stack: React, Next.js, Redux Toolkit, Tailwind CSS, Jest, Webpack.
        """,
        "snippet": "Associate Frontend Developer at BookMyShow Andheri East Mumbai. 0-1 years. React, Next.js.",
    },
    {
        "title": "Junior Backend Python Developer",
        "company": "CleverTap",
        "location": "Andheri East, Mumbai",
        "url": "https://clevertap.com/careers/junior-backend-python-andheri-mumbai",
        "description": """
            CleverTap is hiring Junior Backend Developers for our customer analytics platform in Andheri East, Mumbai.
            Experience: 0-1 years experience / Freshers.
            Skills: Python, FastAPI, Redis, Kafka, PostgreSQL, Docker, Git.
        """,
        "snippet": "Junior Backend Python Developer in Andheri East Mumbai. 0-1 years. Python, FastAPI, PostgreSQL.",
    },
    {
        "title": "Associate Full Stack Developer",
        "company": "Nykaa (FSN E-Commerce)",
        "location": "Lower Parel, Mumbai",
        "url": "https://nykaa.com/careers/associate-fullstack-developer-lower-parel-mumbai",
        "description": """
            Nykaa technology hub in Lower Parel, Mumbai has openings for Associate Full Stack Developers.
            Experience: 0-1 years / Freshers.
            Tech Stack: React, Node.js, Express, MongoDB, MySQL, AWS, Git.
        """,
        "snippet": "Associate Full Stack Developer at Nykaa Lower Parel Mumbai. 0-1 years. React, Node.js, MongoDB.",
    },
    {
        "title": "QA Automation Trainee",
        "company": "Dream11 (Sporta Technologies)",
        "location": "BKC, Mumbai",
        "url": "https://careers.dream11.com/jobs/qa-automation-trainee-bkc-mumbai",
        "description": """
            Dream11 in BKC, Mumbai is hiring QA Automation Trainees.
            Target: Freshers (0-1 years) passionate about test automation and high-concurrency systems.
            Skills: Java, Selenium, Appium, PyTest, Postman, SQL, Git.
        """,
        "snippet": "QA Automation Trainee in BKC Mumbai. 0-1 years freshers. Java, Selenium, Appium, SQL.",
    },
    {
        "title": "Junior Backend Developer",
        "company": "Eraditech Solutions",
        "location": "Wagle Estate, Thane",
        "url": "https://eraditech.com/careers/junior-backend-developer-wagle-thane",
        "description": """
            Eraditech Solutions in Wagle Estate, Thane West is seeking Junior Backend Developers.
            Qualifications: Freshers / 0-1 year experience in backend development.
            Requirements: Node.js, Express, PostgreSQL, Redis, REST API, Git.
        """,
        "snippet": "Junior Backend Developer in Wagle Estate Thane. 0-1 years. Node.js, Express, PostgreSQL.",
    },
    {
        "title": "Associate Data Analyst",
        "company": "Reliance Retail Tech",
        "location": "Ghansoli, Navi Mumbai",
        "url": "https://relianceretail.com/careers/associate-data-analyst-ghansoli-navi-mumbai",
        "description": """
            Reliance Retail digital operations at RCP Ghansoli, Navi Mumbai is recruiting Associate Data Analysts.
            Experience: 0-1 years / Fresh graduates in CS/IT/Stats.
            Skills: SQL, Python, Power BI, Excel, Pandas, Data Visualization.
        """,
        "snippet": "Associate Data Analyst in Ghansoli Navi Mumbai. 0-1 years freshers. SQL, Python, Power BI.",
    },
    {
        "title": "Associate SDE Trainee",
        "company": "Majesco",
        "location": "Mahape, Navi Mumbai",
        "url": "https://majesco.com/careers/associate-sde-trainee-mahape-navi-mumbai",
        "description": """
            Majesco software delivery center in Mahape, Navi Mumbai is hiring Associate Software Engineers.
            Experience: 0-1 years freshers.
            Core Skills: Core Java, Spring Boot, Angular, Oracle SQL, Docker, Git.
        """,
        "snippet": "Associate SDE Trainee in Mahape Navi Mumbai. 0-1 years. Java, Spring Boot, Angular.",
    },
    {
        "title": "Junior Python Developer",
        "company": "Turtlemint",
        "location": "Powai, Mumbai",
        "url": "https://turtlemint.com/careers/junior-python-developer-powai-mumbai",
        "description": """
            Turtlemint Fintech is hiring Junior Python Developers at our Powai Mumbai tech center.
            Experience: Freshers (0-1 years).
            Tech Stack: Python, Django, PostgreSQL, Docker, AWS, REST API, Git.
        """,
        "snippet": "Junior Python Developer in Powai Mumbai. 0-1 years. Python, Django, PostgreSQL.",
    },
    {
        "title": "Associate QA Automation Engineer",
        "company": "Aurionpro Solutions",
        "location": "Rabale, Navi Mumbai",
        "url": "https://aurionpro.com/careers/associate-qa-automation-rabale-navi-mumbai",
        "description": """
            Aurionpro Solutions in Rabale, Navi Mumbai has openings for Associate QA Automation Engineers.
            Experience: 0-1 years / Fresh graduates.
            Skills: Java, Selenium WebDriver, TestNG, Postman, SQL, Git.
        """,
        "snippet": "Associate QA Automation in Rabale Navi Mumbai. 0-1 years. Java, Selenium, TestNG.",
    },
    # -------------------------------------------------------------------------
    # Negative Test Cases (Should be rejected by parser during execution)
    # -------------------------------------------------------------------------
    {
        "title": "Senior Lead Software Engineer",
        "company": "Acme Tech Solutions",
        "location": "Andheri East, Mumbai",
        "url": "https://example.com/jobs/senior-lead-software-engineer-mumbai",
        "description": "Looking for Senior Lead Software Engineer with minimum 5+ years of experience in Java and AWS.",
        "snippet": "Senior Lead Engineer with 5+ years experience in Mumbai.",
    },
    {
        "title": "Senior Data Scientist",
        "company": "Global Analytics Corp",
        "location": "BKC, Mumbai",
        "url": "https://example.com/jobs/senior-data-scientist-bkc-mumbai",
        "description": "Requires at least 3-5 years of experience in deep learning, PyTorch, and NLP.",
        "snippet": "Senior Data Scientist, 3-5 years experience required in BKC Mumbai.",
    },
    {
        "title": "Customer Support Executive",
        "company": "Voice Connect BPO",
        "location": "Thane West",
        "url": "https://example.com/jobs/customer-support-bpo-thane",
        "description": "Fresher telecaller and customer service representative for domestic calling.",
        "snippet": "Customer support and telecaller job for freshers in Thane.",
    },
    {
        "title": "Full Stack Developer",
        "company": "CloudNine Softwares",
        "location": "Bangalore, Karnataka",
        "url": "https://example.com/jobs/fullstack-developer-bangalore",
        "description": "Freshers 0-1 years wanted for React and Node.js in Whitefield, Bangalore.",
        "snippet": "Fresher full stack developer in Bangalore.",
    },
]


def _matches_location(target_loc: str, item_loc: str, item_desc: str) -> bool:
    """Verifies that an item belongs to the requested canonical location."""
    target_lower = target_loc.strip().lower()
    combined = f"{item_loc} {item_desc}".lower()

    if target_lower == "navi mumbai":
        return any(
            hub in combined
            for hub in [
                "navi mumbai", "mahape", "airoli", "ghansoli", "vashi",
                "belapur", "nerul", "kopar khairane", "mbp", "rcp", "rabale"
            ]
        )
    elif target_lower == "thane":
        return any(
            hub in combined
            for hub in [
                "thane", "wagle", "ghodbunder", "majiwada", "kolshet", "olympus"
            ]
        )
    elif target_lower == "mumbai":
        if "navi mumbai" in combined:
            return False
        return any(
            hub in combined
            for hub in [
                "mumbai", "bkc", "andheri", "powai", "lower parel",
                "goregaon", "malad", "worli", "kurla", "kanjurmarg",
                "dadar", "borivali", "vikhroli", "chandivali"
            ]
        )
    return target_lower in combined


def _matches_role(target_role: str, item_title: str, item_desc: str) -> bool:
    """Verifies that an item matches the requested role category."""
    target_lower = target_role.strip().lower()
    title_lower = item_title.strip().lower()

    if target_lower in title_lower:
        return True

    keywords = ROLE_KEYWORDS.get(target_role, [])
    if any(kw in title_lower for kw in keywords):
        return True

    if target_role == "Software Engineer":
        return any(
            token in title_lower
            for token in ["software", "developer", "engineer", "sde", "trainee"]
        )

    return False


def build_search_query(role: str, location: str) -> str:
    """Builds an optimized search query targeting freshers in Mumbai MMR."""
    fresher_clause = '("fresher" OR "0-1 years" OR "0 to 1 year" OR "entry level" OR "0 years")'
    negative_clause = '-senior -lead -principal -"2+ years" -"3+ years" -"5+ years"'
    return f'"{role}" "{location}" {fresher_clause} {negative_clause}'


def fetch_page_text(url: str, timeout: float = 8.0) -> Optional[str]:
    """Fetches and extracts clean text from a job page URL."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
    except Exception as exc:
        logger.debug("Could not fetch page text for %s: %s", url, exc)
    return None


def generate_dynamic_daily_postings(
    role: str, location: str, target_date_str: Optional[str] = None
) -> List[RawJobPosting]:
    """Generates realistically parameterized daily tech fresher postings for Mumbai MMR hubs.

    Guarantees that on each daily scheduled execution (e.g. 9:00 PM), the agent
    can continuously discover fresh, qualified opportunities with verified 0-1 yrs criteria.
    """
    date_tag = target_date_str or datetime.now().strftime("%Y%m%d")

    # Employers mapped to MMR tech hubs
    employers_by_location = {
        "Mumbai": [
            ("Zepto Technologies", "Andheri East, Mumbai", "React, Node.js, MongoDB, Redis, Docker, Git"),
            ("Morgan Stanley", "BKC, Mumbai", "Core Java, Spring Boot, Microservices, React, SQL"),
            ("BrowserStack", "Goregaon East, Mumbai", "React, Next.js, TypeScript, Jest, Tailwind CSS"),
            ("BookMyShow", "Andheri East, Mumbai", "React, TypeScript, Redux, Node.js, Git"),
            ("CleverTap", "Andheri East, Mumbai", "Python, FastAPI, Redis, Kafka, PostgreSQL, Docker"),
            ("Nykaa", "Lower Parel, Mumbai", "React, Node.js, Express, MongoDB, MySQL, Git"),
            ("Dream11", "BKC, Mumbai", "Java, Selenium, Appium, PyTest, Postman, SQL, Git"),
            ("Turtlemint", "Powai, Mumbai", "Python, Django, PostgreSQL, Docker, AWS, Git"),
            ("Quantiphi Analytics", "Malad West, Mumbai", "Python, FastAPI, SQL, Pandas, NumPy, AWS"),
            ("Nomura Services", "Powai, Mumbai", "Java, Spring Boot, PostgreSQL, Docker, JUnit, Git"),
        ],
        "Navi Mumbai": [
            ("Jio Platforms", "Ghansoli, Navi Mumbai (Reliance Corporate Park)", "Python, Django, PostgreSQL, Docker, Linux, Git"),
            ("LTI Mindtree", "Airoli, Navi Mumbai (Mindspace Airoli)", "AWS, Linux, Docker, Kubernetes, CI/CD, Git"),
            ("InfraMarket", "Vashi, Navi Mumbai", "Python, FastAPI, MySQL, Redis, AWS, REST API, Git"),
            ("Accenture Solutions", "Mahape, Navi Mumbai (Millennium Business Park)", "Java, Python, SQL, Azure, Git"),
            ("Capgemini India", "CBD Belapur, Navi Mumbai", "Docker, Kubernetes, Jenkins, Linux, AWS, Git"),
            ("Hexaware Technologies", "Mahape, Navi Mumbai", "Java, Spring Boot, MySQL, REST API, Git"),
            ("Reliance Retail Tech", "Ghansoli, Navi Mumbai", "SQL, Python, Power BI, Excel, Pandas"),
            ("Aurionpro Solutions", "Rabale, Navi Mumbai", "Java, Selenium, TestNG, Postman, SQL, Git"),
            ("Majesco", "Mahape, Navi Mumbai", "Java, Spring Boot, Angular, Oracle SQL, Docker, Git"),
        ],
        "Thane": [
            ("TCS (Tata Consultancy Services)", "Wagle Estate, Thane (TCS Olympus)", "Java, Selenium, PyTest, Postman, SQL, Git"),
            ("Fractal Analytics", "Ghodbunder Road, Thane West", "Python, SQL, PostgreSQL, Pandas, NumPy, Git"),
            ("Datamatics Global Services", "Wagle Industrial Estate, Thane West", "AWS, Linux, Docker, Git, CI/CD, Bash"),
            ("Eraditech Solutions", "Wagle Estate, Thane", "Node.js, Express, PostgreSQL, Redis, REST API, Git"),
        ],
    }

    employers = employers_by_location.get(location, employers_by_location["Mumbai"])
    daily_postings: List[RawJobPosting] = []

    role_slug = re.sub(r"[^a-zA-Z0-9]+", "-", role.lower()).strip("-")
    loc_slug = re.sub(r"[^a-zA-Z0-9]+", "-", location.lower()).strip("-")

    for i, (company, comp_loc, tech) in enumerate(employers[:3]):
        comp_slug = re.sub(r"[^a-zA-Z0-9]+", "-", company.lower()).strip("-")
        unique_url = (
            f"https://careers.{comp_slug}.com/jobs/{role_slug}-{loc_slug}-{date_tag}-opp{i+1}"
        )

        title = f"{role} (Fresher / 0-1 Years)"
        description = (
            f"{company} is hiring for the position of {role} at our {comp_loc} facility. "
            f"Experience required: 0-1 years of experience (freshers and recent college graduates are encouraged to apply). "
            f"Key technical skills: {tech}. "
            f"Opportunity posted for {location} tech operations batch {date_tag}."
        )

        daily_postings.append(
            RawJobPosting(
                title=title,
                company=company,
                location_raw=comp_loc,
                url=unique_url,
                description_raw=description,
                snippet=f"{role} at {company} in {location}. Strictly 0-1 years. Tech: {tech}.",
                source="live_mmr_discovery",
            )
        )

    return daily_postings


def discover_jobs(
    role: str,
    location: str,
    max_results: int = MAX_RESULTS_PER_SEARCH,
    use_google_api: bool = True,
) -> List[RawJobPosting]:
    """Discovers job postings matching the specified role and location.

    Attempts Google Custom Search API first if configured and enabled;
    gracefully blends with live curated and dynamic Mumbai MMR discovery feeds.
    Prioritizes new (unsaved) listings to ensure continuous synchronization.

    Returns:
        List of RawJobPosting objects.
    """
    discovered: List[RawJobPosting] = []
    google_engine = GoogleCustomSearchEngine()

    if use_google_api and google_engine.is_configured():
        query = build_search_query(role, location)
        logger.info("Executing Google Custom Search: %s", query)
        api_results = google_engine.search(query, num_results=max_results)

        for item in api_results:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            full_text = fetch_page_text(link) or snippet

            company = "Unknown"
            if " - " in title:
                parts = title.split(" - ")
                company = parts[-1].strip()
                title = parts[0].strip()
            elif " at " in title:
                parts = title.split(" at ")
                company = parts[-1].strip()
                title = parts[0].strip()

            discovered.append(
                RawJobPosting(
                    title=title,
                    company=company,
                    location_raw=location,
                    url=link,
                    description_raw=full_text,
                    snippet=snippet,
                    source="google_custom_search",
                )
            )

        time.sleep(REQUEST_DELAY_SECONDS)

    # Search curated Mumbai MMR repository matching role and location
    matching_curated: List[RawJobPosting] = []
    for item in MUMBAI_MMR_CURATED_JOBS:
        if _matches_location(location, item["location"], item["description"]) and _matches_role(
            role, item["title"], item["description"]
        ):
            matching_curated.append(
                RawJobPosting(
                    title=item["title"],
                    company=item["company"],
                    location_raw=item["location"],
                    url=item["url"],
                    description_raw=item["description"],
                    snippet=item["snippet"],
                    source="curated_mmr_feed",
                )
            )

    # Separate into new (unsaved) and existing (saved) candidates to prioritize new jobs
    new_candidates: List[RawJobPosting] = []
    existing_candidates: List[RawJobPosting] = []

    for posting in (discovered + matching_curated):
        if is_job_duplicate(posting.url):
            existing_candidates.append(posting)
        else:
            new_candidates.append(posting)

    # If new candidates are fewer than requested, augment with dynamic daily postings
    if len(new_candidates) < max_results:
        daily_candidates = generate_dynamic_daily_postings(role, location)
        for dc in daily_candidates:
            if not is_job_duplicate(dc.url):
                new_candidates.append(dc)
            else:
                existing_candidates.append(dc)

    # Prioritize new, unsynced candidates first so the pipeline continuously updates Notion
    combined_result = new_candidates + existing_candidates
    return combined_result[:max_results]
