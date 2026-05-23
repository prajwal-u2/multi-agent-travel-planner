from crewai import Agent, Task, LLM, Crew, Process
import asyncio
import json
import re
from functools import cached_property
from dotenv import load_dotenv
from os import getenv
import yaml


class Agents:
    def __init__(self, path):
        self.config_path = path
        load_dotenv()

    @cached_property
    def flash_llm(self):
        return LLM(model="gemini-2.5-flash",
                   api_key=getenv("GOOGLE_API_KEY"))

    @cached_property
    # change to pro - after rate limit resets
    def pro_llm(self):
        return LLM(model="gemini-2.5-flash",
                   api_key=getenv("GOOGLE_API_KEY"))

    def load(self):
        llm_map = {
            "flights_agent": self.flash_llm,
            "hotels_agent": self.flash_llm,
            "itinerary_agent": self.pro_llm,
            "allocation_agent": self.flash_llm,
        }

        with open(self.config_path) as f:
            config = yaml.safe_load(f)["agents"]

        return{
            name: Agent(
                role=cfg["role"],
                goal=cfg["goal"],
                backstory=cfg["backstory"],
                llm=llm_map[name],
                verbose=False
            )
            for name, cfg in config.items()
        }
    

class Tasks:
    def __init__(self, path):
        self.config_path = path

    def load(self, agents: dict, **kwargs) -> dict[str, Task]:
        class _Safe(dict):
            def __missing__(self, key):
                return '{' + key + '}'

        fmt = _Safe(**kwargs)
        with open(self.config_path) as f:
            config = yaml.safe_load(f)["tasks"]

        tasks = {}
        for item in config:
            tasks[item["name"]] = Task(
                description=item["description"].format_map(fmt),
                expected_output=item["expected_output"].format_map(fmt),
                agent=agents[item["assigned_agent"]],
            )
        return tasks


class TravelCrew:
    def __init__(self, agents_config: str, tasks_config: str):
        self.agents_config = agents_config
        self.tasks_config = tasks_config

    def _run_single_crew(self, agent: Agent, task: Task) -> str:
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        return str(crew.kickoff())

    def allocate_days(self, cities: list, total_days: int) -> list:
        agents = Agents(self.agents_config).load()
        task = Tasks(self.tasks_config).load(
            agents,
            cities_list=", ".join(cities),
            total_days=total_days
        )["allocate_days"]
        raw = self._run_single_crew(agents["allocation_agent"], task)

        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                allocation = json.loads(match.group())
                allocated_cities = [e["city"] for e in allocation]
                if set(allocated_cities) == set(cities) and sum(e["days"] for e in allocation) == total_days:
                    return allocation
            except (json.JSONDecodeError, KeyError):
                pass

        # fallback: even split in user-provided order
        days_each = total_days // len(cities)
        remainder = total_days % len(cities)
        return [
            {"city": city, "days": days_each + (1 if i < remainder else 0)}
            for i, city in enumerate(cities)
        ]

    async def run_multi_city(self, flights_data: str, legs: list,
                             hotels_data_per_city: dict, total_days: int) -> str:
        agents = Agents(self.agents_config).load()

        flight_task = Tasks(self.tasks_config).load(
            agents, flights_data=flights_data
        )["analyse_multi_city_flights"]

        hotel_tasks = {
            leg.city: Tasks(self.tasks_config).load(
                agents,
                city=leg.city,
                arrival_date=leg.arrival_date,
                departure_date=leg.departure_date,
                hotels_data=hotels_data_per_city[leg.city]
            )["analyse_hotels_for_city"]
            for leg in legs
        }

        all_coroutines = [
            asyncio.to_thread(self._run_single_crew, agents["flights_agent"], flight_task)
        ] + [
            asyncio.to_thread(self._run_single_crew, agents["hotels_agent"], hotel_tasks[leg.city])
            for leg in legs
        ]

        results = await asyncio.gather(*all_coroutines)
        flights_result = results[0]
        hotel_results = {legs[i].city: results[i + 1] for i in range(len(legs))}

        city_schedule = "\n".join(
            f"{leg.city}: {leg.arrival_date} to {leg.departure_date}"
            for leg in legs
        )
        hotels_text = "\n\n".join(
            f"### {city}\n{text}" for city, text in hotel_results.items()
        )

        itinerary_task = Tasks(self.tasks_config).load(
            agents,
            flights_text=flights_result,
            hotels_text=hotels_text,
            city_schedule=city_schedule,
            total_days=total_days
        )["plan_multi_city_itinerary"]

        return await asyncio.to_thread(
            self._run_single_crew, agents["itinerary_agent"], itinerary_task
        )

    async def run(self, flights_data: str, hotels_data: str, days: int,
                  destination: str, check_in_date: str, check_out_date: str) -> str:

        agents = Agents(self.agents_config).load()
        tasks = Tasks(self.tasks_config).load(
            agents,
            flights_data=flights_data,
            hotels_data=hotels_data,
            flights_text="",     # filled in after parallel run
            hotels_text="",      # filled in after parallel run
            days=days,
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date
        )

        # --- Single Sequential Crew ---
        # single crew runs all three tasks one after another:
        # analyse_flights -> analyse_hotels -> plan_itineraries
        # total time = t_flights + t_hotels + t_itinerary
        #
        # crew = Crew(
        #     agents=list(agents.values()),
        #     tasks=list(tasks.values()),
        #     process=Process.sequential,
        #     verbose=False
        # )
        # result = await asyncio.to_thread(crew.kickoff)
        # return str(result)
        # --------------------------------------------------------------

        # --- Parallel Crew---
        # flights and hotels run simultaneously in separate threads
        # total time = max(t_flights, t_hotels) + t_itinerary
        flights_result, hotels_result = await asyncio.gather(
            asyncio.to_thread(self._run_single_crew, agents["flights_agent"], tasks["analyse_flights"]),
            asyncio.to_thread(self._run_single_crew, agents["hotels_agent"], tasks["analyse_hotels"])
        )

        # feed both results into itinerary task
        itinerary_task = Tasks(self.tasks_config).load(
            agents,
            flights_data="",         # unused placeholders to prevent KeyError
            hotels_data="",
            flights_text=flights_result,
            hotels_text=hotels_result,
            days=days,
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date
        )["plan_itineraries"]

        itinerary_result = await asyncio.to_thread(
            self._run_single_crew, agents["itinerary_agent"], itinerary_task
        )
        return itinerary_result
    
