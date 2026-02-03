# AI Agent Context File (AGENT.md)

## Project Overview: TrioAgent (DevRunAuto)
This project is an advanced **Hybrid AI Agent System** capable of performing real-world actions on an Android device (via `DroidRun`/`MobileRun`) triggered by natural language commands from WhatsApp (via `OpenClaw`).

### Core Philosophy
- **The Brain (Router)**: OpenClaw (formerly Moltbot) runs on the PC, listens to messaging channels (WhatsApp), and routes "Android Actions" to the local bridge.
- **The Bridge**: A Python script (`bridge.py`) that translates OpenClaw commands into TrioAgent tasks.
- **The Muscle (Executor)**: TrioAgent (built on DroidRun Framework) executes ADB commands on the connected Android device to interact with apps like Uber, Zomato, Amazon, etc.

---

## System Architecture

### 1. Integration Layer (OpenClaw)
- **Role**: Interface between User (WhatsApp) and System.
- **Location**: `~/.openclaw` (PC User Directory).
- **Key Files**:
    - `skills/trio_agent/SKILL.md`: Instructs OpenClaw when to use the tool.
    - `skills/trio_agent/tool.json`: Maps the tool to the `bridge.py` script.
    - `skills/trio_agent/bridge.py`: The entry point script that imports `AgentFactory`.

### 2. Execution Layer (TrioAgent Codebase)
- **Repo Root**: `devrunauto/`
- **Key Components**:
    - `agents/agent_factory.py`: The main entry point for running tasks. It intelligently selects between **MobileRun (Cloud)** (if available via `mobile-use`) or **DroidRun (Local)**.
    - `agents/mobile_run_wrapper.py`: Wrapper for Cloud/Local fallback logic.
    - `agents/commerce_agent.py`, `ride_comparison_agent.py`: Specialized domain agents.
    - `.env`: Contains API Keys (`GEMINI_API_KEY`, `MOBILERUN_API_KEY`) and Configuration (`USE_MOBILE_RUN`).

### 3. Device Layer
- **Local**: Android Phone connected via USB (Debugging ON).
- **Cloud**: Pixel 8 Pro instances via MobileRun API (if configured).

---

## Deployment & Setup Guide

### prerequisites
1.  **Python 3.10+** (Added to PATH).
2.  **Node.js 22+** (For OpenClaw).
3.  **Android SDK Platform-Tools** (ADB) in PATH.
4.  Physical Android Device (Developer Mode -> USB Debugging).

### Installation
```bash
# 1. Install Dependencies
pip install -r requirements.txt
pip install mobile-use  # For MobileRun Cloud support

# 2. Install OpenClaw (The interface)
powershell -Command "iwr -useb https://molt.bot/install.ps1 | iex"
openclaw onboard # Follow wizard to link WhatsApp
```

### Configuration
1.  **Environment Variables (`.env`)**:
    ```ini
    GOOGLE_API_KEY=AIza...
    MOBILERUN_API_KEY=dr_sk_...
    USE_MOBILE_RUN=True # Set True for Cloud, False for Local USB
    ```
2.  **OpenClaw Skill**:
    Ensure the `trio_agent` skill exists in `~/.openclaw/skills/`. If not, copy from backup or recreate.

---

## Current Implementation Status
- [x] **Hybrid Integration**: OpenClaw -> Bridge -> DroidRun/MobileRun works.
- [x] **Package Fix**: specific `mobile-use` python package is used instead of `mobilerun`.
- [x] **Fallback Logic**: System auto-falls back to Local USB if MobileRun key/package is missing.
- [x] **Reasoning Disabled**: Reasoning feature in DroidRun config is explicitly set to `False` for speed/compatibility.

## Troubleshooting Context
- **"Connection Refused" on OpenClaw**: usually means `openclaw gateway` service is down. Run `openclaw gateway --restart`.
- **"MobileRunClient not found"**: Ensure `pip install mobile-use` was successful. The code handles import errors gracefully.
- **Blank Screen on Website**: Hard refresh (Ctrl+F5) usually fixes it; caused by caching of old Moltbot UI assets vs new OpenClaw assets.
