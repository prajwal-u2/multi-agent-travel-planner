# Streamlit Frontend Guide — Multi-Agent Travel Planner

## Overview
The frontend is a single-page Streamlit app that talks to the FastAPI backend (`/plan` endpoint).
User fills in trip details → hits a button → sees the AI-generated itinerary.

---

## What to Build (in order)

### 1. Page Config & Title
```python
import streamlit as st
import requests

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide")
st.title("✈️ AI Travel Planner")
st.caption("Powered by Gemini + CrewAI")
```
**Why:** `set_page_config` must be the first Streamlit call. Sets the browser tab title, icon, and layout.

---

### 2. Input Form (Sidebar)
```python
with st.sidebar:
    st.header("Plan Your Trip")
    origin = st.text_input("Origin Airport Code", placeholder="e.g. BOS, JFK, LAX")
    destination = st.text_input("Destination City", placeholder="e.g. Paris, Minneapolis")
    check_in = st.date_input("Check-in Date")
    check_out = st.date_input("Check-out Date")
    submit = st.button("Generate Itinerary", type="primary")
```
**Why:** Sidebar keeps the form separate from the results. `date_input` returns a Python `date`
object — you'll need to convert it to a string (`str(check_in)`) before sending to the API.

---

### 3. Validation Before API Call
```python
if submit:
    if not origin or not destination:
        st.error("Please fill in all fields.")
    elif check_out <= check_in:
        st.error("Check-out date must be after check-in date.")
    else:
        # make the API call
```
**Why:** Catch obvious errors before hitting the backend. Saves quota and gives instant feedback.

---

### 4. API Call with Loading Spinner
```python
    with st.spinner("AI agents are planning your trip..."):
        response = requests.post(
            "http://localhost:8000/plan",
            json={
                "origin": origin.strip().upper(),
                "destination": destination.strip(),
                "check_in_date": str(check_in),
                "check_out_date": str(check_out)
            }
        )
```
**Why:** `st.spinner` shows a loading animation while waiting for the response (~30-60s).
The `requests.post` call is synchronous — Streamlit will block here until the backend responds.

---

### 5. Display Results
```python
    if response.status_code == 200:
        data = response.json()
        st.success("Your itinerary is ready!")
        st.markdown(data["itinerary"])
    else:
        st.error(f"Something went wrong: {response.status_code}")
```
**Why:** `st.markdown` renders the itinerary beautifully since the backend returns markdown
with headings, bullet points, and emojis. Much better than plain text.

---

### 6. Error Handling for Connection Failures
```python
    try:
        response = requests.post(...)
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend. Make sure FastAPI is running on port 8000.")
```
**Why:** If the backend isn't running, `requests` throws a `ConnectionError` — catch it and
show a friendly message instead of a raw Python traceback.

---

### 7. (Optional) Download Button
```python
    st.download_button(
        label="Download Itinerary",
        data=data["itinerary"],
        file_name="itinerary.md",
        mime="text/markdown"
    )
```
**Why:** Lets users save the itinerary as a markdown file. One line of code, nice UX touch.

---

## Full File Structure
```python
# frontend/app.py

import streamlit as st
import requests

# 1. Page config
# 2. Title
# 3. Sidebar form (origin, destination, dates, button)
# 4. On submit: validate → spinner → API call → display results
# 5. Error handling
# 6. (Optional) download button
```

---

## Running
```bash
# Terminal 1 — backend
source .venv/bin/activate
python src/main.py

# Terminal 2 — frontend
source .venv/bin/activate
streamlit run frontend/app.py
```

Backend: http://localhost:8000
Frontend: http://localhost:8501
