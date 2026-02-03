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

class CommerceAgent:
    """
    Professional Commerce Agent using MobileRun Cloud (with DroidRun Fallback).
    """
    
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.runner = MobileRunWrapper(provider=provider, model=model)

    def _parse_price(self, price_str):
        """Robust price parsing utility."""
        if not price_str: return float('inf')
        try:
            raw = str(price_str).strip()
            clean = raw.lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            
            if match:
                 val = float(match.group())
                 return val
            else:
                 print(f"[Warn] Could not extract number from price string: '{raw}'")
                 return float('inf')
        except Exception as e:
            print(f"[Error] Price Parse Failed for '{price_str}': {e}")
            return float('inf')

    async def execute_task(self, app_name: str, query: str, item_type: str, action: str = "search", target_item: str = None) -> dict:
        """
        Spawns a MobileRun/DroidAgent to execute a specific commerce task.
        """
        print(f"\n[CommerceAgent] Initializing Task for: {app_name} (Action: {action})")
        
        # 1. Define Goal
        if action == "order":
            item_instruction = f"find the item '{target_item}'" if target_item else "Select the first relevant item"
            goal = (
                f"Open the app '{app_name}'. "
                f"Search for '{query}'. "
                f"Wait for results. "
                f"Visually SCAN and {item_instruction}. "
                f"Click 'Add' or 'Add to Cart'. "
                f"Go to View Cart. "
                f"Click 'Proceed to Pay' or 'Checkout'. "
                f"Select 'Cash on Delivery' (COD) or 'Pay on Delivery'. "
                f"CRITICAL: Click 'Place Order', 'Confirm Order', or 'Swipe to Pay' to finalize the booking. "
                f"Return a strict JSON object with keys: 'status' (success/failed), 'order_id', 'final_price'. "
            )
        else:
            goal = (
                f"Open the app '{app_name}'. "
                f"Search for '{query}'. "
                f"Wait for the search results to load. "
                f"Visually SCAN the search results. "
                f"Identify multiple items matching '{query}'. "
                f"COMPARE their prices and Select the CHEAPEST option. "
                f"Extract the following details for the CHEAPEST item: "
                f"1. Product Name (title) "
                f"2. Price (numeric value) "
                f"3. Rating "
                f"4. Restaurant Name "
                f"Return a strict JSON object with keys: 'title', 'price', 'rating', 'restaurant'. "
                f"If no exact match is found, find the closest match. "
            )

        # 2. Execute via Wrapper
        start_data = {"platform": app_name, "status": "failed", "data": {}}
        
        try:
             result = await self.runner.run_agent(app_name, goal)
             
             # Handle Output
             if result:
                 # Check for explicit failure from wrapper parse
                 if result.get("status") == "failed" and "data" not in result:
                      print(f"[Warn] Agent reported failure: {result}")
                 else:
                      start_data["data"] = result
                      start_data["status"] = "success"
                      start_data["data"]["numeric_price"] = self._parse_price(result.get("price"))
                      if "restaurant" not in start_data["data"]:
                          start_data["data"]["restaurant"] = "Unknown"
             return start_data

        except Exception as e:
             print(f"[Error] Task Execution Failed: {e}")
             return start_data


    async def auto_order_cheapest(self, query):
        """
        High-level method to Find Cheapest Food -> Order It.
        """
        print(f"\n[CommerceAgent] 🤖 Autonomous Ordering Sequence Initiated for: '{query}'")
        
        # 1. Compare Prices
        platforms = ["Zomato", "Swiggy"]
        results = {}
        
        for platform in platforms:
            res = await self.execute_task(platform, query, "food item", action="search")
            results[platform.lower()] = res
            await asyncio.sleep(2)

        # 2. Determine Victor
        z_price = float('inf')
        s_price = float('inf')
        
        if results.get('zomato', {}).get('status') == 'success':
            z_price = results['zomato']['data'].get('numeric_price', float('inf'))
            
        if results.get('swiggy', {}).get('status') == 'success':
             s_price = results['swiggy']['data'].get('numeric_price', float('inf'))
             
        victor = None
        target_app = None
        target_title = None
        
        if z_price < s_price:
            victor = results['zomato']
            target_app = "Zomato"
            target_title = victor['data'].get('title')
        elif s_price < z_price:
             victor = results['swiggy']
             target_app = "Swiggy"
             target_title = victor['data'].get('title')
        elif s_price == z_price and s_price != float('inf'):
             target_app = "Swiggy" # Default to Swiggy on tie
             victor = results['swiggy']
             target_title = victor['data'].get('title')
        
        if not target_app:
             print("\n❌ Could not determine valid pricing on either app. Aborting order.")
             return results

        print(f"\n[CommerceAgent] 🏆 Best Deal identify: {target_app} @ {victor['data'].get('price')}")
        print(f"Details: {target_title}")
        print(f"Proceeding to ORDER on {target_app}...")
        
        # 3. Order
        # We perform the order action on the winning app with specific target
        booking_result = await self.execute_task(target_app, query, "food item", action="order", target_item=target_title)
        
        results["order_status"] = booking_result
        return results

async def main():
    parser = argparse.ArgumentParser(description="BestBuy-Agent: Commerce Automation (MobileRun)")
    parser.add_argument("--task", choices=['shopping', 'food'], default='shopping')
    parser.add_argument("--query", required=True)
    parser.add_argument("--action", choices=['search', 'order'], default='search', help="Action to perform")
    parser.add_argument("--app", help="Specific app to use (e.g., Swiggy, Zomato)")
    args = parser.parse_args()

    # Initialize Controller
    commerce_bot = CommerceAgent(provider="gemini", model="models/gemini-2.5-flash")
    
    # Workflow Logic
    if args.action == "order" and not args.app:
        # Autonomous Comparative Ordering
        await commerce_bot.auto_order_cheapest(args.query)
    else:
        # Standard Execution (Search or Specific App Order)
        if args.task == "shopping":
            platforms = ["Amazon", "Flipkart"]
            item_type = "product"
        else:
            platforms = ["Zomato", "Swiggy"]
            item_type = "food item"
        
        if args.app:
            platforms = [p for p in platforms if p.lower() == args.app.lower()]

        results = {}
        for platform in platforms:
            res = await commerce_bot.execute_task(platform, args.query, item_type, action=args.action)
            results[platform.lower()] = res
            await asyncio.sleep(2)
            
        print("\n--- Final Results ---")
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
