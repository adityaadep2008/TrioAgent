from schemas import FullTripPlan

class TripVisualizer:
    @staticmethod
    def generate_mermaid(trip_plan: FullTripPlan) -> str:
        """
        Generates a Mermaid JS Graph TD string from the FullTripPlan.
        """
        graph = ["graph TD"]
        
        # 1. Home
        # Assuming trip starts some time before pickup, but for graph we can just start at Home
        graph.append(f"    Start((Home)) -->|Pick up| Cab1{{{{Cab: {trip_plan.arrival_cab.provider} {trip_plan.arrival_cab.pickup_time.strftime('%H:%M')}}}}}")
        
        # 2. Flight
        # Note: In the user prompt, logic was: Flight -> Cab -> Hotel. 
        # But wait, usually it's Home -> Cab -> Airport -> Flight -> Airport -> Cab -> Hotel.
        # The user example was: Home -> Cab -> Flight -> Cab -> Hotel.
        # My schemas have: flight, arrival_cab, hotel.
        # It seems we are missing the "departure cab" in the schema, but I must follow the Request.
        # The request said: "Function book_cab... schedule the ride based on the arrival_time + 45 mins buffer."
        # This implies 'arrival_cab' is the one at the destination.
        # The prompt EXAMPLE showed: 
        # Start((Home)) -->|10:00 AM| Cab1{{Uber to Airport}} --> ...
        # But my schema only has `arrival_cab`.
        # I will do my best to visualize what I have.
        # I will assume the `arrival_cab` is the one taking user FROM destination airport TO hotel.
        # The flight object has `arrival_time`.
        # So: Flight -> Arrival Cab -> Hotel.
        
        # Let's constructs nodes based on available data.
        
        # Flight Node
        flight_node = f"Flight[Flight: {trip_plan.flight.airline} {trip_plan.flight.flight_number}]"
        
        # Arrival Cab Node
        cab_node = f"CabArr{{{{Cab: {trip_plan.arrival_cab.provider} {trip_plan.arrival_cab.pickup_time.strftime('%H:%M')}}}}}"
        
        # Hotel Node
        hotel_node = f"Hotel>Hotel: {trip_plan.hotel.name}]"
        
        # Connecting them
        # Start(Home) -> Flight (Simplified, as we don't have departure details in schema yet, 
        # strictly following the prompt instructions for schemas: "flight, arrival_cab, hotel, daily_schedule")
        
        graph.append(f"    Start((Home)) -->|Fly| {flight_node}")
        graph.append(f"    {flight_node} -->|Arrive {trip_plan.flight.arrival_time.strftime('%H:%M')}| {cab_node}")
        graph.append(f"    {cab_node} -->|To Hotel| {hotel_node}")
        
        # Daily Schedule
        last_node = "Hotel"
        
        for day in trip_plan.daily_schedule:
            for i, activity in enumerate(day.activities):
                act_id = f"Day{day.day_number}Act{i}"
                act_node = f"{act_id}({activity.time}: {activity.description})"
                
                graph.append(f"    {last_node} -->|Next| {act_node}")
                last_node = act_id
        
        # Sleep
        graph.append(f"    {last_node} --> Sleep((Sleep))")
        
        return "\n".join(graph)
