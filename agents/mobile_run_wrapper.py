import os
import asyncio
import json
import sys
from dotenv import load_dotenv

# Load env to get keys
load_dotenv()

# --- MobileRun SDK ---
try:
    from mobilerun import MobileRunClient
except ImportError:
    try:
        from mobile_use import MobileRunClient
    except ImportError:
        # If sdk not installed, we will rely 100% on fallback
        MobileRunClient = None
        print("[MobileRun] SDK not found. Will default to DroidRun.")

# --- DroidRun Imports (for Fallback) ---
try:
    from droidrun.agent.droid import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found.")
    sys.exit(1)

class MobileRunWrapper:
    """
    Unified client for MobileRun Cloud with DroidRun Local Fallback.
    """
    
    APP_MAPPING = {
        # Transit
        "Uber": "com.ubercab",
        "MakeMyTrip": "com.makemytrip",
        
        # Stay
        "Booking.com": "com.booking",
        
        # Commerce
        "Amazon": "com.amazon.mShop.android.shopping",
        "Flipkart": "com.flipkart.android",
        "Zomato": "com.application.zomato",
        "Swiggy": "in.swiggy.android", # Check exact ID, usually this or bundl
        
        # Social
        "WhatsApp": "com.whatsapp",
        
        # Pharmacy
        "PharmEasy": "com.pharmeasy.app",
        "Apollo 24|7": "com.apollo.patientapp",
        "Tata 1mg": "com.aranoah.healthkart.plus",
        
        # Ride
        "Ola": "com.olacabs.customer"
    }

    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        
        self.mobilerun_key = os.getenv("MOBILERUN_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        self.client = None
        if self.mobilerun_key and MobileRunClient:
            try:
                self.client = MobileRunClient(api_key=self.mobilerun_key)
                print("[Init] MobileRun Client Ready ☁️")
            except Exception as e:
                print(f"[Init] MobileRun Client Failed: {e}. using Local DroidRun.")
        else:
            print("[Init] MobileRun Key missing or SDK absent. Using Local DroidRun.")

    async def run_agent(self, app_name: str, goal: str) -> dict:
        """
        Attempts to run via MobileRun. Falls back to DroidRun on failure.
        """
        app_id = self.APP_MAPPING.get(app_name)
        
        # --- 1. MobileRun Execution ---
        if self.client and app_id:
            try:
                print(f"[MobileRun] ☁️ Submitting Job for {app_name} ({app_id})...")
                job = await self.client.submit_job(
                    app_id=app_id,
                    instruction=goal,
                    device="pixel_8_pro",
                    session_id=f"session_{os.getpid()}",
                    stream=True
                )
                
                print("[MobileRun] Waiting for result...")
                result = await job.result()
                
                if result.status == "COMPLETED":
                    print("[MobileRun] ✅ Success!")
                    # Handle Output format (assume Cloud returns parseable Text or JSON)
                    return self._parse_output(result.output)
                else:
                    print(f"[MobileRun] ❌ Job Failed: {result.status}")
                    # Fallthrough to backup
            except Exception as e:
                print(f"[MobileRun] ⚠️ Error: {e}")
                # Fallthrough to backup
        
        # --- 2. DroidRun Logic (Fallback) ---
        print(f"[Fallback] 📱 Switching to Local DroidRun for {app_name}...")
        return await self._run_local_droid(goal)

    async def _run_local_droid(self, goal: str) -> dict:
        """
        Internal: Executes using DroidRun Local Agent
        """
        provider_name = "GoogleGenAI" if self.provider == "gemini" else self.provider
        llm = load_llm(provider_name=provider_name, model=self.model, api_key=self.gemini_key)
        
        manager_config = ManagerConfig(vision=True)
        executor_config = ExecutorConfig(vision=True)
        agent_config = AgentConfig(reasoning=False, manager=manager_config, executor=executor_config)
        telemetry_config = TelemetryConfig(enabled=False)
        config = DroidrunConfig(agent=agent_config, telemetry=telemetry_config)

        agent = DroidAgent(goal=goal, llms=llm, config=config)
        
        try:
            print(f"      [DroidRun] 🧠 Analyzing...")
            result = await agent.run()
            
            # Robust Parsing from original logic
            raw_text = str(result.reason) if hasattr(result, 'reason') else str(result)
            return self._parse_output(raw_text)
                
        except Exception as e:
            print(f"[DroidRun] Error: {e}")
            return {"status": "failed", "error": str(e)}

    def _parse_output(self, raw_text: str) -> dict:
        """Shared parser for both Cloud and Local outputs"""
        import re
        
        # Try finding JSON block
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        
        clean_json = "{}"
        if json_match:
            clean_json = json_match.group(1)
        else:
            clean_json = raw_text.strip()
            # Cleanup XML tags if present
            if "<request_accomplished" in clean_json:
                 try:
                     clean_json = clean_json.split(">")[1].split("</request_accomplished>")[0].strip()
                 except: pass

        try:
            data = json.loads(clean_json)
            return data
        except json.JSONDecodeError:
            print(f"[Parser] Warn: Could not parse JSON. Raw: {clean_json[:50]}...")
            return {"status": "failed", "raw": clean_json, "error": "json_parse_error"}
