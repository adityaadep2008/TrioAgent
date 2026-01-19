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

The system is built with a modular "Persona" architecture:
*   **Backend**: FastAPI server with WebSocket support for real-time status broadcasting.
*   **Frontend**: A sleek, GSAP-animated web interface for selecting personas and monitoring tasks.
*   **Agents**: specialized Python classes (`CommerceAgent`, `EventCoordinatorAgent`, etc.) wrapping DroidRun logic.
*   **Vision & Reasoning**: Uses screen parsing (Vision) to interact with non-API-enabled mobile apps natively.

---

## 📦 Installation

### Prerequisites
1.  **Android Phone** enabled with USB Debugging connected to PC.
2.  **Python 3.10+** installed.
3.  **ADB (Android Debug Bridge)** installed and available in PATH.
4.  **Google Gemini API Key**.

### Setup
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

### 1. Start the System (Recommended)
Run the all-in-one launcher (if available) or start manually:

**Backend (Terminal 1):**
```bash
python server.py
```

**Frontend (Terminal 2):**
```bash
cd frontend
python -m http.server 8081
```

### 2. Access the Interface
Open your browser and navigate to: `http://localhost:8081`

### 3. Select a Persona
*   **Shopper**: Enter a product name (e.g., "Nike Shoes") -> Watch it compare prices.
*   **Food Order (Foodie)**:
    *   Enter a craving (e.g., "Chicken Biryani").
    *   **Toggle Switch**:
        *   *Find Best Deal*: Safe mode. Scans apps and tells you the cheapest price.
        *   *Autonomous Order*: **DANGER ZONE**. Will actually add to cart and place a COD order.

---

## 📂 Project Structure

*   `server.py`: Main FastAPI entry point and WebSocket manager.
*   `commerce_agent.py`: Logic for Shopping and Food Ordering (Swiggy/Zomato).
*   `event_coordinator_agent.py`: Complex logic for WhatsApp coordination and event planning.
*   `frontend/`: HTML/CSS/JS files for the web UI.
*   `requirements.txt`: Python dependencies.

---

## ⚠️ Disclaimer

**This tool performs REAL actions on your device.**
*   "Autonomous Order" mode **WILL** place orders if not interrupted. 
*   Always monitor the agent during execution.
*   The developers are not responsible for accidental orders or unintended messages sent by the agents.
