# AI Agent Context File (AGENT.md)

## Project Overview: TrioAgent (DevRunAuto)
This project is an advanced **Hybrid AI Agent System** capable of performing real-world actions on an Android device triggered by a Web Interface.

### Core Philosophy
- **The Interface**: A local Web Dashboard (`frontend/index.html`) acting as the Mission Control.
- **The Brain**: A Python Backend (`server.py`) that processes tasks and routes them to the agents.
- **The Muscle**: TrioAgent (built on DroidRun) executes ADB commands on the connected Android device.

---

## System Architecture

### 1. Control Layer (Web UI)
- **Location**: `frontend/`
- **Features**:
   - **Persona Selectors**: Specialized forms for Shopping, Cab Booking, etc.
   - **Universal Agent**: A natural language command interface for any task (e.g., "Check Uber price").
   - **WebSocket**: Real-time log streaming from the backend.

### 2. Execution Layer (Backend)
- **Entry Point**: `server.py` (FastAPI).
- **Router**: `agents/agent_factory.py` - Intelligently selects between **MobileRun (Cloud)** or **DroidRun (Local)**.
- **Agents**:
    - `commerce_agent.py`: Shopping & Food.
    - `ride_agent.py`: Cab booking.
    - `pharmacy_agent.py`: Medicine ordering.

### 3. Device Layer
- **Local**: Android Phone connected via USB (Debugging ON).
- **Cloud**: Pixel 8 Pro instances via MobileRun API (if configured).

---

## Deployment & Setup Guide

### Prerequisites
1.  **Python 3.10+**.
2.  **Android SDK Platform-Tools** (ADB).
3.  Physical Android Device (Developer Mode -> USB Debugging).

### Installation
```bash
pip install -r requirements.txt
pip install mobile-use  # For Cloud support
```

### Running the System
```bash
# Start the Backend Server
python server.py

# Open the Frontend
start frontend/index.html
```

### Configuration
- **Environment Variables (`.env`)**:
    ```ini
    GOOGLE_API_KEY=AIza...
    MOBILERUN_API_KEY=dr_sk_...
    USE_MOBILE_RUN=True # Set True for Cloud, False for Local USB
    ```

---

## Current Capabilities
- **Universal Commands**: "Open Amazon and find iPhone 16".
- **Structured Tasks**: "Book Uber to Airport" (via UI Form).
- **Hybrid Execution**: Auto-fallback to local device if cloud credits are low.
