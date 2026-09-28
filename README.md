\# DriveSense — Drive For Safety



Driver behavior scoring platform. It analyzes accelerometer, gyroscope, and GPS data from a trip, detects harsh braking, acceleration, cornering, speed-limit violations, and crashes, and produces a 0–100 driving score with an interactive map and AI-generated feedback.



\## Features

\- Butterworth low-pass filtering and SciPy peak detection for harsh driving events

\- Speed-limit violations scored with tiered penalties using the TomTom API

\- Crash detection fusing accelerometer, gyroscope, and GPS speed data

\- Interactive Folium map and Plotly sensor charts

\- Trip history stored in SQLite

\- Driving feedback generated with the Gemini API



\## Run locally

pip install -r requirements.txt

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and add your own keys.

streamlit run app.py

Upload the three CSV files from `data/sample/` to try it.



\## Team

\- Burak Sıkı — Python backend: signal processing, event detection, scoring, TomTom integration

\- Özberk Harman — Streamlit interface

\- Mücahid Eren Karaman — sensor hardware

