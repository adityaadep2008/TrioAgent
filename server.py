import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Agents
from commerce_agent import CommerceAgent
from ride_comparison_agent import RideComparisonAgent
from pharmacy_agent import PharmacyAgent
from event_coordinator_agent import EventCoordinatorAgent
from agents.general_agent import GeneralAgent
from fastapi.staticfiles import StaticFiles

# Voyager-1 Imports
from agents.transit_agent import TransitManager
from agents.stay_agent import StayManager
from trip_visualizer import TripVisualizer
from schemas import FullTripPlan

# Import Factory
from agents.agent_factory import AgentFactory

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DroidServer")

app = FastAPI()

# Mount Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- InMemory Task Store ---
# Structure: { task_id: { "id": str, "persona": str, "status": str, "logs": list, "result": Any, "timestamp": str } }
task_history: List[Dict[str, Any]] = []

def add_task_record(task_id: str, persona: str, payload: Any):
    record = {
        "id": task_id,
        "persona": persona,
        "status": "running",
        "created_at": datetime.now().isoformat(),
        "logs": [],
        "result": None,
        "payload": payload.dict()
    }
    task_history.insert(0, record) # Newest first
    return record

def update_task_status(task_id: str, status: str, result: Any = None):
    for task in task_history:
        if task["id"] == task_id:
            task["status"] = status
            if result:
                task["result"] = result
            break

def append_task_log(task_id: str, message: str):
    for task in task_history:
        if task["id"] == task_id:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            task["logs"].append(log_entry)
            break

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # Legacy support if needed, but we prefer structured
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

    async def broadcast_json(self, data: Dict[str, Any]):
        message = json.dumps(data, default=str)
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Data Models
class TaskPayload(BaseModel):
    persona: str
    instruction: Optional[str] = None # Universal instruction
    product: Optional[str] = None
    url: Optional[str] = None
    # For Rider
    pickup: str = None
    drop: str = None
    preference: str = "cab" # auto, cab, sedan
    
    # For Patient: List of {name, qty}
    medicine: Any = [] 
    # For Foodie
    food_item: str = None
    action: str = "search" # 'search' or 'order'
    # For Coordinator: List of names (str)
    event_name: str = None
    guest_list: List[str] = [] 
    
    # For Traveller
    source: str = None
    destination: str = None
    date: str = None
    date: str = None
    user_interests: str = None

class ChatPayload(BaseModel):
    session_id: str
    message: str
    
from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

# --- CHAT ENDPOINT ---
general_agent = GeneralAgent()

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    """Voice OS Endpoint"""
    logger.info(f"Chat Request: {payload.message}")
    response = await general_agent.chat(payload.session_id, payload.message)
    return response

@app.get("/tasks")
async def get_tasks():
    return task_history

