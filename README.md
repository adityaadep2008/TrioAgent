# DroidRun Auto 🤖📱

**Autonomous Multi-Agent System for Mobile Interaction**

DroidRun Auto is a cutting-edge autonomous agent framework capable of executing complex real-world tasks on an Android device. By leveraging **Gemini 2.5 Flash** and the **DroidRun framework**, it orchestrates specialized agents to perform actions like price comparison, ride booking, pharmacy searches, and autonomous food ordering.

---

## 🚀 Features

*   **🛒 Autonomous Shopping**: Scans Amazon and Flipkart to find the best deals for a product.
*   **🚕 Ride Comparison**: Compares prices between Uber and Ola (simulated/vision-based) to find the cheapest ride.
*   **💊 Pharmacy Scout**: Searches online pharmacies like 1mg or Apollo for medicine availability.
*   **🎈 Event Coordinator**:
    *   Sends invitations via WhatsApp.
    *   Polls for replies (e.g., "I want Pizza").
    *   Autonomously researches food prices across Swiggy and Zomato.
*   **🍔 Foodie Persona (NEW/HOT)**:
    *   **Find Best Deal**: Searches Swiggy and Zomato for your craving and reports the cheapest option.
    *   **Autonomous Order**: Actually places the order via Cash on Delivery (COD) for true "hands-off" convenience.

---

## 🛠️ Architecture

The system is built with a modular "Persona" / "Brain & Senses" architecture:

### 1. The Brain (Backend & Agents)
-   **FastAPI Server (`server.py`)**: The central nervous system. It manages agent lifecycles, maintains a real-time task history, and broadcasts status updates via WebSockets.
-   **Agents (`commerce_agent.py`, etc.)**: Specialized Python classes that encapsulate logic for different domains. They utilize the `DroidRun` framework to "reason" about what to do next based on the user's goal.
-   **Gemini 2.5 Flash**: The cognitive engine. It analyzes screen content (Vision) and decides which UI elements to interact with.

### 2. The Senses (DroidRun & ADB)
-   **DroidRun Framework**: Acts as the bridge between the Python agents and the Android device. It translates high-level goals (e.g., "Order Pizza") into low-level ADB commands.
-   **ADB (Android Debug Bridge)**: The physical/digital link. It captures screenshots for the AI to "see" and injects touch/text events for the AI to "act".
-   **Device Portal**: A lightweight on-device service (initialized via `droidrun setup`) that assists with accessibility and screen coordinate mapping.

### 3. The Face (Frontend)
-   **Web UI**: A responsive, GSAP-enhanced interface (running on port 8081) that allows users to issue commands and watch the agents work in real-time.

---

## 📦 Installation & Setup Guide

### Prerequisites
1.  **Android Phone**: Must have **Developer Options** and **USB Debugging** enabled.
2.  **Python 3.10+**: Required for the backend.
3.  **ADB Installed**: Available in your system PATH.
4.  **Google Gemini API Key**: For the AI model.

### 🔌 Step 1: Device Setup (Critical)

1.  **Enable Developer Options**:
    -   Go to **Settings** > **About Phone**.
    -   Tap **Build Number** 7 times until you see "You are a developer".
    -   Go back to **System** > **Developer Options**.
    -   Enable **USB Debugging**.

2.  **Connect via ADB**:
    -   **USB**: Connect your phone to PC. A popup "Allow USB Debugging?" will appear on phone. Check "Always allow" and tap **Allow**.
    -   **Wireless**:
        -   Enable "Wireless Debugging" in Developer Options.
        -   Run `adb pair [ip]:[port]` (using code from "Pair device with pairing code").
        -   Run `adb connect [ip]:[port]`.

3.  **Verify Connection**:
    ```bash
    adb devices
    ```
    *Ensure your device is listed as `device` (not `unauthorized`).*

4.  **Initialize DroidRun**:
    Open a terminal and run:
    ```bash
    droidrun setup
    ```
    -   This will install the necessary helper services on your phone.
    -   **IMPORTANT**: Watch your phone screen! You must grant **Accessibility Permissions** and **Screen Recording Permissions** when prompted by the DroidRun app.

### 💻 Step 2: Project Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/devrunauto.git
    cd devrunauto
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    Create a `.env` file in the root directory:
    ```env
    GOOGLE_API_KEY=your_gemini_api_key_here
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

---

## 🚦 Usage

### 1. Start the Backend
Open a terminal in the root `devrunauto` folder:
```bash
python server.py
```
*You should see "DroidRun Server Running" logs.*

### 2. Start the Frontend
Open a **new** terminal, navigate to `frontend`, and start a simple server:
```bash
cd frontend
python -m http.server 8081
```

### 3. Run the App
-   Open your browser to: `http://localhost:8081`
-   Select a **Persona** (e.g., Foodie).
-   Enter your query (e.g., "Pizza").
-   Click **Start**.
-   **Watch your phone!** The agent will physically open apps and start working.

---

## 📂 Project Structure

*   `server.py`: Main backend server.
*   `commerce_agent.py`: Agent logic for Shopping/Food.
*   `ride_comparison_agent.py`: Agent logic for Rides.
*   `frontend/`: Web interface files.
*   `requirements.txt`: Python dependencies.

---

## ⚠️ Disclaimer

**This tool performs REAL actions on your device.**
*   "Autonomous Order" mode **WILL** place orders if not interrupted. 
*   Always monitor the agent during execution.
*   The developers are not responsible for accidental orders or unintended messages sent by the agents.
