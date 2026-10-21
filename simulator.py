"""Simulated wearable devices. One virtual patient = one 'device' that publishes
heart rate, SpO2 and body temperature over MQTT every second."""
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

import config

PATIENTS = [f"P{str(i + 1).zfill(2)}" for i in range(config.NUM_PATIENTS)]

# Each episode shifts the vitals in a medically-plausible way for ~15-30 ticks.
EPISODES = {
    "hypoxia":    {"spo2": -9.0, "hr": +25.0, "temp": 0.0},
    "fever":      {"spo2": -1.0, "hr": +20.0, "temp": +2.2},
    "tachycardia": {"spo2": 0.0, "hr": +55.0, "temp": 0.0},
    "bradycardia": {"spo2": -1.0, "hr": -28.0, "temp": -0.3},
}


class VirtualPatient:
    def __init__(self, pid):
        self.pid = pid
        self.base_hr = random.uniform(65, 85)
        self.base_spo2 = random.uniform(96.5, 99)
        self.base_temp = random.uniform(36.4, 37.0)
        self.episode = None
        self.ticks_left = 0
        self.progress = 0.0

    def step(self):
        if self.episode is None and random.random() < config.ANOMALY_PROBABILITY:
            self.episode = random.choice(list(EPISODES))
            self.ticks_left = random.randint(15, 30)
            self.progress = 0.0
        shift = {"hr": 0.0, "spo2": 0.0, "temp": 0.0}
        if self.episode:
            self.progress = min(1.0, self.progress + 0.2)     # ramp up smoothly
            for k, v in EPISODES[self.episode].items():
                shift[k] = v * self.progress
            self.ticks_left -= 1
            if self.ticks_left <= 0:
                self.episode = None
        hr = self.base_hr + shift["hr"] + random.gauss(0, 1.5)
        spo2 = min(100.0, self.base_spo2 + shift["spo2"] + random.gauss(0, 0.3))
        temp = self.base_temp + shift["temp"] + random.gauss(0, 0.05)
        return {
            "patient_id": self.pid,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "heart_rate": round(hr, 1),
            "spo2": round(spo2, 1),
            "temperature": round(temp, 2),
        }


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="wearable-simulator")
    while True:
        try:
            client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=30)
            break
        except OSError:
            print("[simulator] waiting for MQTT broker...", flush=True)
            time.sleep(1)
    client.loop_start()
    patients = [VirtualPatient(p) for p in PATIENTS]
    print(f"[simulator] publishing for {len(patients)} virtual patients "
          f"to {config.MQTT_HOST}:{config.MQTT_PORT}", flush=True)
    try:
        while True:
            for p in patients:
                reading = p.step()
                topic = f"{config.TOPIC_PREFIX}/{p.pid}/vitals"
                client.publish(topic, json.dumps(reading), qos=1)
            time.sleep(config.PUBLISH_INTERVAL_SEC)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
