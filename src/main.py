from fastapi import FastAPI
from models import ItineraryRequest, FlightRequest, HotelRequest, MultiCityRequest, CityLeg
from search import Search
from agent_crew import TravelCrew
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
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


def compute_legs(origin_city: str, start_date: str, allocation: list) -> tuple:
    origin_codes = search.search_airport(origin_city)
    current = datetime.strptime(start_date, "%Y-%m-%d")
    legs = []
    for entry in allocation:
        city, days = entry["city"], entry["days"]
        arrival = current
        departure = current + timedelta(days=days)
        legs.append(CityLeg(
            city=city,
            airport_codes=search.search_airport(city),
            arrival_date=arrival.strftime("%Y-%m-%d"),
            departure_date=departure.strftime("%Y-%m-%d")
        ))
        current = departure
    return origin_codes, legs


@app.post("/plan/multi-city")
async def plan_multi_city_trip(request: MultiCityRequest):
    total_days = (
        datetime.strptime(request.return_date, "%Y-%m-%d") -
        datetime.strptime(request.start_date, "%Y-%m-%d")
    ).days

    # step 1: allocation agent decides order + days per city
    allocation = await asyncio.to_thread(crew.allocate_days, request.cities, total_days)

    # step 2: compute leg dates from allocation
    origin_codes, legs = compute_legs(request.origin_city, request.start_date, allocation)
    return_date = legs[-1].departure_date

    # step 3: flight search + all hotel searches in parallel
    hotel_searches = [
        search.search_hotels(HotelRequest(
            location=leg.city,
            check_in_date=leg.arrival_date,
            check_out_date=leg.departure_date
        ))
        for leg in legs
    ]
    flights, *hotels_per_city = await asyncio.gather(
        search.search_multi_city_flights(legs, origin_codes, return_date),
        *hotel_searches
    )

    flights_data = search.format_multi_city_flights(flights)
    hotels_data_per_city = {
        legs[i].city: search.format_hotels(hotels_per_city[i])
        for i in range(len(legs))
    }

    # step 4: flights agent + N hotel agents + itinerary agent
    result = await crew.run_multi_city(
        flights_data=flights_data,
        legs=legs,
        hotels_data_per_city=hotels_data_per_city,
        total_days=total_days,
    )

    return {"itinerary": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
