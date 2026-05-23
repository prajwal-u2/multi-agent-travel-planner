import asyncio
import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from src.search import Search
from src.models import CityLeg

search = Search()

# Simulating: New York → Minneapolis → Chicago → New York
# Minneapolis: 2026-05-23 to 2026-05-24
# Chicago:     2026-05-24 to 2026-05-27

legs = [
    CityLeg(city="Minneapolis", airport_codes="MSP", arrival_date="2026-05-23", departure_date="2026-05-24"),
    CityLeg(city="Chicago",     airport_codes="ORD", arrival_date="2026-05-24", departure_date="2026-05-27"),
]
origin_codes = "JFK,LGA"
return_date  = "2026-05-27"

async def main():
    print("\n" + "="*60)
    print("TEST 1: Per-leg one-way searches (new approach)")
    print("="*60)
    leg_results = await search.search_multi_city_flights(legs, origin_codes, return_date)
    for label, flights in leg_results:
        print(f"\n--- {label} ---")
        print(f"  Flights returned: {len(flights)}")
        if flights:
            f = flights[0]
            segs = f.get("flights", [])
            print(f"  Best option: ${f.get('price')} | {f.get('total_duration')} min | {len(segs)} segment(s)")
            for s in segs:
                dep = s.get("departure_airport", {})
                arr = s.get("arrival_airport", {})
                print(f"    {s.get('airline')} {dep.get('id')} {dep.get('time')} → {arr.get('id')} {arr.get('time')}")

    print("\n" + "="*60)
    print("Formatted output (what agents see):")
    print("="*60)
    print(search.format_multi_city_flights(leg_results))

asyncio.run(main())
