import os
import asyncio
import sys
import json
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# --- Imports ---
try:
    from mobilerun import MobileRunClient
except ImportError:
    try:
        from mobile_use import MobileRunClient
    except ImportError:
        MobileRunClient = None

try:
    from droidrun.agent.droid import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found.")
    sys.exit(1)

# CONFIGURATION
# Set this to FALSE if cloud credits run out during the demo!
USE_CLOUD = os.getenv("USE_MOBILE_RUN", "False").lower() == "true"

class AgentFactory:
    
    APP_MAPPING = {
        "Uber": "com.ubercab",
        "MakeMyTrip": "com.makemytrip",
        "Booking.com": "com.booking",
        "Amazon": "com.amazon.mShop.android.shopping",
        "Flipkart": "com.flipkart.android",
        "Zomato": "com.application.zomato",
        "Swiggy": "in.swiggy.android", 
        "WhatsApp": "com.whatsapp",
        "PharmEasy": "com.pharmeasy.app",
        "Apollo 24|7": "com.apollo.patientapp",
        "Tata 1mg": "com.aranoah.healthkart.plus",
        "Ola": "com.olacabs.customer"
    }

    @staticmethod
    async def run_task(app_identifier, instruction, provider="gemini", model="models/gemini-2.5-flash"):
        """
        Smart Router: Decides whether to use Local Phone or Cloud Fleet
        app_identifier: Can be App Name (e.g. "Uber") or Package ID.
        """
        # Resolve App ID
        app_package = AgentFactory.APP_MAPPING.get(app_identifier, app_identifier)

        if USE_CLOUD and MobileRunClient:
            try:
                print(f"☁️ Cloud: Dispatching '{instruction[:50]}...' to MobileRun...")
                api_key = os.getenv("MOBILERUN_API_KEY")
                if not api_key:
                    raise ValueError("MOBILERUN_API_KEY not set")
                    
                client = MobileRunClient(api_key=api_key)
                
                job = await client.submit_job(
                    app_id=app_package,
                    instruction=instruction,
                    device="pixel_8_pro",
                    stream=True
                )
                result = await job.result()
                
                if result.status == "COMPLETED":
                    return AgentFactory._parse_output(result.output)
                else:
                    print(f"⚠️ Cloud Job Status: {result.status}")
                    # Fallthrough
                
            except Exception as e:
                print(f"⚠️ Cloud Failed: {e}. Falling back to Local DroidRun.")
                # Fallthrough to local execution
                
        # LOCAL EXECUTION (DroidRun)
        print(f"📱 Local: Executing '{instruction[:50]}...' on USB Device...")
        
        # Initialize DroidAgent with proper config
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        provider_name = "GoogleGenAI" if provider == "gemini" else provider
        
        llm = load_llm(provider_name=provider_name, model=model, api_key=gemini_key)
        
        manager_config = ManagerConfig(vision=True)
        executor_config = ExecutorConfig(vision=True)
        agent_config = AgentConfig(reasoning=False, manager=manager_config, executor=executor_config)
        telemetry_config = TelemetryConfig(enabled=False)
        config = DroidrunConfig(agent=agent_config, telemetry=telemetry_config)

        agent = DroidAgent(goal=instruction, llms=llm, config=config)
        
        try:
            result = await agent.run()
            raw_text = str(result.reason) if hasattr(result, 'reason') else str(result)
            return AgentFactory._parse_output(raw_text)
        except Exception as e:
            print(f"❌ Local Execution Failed: {e}")
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def _parse_output(raw_text: str) -> dict:
        """Shared parser helper"""
        import re
        # Clean up output
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        
        clean_json = "{}"
        if json_match:
            clean_json = json_match.group(1)
        else:
            clean_json = raw_text.strip()
            if "<request_accomplished" in clean_json:
                 try:
                     clean_json = clean_json.split(">")[1].split("</request_accomplished>")[0].strip()
                 except: pass

        try:
            return json.loads(clean_json)
        except json.JSONDecodeError:
            return {"status": "failed", "raw": clean_json, "error": "json_parse_error"}
