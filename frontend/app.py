import streamlit as st
import requests

st.set_page_config(page_title="AI Travel Planner", page_icon='AI', layout="wide")
st.title("AI Travel Planner")
st.caption("CrewAI Agentic AI")

with st.sidebar:
    mode = st.radio("Trip Type", ["Single City", "Multi-City"], horizontal=True)
    st.divider()

    st.header("Plan Your Trip")
    origin = st.text_input("Origin City", placeholder="New York...")

    if mode == "Single City":
        destination = st.text_input("Destination City", placeholder="Los Angeles...")
    else:
        mc_cities = st.text_input("Cities to Visit", placeholder="Paris, Rome, Barcelona...")

    check_in = st.date_input("Start Date")
    check_out = st.date_input("Return Date")
    submit = st.button("Generate Itinerary", type="primary")

if mode == "Single City" and submit:
    error = False
    if not origin or not destination:
        st.error("Please fill in all fields.")
        error = True
    elif origin.strip().lower() == destination.strip().lower():
        st.error("Origin and destination cannot be the same.")
        error = True
    elif check_out <= check_in:
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

elif mode == "Multi-City" and submit:
    cities = [c.strip() for c in mc_cities.split(",") if c.strip()]
    error = False

    if not origin:
        st.error("Please enter your origin city.")
        error = True
    elif len(cities) < 2:
        st.error("Please enter at least 2 cities to visit.")
        error = True
    elif check_out <= check_in:
        st.error("Return date must be after departure date.")
        error = True
    elif (check_out - check_in).days < len(cities):
        st.error(f"Trip is too short — need at least {len(cities)} days for {len(cities)} cities.")
        error = True

    if not error:
        route = f"{origin.strip()} → {' → '.join(cities)} → {origin.strip()}"
        st.caption(f"Route: {route}")

        with st.spinner("Planning your multi-city trip..."):
            try:
                response = requests.post(
                    "http://localhost:8000/plan/multi-city",
                    json={
                        "origin_city": origin.strip(),
                        "cities": cities,
                        "start_date": str(check_in),
                        "return_date": str(check_out)
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
