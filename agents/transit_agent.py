import os
import json
import asyncio
from datetime import datetime, timedelta
import sys

# Import AgentFactory
try:
    from agents.agent_factory import AgentFactory
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from agents.agent_factory import AgentFactory

from schemas import FlightDetails, CabDetails

class TransitManager:
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model

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
        
        # Use AgentFactory Smart Router
        result = await AgentFactory.run_task(
            app_identifier="MakeMyTrip",
            instruction=goal,
            provider=self.provider,
            model=self.model
        )
        
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

        # Use AgentFactory Smart Router
        result = await AgentFactory.run_task(
            app_identifier="Uber",
            instruction=goal,
            provider=self.provider,
            model=self.model
        )
        
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


