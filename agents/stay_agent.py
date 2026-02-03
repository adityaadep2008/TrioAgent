import os
import json
import asyncio
import google.generativeai as genai
import sys
from datetime import datetime

# Import the new wrapper
try:
    from agents.mobile_run_wrapper import MobileRunWrapper
except ImportError:
    # Handle running from root or subfolder
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from agents.mobile_run_wrapper import MobileRunWrapper

from schemas import HotelDetails, ItineraryDay, ItineraryActivity, FullTripPlan

class StayManager:
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
        # Initialize MobileRun Runner
        self.runner = MobileRunWrapper(provider=provider, model=model)

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
            f"9. **CLICK** on the first hotel card/image to open details. "
            f"10. Wait for details page. "
            f"11. Extract: Hotel Name, Address, Price Per Night. "
            f"12. Return strict JSON: {{'name': '...', 'address': '...', 'price_per_night': '...'}}."
        )
        
        # Use Wrapper -> "Booking.com"
        result = await self.runner.run_agent("Booking.com", goal)
        
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
        
        # This part uses LLM directly (Text Gen), not UI Agent, so it stays as is.
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

