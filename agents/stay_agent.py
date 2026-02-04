import os
import json
import asyncio
import google.generativeai as genai
import sys
from datetime import datetime

# --- DroidRun Professional Architecture Imports ---
try:
    from droidrun.agent.droid.droid_agent import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun import AdbTools
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found.")
    sys.exit(1)

from schemas import HotelDetails, ItineraryDay, ItineraryActivity, FullTripPlan

class StayManager:
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    async def _run_agent(self, goal: str) -> dict:
        """Helper to run DroidAgent for Hotel Search."""
        provider_name = "GoogleGenAI" if self.provider == "gemini" else self.provider
        llm = load_llm(provider_name=provider_name, model=self.model, api_key=self.api_key)
        
        tools = await AdbTools.create()

        agent = DroidAgent(
            goal=goal, 
            llm=llm, 
            tools=tools,
            vision=True, 
            reasoning=True, 
            timeout=1000, # Hardcoded, assuming default or acceptable timeout
            debug=False
        )
        
        try:
            print(f"      🧠 StayAgent Analyzing...")
            result = await agent.run()
            
            # Robust Parsing
            raw_text = str(result.reason) if hasattr(result, 'reason') else str(result)
            import re
            
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            
            clean_json = "{}"
            if json_match:
                clean_json = json_match.group(1)
            else:
                clean_json = raw_text.strip()

            try:
                data = json.loads(clean_json)
                return data
            except json.JSONDecodeError:
                print(f"[Warn] JSON Parse Error. Raw: {clean_json[:100]}...")
                return {"status": "failed", "raw": clean_json}
                
        except Exception as e:
            print(f"[Error] Agent Execution Failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def find_hotel(self, city: str, check_in_date: str) -> HotelDetails:
        print(f"🏨 Searching Hotel in {city} for {check_in_date}")
        
        goal = (
            f"1. Open 'MakeMyTrip'. "
            f"2. Handle any Ads/Popups if they appear. "
            f"3. Click on 'Hotels'. "
            f"4. Enter Location/City: '{city}'. "
            f"5. Select Check-in Date: '{check_in_date}'. "
            f"6. Click the central 'SEARCH' button. "
            f"7. Wait 10 seconds for the hotel list. "
            f"8. **SCROLL DOWN** slightly to see hotel cards. "
            f"9. Identify the FIRST hotel card in the list. "
            f"10. Extract directly from card: Hotel Name, Location/Address, Price Per Night. "
            f"11. Return strict JSON: {{'name': '...', 'address': '...', 'price_per_night': '...'}}."
        )
        
        result = await self._run_agent(goal)
        
        try:
             hotel = HotelDetails(
                 name=result.get("name", "Unknown Hotel"),
                 address=result.get("address", "Unknown Address"),
                 price_per_night=result.get("price_per_night", "Unknown")
             )
             return hotel
        except Exception as e:
            print(f"Error parsing hotel details: {e}")
            raise e

    async def generate_itinerary(self, hotel_location: str, user_interests: str, days: int = 3) -> list[ItineraryDay]:
        print(f"🗺️ Generating Itinerary for {days} days based on interests: {user_interests}")
        
        prompt = (
            f"Create a {days}-day travel itinerary for a trip staying at {hotel_location}. "
            f"User Interests: {user_interests}. "
            f"Strict Rules: \n"
            f"1. Lunch MUST be at 1:00 PM every day. \n"
            f"2. Activities MUST end by 10:00 PM (Sleep time). \n"
            f"3. Include travel time between places. \n"
            f"Return ONLY raw JSON list of objects matching this schema: \n"
            f"[{{'day_number': 1, 'activities': [{{'time': '...','description': '...'}}]}}]"
        )
        
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        
        try:
            # Clean up response
            text = response.text
            import re
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
                data = json.loads(clean_json)
                
                itinerary = []
                for day in data:
                    activities = [ItineraryActivity(**a) for a in day['activities']]
                    itinerary.append(ItineraryDay(day_number=day['day_number'], activities=activities))
                return itinerary
            else:
                 print("Error: Could not find JSON in LLM response")
                 return []
        except Exception as e:
            print(f"Error generating itinerary: {e}")
            return []
