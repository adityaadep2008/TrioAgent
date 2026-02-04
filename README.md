# DroidRun Auto: Agentic OS 🤖📱

**Voice-Activated Autonomous Mobile Agents for Accessibility & Automation**

DroidRun Auto is an "Agentic OS" that turns any Android device into a helpful assistant. It uses **Google Gemini 2.5 Flash** to understand your natural language commands and executes them on real mobile apps (Uber, Zomato, Amazon, Apollo, etc.) using either a **Local Android Device** (via DroidRun) or the **MobileRun Cloud Fleet**.

Designed for **Accessibility**, the system features a high-contrast **Voice Interface** that allows elderly or disabled users to complete complex tasks just by speaking.

---

## 🌟 Key Features

*   **🎙️ Voice Agentic OS**:
    *   **Speak**: "Book a cab to the airport."
    *   **Listen**: The agent replies via Text-to-Speech: "Okay, finding the best ride..."
    *   **Conversational**: "Which airport?" -> "Mumbai Terminal 2."
*   **🛒 Shopping**: Finds and buys products on Amazon/Flipkart.
*   **🍔 Food Ordering**: Compares Swiggy vs Zomato and places orders.
*   **💊 Medicine**: Finds medicines on PharmEasy/Apollo.
*   **🚕 Ride Booking**: Autosurfs Uber/Ola to find the cheapest ride.
*   **✈️ Travel**: Plans full trips (Flight + Hotel + Cab) on MakeMyTrip/Booking.com.
*   **☁️ Hybrid Execution**:
    *   **Local Mode**: Uses your USB-connected Phone.
    *   **Cloud Mode**: Uses `MobileRun` virtual devices in the cloud.

---

## 🛠️ Architecture

*   **Brain**: `agents/general_agent.py` - Understanding intent & context.
*   **Router**: `agents/agent_factory.py` - Smartly dispatching tasks to Cloud or Local.
*   **API**: FastAPI Server (`server.py`) exposing `/api/chat`.
*   **UI**: `frontend/accessibility.html` (Voice) & `frontend/index.html` (Dashboard).
*   **Core**: DroidRun (Local) & MobileRun (Cloud).

---

## 🚀 Getting Started

### 1. Prerequisites
*   **Python 3.10+**
*   **Android Device** (Enable "USB Debugging" & connect via USB).
*   **API Keys**:
    *   Google Gemini API Key (for intelligence).
    *   MobileRun API Key (optional, for cloud mode).

### 2. Installation
Clone the repo and install dependencies:
```bash
git clone https://github.com/your-username/devrunauto.git
cd devrunauto
pip install -r requirements.txt
```

### 3. Configuration (.env)
Create a `.env` file in the root folder (copy from `.env.example`):
```bash
cp .env.example .env
```
Edit `.env` with your keys:
```env
# Required for Intelligence
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Mode Selection
# True = Cloud (Requires MobileRun Key)
# False = Local (Uses USB Device)
USE_MOBILE_RUN=False
MOBILERUN_API_KEY=your_mobilerun_api_key_here
```

### 4. Running the System

#### Option A: The Accessibility Voice OS (Recommended)
1.  Start the Server:
    ```bash
    python server.py
    ```
2.  Open your browser to:
    👉 **http://localhost:8000/static/accessibility.html**
3.  Click the **Microphone Button** and speak!
    *   *"I want to order a Chicken Burger."*
    *   *"Book a cab to Cyber Hub."*

#### Option B: Individual Agents (CLI)
You can run specific task agents directly from the terminal:
```bash
# Shop for iPhones
python commerce_agent.py --action search --query "iPhone 15"

# Compare Rides
python ride_comparison_agent.py --pickup "Home" --drop "Office"

# Send WhatsApp Invite
python event_coordinator_agent.py --contacts "Mom, Dad" --event "Dinner" ...
```

---

## 📂 Directory Structure

| File/Folder | Description |
| :--- | :--- |
| `server.py` | Main Backend API & WebSocket Server. |
| `agents/general_agent.py` | The "Brain" that handles conversation & routing. |
| `agents/agent_factory.py` | Decides whether to run on Cloud vs Local. |
| `agents/mobile_run_wrapper.py` | Wrapper for Cloud execution. |
| `frontend/accessibility.html` | The Voice-First UI for accessibility. |
| `commerce_agent.py` | Shopping/Food Agent. |
| `ride_comparison_agent.py` | Uber/Ola Agent. |
| `requirements.txt` | Dependency list. |

---

## ⚠️ Important Notes
*   **Real Actions**: In "Local Mode", this software clicks real buttons on your phone. Watch it carefully!
*   **Permissions**: Ensure your phone stays unlocked or has "Stay Awake" enabled during execution.
*   **Cloud Mode**: MobileRun execution relies on having credits/quota.

---
*Built with ❤️ for AI Agents Hackathon 2026*
