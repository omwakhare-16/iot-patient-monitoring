"""Cloud-side backend: subscribes to MQTT, stores every reading in a database,
runs anomaly detection (rules + Isolation Forest) and raises alerts."""
import json
import os
import smtplib
import sqlite3
import threading
import time
from email.message import EmailMessage

import numpy as np
import paho.mqtt.client as mqtt
from sklearn.ensemble import IsolationForest

import config

FEATURES = ["heart_rate", "spo2", "temperature"]
db_lock = threading.Lock()


# ---------------------------------------------------------------- database
def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS vitals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT, timestamp TEXT,
        heart_rate REAL, spo2 REAL, temperature REAL,
        rule_alert INTEGER, ml_anomaly INTEGER, ml_score REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT, timestamp TEXT, source TEXT, message TEXT)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vitals_pid ON vitals(patient_id, id)")
    conn.commit()
    return conn


# ------------------------------------------------------------- ML detector
def train_model():
    """Train an Isolation Forest on synthetic *normal* vitals. In a real system
    this would be trained on historical data of healthy readings."""
    rng = np.random.default_rng(42)
    n = 6000
    hr = rng.normal(75, 9, n).clip(52, 105)
    spo2 = rng.normal(97.8, 0.9, n).clip(94, 100)
    temp = rng.normal(36.7, 0.25, n).clip(36.0, 37.6)
    X = np.column_stack([hr, spo2, temp])
    model = IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
    model.fit(X)
    return model


# ------------------------------------------------------------------- rules
def rule_check(r):
    reasons = []
    if r["heart_rate"] > config.HR_HIGH:
        reasons.append(f"High heart rate ({r['heart_rate']} bpm)")
    if r["heart_rate"] < config.HR_LOW:
        reasons.append(f"Low heart rate ({r['heart_rate']} bpm)")
    if r["spo2"] < config.SPO2_LOW:
        reasons.append(f"Low SpO2 ({r['spo2']} %)")
    if r["temperature"] > config.TEMP_HIGH:
        reasons.append(f"Fever ({r['temperature']} C)")
    if r["temperature"] < config.TEMP_LOW:
        reasons.append(f"Low body temperature ({r['temperature']} C)")
    return reasons


# ------------------------------------------------------------- e-mail alert
_last_email = {}


def maybe_email(patient_id, message):
    if not (config.SMTP_HOST and config.ALERT_TO):
        return
    now = time.time()
    if now - _last_email.get(patient_id, 0) < config.EMAIL_COOLDOWN_SEC:
        return
    _last_email[patient_id] = now
    try:
        msg = EmailMessage()
        msg["Subject"] = f"[Patient Monitor] Alert for {patient_id}"
        msg["From"] = config.SMTP_USER or "monitor@localhost"
        msg["To"] = config.ALERT_TO
        msg.set_content(message)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
            s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASS)
            s.send_message(msg)
    except Exception as e:  # never let e-mail problems crash the pipeline
        print(f"[backend] e-mail failed: {e}", flush=True)


# --------------------------------------------------------------------- main
def main():
    conn = init_db()
    model = train_model()
    in_alert = {}  # patient_id -> bool, so we alert on the *start* of an episode
    print("[backend] anomaly model trained", flush=True)

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe(f"{config.TOPIC_PREFIX}/+/vitals", qos=1)
        print(f"[backend] connected, subscribed to {config.TOPIC_PREFIX}/+/vitals", flush=True)

    def on_message(client, userdata, msg):
        try:
            r = json.loads(msg.payload)
            x = np.array([[r[f] for f in FEATURES]])
            ml_anomaly = int(model.predict(x)[0] == -1)
            ml_score = float(model.decision_function(x)[0])
            reasons = rule_check(r)
            rule_alert = int(bool(reasons))
            pid = r["patient_id"]

            with db_lock:
                conn.execute(
                    "INSERT INTO vitals(patient_id,timestamp,heart_rate,spo2,temperature,"
                    "rule_alert,ml_anomaly,ml_score) VALUES(?,?,?,?,?,?,?,?)",
                    (pid, r["timestamp"], r["heart_rate"], r["spo2"], r["temperature"],
                     rule_alert, ml_anomaly, ml_score))
                abnormal = bool(rule_alert or ml_anomaly)
                if abnormal and not in_alert.get(pid, False):
                    source = "RULE+ML" if (rule_alert and ml_anomaly) else ("RULE" if rule_alert else "ML")
                    detail = "; ".join(reasons) if reasons else "Unusual combination of vitals (ML)"
                    message = (f"{pid}: {detail} | HR={r['heart_rate']} "
                               f"SpO2={r['spo2']} Temp={r['temperature']}")
                    conn.execute("INSERT INTO alerts(patient_id,timestamp,source,message) VALUES(?,?,?,?)",
                                 (pid, r["timestamp"], source, message))
                    print(f"[ALERT:{source}] {message}", flush=True)
                    threading.Thread(target=maybe_email, args=(pid, message), daemon=True).start()
                in_alert[pid] = abnormal
                conn.commit()
        except Exception as e:
            print(f"[backend] bad message skipped: {e}", flush=True)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-backend")
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=30)
            break
        except OSError:
            print("[backend] waiting for MQTT broker...", flush=True)
            time.sleep(1)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
