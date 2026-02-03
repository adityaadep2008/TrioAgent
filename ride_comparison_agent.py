import os
import json
import argparse
import asyncio
import re
import sys
from dotenv import load_dotenv

# Import MobileRun Wrapper
try:
    from agents.mobile_run_wrapper import MobileRunWrapper
except ImportError:
    # Handle imports from root
    sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))
    try:
        from agents.mobile_run_wrapper import MobileRunWrapper
    except ImportError:
         print("CRITICAL ERROR: 'agents.mobile_run_wrapper' not found.")
         sys.exit(1)

# Load environment variables
load_dotenv()

class RideComparisonAgent:
    """
    Agent to compare ride prices between Uber and Ola using MobileRun Cloud.
    """
    
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.runner = MobileRunWrapper(provider=provider, model=model)

    def _parse_price(self, price_str):
        """Robust price parsing utility handling currency symbols."""
        if not price_str: return float('inf')
        try:
            clean = str(price_str).lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            return float(match.group()) if match else float('inf')
        except:
            return float('inf')

    async def execute_task(self, app_name: str, pickup: str, drop: str, preference: str = "cab", action: str = "compare") -> dict:
        """
        Executes a ride check task on a specific app.
        """
        print(f"\n[RideAgent] Initializing Task for: {app_name} (Action: {action}, Pref: {preference})")
        
        # Define Goal with specific instructions for each app
        ride_keywords = "Uber Go, Premier" # Default
        if preference == "auto":
            ride_keywords = "Uber Auto" if app_name == "Uber" else "Ola Auto"
        elif preference == "sedan":
            ride_keywords = "Uber Premier" if app_name == "Uber" else "Ola Prime Sedan"
        else:
             ride_keywords = "Uber Go, Uber Moto" if app_name == "Uber" else "Ola Mini, Ola Bike"

        if action == "book":
            goal = (
                f"Open the app '{app_name}'. "
                f"If a 'Location Permission' popup appears, click 'While using the app' or 'Allow'. "
                f"Click on 'Ride' or the search bar. "
                f"Enter pickup location: '{pickup}'. "
                f"Enter destination: '{drop}'. "
                f"Wait for ride options. "
                f"Select the CHEAPEST available ride matching preference '{preference}' (Look for: {ride_keywords}). "
                f"Click 'Book' or 'Confirm'. "
                f"Change Payment Method to 'Cash' if not already selected. "
                f"Click 'Confirm Booking' or 'Request Ride'. "
                f"Wait for the 'Driver Found' screen. "
                f"Extract Driver Name, Vehicle Number, and OTP if visible. "
                f"Return a strict JSON with keys: 'status', 'driver_details', 'cab_details', 'price', 'eta'. "
            )
        else:
            goal = (
                f"Open the app '{app_name}'. "
                f"If a 'Location Permission' popup appears, click 'While using the app' or 'Allow'. "
                f"Click on 'Ride' or the search bar to start a booking. "
                f"Enter pickup location: '{pickup}'. "
                f"Enter destination: '{drop}'. "
                f"Wait for the ride options to load. "
                f"Visually SCAN for rides matching preference '{preference}' (Look for: {ride_keywords}). "
                f"Extract the ride type, price, and ETA. "
                f"Return a strict JSON object with keys: 'app', 'ride_type', 'price', 'eta'. "
                f"Ensure strict JSON format."
            )

        # Execute via Wrapper
        result_data = {"app": app_name, "status": "failed", "data": {}, "numeric_price": float('inf')}

        try:
            print(f"[RideAgent] 🧠 Running Agent on {app_name}...")
            result = await self.runner.run_agent(app_name, goal)
            
            if result:
                 # Check for wrapper failure pattern
                if result.get("status") == "failed" and "data" not in result:
                     print(f"[Warn] Agent reported failure: {result}")
                else:
                    result_data["data"] = result
                    result_data["status"] = "success"
                    # Default parsing
                    price_val = result.get("price", "inf")
                    result_data["numeric_price"] = self._parse_price(price_val)
            
            return result_data

        except Exception as e:
            print(f"[Error] Task Execution Failed for {app_name}: {e}")
            return result_data

    async def compare_rides(self, pickup, drop, preference="cab"):
        apps = ["Uber", "Ola"]
        results = {}

        for app in apps:
            res = await self.execute_task(app, pickup, drop, preference, action="compare")
            results[app] = res
            # Cooldown to allow app switching/closing
            await asyncio.sleep(3)

        # Comparison Logic
        print("\n--- Final Aggregated Results ---")
        best_deal = None
        min_price = float('inf')

        for app, res in results.items():
            if res["status"] == "success":
                price = res["numeric_price"]
                print(f"{app}: {res['data'].get('ride_type')} - {res['data'].get('price')} (Numeric: {price})")
                
                if price < min_price:
                    min_price = price
                    best_deal = res
            else:
                print(f"{app}: Failed to get data.")

        results["best_deal"] = best_deal

        if best_deal:
            print(f"\n🏆 Best Deal: {best_deal['app']} - {best_deal['data'].get('price')}")
        else:
            print("\n❌ Could not determine best deal.")
        
        return results

    async def book_cheapest_ride(self, pickup, drop, preference="cab"):
        """
        High-level method to Find Cheapest -> Book It.
        """
        print(f"\n[RideAgent] 🤖 Autonomous Booking Sequence Initiated...")
        
        # 1. Compare
        results = await self.compare_rides(pickup, drop, preference)
        best_deal = results.get("best_deal")
        
        if not best_deal:
            print("[Error] No valid rides found to book.")
            return {"status": "failed", "message": "No rides found"}
        
        target_app = best_deal['app']
        price = best_deal['data'].get('price')
        print(f"[RideAgent] 🏆 Best Deal identified: {target_app} @ {price}. Proceeding to BOOK...")
        
        # 2. Book
        booking_result = await self.execute_task(target_app, pickup, drop, preference, action="book")
        
        print(f"\n[RideAgent] Booking Status for {target_app}: {booking_result.get('status')}")
        if booking_result.get('status') == 'success':
             print(f"✅ Cab Booked! Driver Details: {booking_result['data'].get('driver_details')}")
        else:
             print("❌ Booking Failed.")

        return booking_result

async def main():
    parser = argparse.ArgumentParser(description="Ride Comparison Agent (Uber vs Ola)")
    parser.add_argument("--pickup", required=True, help="Pickup location")
    parser.add_argument("--drop", required=True, help="Drop location")
    parser.add_argument("--preference", default="cab", choices=["cab", "auto", "sedan"], help="Preferred ride type")
    parser.add_argument("--action", default="compare", choices=["compare", "book"], help="Action to perform")
    args = parser.parse_args()

    # Use models/gemini-2.5-flash as per new standard
    agent = RideComparisonAgent(model="models/gemini-2.5-flash")
    
    if args.action == "book":
        await agent.book_cheapest_ride(args.pickup, args.drop, args.preference)
    else:
        await agent.compare_rides(args.pickup, args.drop, args.preference)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

