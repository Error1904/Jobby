# Autonomous Tech Fresher Job Pipeline (Mumbai MMR)

An autonomous, production-grade Python pipeline that scrapes, filters, parses, deduplicates, and synchronizes entry-level technical job openings (strictly 0–1 years of experience) across **Mumbai**, **Navi Mumbai**, and **Thane**. New opportunities are persisted to a local **SQLite database** and synced in real-time to a connected **Notion Database**.

---

## 📁 Directory Structure

```text
/tech_job_agent
├── config.py             # Configuration settings, API keys, MMR locations, and tech stack taxonomy
├── database.py           # SQLite schema, deduplication via UNIQUE URL index, and queries
├── notion_sync.py        # Official Notion SDK client integration to create database pages
├── parser.py             # Regex & rule-based parser enforcing strict 0-1 yr filter and tech extraction
├── search_engine.py      # Google Custom Search API wrapper + live Mumbai MMR discovery feed
├── agent.py              # Main orchestrator pipeline linking discovery, filtering, DB, and Notion
├── test_pipeline.py      # Automated test suite validating parser, SQLite deduplication, and Notion
├── requirements.txt      # Required PyPI packages: requests, pydantic, beautifulsoup4, notion-client
├── .env.example          # Environment variables template
└── README.md             # Documentation and execution guide
```

---

## 🎯 Target Scope & Filtering Rules

### 1. Geographic Coverage (Mumbai Metropolitan Region - MMR)
* **Mumbai**: BKC (Bandra Kurla Complex), Andheri (East/West), Powai (Hiranandani), Lower Parel, Goregaon, Malad (Mindspace), Worli, Kurla, Dadar, Borivali.
* **Navi Mumbai**: Mahape (Millennium Business Park), Vashi, Airoli (Mindspace), Ghansoli (Reliance Corporate Park), CBD Belapur, Nerul, Kopar Khairane.
* **Thane**: Wagle Industrial Estate (TCS Olympus), Ghodbunder Road, Thane West, Majiwada, Kolshet Road.

### 2. Technical Roles Only
* Software Engineer / Graduate Trainee / Associate SDE
* Full Stack Developer (MERN, MEAN, Python/React, Java/Angular)
* Python Developer / Django / FastAPI Backend
* Java Developer / Spring Boot Microservices
* Data Analyst / Junior Data Engineer / BI Analyst
* Cloud / DevOps Engineer (AWS, Azure, Docker, Kubernetes)
* QA / Automation Testing Engineer (Selenium, PyTest, Postman)

### 3. Strict Experience Constraint (0–1 Years / Freshers Only)
* **Accepted**: Freshers, Entry-Level, Graduate Trainee, 0-1 years, 0 to 1 year, 0 years, intern-to-hire, up to 12 months.
* **Strictly Disqualified**: Any role requiring **2+ years** of experience (e.g., `2+ years`, `3-5 years`, `min 2 years`, `at least 2 years`, `senior`, `lead`, `architect`).

### 4. Tech Stack Extraction
Automatically identifies languages, libraries, frameworks, databases, and DevOps tools using boundary regexes (Python, Java, React, Node.js, SQL, AWS, Docker, FastAPI, Django, PostgreSQL, MongoDB, TypeScript, Next.js, etc.).

---

## 🗄️ SQLite Storage & Deduplication

* **Database File**: `mumbai_tech_jobs.db`
* **Table**: `tech_jobs`
* **Deduplication Strategy**: Enforces a `UNIQUE` constraint and index on `website_url`. Any repeated postings discovered across search iterations are skipped instantly without redundant network calls or DB mutations.

```sql
CREATE TABLE tech_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    location TEXT NOT NULL,
    website_url TEXT UNIQUE NOT NULL,
    experience_required TEXT NOT NULL,
    tech_stack TEXT NOT NULL,          -- JSON serialized list of tags
    description_summary TEXT NOT NULL,
    role_category TEXT,
    notion_synced INTEGER DEFAULT 0,    -- 0=Pending, 1=Synced
    notion_page_id TEXT,
    created_at TEXT NOT NULL
);
```

---

## 📝 Notion Database Configuration

To enable live Notion sync, set up a Notion database with the following property names and types:

| Notion Property Name | Notion Property Type | Description |
| :--- | :--- | :--- |
| **`Job Title`** | **Title** | The job title |
| **`Company`** | **Rich Text** | Hiring company name |
| **`Location`** | **Select** | Canonical hub (`Mumbai`, `Navi Mumbai`, `Thane`) |
| **`Apply Link`** | **URL** | Direct URL to job posting |
| **`Tech Stack`** | **Multi-select** | Extracted tech stack tags |
| **`Experience`** | **Rich Text** | Detected experience requirement string |

