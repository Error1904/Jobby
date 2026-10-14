# Jobby - Autonomous Tech Job Discovery & Sync Agent

An autonomous Python agent that continuously discovers, parses, filters, and synchronizes fresher tech job opportunities (0–1 years experience) across Mumbai, Navi Mumbai, and Thane directly to Notion and SQLite.

## ✨ Features
- **Strict Fresher Filtering (0–1 Years):** Automatically filters out senior roles (rejects 2+ years) and extracts relevant tech stacks.
- **Geographic Focus:** Mumbai Metropolitan Region (BKC, Andheri, Powai, Airoli, Vashi, Thane Wagle Estate, etc.).
- **Dual Persistence:** SQLite database storage with strict URL deduplication + live sync to Notion Database.
- **Autonomous Execution:**
  - **Daily Schedule:** Automatically runs at 9:00 PM via Windows Task Scheduler.
  - **Startup Auto-Run:** Automatically runs silently in the background whenever Windows starts up.
- **Complete Logging:** Timestamped logging in `agent_execution.log`.

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Error1904/Jobby.git
cd Jobby

# Set up virtual environment
python -m venv .venv
.venv\Scripts\pip install -r tech_job_agent\requirements.txt
```

### 2. Configure Environment
Copy `.env.example` in `tech_job_agent`:
```bash
copy tech_job_agent\.env.example tech_job_agent\.env
```
Fill in your `NOTION_API_KEY` and `NOTION_DATABASE_ID`.

### 3. Run Manually
```bash
cd tech_job_agent
python agent.py
```

### 4. Setup Windows Automation (9 PM Daily + Startup)
```cmd
cd tech_job_agent
setup_windows_scheduler.bat
```

For full details, configuration options, and architecture, see [tech_job_agent/README.md](tech_job_agent/README.md).
