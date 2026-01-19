import os
import json
import asyncio
from datetime import datetime, timedelta
import sys

# --- DroidRun Professional Architecture Imports ---
try:
    from droidrun.agent.droid import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found.")
    sys.exit(1)

from schemas import FlightDetails, CabDetails

class TransitManager:
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    async def _run_agent(self, goal: str) -> dict:
        """Helper to run DroidAgent."""
        # Config setup
        provider_name = "GoogleGenAI" if self.provider == "gemini" else self.provider
        llm = load_llm(provider_name=provider_name, model=self.model, api_key=self.api_key)
        
        manager_config = ManagerConfig(vision=True)
        executor_config = ExecutorConfig(vision=True)
        agent_config = AgentConfig(reasoning=True, manager=manager_config, executor=executor_config)
        telemetry_config = TelemetryConfig(enabled=False)
        config = DroidrunConfig(agent=agent_config, telemetry=telemetry_config)

        agent = DroidAgent(goal=goal, llms=llm, config=config)
        
        try:
            print(f"      🧠 TransitAgent Analyzing...")
            result = await agent.run()
            
            # Robust Parsing (based on EventCoordinator logic)
            raw_text = str(result.reason) if hasattr(result, 'reason') else str(result)
            import re
            
            # Try finding JSON block
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            
            clean_json = "{}"
            if json_match:
                clean_json = json_match.group(1)
            else:
                clean_json = raw_text.strip() # Attempt direct parse

            try:
                data = json.loads(clean_json)
                return data
            except json.JSONDecodeError:
                print(f"[Warn] JSON Parse Error. Raw: {clean_json[:100]}...")
                return {"status": "failed", "raw": clean_json}
                
        except Exception as e:
            print(f"[Error] Agent Execution Failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def find_best_flight(self, source: str, dest: str, date: str) -> FlightDetails:
        print(f"✈️ Searching Flight: {source} to {dest} on {date}")
        
        goal = (
            f"1. Open 'MakeMyTrip'. "
            f"2. Handle any Ads/Popups if they appear (Click 'X' or 'Skip'). "
            f"3. Click on 'Flights'. "
            f"4. Select 'One Way'. "
            f"5. Enter From: '{source}' and To: '{dest}'. "
            f"6. Select Date: '{date}'. "
            f"7. Click 'Search Flights'. "
            f"8. Wait 10 seconds for results to fully load. "
            f"9. **SCROLL DOWN** slowly to ensure flight cards are rendered. "
            f"10. **CLICK** on the FIRST visible flight card to expand details. "
            f"11. Wait for the details view. "
            f"12. Extract: Airline Name, Flight Number, Price, and ARRIVAL Time. "
            f"13. Return strict JSON: {{'airline': '...', 'flight_number': '...', 'price': '...', 'arrival_time': 'YYYY-MM-DD HH:MM:SS'}}."
        )
        
        result = await self._run_agent(goal)
        
        # Fallback/Validation logic could go here
        try:
             # Basic validation of return format
             flight = FlightDetails(
                 airline=result.get("airline", "Unknown"),
                 flight_number=result.get("flight_number", "Unknown"),
                 price=result.get("price", "Unknown"),
                 arrival_time=datetime.strptime(result.get("arrival_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S")
             )
             return flight
        except Exception as e:
            print(f"Error parsing flight details: {e}")
            # Return dummy/error object or raise
            raise e

    async def book_cab(self, location: str, flight_arrival_time: datetime) -> CabDetails:
        pickup_time = flight_arrival_time + timedelta(minutes=45)
        pickup_str = pickup_time.strftime("%H:%M")
        
        print(f"🚖 Booking Cab from {location} for {pickup_str} (45 mins after arrival)")
        
        goal = (
            f"1. Open 'MakeMyTrip'. "
            f"2. Click on 'Airport Cabs' or 'Cabs'. "
            f"3. Select 'Airport Pick-up/Drop'. "
            f"4. Enter Airport as Source, and '{location}' as Destination. "
            f"5. Select Pickup Time: {pickup_str}. "
            f"6. Click 'Search'. "
            f"7. Select the cheapest/best cab option. "
            f"8. Return strict JSON: {{'provider': 'MakeMyTrip Cabs', 'pickup_time': '{pickup_time.strftime('%Y-%m-%d %H:%M:%S')}', 'estimated_price': '...'}}."
        )

        result = await self._run_agent(goal)
        
        try:
             cab = CabDetails(
                 provider=result.get("provider", "Uber"),
                 pickup_time=datetime.strptime(result.get("pickup_time", pickup_time.strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S"),
                 estimated_price=result.get("estimated_price", "Unknown")
             )
             return cab
        except Exception as e:
            print(f"Error parsing cab details: {e}")
            raise e
