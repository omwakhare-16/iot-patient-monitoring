# Cloud-Based Remote Patient Monitoring (Simulated IoT)

IoT mini project (hardware-free). Virtual wearables send **heart rate, SpO2 and body temperature**
over **MQTT** to a cloud-hosted backend, which stores the data, detects anomalies
(**rules + Isolation Forest ML**), raises alerts and shows everything on a **live dashboard**.

```
Simulated wearables --MQTT--> Broker --> Backend (store + detect + alert) --> Database --> Dashboard
   (simulator.py)           (broker.py /      (backend.py)                  (SQLite)    (dashboard.py)
                             Mosquitto)
```

## 1. Run it on your laptop (no hardware, no accounts)

Requires Python 3.9+.

```bash
pip install -r requirements.txt
python run_all.py
```

Open **http://localhost:8501**. Stop with `Ctrl+C`.
(If `python` doesn't work, use `python3`. On Windows: `py run_all.py`.)

You will see 4 patients (green = normal, red = alert). Anomalies (hypoxia, fever,
tachycardia, bradycardia) are injected randomly; alerts appear in the table and in the terminal.
To see more alerts faster: `ANOMALY_PROBABILITY=0.08 python run_all.py`
(Windows PowerShell: `$env:ANOMALY_PROBABILITY="0.08"; python run_all.py`).

## 2. Deploy it to the cloud (this is your cloud-computing part)

Works on any cloud VM (AWS EC2, Azure VM, Google Compute Engine, Oracle free tier...).

1. Create an Ubuntu VM. In its firewall / security group, allow inbound **TCP 8501** (dashboard)
   and **TCP 22** (SSH). Keep 1883 closed.
2. SSH in and install Docker:
   `curl -fsSL https://get.docker.com | sudo sh`
3. Copy this folder to the VM (`scp -r iot-patient-monitor user@<ip>:~/` or `git clone`).
4. Run:
   ```bash
   cd iot-patient-monitor
   sudo docker compose up -d --build
   ```
5. Open `http://<vm-public-ip>:8501`. Take screenshots of the VM console + dashboard for your report.

Check free-tier limits of your provider before creating resources, and stop/delete the VM afterwards.

## 3. Optional e-mail alerts

Set these environment variables before starting (Gmail needs an *app password*):
`SMTP_HOST=smtp.gmail.com SMTP_USER=you@gmail.com SMTP_PASS=xxxx ALERT_TO=doctor@example.com`
(For Docker, add them under `backend: environment:` in `docker-compose.yml`.)

## 4. Files

| File | Role |
|---|---|
| `simulator.py` | Virtual wearable devices (IoT perception layer) |
| `broker.py` / Mosquitto | MQTT broker (network layer) |
| `backend.py` | Subscriber, database, rule + ML anomaly detection, alerts (cloud processing) |
| `dashboard.py` | Streamlit live dashboard (application layer) |
| `config.py` | Thresholds, number of patients, intervals |
| `run_all.py` | Starts everything locally with one command |
| `Dockerfile`, `docker-compose.yml` | Cloud deployment |

## 5. How detection works

* **Rules:** HR outside 50-110 bpm, SpO2 < 92 %, temperature outside 35.5-38.0 C (edit in `config.py`).
* **ML:** an Isolation Forest trained on normal vitals flags unusual *combinations* of the three
  parameters. In this demo it is trained on synthetic normal data; a real system would use
  historical patient data.
* The ML model often fires *earlier* than the rules, while vitals are still drifting but within normal limits (early warning).
* An alert is raised once when a patient *enters* an abnormal state (not on every reading).

## 6. Viva cheat-sheet

* **Why MQTT?** Lightweight publish/subscribe protocol designed for constrained devices and unreliable networks; low overhead vs HTTP polling.
* **Why cloud?** Central storage, remote access for doctors, scalability, and the backend/dashboard run 24x7 independent of any device.
* **Why Isolation Forest?** Unsupervised: needs only normal data, no labelled disease data; isolates outliers quickly.
* **What is simulated?** The sensors/wearables only. Protocol, broker, backend, storage, ML, alerts, dashboard and deployment are real.
* **Limitations:** synthetic data, not clinically validated, no authentication/TLS on the broker (add both for production). This is a demo, not a medical device.
* **Future work:** real wearables (ESP32 + MAX30102), TLS + auth, managed services (AWS IoT Core, DynamoDB, SNS), per-patient adaptive baselines.
