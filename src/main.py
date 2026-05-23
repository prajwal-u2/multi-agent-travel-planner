from fastapi import FastAPI
from models import ItineraryRequest, FlightRequest, HotelRequest
from search import Search
from agent_crew import TravelCrew
from datetime import datetime
from pathlib import Path
import asyncio
import uvicorn

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Travel Itinerary Planner API", version="0.0.1")
search = Search()
crew = TravelCrew(
    str(BASE_DIR / "config/agents.yaml"),
    str(BASE_DIR / "config/tasks.yaml")
)


@app.post("/plan")
async def plan_trip(request: ItineraryRequest):
    # resolve city names to airport codes
    origin_code = search.search_airport(request.origin_city)
    destination_code = search.search_airport(request.destination_city)

    # fetch flights and hotels in parallel
    flights, hotels = await asyncio.gather(
        search.search_flights(FlightRequest(
            origin=origin_code,
            destination=destination_code,
            outbound_date=request.check_in_date,
            return_date=request.check_out_date
        )),
        search.search_hotels(HotelRequest(
            location=request.destination_city,
            check_in_date=request.check_in_date,
            check_out_date=request.check_out_date
        ))
    )

    flights_data = search.format_flights(flights)
    hotels_data = search.format_hotels(hotels)
    days = (datetime.strptime(request.check_out_date, "%Y-%m-%d") -
            datetime.strptime(request.check_in_date, "%Y-%m-%d")).days

    result = await crew.run(
        flights_data=flights_data,
        hotels_data=hotels_data,
        days=days,
        destination=request.destination_city,
        check_in_date=request.check_in_date,
        check_out_date=request.check_out_date
    )

    print("\n" + "="*60)
    print("FLIGHTS DATA:\n", flights_data)
    print("="*60)
    print("HOTELS DATA:\n", hotels_data)
    print("="*60)
    print("ITINERARY:\n", result)
    print("="*60 + "\n")

    return {"itinerary": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
