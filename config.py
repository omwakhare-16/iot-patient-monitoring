"""Shared configuration. Override any value with an environment variable."""
import os

# --- MQTT broker ---------------------------------------------------------
# Default: a broker started locally by run_all.py (no install needed).
# On a cloud VM / docker-compose, set MQTT_HOST to the broker's address.
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_PREFIX = os.getenv("TOPIC_PREFIX", "hospital/patients")   # hospital/patients/<id>/vitals

# --- Simulator -----------------------------------------------------------
NUM_PATIENTS = int(os.getenv("NUM_PATIENTS", "4"))
PUBLISH_INTERVAL_SEC = float(os.getenv("PUBLISH_INTERVAL_SEC", "1.0"))
ANOMALY_PROBABILITY = float(os.getenv("ANOMALY_PROBABILITY", "0.02"))  # chance per patient per tick to start an episode

# --- Storage -------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "data/vitals.db")

# --- Rule thresholds (the three monitored parameters) ---------------------
HR_LOW, HR_HIGH = 50, 110          # heart rate, bpm
SPO2_LOW = 92                      # oxygen saturation, %
TEMP_LOW, TEMP_HIGH = 35.5, 38.0   # body temperature, deg C

# --- Optional e-mail alerts (leave blank to disable) ---------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_TO = os.getenv("ALERT_TO", "")
EMAIL_COOLDOWN_SEC = int(os.getenv("EMAIL_COOLDOWN_SEC", "300"))
