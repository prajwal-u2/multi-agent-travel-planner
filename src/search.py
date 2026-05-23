import asyncio
import json
import airportsdata
from serpapi import GoogleSearch
from fastapi import HTTPException
import logging
from models import FlightRequest, HotelRequest, CityLeg
from os import getenv

_airports = airportsdata.load("IATA")

# Initialize Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Search:
    async def run_search(self, params):
        """function to run SerpAPI asynchronosuly"""
        try:
            return await asyncio.to_thread(lambda: GoogleSearch(params).get_dict())
        except Exception as e:
            logger.exception(f"SerpAPI Search Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search Error: {str(e)}")
    
    def search_airport(self, city: str) -> str:
        """Resolve a city name to a comma-separated list of IATA codes for all matching airports."""
        logger.info(f"resolving airport code(s) for: {city}")
        city_lower = city.strip().lower()
        matches = [
            (code, info) for code, info in _airports.items()
            if city_lower in info.get("city", "").lower()
        ]
        if not matches:
            raise HTTPException(status_code=400, detail=f"Could not find airport for city: {city}")
        result = ",".join(code for code, _ in matches)
        logger.info(f"resolved {city} → {result}")
        return result

    async def search_flights(self, flight_request: FlightRequest):
        """function to search for flights"""
        logger.info(f"searching for flights: {flight_request.origin} to {flight_request.destination}")
        params = {
            "api_key": getenv("SERP_API_KEY"),
            "engine": "google_flights",
            "hl": "en",
            "gl": "us",
            "departure_id": flight_request.origin.strip().upper(),
            "arrival_id": flight_request.destination.strip().upper(),
            "outbound_date": flight_request.outbound_date,
            "return_date": flight_request.return_date,
            "currency": "USD"
        }

        search_results = await self.run_search(params)
        flights = search_results.get("best_flights") or search_results.get("other_flights") or []
        return flights
    
    async def search_hotels(self, hotel_request: HotelRequest):
        """function to search for hotels"""
        logger.info(f"searching for hotels: {hotel_request.location}")
        params = {
            "api_key": getenv("SERP_API_KEY"),
            "engine": "google_hotels",
            "q": hotel_request.location,
            "hl": "en",
            "gl": "us",
            "check_in_date": hotel_request.check_in_date,
            "check_out_date": hotel_request.check_out_date,
            "currency": "USD",
            "sort_by": 3,
            "rating": 8
        }

        search_results = await self.run_search(params)
        hotels = search_results.get("properties")
        return hotels

    def format_flights(self, flights: list) -> str:
        if not flights:
            return "No flights found."
        lines = []
        for i, f in enumerate(flights, 1):
            legs = f.get("flights", [])
            airline = legs[0].get("airline", "N/A") if legs else "N/A"
            travel_class = legs[0].get("travel_class", "N/A") if legs else "N/A"
            departure = legs[0].get("departure_airport", {}).get("time", "N/A") if legs else "N/A"
            arrival = legs[-1].get("arrival_airport", {}).get("time", "N/A") if legs else "N/A"
            stops = len(legs) - 1
            duration = f"{f.get('total_duration', 0) // 60}h {f.get('total_duration', 0) % 60}m"
            price = f"${f.get('price', 'N/A')}"
            lines.append(
                f"Flight {i}: {airline} | {price} | {duration} | "
                f"{'Nonstop' if stops == 0 else f'{stops} stop(s)'} | "
                f"Departs {departure} | Arrives {arrival} | {travel_class}"
            )
        return "\n".join(lines)

    def build_multi_city_json(self, legs: list, origin_codes: str, return_date: str) -> str:
        stops = []
        for i, leg in enumerate(legs):
            from_codes = origin_codes if i == 0 else legs[i - 1].airport_codes
            stops.append({
                "date": leg.arrival_date,
                "departure_id": from_codes,
                "arrival_id": leg.airport_codes
            })
        stops.append({
            "date": return_date,
            "departure_id": legs[-1].airport_codes,
            "arrival_id": origin_codes
        })
        return json.dumps(stops)

    async def search_multi_city_flights(self, legs: list, origin_codes: str, return_date: str) -> list:
        logger.info(f"searching multi-city flights across {len(legs)} legs")
        params = {
            "api_key": getenv("SERP_API_KEY"),
            "engine": "google_flights",
            "hl": "en",
            "gl": "us",
            "type": "3",
            "currency": "USD",
            "multi_city_json": self.build_multi_city_json(legs, origin_codes, return_date)
        }
        result = await self.run_search(params)
        return result.get("best_flights") or result.get("other_flights") or []

    def format_multi_city_flights(self, flights: list) -> str:
        if not flights:
            return "No flights found."
        lines = []
        for i, f in enumerate(flights, 1):
            legs = f.get("flights", [])
            price = f"${f.get('price', 'N/A')}"
            total_duration = f"{f.get('total_duration', 0) // 60}h {f.get('total_duration', 0) % 60}m"
            lines.append(f"Option {i}: {price} | Total Duration: {total_duration}")
            for j, leg in enumerate(legs, 1):
                dep = leg.get("departure_airport", {})
                arr = leg.get("arrival_airport", {})
                lines.append(
                    f"  Leg {j}: {leg.get('airline', 'N/A')} | "
                    f"{dep.get('id', '?')} {dep.get('time', '?')} → "
                    f"{arr.get('id', '?')} {arr.get('time', '?')} | "
                    f"{leg.get('travel_class', 'N/A')}"
                )
        return "\n".join(lines)

    def format_hotels(self, hotels: list) -> str:
        if not hotels:
            return "No hotels found."
        lines = []
        for i, h in enumerate(hotels, 1):
            price = h.get("rate_per_night", {}).get("lowest", "N/A")
            rating = h.get("overall_rating", "N/A")
            amenities = ", ".join(h.get("amenities", [])[:5])
            lines.append(
                f"Hotel {i}: {h.get('name', 'N/A')} | {price}/night | "
                f"Rating: {rating} | Class: {h.get('hotel_class', 'N/A')} | "
                f"Amenities: {amenities}"
            )
        return "\n".join(lines)