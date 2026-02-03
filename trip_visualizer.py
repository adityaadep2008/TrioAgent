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
        
        def sanitize(text):
            if not text: return "Unknown"
            # Keep line simple: Alphanumeric, spaces, colons, hyphens only
            import re
            valid = re.sub(r'[^a-zA-Z0-9 :.-]', '', str(text))
            return valid.strip()

        # Nodes - Using simple box brackets [] for everything to ensure safety
        flight_label = sanitize(f"Flight: {trip_plan.flight.airline} - {trip_plan.flight.flight_number}")
        flight_node = f'Flight["{flight_label}"]'
        
        cab_label = sanitize(f"Cab: {trip_plan.arrival_cab.provider} at {trip_plan.arrival_cab.pickup_time.strftime('%H:%M')}")
        cab_node = f'CabArr["{cab_label}"]'
        
        hotel_label = sanitize(f"Hotel: {trip_plan.hotel.name}")
        hotel_node = f'Hotel["{hotel_label}"]'
        
        # Edges
        graph.append(f'    Start((Home)) -->|Fly| {flight_node}')
        
        arr_time = trip_plan.flight.arrival_time.strftime("%H:%M")
        graph.append(f'    {flight_node} -->|Arrive {arr_time}| {cab_node}')
        graph.append(f'    {cab_node} -->|To Hotel| {hotel_node}')
        
        # Schedule
        last_node = "Hotel"
        
        for day in trip_plan.daily_schedule:
            for i, activity in enumerate(day.activities):
                act_id = f"Day{day.day_number}Act{i}"
                label = sanitize(f"{activity.time}: {activity.description}")
                # Truncate
                if len(label) > 40: label = label[:37] + "..."
                
                act_node = f'{act_id}["{label}"]'
                
                graph.append(f"    {last_node} -->|Next| {act_node}")
                last_node = act_id
        
        graph.append(f"    {last_node} --> End((Sleep))")
        
        final_code = "\n".join(graph)
        print("\n--- DEBUG: Generated Mermaid Code ---\n")
        print(final_code)
        print("\n-------------------------------------\n")
        
        return final_code
