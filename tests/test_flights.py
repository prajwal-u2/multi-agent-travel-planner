import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.search import Search
from src.models import FlightRequest

async def main():
    s = Search()

    origin_code = s.search_airport("New York")
    dest_code = s.search_airport("Los Angeles")
    print(f"Origin: {origin_code}")
    print(f"Destination: {dest_code}")

    flights = await s.search_flights(FlightRequest(
        origin=origin_code,
        destination=dest_code,
        outbound_date="2026-06-01",
        return_date="2026-06-07"
    ))

    print(s.format_flights(flights))

asyncio.run(main())
