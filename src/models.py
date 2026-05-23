from pydantic import BaseModel
from typing import List, Dict, Optional

class CityLeg(BaseModel):
    city: str
    airport_codes: str    
    arrival_date: str     # "YYYY-MM-DD"
    departure_date: str   

class MultiCityRequest(BaseModel):
    origin_city: str      
    cities: List[str]     
    start_date: str       # "YYYY-MM-DD"
    return_date: str      

class FlightRequest(BaseModel):
    origin: str
    destination: str
    outbound_date: str
    return_date: str

class HotelRequest(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str

class ItineraryRequest(BaseModel):
    origin_city: str       
    destination_city: str  # e.g. "Minneapolis"
    check_in_date: str
    check_out_date: str

class FlightInfo(BaseModel):
    airline: str
    price: str
    duration: str
    stops: str
    departure: str
    arrival: str
    travel_class: str
    return_date: str
    airline_logo: str

class HotelInfo(BaseModel):
    name: str
    price: str
    rating: float
    location: str
    link: str

class AIResponse(BaseModel):
    flights: List[FlightInfo] = []
    hotels: List[HotelInfo] = []
    ai_flight_recommendation: str = ""
    ai_hotel_recommendation: str = ""
    itinerary: str = ""