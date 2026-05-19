import asyncio
from serpapi import GoogleSearch
from fastapi import HTTPException
import logging
from models import FlightRequest, HotelRequest

from os import getenv

# Initialize Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Search:
    def _init__(self):
        pass

    async def run_search(self, params):
        """function to run SerpAPI asynchronosuly"""
        try:
            return await asyncio.to_thread(lambda: GoogleSearch(params).get_dict())
        except Exception as e:
            logger.exception(f"SerpAPI Search Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search Error: {str(e)}")
    
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
        flights = search_results.get("flights")
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