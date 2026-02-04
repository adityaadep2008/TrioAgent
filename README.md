# TrioAgent: The Agentic OS for Everyone 🚀

> **"Technology should bridge gaps, not create them."**

TrioAgent is a next-generation **Agentic Operating System** designed to make digital life accessible to seniors and individuals with physical disabilities. By replacing complex app navigation with a **Voice-First Autonomous Interface**, we empower everyone to command the digital economy effortlessly.

---

## 🌟 The Problem
Modern smartphones are powerful but overwhelming. For an elderly user or someone with limited dexterity, ordering medicine or booking a ride involves navigating a maze of small buttons, multiple apps, and complex flows. This leads to **Digital Exclusion**.

## 💡 The Solution
**TrioAgent** unifies these services into a single, intent-based interface.
- 🗣️ **Just Speak:** "Book a ride to the hospital" or "Order Fried Rice from Zomato".
- 🤖 **Autonomous Execution:** Our backend agents (powered by **Gemini 1.5 Flash**) physically interact with real Android apps (Uber, Apollo, Swiggy) to get the job done.
- 🧠 **Context Aware:** It remembers your preferences and previous requests (e.g., "Order that from Zomato" refers to the dish you just mentioned).

---

## ✨ Key Features

1.  **Voice-First Interface**:
    - High-contrast, large-button UI tailored for accessibility.
    - Real-time transcription and feedback.
    - Completely hands-free operation.

2.  **Multi-Agent Orchestration**:
    - **Commerce Agent**: Comparison shops and orders food/products (Amazon, Flipkart, Zomato, Swiggy).
    - **Ride Agent**: Compares and books rides (Uber, Ola).
    - **Pharmacy Agent**: Finds the best medicine prices (PharmEasy, Apollo).
    - **Voyager Agent**: Plans entire trips (Flights + Hotels + Cabs).

3.  **Manual "Mission Control"**:
    - A visual dashboard for power users to oversee and tweak complex tasks.

---

## 🛠️ Technology Stack
- **Frontend**: HTML5, Vanilla JS (for maximum compatibility), WebSockets.
- **Backend**: Python, FastAPI.
- **AI Core**: Google Gemini 1.5 Flash (via `google-generativeai`).
- **Automation**: `DroidRun` (Custom framework for Android UI interaction).

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- An Android Device (connected via USB) OR Cloud Device credentials.

### Installation

1.  **Clone the Repo**
    ```bash
    git clone https://github.com/adityaadep2008/TrioAgent.git
    cd TrioAgent
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Setup**
    - Copy `.env.example` to `.env`:
      ```bash
      cp .env.example .env
      ```
    - Edit `.env` and add your **GEMINI_API_KEY**.

### Running the System

1.  **Start the Server**
    ```bash
    python server.py
    ```

2.  **Launch the Interface**
    Open your browser and navigate to:
    `http://localhost:8002/static/app.html`

3.  **Speak!**
    Click the microphone and say: *"Order me a pizza."*

---

## 👥 Use Cases
- **Grandparents**: "Call my grandson" or "Order my heart medicine."
- **Visually Impaired**: Full auditory feedback for all actions.
- **Busy Professionals**: "Book the cheapest cab to the airport" (Agents compare Uber/Ola automatically).

---

made with ❤️ by **Team TrioAgent**
