from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FlightDetails(BaseModel):
    airline: str
    flight_number: str
    price: str
    arrival_time: datetime

class CabDetails(BaseModel):
    provider: str
    pickup_time: datetime
    estimated_price: str

class ItineraryActivity(BaseModel):
    time: str
    description: str

class ItineraryDay(BaseModel):
    day_number: int
    activities: List[ItineraryActivity]

class HotelDetails(BaseModel):
    name: str
    address: str
    price_per_night: str

class FullTripPlan(BaseModel):
    flight: FlightDetails
    arrival_cab: CabDetails
    hotel: HotelDetails
    daily_schedule: List[ItineraryDay]
    flowchart_code: Optional[str] = None
