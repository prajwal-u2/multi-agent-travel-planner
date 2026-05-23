import streamlit as st
import requests
import time

st.set_page_config(page_title="AI Travel Planner", page_icon='AI', layout="wide")
st.title("AI Travel Planner")
st.caption("CrewAI Agentic AI")

with st.sidebar:
    st.header('Plan Your Trip')
    origin = st.text_input("Origin City", placeholder="New York...")
    destination = st.text_input("Destination City", placeholder="Los Angeles...")
    check_in = st.date_input("Start Date")
    check_out = st.date_input("Return Date")
    submit = st.button("Generate Itinerary", type="primary")

error_present = False
if submit:
    if not origin or not destination:
        st.error("Please fill in all fields.")
        error_present = True
    if origin == destination:
        st.error("Origin and destination cannot be same")
        error_present = True
    if check_out <= check_in:
        st.error("Check-out date must be after check-in date.")
        error_present = True

    if not error_present:
        with st.spinner("Trip planning in progress"):
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
                # response = {
                #     "status_code": 200,
                #     "itinerary": "# Test Itinerary\n\nThis is a **dummy** itinerary."
                # }
            except Exception as e:
                st.error(f"Cannot connect to the backend: {e}")
                response = None

        if response and response.status_code == 200:
            data = response.json()
            st.success("Itinerary is Ready")
            st.markdown(data["itinerary"])
        elif response:
            st.error(f"Something went wrong: {response.status_code}")
        

    

            

    


