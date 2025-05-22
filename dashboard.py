# Instructions:
# 1. Create and activate a virtual environment:
#    python3 -m venv venv
#    source venv/bin/activate   # on macOS/Linux
#    venv\Scripts\activate    # on Windows
# 2. Install dependencies:
#    pip install --upgrade pip
#    pip install streamlit pandas numpy matplotlib lightweight-charts-python
# 3. Save this script as streamlit_app.py
# 4. Run locally:
#    streamlit run streamlit_app.py
# 5. To deploy on Streamlit Cloud:
#    - Push your code to a GitHub repo
#    - In https://streamlit.io/cloud, click "New app" and link your repo
#    - Specify the main file path (e.g. streamlit_app.py) and hit deploy
# 6. Store your Gemini API keys in Streamlit secrets (via Settings → Secrets) or as environment variables.

import streamlit as st
import pandas as pd
import numpy as np
import ast
from datetime import datetime
import matplotlib.pyplot as plt
import tempfile
import streamlit.components.v1 as components
import lightweight_charts as lwc  # lightweight-charts-python wrapper

st.set_page_config(layout="wide", page_title="🚀 TSLA Dashboard", initial_sidebar_state="expanded")

@st.cache_data
def load_data(path):
    df = pd.read_csv(path, parse_dates=["Date"]).sort_values("Date")
    # Safely parse Support/Resistance lists
    for col in ["Support", "Resistance"]:
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    # Calculate bands
    df["Support_min"] = df["Support"].apply(min)
    df["Support_max"] = df["Support"].apply(max)
    df["Resistance_min"] = df["Resistance"].apply(min)
    df["Resistance_max"] = df["Resistance"].apply(max)
    # Price metrics
    df["Daily_Return"] = df["Close"].pct_change() * 100
    df["MA20"] = df["Close"].rolling(window=20).mean()
    return df

# Sidebar controls
st.sidebar.title("Settings")
uploaded_file = st.sidebar.file_uploader("Upload TSLA CSV", type=["csv"])
date_range = st.sidebar.date_input("Date range", [])
show_ma = st.sidebar.checkbox("Show 20-day MA", value=True)
show_bands = st.sidebar.checkbox("Show Support/Resistance Bands", value=True)
show_markers = st.sidebar.checkbox("Show Trade Markers", value=True)

if uploaded_file:
    df = load_data(uploaded_file)

    # Date filter
    if len(date_range) == 2:
        start, end = date_range
        df = df[(df.Date >= pd.to_datetime(start)) & (df.Date <= pd.to_datetime(end))]

    # Layout tabs
    chart_tab, chat_tab, report_tab = st.tabs(["📈 Chart", "🤖 Chatbot", "📊 Report"])

    with chart_tab:
        st.subheader("Interactive Candlestick Chart with lightweight-charts-python")

        # Prepare candlestick data
        candlesticks = df.assign(
            time=df.Date.dt.strftime('%Y-%m-%d'),
            open=df.Open, high=df.High, low=df.Low, close=df.Close
        )[["time","open","high","low","close"]].to_dict(orient='records')

        # Initialize chart
        chart = lwc.LightweightChart(height=600, width=900, layout={"backgroundColor":"#212121","textColor":"#e0e0e0"})
        cs = chart.add_candlestick_series()
        cs.set_data(candlesticks)

        # Moving average
        if show_ma:
            ma20 = df.assign(
                time=df.Date.dt.strftime('%Y-%m-%d'),
                value=df.MA20
            )[["time","value"]].dropna().to_dict(orient='records')
            ls = chart.add_line_series()
            ls.set_data(ma20)

        # Bands
        if show_bands:
            supp = df.assign(time=df.Date.dt.strftime('%Y-%m-%d'), low=df.Support_min, high=df.Support_max)
            rs = df.assign(time=df.Date.dt.strftime('%Y-%m-%d'), low=df.Resistance_min, high=df.Resistance_max)
            as1 = chart.add_area_series({"topColor":"rgba(0,255,0,0.3)","bottomColor":"rgba(0,255,0,0.1)","lineColor":"rgba(0,255,0,1)"})
            as1.set_data(supp.to_dict(orient='records'))
            as2 = chart.add_area_series({"topColor":"rgba(255,0,0,0.3)","bottomColor":"rgba(255,0,0,0.1)","lineColor":"rgba(255,0,0,1)"})
            as2.set_data(rs.to_dict(orient='records'))

        # Markers
        if show_markers:
            markers = []
            for _, row in df.iterrows():
                markers.append({
                    "time": row.Date.strftime('%Y-%m-%d'),
                    "position": 'belowBar' if row.Direction=='LONG' else 'aboveBar' if row.Direction=='SHORT' else 'inBar',
                    "color": 'green' if row.Direction=='LONG' else 'red' if row.Direction=='SHORT' else 'yellow',
                    "shape": 'arrowUp' if row.Direction=='LONG' else 'arrowDown' if row.Direction=='SHORT' else 'circle'
                })
            cs.set_markers(markers)

        # Render in Streamlit
        components.html(chart.html(), height=650)

    with chat_tab:
        st.subheader("TSLA Data Q&A via Gemini")
        if "history" not in st.session_state:
            st.session_state.history = []

        col1, col2 = st.columns([3,1])
        with col1:
            question = st.text_input("Ask a question about the data...", key="q")
        with col2:
            if st.button("Send"):
                prompt = f"You are a helpful assistant. TSLA dataframe summary:\n{df.describe().to_dict()}\nUser: {question}\nAssistant:"
                answer = "[Gemini API response goes here]"
                st.session_state.history.append((question, answer))

        for q, a in st.session_state.history:
            st.markdown(f"**Q:** {q}")
            st.markdown(f"**A:** {a}")

    with report_tab:
        st.subheader("Automated Summary Report")
        bullish_days = (df.Close > df.Open).sum()
        bearish_days = (df.Close < df.Open).sum()
        avg_return = df.Daily_Return.mean()
        st.metric("Bullish days", bullish_days)
        st.metric("Bearish days", bearish_days)
        st.metric("Avg daily return (%)", f"{avg_return:.2f}")

        st.markdown("**Template questions for Chatbot:**")
        st.write([
            "How many bullish days were there in 2023?",
            "What was the highest daily return and on which date?",
            "Show me the top 5 largest support bands.",
            "List dates where resistance band was below the close price."
        ])

        # Bonus: create replay animation
        if st.checkbox("Show replay animation"):
            from matplotlib.animation import FuncAnimation
            fig, ax = plt.subplots()
            def animate(i):
                ax.clear()
                subset = df.iloc[:i]
                ax.plot(subset.Date, subset.Close)
                ax.set_title(f"TSLA Replay: {i} bars")
            anim = FuncAnimation(fig, animate, frames=len(df), interval=50)
            tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            anim.save(tmp.name, writer='ffmpeg')
            st.video(tmp.name)
