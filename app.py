import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import requests
import re
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from streamlit_autorefresh import st_autorefresh

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="VOYAGER-1 MISSION CONTROL", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #000814; color: #00FF41; }
    .user-name { text-align: right; color: #00FF41; font-family: 'Courier New', monospace; 
                 font-size: 1.3rem; font-weight: bold; margin-top: -0px; }
    [data-testid="stMetric"] { border: 2px solid #00FF41; border-radius: 12px; padding: 18px !important; 
                               background-color: #001d3d; box-shadow: 0 0 20px #00FF41; }
    [data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', monospace; font-size: 1.5rem; }
    div.stPlotlyChart { border: 2px solid #00FF41; border-radius: 12px; box-shadow: 0 0 20px #00FF41; 
                        padding: 12px; background-color: #001d3d; }
    h1, h2, h3 { color: #00FF41 !important; letter-spacing: 1px; }
    </style>
    """, unsafe_allow_html=True)

# ====================== JPL API (FINAL FIXED REGEX) ======================
@st.cache_data(ttl=180)
def fetch_jpl_telemetry():
    try:
        now = datetime.utcnow()
        start = now.strftime("%Y-%m-%d")
        end = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        url = f"https://ssd.jpl.nasa.gov/api/horizons.api?format=text&COMMAND='Voyager 1'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{start}'&STOP_TIME='{end}'&STEP_SIZE='1d'&QUANTITIES='20,23'"

        resp = requests.get(url, timeout=25)
        resp.raise_for_status()
        text = resp.text

        # 2026-இல் வேலை செய்யும் சரியான regex
        match = re.search(r'(\d{4}-[A-Za-z]+-\d{2}\s+\d{2}:\d{2})\s+([\d\.]+)\s+([-+]?\d+\.\d+)', text)

        if match:
            au = float(match.group(2))
            speed = abs(float(match.group(3)))
            light_hours = (au * 149597870.7) / 299792.458 / 3600

            return {
                "au": round(au, 3),
                "speed": round(speed, 3),
                "light": round(light_hours, 2),
                "status": "✅ JPL HORIZONS LIVE"
            }
        else:
            st.error("Regex match failed. Raw output (last 800 chars):")
            st.code(text[-800:], language="text")
            return None

    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

# ====================== NASA NEWS ======================
@st.cache_data(ttl=3600)
def fetch_nasa_news():
    try:
        r = requests.get("https://science.nasa.gov/blogs/voyager/feed/", timeout=15)
        root = ET.fromstring(r.content)
        return [item.find('title').text for item in root.findall('./channel/item')[:5] if item.find('title') is not None]
    except:
        return ["தற்போது Voyager செய்திகள் கிடைக்கவில்லை."]

# ====================== MAIN ======================
data = fetch_jpl_telemetry()
news_items = fetch_nasa_news()

# தமிழ் Title
st.markdown("<h1>🛰️ VOYAGER-1 நிகழ்நேரக் கண்காணிப்பு</h1>", unsafe_allow_html=True)
st.markdown('<div class="user-name">Ajey Adithya</div>', unsafe_allow_html=True)

if data:
    st.success(data["status"])

    c1, c2, c3 = st.columns(3)
    c1.metric("விண்கலத்தின் வேகம் (km/s)", f"{data['speed']}")
    c2.metric("பூமியிலிருந்து தூரம் (AU)", f"{data['au']}")
    c3.metric("சிக்னல் தாமதம் (hours)", f"{data['light']}")

    # Gauges
    g1, g2 = st.columns(2)
    with g1:
        fig1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=data['au'],
            title={"text": "பூமியிலிருந்து தூரம் (AU)"},
            gauge={"axis": {"range": [160, 190]}, "bar": {"color": "#00FF41"}}
        ))
        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "#00FF41"}, height=370)
        st.plotly_chart(fig1, use_container_width=True)

    with g2:
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=data['speed'],
            title={"text": "விண்கலத்தின் வேகம் (km/s)"},
            gauge={"axis": {"range": [0, 4]}, "bar": {"color": "#00FF41"}}
        ))
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "#00FF41"}, height=370)
        st.plotly_chart(fig2, use_container_width=True)

    # Projection
    st.subheader("📈 12 மாத தூர கணிப்பு")
    dates = pd.date_range(datetime.now(), periods=13, freq='ME')
    proj = [data['au'] + i*0.029 for i in range(13)]

    df = pd.DataFrame({"தேதி": dates, "AU": proj})
    fig_p = px.line(df, x="தேதி", y="AU", markers=True, template="plotly_dark")
    fig_p.update_traces(line_color="#00FF41")
    st.plotly_chart(fig_p, use_container_width=True)

else:
    st.error("❌ JPL Horizons இலிருந்து தரவு பெற முடியவில்லை. இணைய இணைப்பை சரிபார்க்கவும்.")

# NASA Eyes
st.subheader("🌌 NASA EYES: விண்கலத்தின் தற்போதைய பயணப்பாதை")
st.components.v1.iframe("https://eyes.nasa.gov/apps/solar-system/#/sc_voyager_1", height=680)

st_autorefresh(interval=90000, key="voyager_tamil")

# News
st.subheader("📰 சமீபத்திய Voyager செய்திகள்")
for item in news_items:
    st.info(item)
