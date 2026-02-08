import os
import json
import argparse
import asyncio
import re
import sys
from typing import Optional
from dotenv import load_dotenv

import asyncio.subprocess
# try:
from droidrun.agent.droid.droid_agent import DroidAgent
from droidrun import AdbTools
# except ImportError:
#     print("CRITICAL ERROR: 'droidrun' library not found or incompatible version.")
#     print("Please ensure you have installed it: pip install droidrun")
#     sys.exit(1)

# Load environment variables
load_dotenv()

class CommerceAgent:
    """
    Professional Commerce Agent using DroidRun Framework.
    Follows the 'Brain' (Host) and 'Senses' (Portal) architecture.
    """
    
    def __init__(self, provider="gemini", model="gemini-1.5-flash"):
        self.provider = provider
        self.model = model
        self._ensure_api_keys()

    def _ensure_api_keys(self):
        if self.provider == "gemini" and not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
             # Fallback check
             print("[Warn] GEMINI_API_KEY not found in env, checking GOOGLE_API_KEY")

    def _parse_price(self, price_str):
        """Robust price parsing utility."""
        if not price_str: return float('inf')
        try:
            raw = str(price_str).strip()
            # print(f"[DEBUG] Parsing Price Raw: '{raw}'") # User requested investigation of mismatched logs
            
            clean = raw.lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            
            if match:
                 val = float(match.group())
                 # print(f"[DEBUG] Parsed Value: {val}")
                 return val
            else:
                 print(f"[Warn] Could not extract number from price string: '{raw}'")
                 return float('inf')
        except Exception as e:
            print(f"[Error] Price Parse Failed for '{price_str}': {e}")
            return float('inf')

    async def execute_task(self, app_name: str, query: Optional[str] = None, item_type: str = "product", action: str = "search", target_item: Optional[str] = None, url: Optional[str] = None) -> dict:
        """
        Spawns a DroidAgent to execute a specific commerce task.
        Uses Vision capabilities for better UI understanding.
        Action: 'search' (compare prices) or 'order' (buy item via COD).
        """
        print(f"\n[CommerceAgent] Initializing Task for: {app_name} (Action: {action})")
        
        # 1. Define Goal (Natural Language with Structural Constraints)
        if url:
            goal = (
                f"Open the app '{app_name}'. "
                f"Navigate directly to the URL: '{url}'. "
                f"Wait for the page to load. "
                f"Visually SCAN the product details page. "
                f"Extract the following details for the item: "
                f"1. Product Name (title) "
                f"2. Price (numeric value) "
                f"3. Rating "
                f"4. Restaurant Name "
                f"Return a strict JSON object with keys: 'title', 'price', 'rating', 'restaurant'. "
                f"If the page fails to load or details cannot be found, return status='failed'. "
            )
        elif action == "order":
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

        # 2. Configure Agent (Professional Pattern)
        # Using load_llm to avoid DroidrunConfig error
        from droidrun.agent.utils.llm_picker import load_llm

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        llm = load_llm(
            provider_name="GoogleGenAI",
            model=self.model,
            api_key=api_key
        )

        # Instantiate DroidAgent using proper Config (v0.3.2 style)
        try:
             from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
             
             manager_config = ManagerConfig(vision=True)
             executor_config = ExecutorConfig(vision=True)
             agent_config = AgentConfig(reasoning=False, manager=manager_config, executor=executor_config)
             telemetry_config = TelemetryConfig(enabled=False)
             config = DroidrunConfig(agent=agent_config, telemetry=telemetry_config)
             
             agent = DroidAgent(
                goal=goal,
                llms=llm,
                config=config
             )
        except ImportError:
             print("Fallback: Config classes not found, trying legacy init...")
             agent = DroidAgent(
                goal=goal,
                llm=llm,
                vision=True,
                reasoning=False
             )

        # 3. Execute
        start_data = {"platform": app_name, "status": "failed", "data": {}}
        try:
            print(f"[CommerceAgent] 🧠 Running Agent Logic...")
            result = await agent.run()
            print(f"[DEBUG] Raw Agent Result type: {type(result)}")
            print(f"[DEBUG] Raw Agent Result: {result}")
            
            # 4. Parse Output
            if result:
                # Handle DroidAgent Event objects
                if hasattr(result, 'reason'):
                     clean_json = str(result.reason).strip()
                else:
                     clean_json = str(result).strip()
                
                print(f"[DEBUG] Processing result string: {clean_json[:100]}...")

                # XML tag cleanup (common with DroidRun Reasoning)
                if "<request_accomplished" in clean_json:
                    try:
                        clean_json = clean_json.split(">")[1].split("</request_accomplished>")[0].strip()
                    except IndexError:
                        pass
                
                # Markdown cleanup
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                # Heuristic validation
                if clean_json.startswith("{"):
                    try:
                         data = json.loads(clean_json)
                         start_data["data"] = data
                         start_data["status"] = "success"
                         start_data["data"]["numeric_price"] = self._parse_price(data.get("price"))
                         # Ensure restaurant key exists
                         if "restaurant" not in start_data["data"]:
                              start_data["data"]["restaurant"] = "Unknown"
                    except json.JSONDecodeError:
                         print(f"[Warn] JSON Decode Error: {clean_json}")
                else:
                     print(f"[Warn] Agent output was not JSON: {clean_json[:50]}...")
            else:
                 print("[Warn] Agent returned None result.")
            
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
    parser = argparse.ArgumentParser(description="BestBuy-Agent: Commerce Automation (DroidRun)")
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
    # if sys.platform == 'win32':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())