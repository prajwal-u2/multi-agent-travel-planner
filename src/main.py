from fastapi import FastAPI
from models import ItineraryRequest, FlightRequest, HotelRequest
from search import Search
from agent_crew import TravelCrew
from datetime import datetime
import asyncio
import uvicorn

app = FastAPI(title="Travel Itinerary Planner API", version="0.0.1")
search = Search()
crew = TravelCrew("config/agents.yaml", "config/tasks.yaml")


@app.post("/plan")
async def plan_trip(request: ItineraryRequest):
    flights, hotels = await asyncio.gather(
        search.search_flights(FlightRequest(
            origin=request.origin,
            destination=request.destination,
            outbound_date=request.check_in_date,
            return_date=request.check_out_date
        )),
        search.search_hotels(HotelRequest(
            location=request.destination,
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
        destination=request.destination,
        check_in_date=request.check_in_date,
        check_out_date=request.check_out_date
    )

    return {"itinerary": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
