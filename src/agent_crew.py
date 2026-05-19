from crewai import Agent, Task, LLM, Crew, Process
import asyncio
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
        return LLM(model="gemini/gemini-2.0-flash",
                   provider="google",
                   api_key=getenv("GOOGLE_API_KEY"))
    
    @cached_property
    def pro_llm(self):
        return LLM(model="gemini/gemini-1.5-pro",
                   provider="google",
                   api_key=getenv("GOOGLE_API_KEY"))

    def load(self):
        llm_map = {
            "flights_agent": self.flash_llm,
            "hotels_agent": self.flash_llm,
            "itinerary_agent": self.pro_llm
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
        with open(self.config_path) as f:
            config = yaml.safe_load(f)["tasks"]

        tasks = {}
        for item in config:
            tasks[item["name"]] = Task(
                description=item["description"].format(**kwargs),
                expected_output=item["expected_output"].format(**kwargs),
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

    async def run(self, flights_data: str, hotels_data: str, days: int,
                  destination: str, check_in_date: str, check_out_date: str) -> str:

        agents = Agents(self.agents_config).load()
        tasks = Tasks(self.tasks_config).load(
            agents,
            flights_data=flights_data,
            hotels_data=hotels_data,
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
        # ----------------------------------------------

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
            flights_data="",         # unused placeholders — prevents KeyError on other tasks
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
    
