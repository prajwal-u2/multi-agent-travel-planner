import streamlit as st
import requests

st.set_page_config(page_title="AI Travel Planner", page_icon='AI', layout="wide")
st.title("AI Travel Planner")
st.caption("CrewAI Agentic AI")

tab1, tab2 = st.tabs(["Single City", "Multi-City"])

with tab1:
    with st.sidebar:
        st.header("Plan Your Trip")
        origin = st.text_input("Origin City", placeholder="New York...")
        destination = st.text_input("Destination City", placeholder="Los Angeles...")
        check_in = st.date_input("Start Date", key="sc_checkin")
        check_out = st.date_input("Return Date", key="sc_checkout")
        submit = st.button("Generate Itinerary", type="primary", key="sc_submit")

    if submit:
        error = False
        if not origin or not destination:
            st.error("Please fill in all fields.")
            error = True
        if origin.strip().lower() == destination.strip().lower():
            st.error("Origin and destination cannot be the same.")
            error = True
        if check_out <= check_in:
            st.error("Return date must be after start date.")
            error = True

        if not error:
            with st.spinner("Planning your trip..."):
                try:
                    response = requests.post(
                        "http://localhost:8000/plan",
                        json={
                            "origin_city": origin.strip(),
                            "destination_city": destination.strip(),
                            "check_in_date": str(check_in),
                            "check_out_date": str(check_out)
                        }
                    )
                except Exception as e:
                    st.error(f"Cannot connect to the backend: {e}")
                    response = None

            if response and response.status_code == 200:
                st.success("Itinerary is Ready")
                st.markdown(response.json()["itinerary"])
            elif response:
                st.error(f"Something went wrong: {response.status_code}")

with tab2:
    with st.sidebar:
        st.header("Plan Multi-City Trip")
        mc_origin = st.text_input("Departing From", placeholder="Boston...", key="mc_origin")
        mc_cities = st.text_input("Cities to Visit", placeholder="Paris, Rome, Barcelona...", key="mc_cities")
        mc_start = st.date_input("Departure Date", key="mc_start")
        mc_return = st.date_input("Return Date", key="mc_return")
        mc_submit = st.button("Generate Multi-City Itinerary", type="primary", key="mc_submit")

    if mc_submit:
        cities = [c.strip() for c in mc_cities.split(",") if c.strip()]
        error = False

        if not mc_origin:
            st.error("Please enter your departure city.")
            error = True
        if len(cities) < 2:
            st.error("Please enter at least 2 cities to visit.")
            error = True
        if mc_return <= mc_start:
            st.error("Return date must be after departure date.")
            error = True
        if not error and (mc_return - mc_start).days < len(cities):
            st.error(f"Trip is too short — need at least {len(cities)} days for {len(cities)} cities.")
            error = True

        if not error:
            route = f"{mc_origin.strip()} → {' → '.join(cities)} → {mc_origin.strip()}"
            st.caption(f"Route: {route}")

            with st.spinner("Planning your multi-city trip..."):
                try:
                    response = requests.post(
                        "http://localhost:8000/plan/multi-city",
                        json={
                            "origin_city": mc_origin.strip(),
                            "cities": cities,
                            "start_date": str(mc_start),
                            "return_date": str(mc_return)
                        }
                    )
                except Exception as e:
                    st.error(f"Cannot connect to the backend: {e}")
                    response = None

            if response and response.status_code == 200:
                st.success("Multi-City Itinerary Ready!")
                st.markdown(response.json()["itinerary"])
            elif response:
                st.error(f"Something went wrong: {response.status_code} — {response.text}")
