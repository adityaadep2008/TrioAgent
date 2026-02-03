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

load_dotenv()

class PharmacyAgent:
    """
    Agent to compare medicine prices across PharmEasy, Apollo 24|7, and Tata 1mg.
    Uses MobileRun Cloud with DroidRun Fallback.
    """
    
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.runner = MobileRunWrapper(provider=provider, model=model)

    def _parse_price(self, price_str):
        if not price_str: return float('inf')
        try:
            clean = str(price_str).lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            # Handle "/ pack" text if present
            clean = clean.split('/')[0].strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            return float(match.group()) if match else float('inf')
        except:
            return float('inf')

    async def execute_task(self, app_name: str, medicine: str, role: str) -> dict:
        print(f"\n[PharmaAgent] Initializing Task for: {app_name} - {medicine} ({role} mode)")
        
        # Mode-specific instructions
        if role == "pharmacist":
            search_instruction = (
                f"Search for '{medicine}'. "
                f"Look specifically for 'bulk packs', 'combo packs', 'wholesale', or largest available strip sizes suitable for restocking. "
                f"If bulk options aren't explicitly labeled, find the standard pack with the best value."
            )
            report_instruction = "Report the Price per pack/unit."
        else:
            search_instruction = f"Search for '{medicine}'. Identify the exact medicine matching the name and dosage."
            report_instruction = "Report the Price."

        goal = (
            f"Open the app '{app_name}'. "
            f"If a 'Location Permission' popup appears, click 'While using the app' or 'Allow'. "
            f"Click on the search bar. "
            f"{search_instruction} "
            f"Visually identify the best result. "
            f"Extract the Price (numeric value). "
            f"Return a strict JSON object with keys: 'app', 'medicine', 'price', 'details'. "
            f"Ensure strict JSON format."
        )

        result_data = {"app": app_name, "medicine": medicine, "status": "failed", "data": {}, "numeric_price": float('inf')}

        try:
            print(f"[PharmaAgent] 🧠 Running Agent on {app_name} for {medicine}...")
            # Execute via Wrapper
            result = await self.runner.run_agent(app_name, goal)
            
            if result:
                # Check for wrapper failure pattern
                if result.get("status") == "failed" and "data" not in result:
                     print(f"[Warn] Agent reported failure: {result}")
                else:
                    result_data["data"] = result
                    result_data["status"] = "success"
                    # Default parsing
                    result_data["numeric_price"] = self._parse_price(result.get("price"))
            
            return result_data

        except Exception as e:
            print(f"[Error] Task Execution Failed for {app_name}: {e}")
            return result_data

    async def compare_prices(self, meds_str, role, apps_filter=None):
        all_apps = ["PharmEasy", "Apollo 24|7", "Tata 1mg"]
        
        if apps_filter:
            # Filter logic: simple case-insensitive partial match
            apps = []
            for requested in apps_filter:
                match = next((a for a in all_apps if requested.lower() in a.lower()), None)
                if match:
                    apps.append(match)
                else:
                    print(f"[Warn] App '{requested}' not supported. Available: {all_apps}")
            if not apps:
                print("[Error] No valid apps selected. Using default list.")
                apps = all_apps
        else:
            apps = all_apps

        # Parse medicines: "Name:Qty, Name:Qty"
        med_list = []
        for item in meds_str.split(','):
            parts = item.strip().split(':')
            name = parts[0].strip()
            qty = int(parts[1].strip()) if len(parts) > 1 else 1
            med_list.append({"name": name, "qty": qty})

        print(f"\n[PharmaAgent] processing List: {med_list}")
        print(f"[PharmaAgent] Apps Selected: {apps}")
        
        app_totals = {} # {app_name: {total_cost: float, items: [details]}}

        for app in apps:
            print(f"\n--- Checking {app} ---")
            total_cost = 0.0
            item_details = []
            all_found = True

            for med in med_list:
                res = await self.execute_task(app, med['name'], role)
                
                if res["status"] == "success":
                    price = res["numeric_price"]
                    qty = med['qty']
                    line_total = price * qty
                    total_cost += line_total
                    item_details.append({
                        "name": med['name'],
                        "unit_price": price,
                        "qty": qty,
                        "line_total": line_total,
                        "details": res['data'].get("details", "")
                    })
                    print(f"  > Found {med['name']} @ {price} x {qty} = {line_total}")
                else:
                    print(f"  > Failed to find {med['name']}")
                    all_found = False
                    break # Stop if one item not found, basket incomplete
                
                # Small cooldown between searches
                await asyncio.sleep(2)

            if all_found:
                app_totals[app] = {"total_cost": total_cost, "items": item_details}
            else:
                app_totals[app] = {"status": "incomplete"}
                print(f"  > Basket incomplete for {app}")
            
            # Cooldown betwen apps
            await asyncio.sleep(3)

        print(f"\n--- Final Aggregated Basket Results ---")
        best_option = None
        min_total = float('inf')

        for app, result in app_totals.items():
            if result.get("status") != "incomplete":
                total = result["total_cost"]
                print(f"{app}: Total Basket = ₹{total:.2f}")
                for item in result["items"]:
                    print(f"  - {item['name']}: ₹{item['unit_price']} x {item['qty']}")
                
                if total < min_total:
                    min_total = total
                    best_option = {"app": app, "total": total, "items": result["items"]}
            else:
                print(f"{app}: Incomplete Basket")

        if best_option:
            print(f"\n🏆 Best Basket Deal: {best_option['app']} - ₹{best_option['total']:.2f}")
        else:
            print("\n❌ Could not determine best basket option.")

async def main():
    parser = argparse.ArgumentParser(description="Pharmacy Agent (Basket Comparison)")
    parser.add_argument("--meds", required=True, help="List of medicines 'Name:Qty, Name:Qty'")
    parser.add_argument("--role", choices=['patient', 'pharmacist'], default='patient', help="User role")
    parser.add_argument("--apps", help="Comma-separated list of apps to use (e.g., 'Tata, Apollo')")
    args = parser.parse_args()

    apps_filter = [a.strip() for a in args.apps.split(',')] if args.apps else None
    
    agent = PharmacyAgent(model="models/gemini-2.5-flash")
    await agent.compare_prices(args.meds, args.role, apps_filter)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

