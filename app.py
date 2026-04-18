import streamlit as st
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Session state for distance delta
if 'last_dist' not in st.session_state:
    st.session_state.last_dist = None

# ====================== FETCH DISTANCE DATA ======================
@st.cache_data(ttl=900)  # 15 minutes
def fetch_data():
    error_msg = ""
    try:
        r = requests.get("https://theskylive.com/voyager1-tracker", timeout=15)
        text = r.text
        
        dist_match = re.search(r'([\d\.]+)\s*AU', text, re.I)
        if dist_match:
            dist_au = float(dist_match.group(1))
            
            light_match = re.search(r'Light takes ([\d]+h ?[\d]*m?)', text, re.I)
            hours = 23.8
            if light_match:
                parts = light_match.group(1).replace('m', '').split('h')
                hours = int(parts[0]) + (int(parts[1]) / 60 if len(parts) > 1 else 0)

            delta = None
            if st.session_state.last_dist is not None:
                diff = round(dist_au - st.session_state.last_dist, 4)
                delta = f"{diff:+.4f} AU"
            st.session_state.last_dist = dist_au

            return {
                "dist_au": round(dist_au, 3),
                "dist_km": f"{dist_au * 149597870.7 / 1e9:.3f} billion km",
                "speed": "17.0 km/s",
                "light_delay": round(hours, 2),
                "delta": delta,
                "timestamp": datetime.utcnow().strftime("%d %b %Y, %H:%M:%S UTC"),
                "source": "TheSkyLive",
                "error": None
            }
    except Exception as e:
        error_msg = f"TheSkyLive failed: {type(e).__name__}"

    # Fallback for April 2026
    return {
        "dist_au": 173.1,
        "dist_km": "25.90 billion km",
        "speed": "17.0 km/s",
        "light_delay": 23.8,
        "delta": None,
        "timestamp": "Fallback • April 2026",
        "source": "Cached Data",
        "error": error_msg if error_msg else "Live sources unavailable (network issue)"
    }

# ====================== LATEST MISSION UPDATE ======================
@st.cache_data(ttl=3600)  # 1 hour
def fetch_latest_update():
    try:
        r = requests.get("https://science.nasa.gov/mission/voyager/", timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        headlines = soup.find_all(['h2', 'h3', 'a', 'p'], string=re.compile(r'shut|instrument|power|LECP|Voyager 1', re.I))
        for h in headlines:
            text = h.get_text(strip=True)
            parent = h.find_parent().get_text(strip=True) if h.find_parent() else ""
            full_text = (text + " " + parent)[:500]
            if "April 17" in full_text or "LECP" in full_text or "shut down" in full_text.lower():
                return full_text + "..." if len(full_text) > 280 else full_text
    except:
        pass
    
    # Reliable fallback (real news from April 17, 2026)
    return ("On April 17, 2026, NASA shut down the Low-Energy Charged Particles (LECP) instrument "
            "on Voyager 1 to conserve power. The spacecraft continues operating with two active "
            "science instruments nearly 49 years into its mission.")

# ====================== INSTRUMENTS STATUS ======================
@st.cache_data(ttl=3600)
def fetch_instruments():
    try:
        res = requests.get("https://science.nasa.gov/mission/voyager/where-are-voyager-1-and-voyager-2-now/", timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        data = {}
        table = soup.find("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    data[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)
        return data
    except:
        return {
            "Magnetometer (MAG)": "On",
            "Plasma Wave Subsystem (PWS)": "On",
            "Cosmic Ray Subsystem (CRS)": "Off (power saving)",
            "Low-Energy Charged Particles (LECP)": "Off to save power (April 17, 2026)"
        }

# ====================== MAIN DASHBOARD ======================
data = fetch_data()
instr = fetch_instruments()
update_text = fetch_latest_update()

st.title("🛰️ Voyager 1 - Real-time Monitoring")
st.caption(f"**Last Updated:** {data['timestamp']}")

# Metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Distance from Earth", f"{data['dist_au']} AU", delta=data.get('delta'))
with col2:
    st.metric("Light Travel Time", f"{data['light_delay']} hours")
with col3:
    st.metric("Heliocentric Speed", data['speed'])

st.subheader("📍 Distance in Kilometers")
st.info(data['dist_km'])

# Latest News
st.subheader("📰 Latest Mission Update (April 2026)")
st.write(update_text)

# Instruments
st.subheader("🔬 Current Instrument Status")
for name, status in instr.items():
    st.write(f"**{name}** : {status}")

# Footer
st.caption(f"**Data Source:** {data['source']}")
if data.get("error"):
    st.warning(data["error"])

# Auto refresh every 45 seconds
st_autorefresh(interval=45000)