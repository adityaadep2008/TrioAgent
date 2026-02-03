import os
import json
import argparse
import asyncio
import sys
import time
import ast 
from dotenv import load_dotenv

# Import MobileRun Wrapper
try:
    from agents.mobile_run_wrapper import MobileRunWrapper
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))
    try:
        from agents.mobile_run_wrapper import MobileRunWrapper
    except ImportError:
         print("CRITICAL ERROR: 'agents.mobile_run_wrapper' not found.")
         sys.exit(1)

# Import Commerce Agent 
try:
    from commerce_agent import CommerceAgent
except ImportError:
    print("CRITICAL ERROR: 'commerce_agent.py' not found.")
    sys.exit(1)

load_dotenv()

class EventCoordinatorAgent:
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.runner = MobileRunWrapper(provider=provider, model=model)
        self.commerce_bot = CommerceAgent(provider=provider, model=model)

    async def send_invite(self, contact_name: str, message: str, app_name: str = "WhatsApp") -> dict:
        print(f"   📨 Sending Invite to: {contact_name}")
        
        goal = (
            f"1. Open '{app_name}'. "
            f"2. IF you see a 'Back' button (arrow) at the top left, Click it to return to the contact list. "
            f"3. Click the 'Search' icon. "
            f"4. Click the 'Search...' input field at the top to ensure it is focused. "
            f"5. Type '{contact_name}' in the search bar. "
            f"6. Wait for the result '{contact_name}' to appear in the list below. "
            f"7. Click the contact found. "
            f"8. Type '{message}' in the message box. "
            f"9. Click the Send button. "
            f"10. Return strict JSON: {{'status': 'success'}}. "
            f"CRITICAL: Do NOT read any messages. Just send and exit."
        )
        return await self.runner.run_agent(app_name, goal)

    async def check_response(self, contact_name: str, invite_snippet: str, app_name: str = "WhatsApp") -> dict:
        print(f"   🔍 Checking {contact_name}...")
        goal = (
            f"1. Open '{app_name}'. "
            f"2. Navigate to the main Chat List (press Back if in a chat). "
            f"3. Search for contact '{contact_name}'. "
            f"4. Tap contact to open chat. "
            f"5. Read the LAST message. "
            f"6. Check if it's from the contact (left side) and NOT our invite (containing '{invite_snippet[:15]}'). "
            f"7. If it IS a new reply (e.g. they say 'Masala Dosa'), extract the item. "
            f"8. Return strict JSON: {{'status': 'new_reply', 'items': ['Item1']}} or {{'status': 'waiting'}}. "
            f"CRITICAL: If a food item is found, you MUST set 'status' to 'new_reply'. Do NOT set it to 'waiting'."
        )
        return await self.runner.run_agent(app_name, goal)
    
    async def go_home(self) -> dict:
        """Helper to ensure device is at Home Screen (via DroidRun default or MobileRun capability)."""
        print("   🏠 Navigating to Home Screen...")
        goal = "Press the System Home Button immediately. Do NOT swipe. Do NOT look for keyboard. Just press 'Home'."
        # We can run this on any registered app context, usually effectively resets state
        # Or we can treat "System" as a pseudo-app if MobileRun supports it, otherwise default to DroidRun fallback
        return await self.runner._run_local_droid(goal) 

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
        
        print(f"      🏆 Winner: {best_app} ({best_restaurant}) @ {best_price}")
        
        return {
            "item_wanted": item,
            "best_app": best_app,
            "best_price": best_price,
            "best_restaurant": best_restaurant,
            "exact_title": best_title,
            "platform_data": results # Saving raw data too
        }

    async def organize_event(self, contacts_str, event_details):
        contacts = [c.strip() for c in contacts_str.split(",")]
        
        invite_msg = (
            f"Hi! Invited to {event_details['name']} on {event_details['date']}. "
            f"Loc: {event_details['location']}. "
            f"Please Reply with FOOD PREFERENCE (e.g. Pizza)."
        )
        
        # --- PHASE 1: INVITE EVERYONE ---
        print(f"\n=== 📨 PHASE 1: SENDING INVITES ===")
        print(f"Targeting: {contacts}")
        
        for contact in contacts:
            await self.go_home() # Clean state start
            await self.send_invite(contact, invite_msg)
            print(f"   🏠 Resetting to Home after invite to {contact}...")
            await self.go_home() 
            await asyncio.sleep(2)
        print("✅ Phase 1 Complete: All invites sent.\n")

        # --- PHASE 2: POLLING & RESEARCH ---
        print(f"=== 👂 PHASE 2: POLLING & RESEARCH (Loop) ===")
        
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
                await self.go_home()
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
                        print(f"   💾 Data saved for {contact}.")
                    else:
                        print(f"   ℹ️ {contact} replied but no items found.")
                else:
                     print(f"   ⏳ {contact} hasn't replied yet.")
                
                await asyncio.sleep(2)
            
            # DORMANT STATE
            print("   💤 Entering Dormant State... Waking up in 10s...")
            await self.go_home() 
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
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())