@app.get("/tasks/{task_id}")
async def get_task_details(task_id: str):
    for task in task_history:
        if task["id"] == task_id:
            return task
    return {"error": "Task not found"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def log_and_broadcast(task_id: str, message: str):
    """Save log to history and broadcast to WS"""
    append_task_log(task_id, message)
    await manager.broadcast_json({
        "type": "log",
        "task_id": task_id,
        "message": message
    })

async def run_agent_task(payload: TaskPayload):
    """
    Executes the agent logic based on persona.
    Broadcasts logs to WebSocket.
    """
    task_id = str(uuid.uuid4())
    add_task_record(task_id, payload.persona, payload)
    
    # Notify start
    await manager.broadcast_json({
        "type": "start",
        "task_id": task_id,
        "persona": payload.persona,
        "timestamp": datetime.now().isoformat()
    })

    await log_and_broadcast(task_id, f"🚀 Starting Executor for Persona: {payload.persona}")
    
    result = None
    status = "failed"
    
    try:
        if payload.persona == "shopper":
            agent = CommerceAgent(model="models/gemini-2.5-flash")
            await log_and_broadcast(task_id, f"Searching for {payload.product or payload.url} on Amazon/Flipkart...")
            
            result = await agent.execute_task("Amazon", payload.product, "product", url=payload.url)
            
            if result['status'] == 'failed':
                 await log_and_broadcast(task_id, "Amazon failed, trying Flipkart...")
                 result = await agent.execute_task("Flipkart", payload.product, "product", url=payload.url)
                 
        elif payload.persona == "rider":
            agent = RideComparisonAgent(model="models/gemini-2.5-flash")
            pref_msg = f" ({payload.preference.upper()})" if payload.preference else ""
            
            await log_and_broadcast(task_id, f"Vehicle Preference: {payload.preference or 'Any'}")
            
            if payload.action == 'book':
                await log_and_broadcast(task_id, f"Initiating Autonomous Booking Sequence to {payload.drop}...")
                
                # Use book_cheapest_ride which handles logic internally
                booking_res = await agent.book_cheapest_ride(payload.pickup, payload.drop, payload.preference)
                
                if booking_res and booking_res.get('status') == 'success':
                     driver = booking_res['data'].get('driver_details', 'Unknown')
                     car = booking_res['data'].get('cab_details', 'Vehicle')
                     price = booking_res['data'].get('price', 'N/A')
                     eta = booking_res['data'].get('eta', 'N/A')
                     
                     msg = f"✅ Ride Booked! {car} ({driver}) arriving in {eta}. Fare: {price}"
                     status = "success"
                     result = booking_res
                else:
                     msg = "❌ Booking Failed. Could not find ride or confirm."
                     status = "failed"
                     result = booking_res
                
                await log_and_broadcast(task_id, msg)

            else:
                # Compare Only
                await log_and_broadcast(task_id, f"Comparing rides from {payload.pickup} to {payload.drop}...")
                full_res = await agent.compare_rides(payload.pickup, payload.drop, payload.preference)
                
                best = full_res.get('best_deal')
                if best:
                    price = best['data'].get('price')
                    app_name = best['app']
                    msg = f"Best Option: {app_name} @ {price}"
                    status = "success"
                    result = {
                        "status": "success",
                        "message": msg,
                        "details": full_res
                    }
                else:
                    msg = "No rides found."
                    status = "failed"
                    result = {"status": "failed", "message": msg}
                
                await log_and_broadcast(task_id, msg)
            
        elif payload.persona == "patient":
            agent = PharmacyAgent(model="models/gemini-2.5-flash")
            await log_and_broadcast(task_id, f"Searching for medicines: {len(payload.medicine) if isinstance(payload.medicine, list) else 1} items...")
            
            # Now passing list of dicts directly
            full_res = await agent.compare_prices(payload.medicine, "patient")
            result = full_res.get('best_option', {"status": "failed"})

        elif payload.persona == "foodie":
             agent = CommerceAgent(model="models/gemini-2.5-flash")
             await log_and_broadcast(task_id, f"🍔 Foodie Mode Activated: {payload.action.upper()} '{payload.food_item}'")
             
             if payload.action == 'order':
                 await log_and_broadcast(task_id, "Initiating autonomous order sequence...")
                 order_res = await agent.auto_order_cheapest(payload.food_item)

                 final_status = order_res.get('order_status', {}).get('status', 'unknown')
                 if final_status == 'success':
                     msg = "✅ Order Placed Successfully!"
                 else:
                     msg = "⚠️ Order Attempted (Check Device)."

                 result = {
                     "status": "success",
                     "message": msg,
                     "details": order_res
                 }

             else:
                 await log_and_broadcast(task_id, "Searching Zomato and Swiggy...")
                 results = {}
                 platforms = ["Zomato", "Swiggy"]
                 for p in platforms:
                      await log_and_broadcast(task_id, f"Checking {p}...")
                      res = await agent.execute_task(p, payload.food_item, "food item", action="search")
                      results[p.lower()] = res
                      await asyncio.sleep(1)
                 
                 z_price = results.get('zomato', {}).get('data', {}).get('price', 'N/A')
                 s_price = results.get('swiggy', {}).get('data', {}).get('price', 'N/A')
                 
                 zp = float(results.get('zomato', {}).get('data', {}).get('numeric_price', float('inf')))
                 sp = float(results.get('swiggy', {}).get('data', {}).get('numeric_price', float('inf')))
                 
                 winner = "None"
                 if zp < sp: winner = "Zomato"
                 elif sp < zp: winner = "Swiggy"
                 elif zp == sp and zp != float('inf'): winner = "Tie"

                 await log_and_broadcast(task_id, f"Prices found: Zomato ({z_price}), Swiggy ({s_price})")
                 result = {
                     "status": "success", 
                     "message": f"Best Deal Found: {winner}. (Zomato: {z_price}, Swiggy: {s_price})",
                     "details": results
                 }

        elif payload.persona == "coordinator":
            agent = EventCoordinatorAgent(model="models/gemini-2.5-flash")
            await log_and_broadcast(task_id, f"🎪 Orchestrating Event: {payload.event_name}")
            
            # Passing list of strings directly to organize_event
            await agent.organize_event(payload.guest_list, {
                "name": payload.event_name,
                "date": "TBD", 
                "location": "TBD",
                "time": "Evening"
            })
            result = {"status": "success", "message": "Event Orchestration Complete"}

        elif payload.persona == "traveller":
            await log_and_broadcast(task_id, f"✈️ Starting Voyager-1: Trip to {payload.destination}...")
            
            transit_agent = TransitManager()
            stay_agent = StayManager()
            
            # 1. Flight (Outbound)
            await log_and_broadcast(task_id, f"Searching OUTBOUND flight from {payload.source} to {payload.destination}...")
            flight = await transit_agent.find_best_flight(payload.source, payload.destination, payload.date)
            await log_and_broadcast(task_id, f"✅ Outbound Found: {flight.airline} ({flight.price})")
            
            # Flight (Return) - Optional
            return_flight = None
            if payload.end_date:
                await log_and_broadcast(task_id, f"Searching RETURN flight from {payload.destination} to {payload.source} on {payload.end_date}...")
                try:
                    return_flight = await transit_agent.find_best_flight(payload.destination, payload.source, payload.end_date)
                    await log_and_broadcast(task_id, f"✅ Return Found: {return_flight.airline} ({return_flight.price})")
                except Exception as e:
                    await log_and_broadcast(task_id, f"⚠️ Return flight search failed: {e}")
            
            # 2. Cab
            await log_and_broadcast(task_id, f"Booking cab for arrival at {flight.arrival_time}...")
            cab = await transit_agent.book_cab(payload.destination, flight.arrival_time)
            await log_and_broadcast(task_id, f"✅ Cab Scheduled: {cab.provider} at {cab.pickup_time}")
            
            # 3. Hotel
            await log_and_broadcast(task_id, f"Finding hotels in {payload.destination}...")
            hotel = await stay_agent.find_hotel(payload.destination, payload.date)
            await log_and_broadcast(task_id, f"✅ Hotel Found: {hotel.name} ({hotel.price_per_night})")
            
            # 4. Itinerary
            await log_and_broadcast(task_id, f"Generating itinerary based on: {payload.user_interests}...")
            itinerary = await stay_agent.generate_itinerary(hotel.name, payload.user_interests)
            await log_and_broadcast(task_id, f"✅ Itinerary Generated for {len(itinerary)} days.")
            
            # Compile
            full_plan = FullTripPlan(
                flight=flight,
                arrival_cab=cab,
                hotel=hotel,
                daily_schedule=itinerary
            )
            
            # 5. Visualizer
            await log_and_broadcast(task_id, "Generating Trip Visualization...")
            mermaid_code = TripVisualizer.generate_mermaid(full_plan)
            full_plan.flowchart_code = mermaid_code
            
            result_dict = full_plan.dict()
            if return_flight:
                result_dict['return_flight'] = return_flight.dict()
            
            result = result_dict
            status = "success"
            msg = f"Trip to {payload.destination} is ready!"

        elif payload.persona == "universal":
            await log_and_broadcast(task_id, f"🤖 Universal Agent Mode: {payload.instruction}")
            
            # Use Factory directly
            res = await AgentFactory.run_task(
                app_identifier="Universal", 
                instruction=payload.instruction,
                provider="gemini"
            )
            
            if res.get("status") == "failed":
                status = "failed"
                msg = f"❌ Error: {res.get('error')}"
                result = res
            else:
                status = "success"
                msg = f"✅ Task Executed: {res.get('status')}"
                result = res
            
            await log_and_broadcast(task_id, msg)

        # Determine final status
        if result:
            status = "success"
            await log_and_broadcast(task_id, f"✅ Task Complete.")
        else:
            status = "failed"
            await log_and_broadcast(task_id, "❌ Task Failed or Returned No Data.")

    except Exception as e:
        logger.error(f"Task Error: {e}")
        status = "failed"
        result = {"error": str(e)}
        await log_and_broadcast(task_id, f"🔥 Error: {str(e)}")

    # Update History and Broadcast Completion
    update_task_status(task_id, status, result)
    await manager.broadcast_json({
        "type": "complete",
        "task_id": task_id,
        "status": status,
        "result": result
    })

@app.post("/task")
async def create_task(payload: TaskPayload):
    # Run in background
    asyncio.create_task(run_agent_task(payload))
    return {"status": "accepted", "message": "Task queued"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
