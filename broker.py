"""Tiny pure-Python MQTT broker so the project runs with zero installs.
(On a cloud VM you can use Mosquitto instead - see docker-compose.yml.)"""
import asyncio
import logging
import os

from amqtt.broker import Broker

PORT = int(os.getenv("MQTT_PORT", "1883"))
BIND = os.getenv("BROKER_BIND", "127.0.0.1")

CONFIG = {
    "listeners": {"default": {"type": "tcp", "bind": f"{BIND}:{PORT}"}},
    "sys_interval": 0,
    "plugins": {
        "amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True},
    },
}


async def main():
    logging.getLogger("amqtt").setLevel(logging.ERROR)
    broker = Broker(CONFIG)
    await broker.start()
    print(f"[broker] MQTT broker listening on {BIND}:{PORT}", flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
