"""Live dashboard (Streamlit). Reads the database the backend writes to."""
import sqlite3
import time

import pandas as pd
import streamlit as st

import config

st.set_page_config(page_title="Remote Patient Monitoring", page_icon="🩺", layout="wide")


@st.cache_resource
def get_conn():
    return sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True, check_same_thread=False)


def q(sql, params=()):
    try:
        return pd.read_sql_query(sql, get_conn(), params=params)
    except Exception:
        return pd.DataFrame()


st.title("🩺 Cloud-Based Remote Patient Monitoring (IoT)")
st.caption("Simulated wearables → MQTT → cloud backend → database → anomaly detection → dashboard")

with st.sidebar:
    st.header("Controls")
    refresh = st.slider("Refresh every (sec)", 1, 10, 2)
    window = st.slider("Chart window (readings)", 30, 300, 120, step=10)
    st.markdown("**Thresholds**")
    st.write(f"Heart rate: {config.HR_LOW}–{config.HR_HIGH} bpm")
    st.write(f"SpO₂: ≥ {config.SPO2_LOW} %")
    st.write(f"Temperature: {config.TEMP_LOW}–{config.TEMP_HIGH} °C")

latest = q("""SELECT v.* FROM vitals v
              JOIN (SELECT patient_id, MAX(id) mid FROM vitals GROUP BY patient_id) m
              ON v.id = m.mid ORDER BY v.patient_id""")

if latest.empty:
    st.info("Waiting for data... make sure the simulator and backend are running.")
else:
    st.subheader("Current status")
    cols = st.columns(len(latest))
    for col, (_, row) in zip(cols, latest.iterrows()):
        abnormal = bool(row.rule_alert or row.ml_anomaly)
        with col:
            st.markdown(f"### {'🔴' if abnormal else '🟢'} {row.patient_id}")
            st.metric("Heart rate (bpm)", f"{row.heart_rate:.0f}")
            st.metric("SpO₂ (%)", f"{row.spo2:.1f}")
            st.metric("Temperature (°C)", f"{row.temperature:.1f}")
            st.caption("ALERT" if abnormal else "Normal")

    st.subheader("Live vitals")
    patient = st.selectbox("Patient", list(latest.patient_id))
    hist = q("SELECT * FROM vitals WHERE patient_id=? ORDER BY id DESC LIMIT ?", (patient, window))
    if not hist.empty:
        hist = hist.iloc[::-1].reset_index(drop=True)
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Heart rate (bpm)**"); c1.line_chart(hist["heart_rate"])
        c2.markdown("**SpO₂ (%)**"); c2.line_chart(hist["spo2"])
        c3.markdown("**Temperature (°C)**"); c3.line_chart(hist["temperature"])

    st.subheader("Recent alerts")
    alerts = q("SELECT timestamp, patient_id, source, message FROM alerts ORDER BY id DESC LIMIT 15")
    if alerts.empty:
        st.success("No alerts yet.")
    else:
        st.dataframe(alerts, use_container_width=True, hide_index=True)

    tot = q("SELECT COUNT(*) n FROM vitals")["n"].iloc[0] if not q("SELECT COUNT(*) n FROM vitals").empty else 0
    st.caption(f"Total readings stored: {tot}")

time.sleep(refresh)
st.rerun()