> **Note**: The pipeline includes fail-safe error handling. If `NOTION_API_KEY` or `NOTION_DATABASE_ID` are not configured, the agent logs an informative notice and runs smoothly in **Local SQLite Persistence Mode**.

---

## 🚀 Setup & Execution Guide

### 1. Create Virtual Environment and Install Dependencies

```bash
# Windows
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your keys (optional for local SQLite testing):

```bash
copy .env.example .env
```

```env
NOTION_API_KEY=ntn_your_notion_api_key_here
NOTION_DATABASE_ID=your_32_char_database_id_here
GOOGLE_SEARCH_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here
```

### 3. Run Pipeline Orchestrator

```bash
# Full execution across Mumbai, Navi Mumbai, and Thane
python agent.py

# Custom role or location execution
python agent.py --roles "Software Engineer,Python Developer" --locations "Mumbai,Navi Mumbai"

# View stored jobs and analytics in SQLite
python agent.py --stats

# Sync previously stored unsynced jobs to Notion
python agent.py --sync-unsynced
```

---

## ⏰ Daily 9:00 PM Automation & Notion Sync

The pipeline supports two methods to run automatically everyday at **9:00 PM (21:00)** and sync to Notion:

### Option A: Windows Task Scheduler, Startup Auto-Run & Desktop Shortcuts (Recommended)
Runs completely in the background without needing a terminal open, and includes desktop shortcuts for when your laptop was off at 9:00 PM:

```powershell
# 1. Setup 9:00 PM daily task + Windows Startup auto-run + Desktop shortcuts
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action all

# 2. Check scheduled task, startup, and desktop shortcuts status
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action status

# 3. Create or recreate Desktop shortcuts only
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action shortcut

# 4. Enable or disable startup auto-run only
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action enable-startup
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action disable-startup

# 5. Manually trigger a test run immediately
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action run

# 6. Remove scheduled task and shortcuts if needed
powershell.exe -ExecutionPolicy Bypass -File "setup_windows_scheduler.ps1" -Action remove
```

Alternatively, use the batch file:
```cmd
setup_windows_scheduler.bat                 :: Register 9:00 PM task + Startup + Desktop Shortcuts
setup_windows_scheduler.bat shortcut        :: Create Desktop shortcuts only
setup_windows_scheduler.bat status          :: Check status of scheduler, startup, and shortcuts
setup_windows_scheduler.bat enable-startup  :: Enable startup run only
setup_windows_scheduler.bat disable-startup :: Disable startup run only
setup_windows_scheduler.bat run             :: Trigger immediately
setup_windows_scheduler.bat remove          :: Remove 9:00 PM scheduled task
```

#### 🖥️ Desktop Catch-Up Shortcuts
If your laptop was shut down or in sleep mode when you were not home at 9:00 PM, two shortcuts are available directly on your Desktop:
- **`Run Tech Job Agent`**: Double-click to run with live terminal output, colorized progress, and execution summary. Pauses on finish so you can see how many jobs were found.
- **`Run Tech Job Agent (Silent)`**: Runs silently in the background with zero pop-up windows, automatically logging to `agent_execution.log`.

### Option B: Standalone Python Daemon Scheduler
If running in a terminal, background worker, or server:

```bash
# Run standalone scheduler waiting until 9:00 PM every day
python scheduler.py --time 21:00

# Run once immediately, then enter the 9:00 PM daily schedule
python scheduler.py --time 21:00 --now

# Or directly through agent orchestrator
python agent.py --schedule 21:00
```

---

## 🔄 Notion Live Sync Checklist

To ensure rows are created in your Notion database at 9:00 PM:

1. Create a Notion integration token at [notion.so/my-integrations](https://www.notion.so/my-integrations).
2. Open your target Notion Database, click **... (top right)** -> **Connections** -> **Connect to**, and select your integration name.
3. Copy your database ID from the Notion URL (`https://www.notion.so/<workspace>/<database_id>?v=...`).
4. Add credentials to `tech_job_agent\.env`:
   ```env
   NOTION_API_KEY=ntn_xxxxxxxxxxxxxxxxxxxxxxxx
   NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. When the 9:00 PM trigger fires, the pipeline automatically parses fresh jobs and creates rows in Notion. To sync any previously collected offline jobs immediately, run:
   ```bash
   python agent.py --sync-unsynced
   ```

---

### 5. Automated Validation Test Suite

```bash
python test_pipeline.py
```

