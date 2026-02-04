import os
import json
import argparse
import asyncio
import sys
import time
import ast # Added for robust parsing
from dotenv import load_dotenv

# --- DroidRun Professional Architecture Imports ---
try:
    from droidrun.agent.droid.droid_agent import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun import AdbTools
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found.")
    sys.exit(1)

# Import Commerce Agent for price discovery and ordering
try:
    from commerce_agent import CommerceAgent
except ImportError:
    print("CRITICAL ERROR: 'commerce_agent.py' not found.")
    sys.exit(1)

load_dotenv()

class EventCoordinatorAgent:
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        self.commerce_bot = CommerceAgent(provider=provider, model=model)
        self._ensure_api_keys()

    def _ensure_api_keys(self):
        if self.provider == "gemini" and not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
             print("[Warn] GEMINI_API_KEY not found in env.")

    async def _run_agent(self, goal: str) -> dict:
        """Helper to run DroidAgent with Robust Regex Parsing."""
        # ... (Config setup same) ...
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        provider_name = "GoogleGenAI" if self.provider == "gemini" else self.provider
        
        llm = load_llm(provider_name=provider_name, model=self.model, api_key=api_key)
        
        tools = await AdbTools.create()
        
        agent = DroidAgent(
            goal=goal,
            llm=llm,
            tools=tools,
            vision=True,
            reasoning=False
        )
        
        try:
            print(f"      🧠 Analyzing...")
            result = await agent.run()
            
            # --- Robust Parsing ---
            raw_text = str(result.reason) if hasattr(result, 'reason') else str(result)
            import re
            
            # 1. Try finding JSON block between ```json ... ``` or just { ... }
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            
            clean_json = "{}"
            if json_match:
                clean_json = json_match.group(1)
            else:
                # Last resort cleanup
                clean_json = raw_text.strip()
                if "<request_accomplished" in clean_json:
                     clean_json = clean_json.split(">")[1].split("</request_accomplished>")[0].strip()

            try:
                # Primary Attempt: Standard JSON
                data = json.loads(clean_json)
                print(f"      📝 Agent Output: {json.dumps(data)}") 
                return data
            except json.JSONDecodeError:
                # Secondary Attempt: Python Literal Eval (handles single quotes)
                try:
                    data = ast.literal_eval(clean_json)
                    print(f"      📝 Agent Output (via AST): {json.dumps(data)}") 
                    return data
                except:
                     print(f"[Warn] JSON Parse Error. Raw Extracted: {clean_json[:100]}...")
                     return {"status": "failed", "raw": clean_json}
            except Exception as e:
                print(f"[Warn] Parse Error: {e}")
                return {"status": "failed", "raw": clean_json}
                
        except Exception as e:
            print(f"[Error] Agent Execution Failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def send_invite(self, contact_name: str, message: str, app_name: str = "WhatsApp") -> dict:
        print(f"   📨 Sending Invite to: {contact_name}")
        
        # Linear Goal: Step-by-step Execution
        goal = (
            f"Open '{app_name}'. "
            f"Navigate to the main Contact List or Search screen (if you see a Back button, press it). "
            f"Search for the contact '{contact_name}' by clicking the search icon and typing the name. "
            f"Tap the correct contact from the results list to open the chat. "
            f"Type the message '{message}' in the text box. "
            f"Click the Send button. "
            f"Return a strict JSON object: {{'status': 'success'}}. "
            f"Do NOT read previous messages."
        )
        return await self._run_agent(goal)

    async def check_response(self, contact_name: str, invite_snippet: str, app_name: str = "WhatsApp") -> dict:
        print(f"   � Checking {contact_name}...")
        goal = (
            f"Open '{app_name}'. "
            f"Navigate to the main Chat List (press Back if in a chat). "
            f"Search for contact '{contact_name}'. "
            f"Tap contact to open chat. "
            f"Read the LAST message. "
            f"Check if it's from the contact (left side) and NOT our invite (containing '{invite_snippet[:15]}'). "
            f"If it IS a new reply (e.g. they say 'Masala Dosa'), extract the item. "
            f"Return strict JSON: {{'status': 'new_reply', 'items': ['Item1']}} or {{'status': 'waiting'}}. "
            f"CRITICAL: If a food item is found, you MUST set 'status' to 'new_reply'. Do NOT set it to 'waiting'."
        )
        return await self._run_agent(goal)
    
    # ... (research_item, etc.)

    async def organize_event(self, contacts_str, event_details):
        # ... (Phase 1 remains same)
        contacts = [c.strip() for c in contacts_str.split(",")]
        # ...
        
        # --- PHASE 2: POLLING & RESEARCH ---
        # ...
        for i in range(max_cycles):
            # ...
            for contact in pending_contacts:
                # Poll
                await self.go_home() 
                res = await self.check_response(contact, invite_msg)
                
                # Check for 'new_reply' OR if 'items' exists and is not empty
                is_reply = res.get('status') == 'new_reply'
                has_items = res.get('items') and len(res.get('items')) > 0
                
                if is_reply or has_items:
                    items = res.get('items', [])
                    # ...
    
    # ... (research_item logic remains same)

    async def organize_event(self, contacts_input, event_details):
        if isinstance(contacts_input, list):
            contacts = contacts_input
        else:
            contacts = [c.strip() for c in contacts_input.split(",")]
        
        invite_msg = (
            f"Hi! Invited to {event_details['name']} on {event_details['date']}. "
            f"Loc: {event_details['location']}. "
            f"Please Reply with FOOD PREFERENCE."
        )
        
        # --- PHASE 1: INVITE EVERYONE ---
        print(f"\n=== 📨 PHASE 1: SENDING INVITES ===")
        print(f"Targeting: {contacts}")
        
        for contact in contacts:
            await self.go_home() # Clean state start
            await self.send_invite(contact, invite_msg)
            print(f"   🏠 Resetting to Home after invite to {contact}...")
            await self.go_home() # STRICT EXIT as requested
            await asyncio.sleep(2)
        print("✅ Phase 1 Complete: All invites sent & returned to Home.\n")

        # --- PHASE 2: POLLING & RESEARCH (Infinite) ---
        print(f"=== 👂 PHASE 2: POLLING & RESEARCH (Infinite Loop) ===")
        print(f"ℹ️  Agent will now enter Dormant State and wake up every 10s to check for replies.")
        
        # Central Data Structure
        order_plan = {c: {"status": "invited", "research_data": []} for c in contacts}
        
        cycle_count = 0
        while True:
            cycle_count += 1
            print(f"\n🔄 Cycle {cycle_count} (Infinite Mode)")
            
            pending_contacts = [c for c, data in order_plan.items() if data['status'] == "invited"]
            
            if not pending_contacts:
                print("✅ All contacts has replied and been researched!")
                break
            
            for contact in pending_contacts:
                # Poll
                await self.go_home() 
                res = await self.check_response(contact, invite_msg)
                
                print(f"      [DEBUG] Raw Response for {contact}: {res}")
                
                # Check for 'new_reply' OR if 'items' exists and is not empty
                # Case-insensitive check for reliability
                status = res.get('status', '').lower()
                is_reply = status == 'new_reply'
                has_items = res.get('items') and len(res.get('items')) > 0
                
                if is_reply or has_items:
                    items = res.get('items', [])
                    # Fallback
                    if not items and res.get('content'): items = [res.get('content')]
                    
                    if items:
                        print(f"   🎉 {contact} replied: {items}")
                        order_plan[contact]['status'] = "replied"
                        
                        # Research Loop
                        researched_items = []
                        for item in items:
                            data = await self.research_item(item)
                            if data: researched_items.append(data)
                        
                        order_plan[contact]['research_data'] = researched_items
                        order_plan[contact]['status'] = "researched"
                        print(f"   💾 Data saved for {contact}.")
                    else:
                        print(f"   ℹ️ {contact} replied but no items found. Content: {res.get('content')}")
                else:
                     print(f"   ⏳ {contact} hasn't replied yet.")
                
                await asyncio.sleep(2)

    async def go_home(self) -> dict:
        """Helper to ensure device is at Home Screen."""
        print("   🏠 Navigating to Home Screen...")
        goal = "Press the System Home Button immediately. Do NOT swipe. Do NOT look for keyboard. Just press 'Home'."
        return await self._run_agent(goal)

    async def research_item(self, item: str) -> dict:
        """Finds best price across Swiggy/Zomato. Returns Data Dict (No Order)."""
        print(f"      🔎 Researching Best Deal for: {item}...")
        platforms = ["Zomato", "Swiggy"]
        results = {}
        
        for p in platforms:
             await self.go_home() # Reset state to avoid "Already Open" loops
             await asyncio.sleep(2)
             
             print(f"      👉 Checking {p}...")
             res = await self.commerce_bot.execute_task(p, item, "food item", action="search")
             results[p.lower()] = res
             
             # Verbose Logging as requested
             status = res.get('status', 'failed')
             price = res.get('data', {}).get('price', 'N/A')
             print(f"         [{p}] Status: {status} | Price: {price}")
             
             await asyncio.sleep(2)
             
        z_data = results.get('zomato', {}).get('data', {})
        s_data = results.get('swiggy', {}).get('data', {})
        
        z_price = float(z_data.get('numeric_price', float('inf')))
        s_price = float(s_data.get('numeric_price', float('inf')))
        
        print(f"      ⚖️  Comparison: Zomato ({z_price}) vs Swiggy ({s_price})")
        
        if z_price == float('inf') and s_price == float('inf'):
            print(f"      ❌ Price not found for {item} on ANY platform.")
            return None

        best_app = "Swiggy"
        best_price = s_price
        best_title = s_data.get('title', item)
        best_restaurant = s_data.get('restaurant', 'Unknown')
        
        # Explicit Logic:
        # If Zomato exists and Swiggy fails (inf) -> Zomato wins
        # If Zomato exists and is cheaper than Swiggy -> Zomato wins
        if z_price < s_price: 
            best_app = "Zomato"
            best_price = z_price
            best_title = z_data.get('title', item)
            best_restaurant = z_data.get('restaurant', 'Unknown')
        
        print(f"      🏆 Winner: {best_app} @ {best_price}")
            
        print(f"      🏆 Winner: {best_app} ({best_restaurant}) @ {best_price}")
        
        return {
            "item_wanted": item,
            "best_app": best_app,
            "best_price": best_price,
            "best_restaurant": best_restaurant,
            "exact_title": best_title,
            "platform_data": results # Saving raw data too
        }

    async def organize_event(self, contacts_input, event_details):
        if isinstance(contacts_input, list):
            contacts = contacts_input
        else:
            contacts = [c.strip() for c in contacts_input.split(",")]
        
        invite_msg = (
            f"Hi! Invited to {event_details['name']} on {event_details['date']}. "
            f"Loc: {event_details['location']}. "
            f"Please Reply with FOOD PREFERENCE (e.g. Pizza)."
        )
        
        # --- PHASE 1: INVITE EVERYONE ---
        print(f"\n=== 📨 PHASE 1: SENDING INVITES ===")
        print(f"Targeting: {contacts}")
        
        for contact in contacts:
            await self.send_invite(contact, invite_msg)
            await asyncio.sleep(2)
        print("✅ Phase 1 Complete: All invites sent.\n")

        # --- PHASE 2: POLLING & RESEARCH ---
        print(f"=== 👂 PHASE 2: POLLING & RESEARCH (Loop) ===")
        
        # Central Data Structure
        order_plan = {c: {"status": "invited", "research_data": []} for c in contacts}
        
        max_cycles = 3
        
        for i in range(max_cycles):
            print(f"\n🔄 Cycle {i+1}/{max_cycles}")
            
            pending_contacts = [c for c, data in order_plan.items() if data['status'] == "invited"]
            
            if not pending_contacts:
                print("✅ All contacts has replied and been researched!")
                break
            
            for contact in pending_contacts:
                # Poll
                res = await self.check_response(contact, invite_msg)
                
                if res.get('status') == 'new_reply':
                    items = res.get('items', [])
                    # Fallback
                    if not items and res.get('content'): items = [res.get('content')]
                    
                    if items:
                        print(f"   🎉 {contact} replied: {items}")
                        order_plan[contact]['status'] = "replied"
                        
                        # Research Loop
                        researched_items = []
                        for item in items:
                            data = await self.research_item(item)
                            if data: researched_items.append(data)
                        
                        order_plan[contact]['research_data'] = researched_items
                        order_plan[contact]['status'] = "researched"
                        print(f"   � Data saved for {contact}.")
                    else:
                        print(f"   ℹ️ {contact} replied but no items found.")
                else:
                     print(f"   ⏳ {contact} hasn't replied yet.")
                
                await asyncio.sleep(2)
            
            # DORMANT STATE
            print("   💤 Entering Dormant State... Waking up in 10s...")
            await self.go_home() # Ensure we are at home while waiting
            await asyncio.sleep(10)

        # --- PHASE 3: BULK ORDER ---
        print(f"\n=== 🚀 PHASE 3: BULK ORDER EXECUTION ===")
        
        all_orders = []
        for person, data in order_plan.items():
            if data['status'] == 'researched' and data['research_data']:
                for item_data in data['research_data']:
                    item_data['person'] = person
                    all_orders.append(item_data)
        
        if not all_orders:
            print("⚠️ No valid orders to place.")
            return

        print(f"📋 Placing {len(all_orders)} orders...")
        print(json.dumps(all_orders, indent=2))
        
        for order in all_orders:
            print(f"\n🛒 Ordering for {order['person']}: {order['exact_title']} on {order['best_app']}...")
            await self.commerce_bot.execute_task(
                order['best_app'], 
                order['item_wanted'], 
                "food item", 
                action="order", 
                target_item=order['exact_title']
            )
            print("✅ Order Placed.")
            await asyncio.sleep(5)
            
        print("\n=== 🎉 EVENT COORDINATION COMPLETE ===")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contacts", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--time", required=True)
    parser.add_argument("--location", required=True)
    args = parser.parse_args()

    agent = EventCoordinatorAgent()
    
    details = {
        "name": args.event,
        "date": args.date,
        "time": args.time,
        "location": args.location
    }
    
    await agent.organize_event(args.contacts, details)

if __name__ == "__main__":
    # if sys.platform == 'win32':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())